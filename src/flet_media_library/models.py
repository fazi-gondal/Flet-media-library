from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:
    from .media_library import MediaLibrary


@dataclass
class MediaAsset:
    """A single media item returned by :meth:`MediaLibrary.get_assets`.

    ``width`` and ``height`` are 0 for audio files.
    ``duration_ms`` is 0 for images.
    """

    id: str = ""
    display_name: str = ""
    mime_type: str = ""
    media_type: str = ""  # "image" | "video" | "audio"
    size: int = 0
    width: int = 0
    height: int = 0
    duration_ms: int = 0
    date_added: int = 0  # unix seconds
    date_modified: int = 0  # unix seconds
    orientation: int = 0
    album_id: str = ""
    album_name: str = ""
    relative_path: str = ""
    source_uri: str = ""


@dataclass
class MediaAlbum:
    """A photo-library album (bucket/folder).

    Notes on cross-platform semantics:
    - ``id`` is the platform album/path id (use with :meth:`get_assets`).
    - ``is_system_album`` is approximated as ``is_all`` because photo_manager
      does not expose a dedicated system-album flag.
    - Individual :class:`MediaAsset` objects may not carry a reliable
      ``album_id``; ``album_name`` is often inferred from ``relative_path``.
    """

    id: str = ""
    name: str = ""
    asset_count: int = 0
    media_types: list[str] = field(default_factory=list)
    is_all: bool = False
    is_system_album: bool = False
    platform_identifier: str = ""


@dataclass
class MediaPermissionStatus:
    """Permission snapshot keyed by media type.

    Each value is one of: ``granted``, ``limited``, ``denied``,
    ``denied_forever``, ``restricted``, ``unknown``.
    """

    states: dict[str, str] = field(default_factory=dict)
    can_request: bool = False

    def __getitem__(self, media_type: str) -> str:
        return self.states.get(media_type, "unknown")

    @property
    def all_granted(self) -> bool:
        return bool(self.states) and all(
            v == "granted" for v in self.states.values()
        )

    @property
    def any_limited(self) -> bool:
        return any(v == "limited" for v in self.states.values())


@dataclass
class MediaAssetPage:
    """One page of asset-query results."""

    items: list[MediaAsset] = field(default_factory=list)
    total: int = 0
    offset: int = 0
    limit: int = 50
    has_more: bool = False


@dataclass
class MediaChangeEvent(ft.Event["MediaLibrary"]):
    """Emitted when the device media library changes.

    ``change_type`` is ``added``, ``modified``, ``removed`` or ``other``.
    The underlying backend does not always distinguish these precisely;
    treat ``other`` as "something changed".
    """

    change_type: str = field(default="other", kw_only=True)
    asset_id: str = field(default="", kw_only=True)
    media_type: str = field(default="", kw_only=True)
    timestamp: int = field(default=0, kw_only=True)


def parse_media_asset(data: dict) -> MediaAsset:
    return MediaAsset(
        id=str(data.get("id") or ""),
        display_name=str(data.get("display_name") or ""),
        mime_type=str(data.get("mime_type") or ""),
        media_type=str(data.get("media_type") or ""),
        size=int(data.get("size") or 0),
        width=int(data.get("width") or 0),
        height=int(data.get("height") or 0),
        duration_ms=int(data.get("duration_ms") or 0),
        date_added=int(data.get("date_added") or 0),
        date_modified=int(data.get("date_modified") or 0),
        orientation=int(data.get("orientation") or 0),
        album_id=str(data.get("album_id") or ""),
        album_name=str(data.get("album_name") or ""),
        relative_path=str(data.get("relative_path") or ""),
        source_uri=str(data.get("source_uri") or ""),
    )


def parse_asset_page(data: dict) -> MediaAssetPage:
    items = [parse_media_asset(a) for a in (data.get("items") or [])]
    return MediaAssetPage(
        items=items,
        total=int(data.get("total") or 0),
        offset=int(data.get("offset") or 0),
        limit=int(data.get("limit") or 50),
        has_more=bool(data.get("has_more")),
    )


def parse_permission_status(data: dict) -> MediaPermissionStatus:
    perms = data.get("permissions") or {}
    return MediaPermissionStatus(
        states={str(k): str(v) for k, v in perms.items()},
        can_request=bool(data.get("can_request")),
    )
