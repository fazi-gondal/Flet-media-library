import asyncio
import base64
import os
from typing import Any, Callable, Optional

import flet as ft

from .exceptions import InvalidArgumentError, error_from_exception
from .models import (
    MediaAsset,
    MediaAssetPage,
    MediaAlbum,
    MediaChangeEvent,
    MediaPermissionStatus,
    parse_asset_page,
    parse_media_asset,
    parse_permission_status,
)

VALID_MEDIA_TYPES = ("image", "video", "audio", "all")
VALID_SORT_FIELDS = (
    "date_added",
    "date_modified",
    "display_name",
    "size",
    "duration",
)


@ft.control("MediaLibrary")
class MediaLibrary(ft.Service):
    """Cross-platform media library service for Flet, powered by
    `photo_manager`.

    Usage::

        media = MediaLibrary()
        page.services.append(media)
        page.update()

        status = await media.request_permissions(["image", "video"])
        if status.all_granted:
            page_items = await media.get_assets(media_type="image", limit=20)
    """

    on_change: Optional[ft.EventHandler[MediaChangeEvent]] = None
    """Fired when the device media library changes.

    ``e.data`` is a :class:`MediaChangeEvent` with ``change_type`` of
    ``added``/``modified``/``removed``/``other``. The backend does not always
    distinguish change types precisely; treat ``other`` as "something changed".
    Call :meth:`start_change_notify` to begin receiving events.
    """

    # ─────────────────────────────── permissions ──────────────────────────────

    async def check_permissions(
        self, media_types: list[str] | None = None
    ) -> MediaPermissionStatus:
        """Return the current permission status without prompting the user.

        ``media_types`` defaults to all supported types. Values may include
        ``"image"``, ``"video"``, ``"audio"``.
        """
        result = await self._invoke(
            "check_permissions", {"media_types": media_types or VALID_MEDIA_TYPES[:-1]}
        )
        return parse_permission_status(result)

    async def request_permissions(
        self, media_types: list[str] | None = None
    ) -> MediaPermissionStatus:
        """Show the system permission dialog for the given media types.

        Only the requested types are prompted for (least privilege).
        On iOS the result may be ``limited``, meaning the user granted access
        to selected items only; use :meth:`present_limited` to re-open the
        selection UI.
        """
        result = await self._invoke(
            "request_permissions",
            {"media_types": media_types or VALID_MEDIA_TYPES[:-1]},
            timeout=60.0,
        )
        return parse_permission_status(result)

    async def open_settings(self) -> None:
        """Open this app's system settings page."""
        await self._invoke("open_settings")

    async def present_limited(
        self, media_types: list[str] | None = None
    ) -> None:
        """Open the system limited-selection picker (iOS 14+, Android 14+)."""
        await self._invoke(
            "present_limited", {"media_types": media_types or ["all"]}
        )

    # ───────────────────────────────── albums ──────────────────────────────────

    async def get_albums(self, media_type: str = "all") -> list[MediaAlbum]:
        """Return albums (buckets) matching ``media_type``."""
        self._validate_media_type(media_type)
        result = await self._invoke("get_albums", {"media_types": [media_type]})
        return [
            MediaAlbum(
                id=str(a.get("id") or ""),
                name=str(a.get("name") or ""),
                asset_count=int(a.get("asset_count") or 0),
                media_types=[str(t) for t in (a.get("media_types") or [])],
                is_all=bool(a.get("is_all")),
                is_system_album=bool(a.get("is_system_album")),
                platform_identifier=str(a.get("platform_identifier") or ""),
            )
            for a in (result.get("albums") or [])
        ]

    # ───────────────────────────────── assets ──────────────────────────────────

    async def get_assets(
        self,
        media_type: str = "all",
        album: str | None = None,
        mime_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "date_added",
        sort_order: str = "desc",
    ) -> MediaAssetPage:
        """Query assets with pagination.

        Parameters
        ----------
        media_type:
            ``"all"`` (default), ``"image"``, ``"video"`` or ``"audio"``.
        album:
            Album id from :meth:`get_albums`, or ``None`` to query everything.
        mime_type:
            Exact MIME filter such as ``"video/mp4"``. **Android only** —
            raises :class:`UnsupportedError` elsewhere.
        limit:
            Page size between 1 and 500.
        offset:
            Number of items to skip.
        sort_by:
            ``date_added`` (default), ``date_modified``, ``display_name``,
            ``size`` or ``duration``. The last three require album=None.
        sort_order:
            ``desc`` (default) or ``asc``.
        """
        self._validate_media_type(media_type)
        if sort_by not in VALID_SORT_FIELDS:
            raise InvalidArgumentError(f"invalid sort_by value: {sort_by!r}")
        if sort_order not in ("asc", "desc"):
            raise InvalidArgumentError(f"invalid sort_order value: {sort_order!r}")
        if not isinstance(limit, int) or limit < 1 or limit > 500:
            raise InvalidArgumentError("limit must be an integer between 1 and 500")
        if not isinstance(offset, int) or offset < 0:
            raise InvalidArgumentError("offset must be an integer >= 0")
        result = await self._invoke(
            "get_assets",
            {
                "media_type": media_type,
                "album": album,
                "mime_type": mime_type,
                "limit": limit,
                "offset": offset,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )
        return parse_asset_page(result)

    async def get_asset(self, asset_id: str) -> MediaAsset:
        """Fetch a single asset by id."""
        if not asset_id:
            raise InvalidArgumentError("asset_id must not be empty")
        result = await self._invoke("get_asset", {"asset_id": asset_id})
        return parse_media_asset(result)

    # ─────────────────────────────── thumbnails ────────────────────────────────

    async def get_thumbnail(
        self,
        asset_id: str,
        width: int = 200,
        height: int = 200,
        quality: int = 90,
    ) -> str:
        """Return a base64-encoded JPEG thumbnail usable in ``ft.Image(src=…)``.

        Works for images **and** video frames on both platforms.
        """
        if not asset_id:
            raise InvalidArgumentError("asset_id must not be empty")
        result = await self._invoke(
            "get_thumbnail",
            {
                "asset_id": asset_id,
                "width": width,
                "height": height,
                "quality": quality,
            },
            timeout=30.0,
        )
        data = result.get("data")
        if isinstance(data, bytes):
            return base64.b64encode(data).decode("ascii")
        if isinstance(data, str) and data:
            return data
        return ""

    # ───────────────────────────────── saving ──────────────────────────────────

    async def save_image(
        self,
        file_path: str,
        file_name: str | None = None,
        album: str | None = None,
    ) -> MediaAsset:
        """Copy an image file into the device gallery."""
        return parse_media_asset(await self._save("save_image", file_path, file_name, album))

    async def save_video(
        self,
        file_path: str,
        file_name: str | None = None,
        album: str | None = None,
    ) -> MediaAsset:
        """Copy a video file into the device gallery."""
        return parse_media_asset(await self._save("save_video", file_path, file_name, album))

    async def save_audio(
        self,
        file_path: str,
        file_name: str | None = None,
        album: str | None = None,
    ) -> MediaAsset:
        """Copy an audio file into the device gallery (Android only)."""
        return parse_media_asset(await self._save("save_audio", file_path, file_name, album))

    async def _save(
        self, method: str, file_path: str, file_name: str | None, album: str | None
    ) -> dict[str, Any]:
        if not file_path or not str(file_path).strip():
            raise InvalidArgumentError("file_path must not be empty")
        # Validate local existence only when the path is reachable from this
        # process. On packaged mobile builds the file lives on the device, so
        # a host-side exists() check would be wrong — skip it then.
        try:
            if os.path.isfile(file_path) is False and os.path.exists(
                os.path.dirname(file_path) or "."
            ):
                # Directory is local and visible, but the file is missing.
                raise InvalidArgumentError(f"file does not exist: {file_path}")
        except OSError:
            # Path not resolvable from this process (typical on device builds).
            pass
        args: dict[str, Any] = {"file_path": file_path}
        if file_name is not None:
            args["filename"] = file_name
        if album is not None:
            args["album"] = album
        return await self._invoke(method, args, timeout=120.0)

    # ──────────────────────────── delete / copy / move ─────────────────────────

    async def delete_asset(self, asset_id: str) -> bool:
        """Delete one asset. Returns True if it was actually deleted.

        Platforms may show a system confirmation dialog; cancelling it makes
        this method return False.
        """
        deleted = await self.delete_assets([asset_id])
        return asset_id in deleted

    async def delete_assets(self, asset_ids: list[str]) -> list[str]:
        """Batch-delete assets and return the ids that were actually deleted."""
        if not asset_ids:
            raise InvalidArgumentError("asset_ids must be a non-empty list")
        result = await self._invoke(
            "delete_assets", {"asset_ids": asset_ids}, timeout=60.0
        )
        return [str(i) for i in (result.get("deleted") or [])]

    async def copy_asset(self, asset_id: str, target_album: str) -> MediaAsset:
        """Copy an asset into an album.

        Platform behaviour differs: a real duplicate on Android <11, an album
        link on iOS, and unsupported on Android 11+ (scoped storage).
        """
        if not target_album:
            raise InvalidArgumentError("target_album must not be empty")
        result = await self._invoke(
            "copy_asset",
            {"asset_id": asset_id, "target_album": target_album},
        )
        return parse_media_asset(result)

    async def move_asset(self, asset_id: str, target_relative_path: str) -> bool:
        """Move an asset to another folder by relative path (e.g.
        ``"Movies/Archive"``). Android 10+ only; on Android 11+ the system may
        show a confirmation dialog."""
        if not asset_id:
            raise InvalidArgumentError("asset_id must not be empty")
        if not target_relative_path:
            raise InvalidArgumentError("target_relative_path must not be empty")
        result = await self._invoke(
            "move_asset",
            {
                "asset_id": asset_id,
                "target_relative_path": target_relative_path.strip("/"),
            },
            timeout=60.0,
        )
        return bool(result.get("ok"))

    async def rename_asset(self, asset_id: str, new_name: str) -> bool:
        """Rename an asset's display name, including extension (Android only)."""
        if not asset_id:
            raise InvalidArgumentError("asset_id must not be empty")
        if not new_name or not new_name.strip():
            raise InvalidArgumentError("new_name must not be empty")
        result = await self._invoke(
            "rename_asset",
            {"asset_id": asset_id, "new_name": new_name.strip()},
        )
        return bool(result.get("ok"))

    # ───────────────────────────── change notifications ────────────────────────

    async def start_change_notify(self) -> None:
        """Start listening for library changes; delivers to :attr:`on_change`."""
        await self._invoke("start_change_notify")

    async def stop_change_notify(self) -> None:
        await self._invoke("stop_change_notify")

    # ───────────────────────────────── utilities ───────────────────────────────

    async def clear_file_cache(self) -> None:
        """Clear thumbnail/file caches created by the underlying plugin."""
        await self._invoke("clear_file_cache")

    # ───────────────────────────────── internals ────────────────────────────────

    async def _invoke(
        self,
        method_name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        try:
            result = await self._invoke_method(
                method_name,
                arguments={k: v for k, v in (arguments or {}).items() if v is not None},
                timeout=timeout or 30.0,
            )
        except Exception as e:  # noqa: BLE001 - converted to structured errors
            raise error_from_exception(e) from None
        return result if isinstance(result, dict) else {}

    @staticmethod
    def _validate_media_type(media_type: str) -> None:
        if media_type not in VALID_MEDIA_TYPES:
            raise InvalidArgumentError(
                f"invalid media_type {media_type!r}; "
                f"expected one of {', '.join(VALID_MEDIA_TYPES)}"
            )


__all__ = [
    "MediaLibrary",
    "MediaAsset",
    "MediaAssetPage",
    "MediaAlbum",
    "MediaChangeEvent",
    "MediaPermissionStatus",
]
