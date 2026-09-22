package com.fazigondal.flet_media_library

import android.app.Activity
import android.app.RecoverableSecurityException
import android.content.ContentUris
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import android.util.Log
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.embedding.engine.plugins.activity.ActivityAware
import io.flutter.embedding.engine.plugins.activity.ActivityPluginBinding
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.PluginRegistry

/**
 * Minimal native fallback for capabilities photo_manager 3.12.0 lacks:
 *
 *  - saveAudio   : MediaStore insert of audio files
 *  - renameAsset : DISPLAY_NAME update by MediaStore _id (with MediaStore.createWriteRequest
 *                  consent prompt for non-owned media on Android 11+)
 *  - moveAsset   : RELATIVE_PATH update by MediaStore _id (Android 10 only;
 *                  Android 11+ goes through photo_manager's moveAssetsToPath)
 *
 * Everything else is handled by photo_manager in Dart.
 */
class FletMediaLibraryPlugin : FlutterPlugin, MethodChannel.MethodCallHandler, ActivityAware, PluginRegistry.ActivityResultListener {

    companion object {
        private const val TAG = "FletMediaLibrary"
        private const val CHANNEL = "flet_media_library/native_fallback"

        /** Default album folder for saved audio when none is provided. */
        private const val DEFAULT_AUDIO_DIR = "Music/FletMediaLibrary"

        /** Request code for user write-permission prompt. */
        private const val REQUEST_CODE_WRITE_PERMISSION = 42021
    }

    private var context: Context? = null
    private var activity: Activity? = null
    private var activityBinding: ActivityPluginBinding? = null
    private var channel: MethodChannel? = null

    // Pending operation waiting for system user consent dialog.
    // Only one write-consent flow may be active at a time; a second concurrent
    // rename/move that needs user consent is rejected until the first settles.
    private var pendingResult: MethodChannel.Result? = null
    private var pendingUri: Uri? = null
    private var pendingValues: ContentValues? = null

    private fun hasPendingWriteConsent(): Boolean = pendingResult != null

    private fun setPendingWriteConsent(
        result: MethodChannel.Result,
        uri: Uri,
        values: ContentValues,
    ) {
        pendingResult = result
        pendingUri = uri
        pendingValues = values
    }

    private fun clearPendingWriteConsent() {
        pendingResult = null
        pendingUri = null
        pendingValues = null
    }

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

    override fun onAttachedToActivity(binding: ActivityPluginBinding) {
        activity = binding.activity
        activityBinding = binding
        binding.addActivityResultListener(this)
    }

    override fun onDetachedFromActivityForConfigChanges() {
        activityBinding?.removeActivityResultListener(this)
        activity = null
        activityBinding = null
        // Keep pending state across config changes; activity result will be
        // re-delivered after reattach. Do not clear pendingResult here.
    }

    override fun onReattachedToActivityForConfigChanges(binding: ActivityPluginBinding) {
        onAttachedToActivity(binding)
    }

