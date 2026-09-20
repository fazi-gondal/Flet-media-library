package com.fazigondal.flet_media_library

import android.content.ContentUris
import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import android.util.Log
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Minimal native fallback for capabilities photo_manager 3.12.0 lacks:
 *
 *  - saveAudio   : MediaStore insert of audio files
 *  - renameAsset : DISPLAY_NAME update by MediaStore _id
 *  - moveAsset   : RELATIVE_PATH update by MediaStore _id (Android 10 only;
 *                  Android 11+ goes through photo_manager's createWriteRequest)
 *
 * Everything else is handled by photo_manager in Dart.
 */
class FletMediaLibraryPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {

    companion object {
        private const val TAG = "FletMediaLibrary"
        private const val CHANNEL = "flet_media_library/native_fallback"

        /** Default album folder for saved audio when none is provided. */
        private const val DEFAULT_AUDIO_DIR = "Music/FletMediaLibrary"
    }

    private var context: Context? = null
    private var channel: MethodChannel? = null

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, CHANNEL)
        channel?.setMethodCallHandler(this)
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel?.setMethodCallHandler(null)
        channel = null
        context = null
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        try {
            when (call.method) {
                "saveAudio" -> saveAudio(call, result)
                "renameAsset" -> renameAsset(call, result)
                "moveAsset" -> moveAsset(call, result)
                else -> result.notImplemented()
            }
        } catch (e: Exception) {
            Log.e(TAG, "${call.method}: ${e.message}", e)
            result.error("PLATFORM_ERROR", e.message, null)
        }
    }

    // ─────────────────────────────────── saveAudio ──────────────────────────────

    private fun saveAudio(call: MethodCall, result: MethodChannel.Result) {
        val ctx = context ?: run { result.error("NO_CONTEXT", "no context", null); return }
        val filePath = call.argument<String>("filePath")
        if (filePath.isNullOrBlank()) {
            result.error("INVALID_ARGUMENT", "filePath is required", null); return
        }
        val source = java.io.File(filePath)
        if (!source.isFile) {
            result.error("FILE_NOT_FOUND", "file not found: $filePath", null); return
        }
        val displayName = call.argument<String>("filename")?.trim()?.takeIf { it.isNotBlank() }
            ?: source.name
        val relativePath = call.argument<String>("relativePath")?.trim()?.trim('/')
            ?.takeIf { it.isNotBlank() } ?: DEFAULT_AUDIO_DIR

        val collection = MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        val resolver = ctx.contentResolver
        var uri: Uri? = null
        try {
            val values = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
                put(MediaStore.MediaColumns.MIME_TYPE, guessMime(displayName))
                put(MediaStore.MediaColumns.DATE_ADDED, System.currentTimeMillis() / 1000)
                put(MediaStore.MediaColumns.DATE_MODIFIED, source.lastModified() / 1000)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(MediaStore.MediaColumns.RELATIVE_PATH, "$relativePath/")
                    put(MediaStore.Audio.Media.IS_PENDING, 1)
                }
            }
            uri = resolver.insert(collection, values)
                ?: throw IllegalStateException("MediaStore insert returned null")
            resolver.openOutputStream(uri)?.use { out ->
                source.inputStream().use { it.copyTo(out) }
            } ?: throw IllegalStateException("Unable to open MediaStore output stream")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                resolver.update(uri, ContentValues().apply {
                    put(MediaStore.Audio.Media.IS_PENDING, 0)
                }, null, null)
            }
            result.success(mapOf("id" to ContentUris.parseId(uri).toString()))
        } catch (e: Exception) {
            Log.e(TAG, "saveAudio: ${e.message}", e)
            uri?.let { runCatching { resolver.delete(it, null, null) } }
            result.error("SAVE_ERROR", e.message, null)
        }
    }

    // ────────────────────────────── rename / move ───────────────────────────────

    private fun renameAsset(call: MethodCall, result: MethodChannel.Result) {
        val assetId = call.argument<String>("assetId")?.toLongOrNull()
        val newName = call.argument<String>("newName")?.trim()?.takeIf { it.isNotBlank() }
        if (assetId == null || newName == null) {
            result.error("INVALID_ARGUMENT", "assetId and newName are required", null); return
        }
        val updated = updateAcrossCollections(assetId) { _, values ->
            values.put(MediaStore.MediaColumns.DISPLAY_NAME, newName)
        }
        result.success(updated)
    }

    private fun moveAsset(call: MethodCall, result: MethodChannel.Result) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            result.error("UNSUPPORTED", "moveAsset requires Android 10+ (API 29)", null); return
        }
        val assetId = call.argument<String>("assetId")?.toLongOrNull()
        val targetRelativePath = call.argument<String>("targetRelativePath")
            ?.trim()?.trim('/')?.takeIf { it.isNotBlank() }
        if (assetId == null || targetRelativePath == null) {
            result.error(
                "INVALID_ARGUMENT",
                "assetId and targetRelativePath are required", null,
            ); return
        }
        val updated = updateAcrossCollections(assetId) { _, values ->
            values.put(MediaStore.MediaColumns.RELATIVE_PATH, "$targetRelativePath/")
        }
        result.success(updated)
    }

    /**
     * Runs [fill] against each MediaStore collection until one reports an
     * updated row. photo_manager exposes bare MediaStore ids without the
     * owning collection, so the collection must be discovered here.
     */
    private inline fun updateAcrossCollections(
        assetId: Long,
        fill: (Uri, ContentValues) -> Unit,
    ): Boolean {
        val ctx = context ?: return false
        val collections = listOf(
            MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
            MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
            MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
        )
        for (collection in collections) {
            val uri = ContentUris.withAppendedId(collection, assetId)
            val values = ContentValues()
            fill(uri, values)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                values.put(MediaStore.MediaColumns.IS_PENDING, 1)
            }
            val rows = try {
                ctx.contentResolver.update(uri, values, null, null)
            } catch (_: Exception) {
                continue
            }
            if (rows > 0) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    runCatching {
                        ctx.contentResolver.update(
                            uri,
                            ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) },
                            null, null,
                        )
                    }
                }
                return true
            }
        }
        return false
    }

    private fun guessMime(name: String): String {
        val ext = name.substringAfterLast('.', "").lowercase()
        return mapOf(
            "mp3" to "audio/mpeg",
            "m4a" to "audio/mp4",
            "aac" to "audio/aac",
            "flac" to "audio/flac",
            "wav" to "audio/wav",
            "ogg" to "audio/ogg",
            "opus" to "audio/opus",
            "wma" to "audio/x-ms-wma",
        ).getOrElse(ext) { "audio/mpeg" }
    }
}
