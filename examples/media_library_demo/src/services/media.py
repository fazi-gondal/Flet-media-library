"""Thin session wrapper around MediaLibrary for the demo app."""

from __future__ import annotations

from dataclasses import dataclass, field

from flet_media_library import MediaLibrary, MediaPermissionStatus


@dataclass
class DemoSession:
    """Shared state for all demo screens."""

    media: MediaLibrary
    # Asset ids created by this demo session (safe to delete without confirm).
    owned_asset_ids: list[str] = field(default_factory=list)
    last_permission: MediaPermissionStatus | None = None
    change_log: list[str] = field(default_factory=list)

    def track_owned(self, asset_id: str) -> None:
        if asset_id and asset_id not in self.owned_asset_ids:
            self.owned_asset_ids.append(asset_id)

    def untrack(self, asset_id: str) -> None:
        if asset_id in self.owned_asset_ids:
            self.owned_asset_ids.remove(asset_id)
