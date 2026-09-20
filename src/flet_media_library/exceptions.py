class MediaLibraryError(Exception):
    """Base class for all flet-media-library errors."""

    code = "operation_failed"

    def __init__(self, message: str = "", code: str | None = None):
        super().__init__(message)
        if code is not None:
            self.code = code


class PermissionDeniedError(MediaLibraryError):
    code = "permission_denied"


class PermissionRequiredError(MediaLibraryError):
    code = "permission_required"


class UnsupportedError(MediaLibraryError):
    """The operation is not available on the current platform/backend."""
    code = "unsupported"


class AssetNotFoundError(MediaLibraryError):
    code = "asset_not_found"


class AlbumNotFoundError(MediaLibraryError):
    code = "album_not_found"


class InvalidArgumentError(MediaLibraryError):
    code = "invalid_argument"


class PlatformError(MediaLibraryError):
    """A native platform call failed unexpectedly."""
    code = "platform_error"

    def __init__(self, message: str = "", original: Exception | None = None):
        super().__init__(message)
        self.original = original


_ERROR_CLASSES = {
    cls.code: cls
    for cls in (
        PermissionDeniedError,
        PermissionRequiredError,
        UnsupportedError,
        AssetNotFoundError,
        AlbumNotFoundError,
        InvalidArgumentError,
        PlatformError,
    )
}


def error_from_exception(exc: Exception) -> MediaLibraryError:
    """Convert an exception raised by Flet's invoke-method transport into a
    :class:`MediaLibraryError`, using the ``code: message`` convention used by
    the Dart side."""
    text = str(exc)
    code_part, _, message = text.partition(": ")
    if code_part in _ERROR_CLASSES:
        return _ERROR_CLASSES[code_part](message or text)
    return MediaLibraryError(text)
