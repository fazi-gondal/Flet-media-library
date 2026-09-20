/// Error codes used across the Dart/Python boundary.
class MediaErrorCodes {
  static const permissionDenied = "permission_denied";
  static const permissionRequired = "permission_required";
  static const unsupported = "unsupported";
  static const assetNotFound = "asset_not_found";
  static const albumNotFound = "album_not_found";
  static const invalidArgument = "invalid_argument";
  static const platformError = "platform_error";
  static const operationFailed = "operation_failed";
}

/// Exception carrying a stable [code] understood by the Python layer.
class MediaLibraryException implements Exception {
  final String code;
  final String message;

  const MediaLibraryException(this.code, this.message);

  @override
  String toString() => "$code: $message";
}