    override fun onDetachedFromActivity() {
        activityBinding?.removeActivityResultListener(this)
        activity = null
        activityBinding = null
        // Activity is going away permanently; fail any outstanding consent flow
        // so the Dart side is not left hanging.
        val res = pendingResult
        clearPendingWriteConsent()
        res?.success(false)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        if (requestCode == REQUEST_CODE_WRITE_PERMISSION) {
            val res = pendingResult
            val uri = pendingUri
            val values = pendingValues
            clearPendingWriteConsent()

            if (res == null) return false

            if (resultCode == Activity.RESULT_OK && uri != null && values != null) {
                try {
                    val rows = context?.contentResolver?.update(uri, values, null, null) ?: 0
                    res.success(rows > 0)
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to update after permission granted: ${e.message}", e)
                    res.success(false)
                }
            } else {
                // User denied or dismissed the system prompt
                res.success(false)
            }
            return true
        }
        return false
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

        val ctx = context ?: run { result.error("NO_CONTEXT", "no context", null); return }
        val uri = findAssetUri(ctx, assetId)
        if (uri == null) {
            result.success(false); return
        }

        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, newName)
        }

        try {
            val rows = ctx.contentResolver.update(uri, values, null, null)
            if (rows > 0) {
                result.success(true)
                return
            }
        } catch (secEx: SecurityException) {
            // Android 11+ (API 30+) Scoped Storage consent prompt for other apps' media
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val act = activity
                if (act != null) {
                    if (hasPendingWriteConsent()) {
                        result.error(
                            "CONCURRENT_OPERATION",
                            "Another write-consent operation is already pending. Wait for it to finish.",
                            null,
                        )
                        return
                    }
                    val pendingIntent = MediaStore.createWriteRequest(ctx.contentResolver, listOf(uri))
                    setPendingWriteConsent(result, uri, values)
                    act.startIntentSenderForResult(
                        pendingIntent.intentSender,
                        REQUEST_CODE_WRITE_PERMISSION,
                        null, 0, 0, 0
                    )
                    return
                }
            } else if (Build.VERSION.SDK_INT == Build.VERSION_CODES.Q && secEx is RecoverableSecurityException) {
                // Android 10 (API 29) RecoverableSecurityException
                val act = activity
                if (act != null) {
                    if (hasPendingWriteConsent()) {
                        result.error(
                            "CONCURRENT_OPERATION",
                            "Another write-consent operation is already pending. Wait for it to finish.",
                            null,
                        )
                        return
                    }
                    setPendingWriteConsent(result, uri, values)
                    act.startIntentSenderForResult(
                        secEx.userAction.actionIntent.intentSender,
                        REQUEST_CODE_WRITE_PERMISSION,
                        null, 0, 0, 0
                    )
                    return
                }
            }
            Log.w(TAG, "renameAsset SecurityException for non-owned media: ${secEx.message}")
        } catch (e: Exception) {
            Log.e(TAG, "renameAsset error: ${e.message}", e)
        }

        result.success(false)
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
        val ctx = context ?: run { result.error("NO_CONTEXT", "no context", null); return }
        val uri = findAssetUri(ctx, assetId)
        if (uri == null) {
            result.success(false); return
        }

        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.RELATIVE_PATH, "$targetRelativePath/")
        }

        try {
            val rows = ctx.contentResolver.update(uri, values, null, null)
            if (rows > 0) {
                result.success(true)
                return
            }
        } catch (secEx: SecurityException) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val act = activity
                if (act != null) {
                    if (hasPendingWriteConsent()) {
                        result.error(
                            "CONCURRENT_OPERATION",
                            "Another write-consent operation is already pending. Wait for it to finish.",
                            null,
                        )
                        return
                    }
                    val pendingIntent = MediaStore.createWriteRequest(ctx.contentResolver, listOf(uri))
                    setPendingWriteConsent(result, uri, values)
                    act.startIntentSenderForResult(
                        pendingIntent.intentSender,
                        REQUEST_CODE_WRITE_PERMISSION,
                        null, 0, 0, 0
                    )
                    return
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "moveAsset error: ${e.message}", e)
        }
        result.success(false)
    }

    /**
     * Resolves the canonical MediaStore content Uri (Images, Video, or Audio)
     * for the given numeric MediaStore _id.
     */
    private fun findAssetUri(ctx: Context, assetId: Long): Uri? {
        val collections = listOf(
            MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
            MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
            MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
        )
        for (collection in collections) {
            val uri = ContentUris.withAppendedId(collection, assetId)
            try {
                ctx.contentResolver.query(
                    uri,
                    arrayOf(MediaStore.MediaColumns._ID),
                    null,
                    null,
                    null
                )?.use { cursor ->
                    if (cursor.moveToFirst()) {
                        return uri
                    }
                }
            } catch (_: Exception) {
                continue
            }
        }
        return null
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
