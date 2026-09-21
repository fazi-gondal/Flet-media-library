import 'package:flutter/services.dart';

/// Minimal escape hatch to native Android for the two capabilities
/// photo_manager 3.12.0 does not provide: saving audio files and renaming
/// assets. Everything else goes through photo_manager.
class NativeFallback {
  static const MethodChannel _channel = MethodChannel(
    'flet_media_library/native_fallback',
  );

  /// Inserts an audio file into MediaStore and returns the new asset id.
  Future<String> saveAudio(
    String filePath,
    String? filename,
    String? relativePath,
  ) async {
    final result = await _channel.invokeMapMethod<String, dynamic>(
      'saveAudio',
      {
        'filePath': filePath,
        if (filename != null) 'filename': filename,
        if (relativePath != null) 'relativePath': relativePath,
      },
    );
    return result?['id'] as String? ?? "";
  }

  /// Updates DISPLAY_NAME on a MediaStore record.
  Future<bool> renameAsset(String assetId, String newName) async {
    final result = await _channel.invokeMethod<bool>('renameAsset', {
      'assetId': assetId,
      'newName': newName,
    });
    return result ?? false;
  }

  /// Updates RELATIVE_PATH on a MediaStore record (Android 10 only path).
  Future<bool> moveAsset(String assetId, String targetRelativePath) async {
    final result = await _channel.invokeMethod<bool>('moveAsset', {
      'assetId': assetId,
      'targetRelativePath': targetRelativePath,
    });
    return result ?? false;
  }
}
