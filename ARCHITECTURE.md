# Architecture

This document describes the design of `flet-media-library` and the capability
audit that drove it.

## Layers

```
                Python (flet_media_library)
                  MediaLibrary service control,
                  models, exceptions
                         │  invoke_method / triggerEvent
                         ▼
              Dart (flet_media_library)
                  MediaLibraryService (FletService)
                         │
                         ▼
                 PhotoManagerAdapter
                (single seam over backend)
                   │               │
                   ▼               ▼
            photo_manager    NativeFallback
                                   │
                                   ▼
                          Kotlin (Android gaps)
```

- **Python layer** is thin: it validates arguments, serializes them through
  Flet's `invoke_method` transport, and parses structured results back into
  dataclasses. No platform logic lives here.
- **Dart layer** owns all behavior. A single `MediaLibraryService` dispatches
  named methods and emits events back to Python.
- **Adapter layer** (`PhotoManagerAdapter`) converts Flet domain models to and
  from `photo_manager` types. This is the only file that imports
  `photo_manager`; replacing the backend later means rewriting one class.
- **Native fallback** exists only where `photo_manager` has no usable API.

## Backend capability audit (photo_manager 3.12.0)

| Capability | photo_manager API | Decision |
| --- | --- | --- |
| Permission check/request | `requestPermissionExtend`, `getPermissionState`, `PermissionState` | Use plugin |
| iOS limited access / Android 14 partial | `presentLimited`, `PermissionState.limited` | Surface as `limited` state |
| Open app settings | `openSetting` | Use plugin |
| Album list | `getAssetPathList` → `AssetPathEntity` | Use plugin |
| Paginated asset query | `getAssetCount`, `getAssetListRange` | Use plugin |
| Date/size/duration filters, sorting | `FilterOptionGroup` (+ `AdvancedCustomFilter` for MIME) | Use plugin |
| MIME filter | `AdvancedCustomFilter` (SQL column `mimeType`) | Use plugin where supported |
| Thumbnails (image + video frame) | `thumbnailDataWithSize` → `Uint8List` | Use plugin |
| Delete / batch delete | `editor.deleteWithIds` → deleted ids | Use plugin (system confirmation applies) |
| Save image/video | `editor.saveImageWithPath`, `editor.saveImage`, `editor.saveVideo` | Use plugin |
| Save audio | none in photo_manager | Native fallback (Android only) |
| Copy asset | `editor.copyAssetToPath` — blocked on Android 30+, album-link semantics on iOS | Plugin first; documented limits |
| Move asset | `editor.android.moveAssetsToPath` (createWriteRequest, Android 11+); `moveAssetToAnother` (Android ≤10) | Plugin on Android 11+; native RELATIVE_PATH fallback on Android 10 only |
| Rename asset | added upstream after 3.12.0 (`android.renameAsset`) | Native fallback (Android only); unsupported elsewhere |
| Change notifications | `addChangeCallback` + `startChangeNotify` | Use plugin; coarse granularity documented honestly |

## Domain models

Flet-owned, never leaking `photo_manager` types:

- `MediaAsset` — id, display_name, mime_type, media_type, size, width, height,
  duration_ms, date_added, date_modified, orientation, album_id, album_name,
  relative_path, source_uri (optional platform metadata).
- `MediaAlbum` — id, name, asset_count, media_type, is_all, is_system_album,
  platform_identifier.
- `MediaPermissionStatus` — per media-type states: granted / limited / denied /
  denied_forever / restricted / unknown, plus `can_request`.
- `MediaAssetPage` — items, total, offset, limit, has_more.
- `MediaChangeEvent` — change_type (added/modified/removed/other), asset_id,
  media_type, timestamp.

Note: `photo_manager` reports duration in seconds; `MediaAsset.duration_ms`
keeps parity with the old v1.7 Python API (milliseconds).

## Method channel surface (Python → Dart)

Single control type `MediaLibrary`. Methods:

```
check_permissions(media_types?)
request_permissions(media_types?)
open_settings()
present_limited(media_types?)
get_albums(media_types?)
get_assets(query)
get_asset(asset_id)
get_thumbnail(asset_id, width, height, quality)
save_image(file_path, filename?, album?)     # also save_video / save_audio
delete_assets(asset_ids)
copy_asset(asset_id, target_album?)
move_asset(asset_id, target_relative_path)
rename_asset(asset_id, new_name)
start_change_notify() / stop_change_notify()
clear_file_cache()
```

Events (Dart → Python): `change`.

## Error model

Structured errors returned as `{ok: false, code, message}` payloads mapped to
Python exceptions: `PermissionDeniedError`, `UnsupportedError`,
`AssetNotFoundError`, `AlbumNotFoundError`, `InvalidArgumentError`,
`PlatformError`. Nothing fails silently.

## Platform notes

- **Android**: manifest declares `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`,
  `READ_MEDIA_AUDIO`, `READ_MEDIA_VISUAL_USER_SELECTED` (API 34+) and
  `READ_EXTERNAL_STORAGE` capped at `maxSdkVersion=32`.
  `ACCESS_MEDIA_LOCATION` optional for EXIF/location data.
  Move/rename fallback uses MediaStore updates identical to v1.7 behavior;
  deletion may show the system confirmation dialog unless the user grants
  "Manage media" (Android 12+).
- **iOS**: needs `NSPhotoLibraryUsageDescription`,
  `NSPhotoLibraryAddUsageDescription`, and optionally
  `PHPhotoLibraryPreventAutomaticLimitedAccessAlert`. Limited access maps to
  the `limited` permission state; `present_limited()` opens the system picker.
  Audio querying is unreliable on iOS because PhotoKit does not index general
  audio files — documented, not hidden.
