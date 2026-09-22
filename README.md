# flet-media-library

A high-performance **Flet service extension** for querying, displaying, saving, mutating, and monitoring the device media library from Python on **Android** and **iOS**.

The Python API is Flet-native, powered on Flutter by [`photo_manager`](https://pub.dev/packages/photo_manager) for cross-platform querying, thumbnails, and saving photos/videos directly to public directories (**`DCIM/`**, **`Pictures/`**, **`Movies/`**), augmented with **custom native Android Kotlin implementations** for saving audio recordings directly to **`Music/`**, renaming assets, and relative directory moving.

[![PyPI - Version](https://img.shields.io/pypi/v/flet-media-library.svg?color=blue)](https://pypi.org/project/flet-media-library/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/flet-media-library.svg)](https://pypi.org/project/flet-media-library/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platforms-Android%20%7C%20iOS-green.svg)]()
[![Flet](https://img.shields.io/badge/Flet-%3E%3D1.0.0-purple.svg)](https://flet.dev)
[![Author: Fazi Gondal](https://img.shields.io/badge/Author-Fazi_Gondal-orange.svg)](https://github.com/fazi-gondal)
[![Download Demo APK](https://img.shields.io/badge/Download_APK-GitHub_Releases-brightgreen?logo=android&logoColor=white)](https://github.com/fazi-gondal/Flet-media-library/releases)

**Current Version:** `1.1.1` | **PyPI Package:** [`flet-media-library`](https://pypi.org/project/flet-media-library/)

> **Developed & Maintained by**: [Fazi Gondal](https://github.com/fazi-gondal)  
> **Try the App**: Download the pre-built [Media Library Demo APK from GitHub Releases](https://github.com/fazi-gondal/Flet-media-library/releases)

---

## Table of Contents

- [Key Features](#key-features)
- [Storage Destinations & Architecture](#storage-destinations--architecture)
- [Permissions Philosophy (No All-Files Access)](#permissions-philosophy-no-all-files-access)
  - [Permission Matrix](#permission-matrix)
  - [Android Manifest Declarations](#android-manifest-declarations)
  - [iOS Info.plist Keys](#ios-infoplist-keys)
- [Installation & Quickstart](#installation--quickstart)
- [Comprehensive API Reference](#comprehensive-api-reference)
  - [Service Registration](#service-registration)
  - [Permissions APIs](#permissions-apis)
  - [Album Queries](#album-queries)
  - [Asset Queries & Pagination](#asset-queries--pagination)
  - [Thumbnails](#thumbnails)
  - [Saving Media (Images, Videos, Audio)](#saving-media-images-videos-audio)
  - [Mutations (Rename, Move, Copy, Delete)](#mutations-rename-move-copy-delete)
  - [Live Media Change Notifications](#live-media-change-notifications)
  - [Platform Capabilities](#platform-capabilities)
  - [Cache Management](#cache-management)
- [Data Models](#data-models)
- [Exception Hierarchy](#exception-hierarchy)
- [Practical Cookbooks & Examples](#practical-cookbooks--examples)
  - [Cookbook 1: Request Permissions & Load Thumbnail Grid](#cookbook-1-request-permissions--load-thumbnail-grid)
  - [Cookbook 2: Capture/Record & Save Directly to Gallery](#cookbook-2-capturerecord--save-directly-to-gallery)
  - [Cookbook 3: Moving and Renaming Assets (Android)](#cookbook-3-moving-and-renaming-assets-android)
  - [Cookbook 4: Real-time Change Monitoring](#cookbook-4-real-time-change-monitoring)
- [Building Packaged Mobile Apps](#building-packaged-mobile-apps)
  - [Android (APK)](#android-apk)
  - [iOS (IPA / Simulator)](#ios-ipa--simulator)
- [Demo App & APK Download](#demo-app--apk-download)
- [Local Development Setup](#local-development-setup)
- [Credits & Acknowledgments](#credits--acknowledgments)
- [License](#license)

---

## Key Features

- **Direct Public Media Ingestion**: Save photos directly to **`DCIM/`** and **`Pictures/`**, videos to **`Movies/`** and **`DCIM/`**, and audio recordings directly to **`Music/`**.
- **Purpose-Specific Media Access**: Compliant with Google Play and Apple App Store policies. Never asks for `MANAGE_EXTERNAL_STORAGE`.
- **Custom Android Kotlin Engine**: Native fallbacks for operations unsupported by `photo_manager`: audio saving to `Music/`, in-place file renaming, and relative folder moving.
- **Fast Thumbnails**: Base64 JPEG for simple `ft.Image` use, plus **`get_thumbnail_path()`** for large galleries (cached file path, no Base64 over the bridge).
- **Per-type permissions**: Image, video, and audio states are queried independently (important on Android 13+ granular `READ_MEDIA_*`).
- **Capability discovery**: **`get_capabilities()`** reports what the current platform supports (`supports_audio_save`, `supports_move`, `supports_rename`, etc.).
- **Album & Bucket Browsing**: Fetch standard and custom user albums (`Camera`, `Screenshots`, `Download`, `Music`, `WhatsApp`, etc.).
- **Rich Filtering & Sorting**: Sort by date added, date modified, size, duration, or filename; optional **date range** filters; pagination (`limit`, `offset`, `has_more`).
- **In-Place Gallery Mutations**: Delete single or batch assets, rename files, copy assets between albums, and move assets across directories (Android write-consent flows are serialized safely).
- **Live Change Events**: Subscribe to real-time additions, deletions, or edits in the device media store.
- **Structured Error Handling**: Dedicated typed exceptions (`PermissionRequiredError`, `UnsupportedError`, `AssetNotFoundError`, etc.).

---

## Storage Destinations & Architecture

`flet-media-library` saves media directly into standard Android and iOS public directories via native platform MediaStore and PhotoKit APIs:

| Operation | Public Storage Destination | Under the Hood Implementation | Platform Support |
|---|---|---|---|
| **Save Photo** (`save_image`) | **`DCIM/`** or **`Pictures/`** | `photo_manager` (`saveImageWithPath`) | Android & iOS |
| **Save Video** (`save_video`) | **`Movies/`** or **`DCIM/`** | `photo_manager` (`saveVideo`) | Android & iOS |
| **Save Audio** (`save_audio`) | **`Music/`** (e.g. `Music/Recordings/`) | **Custom Native Kotlin** (`MediaStore.Audio`) | **Android Only** |
| **Rename Asset** (`rename_asset`) | Renames display name in-place | **Custom Native Kotlin** (`MediaStore` update) | **Android Only** |
| **Move Asset** (`move_asset`) | Moves between public albums/folders | **Custom Native Kotlin** (`RELATIVE_PATH` update) | **Android Only** |
| **Delete Assets** (`delete_assets`) | Deletes from system gallery | `photo_manager` (`deleteWithIds`) | Android & iOS |

> [!IMPORTANT]
> **Custom Kotlin Implementation on Android:**  
> Upstream Flutter `photo_manager` lacks APIs to **save audio**, **rename assets**, or **move assets between folders**. To provide these essential features on Android without requiring dangerous all-files access (`MANAGE_EXTERNAL_STORAGE`), `flet-media-library` includes custom native Android Kotlin code (`FletMediaLibraryPlugin.kt`).  
> Consequently, `save_audio`, `rename_asset`, and `move_asset` are **Android-only features**. On iOS, calling these methods cleanly raises `UnsupportedError`.

## Permissions Philosophy (No All-Files Access)

`flet-media-library` strictly follows the principle of **least privilege**. You do **not** need (and should never request) broad filesystem access or `MANAGE_EXTERNAL_STORAGE` for media operations.

### Permission Matrix

| Android API Version | Permission Mechanism | Purpose |
|---------------------|----------------------|---------|
| **Android 6 – 12 (API 23–32)** | `READ_EXTERNAL_STORAGE` (`maxSdkVersion=32`) | Reads shared media library |
| **Android 13+ (API 33+)** | `READ_MEDIA_IMAGES`<br>`READ_MEDIA_VIDEO`<br>`READ_MEDIA_AUDIO` | Granular permission for specific media types |
| **Android 14+ (API 34+)** | `READ_MEDIA_VISUAL_USER_SELECTED` | User grants access only to selected items |
| **iOS 14+** | PhotoKit Authorization | Full, limited (partial), or denied access |
| **Saving Media** | MediaStore / PhotoKit Insert APIs | No broad write permission needed on modern systems |

### Android Manifest Declarations

This package automatically bundles the following permissions into your Android build manifest:

```xml
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
<uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
<uses-permission android:name="android.permission.READ_MEDIA_VISUAL_USER_SELECTED" />
```

### iOS Info.plist Keys

When compiling for iOS (`flet build ipa`), declare usage descriptions for the photo library:

```xml
<key>NSPhotoLibraryUsageDescription</key>
<string>This app requires access to your photo library to browse and select media.</string>
<key>NSPhotoLibraryAddUsageDescription</key>
<string>This app requires permission to save photos and videos to your gallery.</string>
```

---

## Installation & Quickstart

### PyPI

```bash
pip install flet-media-library
# or using uv
uv add flet-media-library
```

### Add to `pyproject.toml`

```toml
[project]
dependencies = [
    "flet>=1.0.0",
    "flet-media-library>=1.0.1",
]
```

### Quickstart Example

```python
import flet as ft
from flet_media_library import MediaLibrary

async def main(page: ft.Page):
    media = MediaLibrary()
    page.services.append(media)
    page.update()

    # Request permissions for images and videos
    status = await media.request_permissions(["image", "video"])
    if not status.all_granted and not status.any_limited:
        page.add(ft.Text("Media permission was denied!"))
        return

    # Query latest 20 photos
    page_data = await media.get_assets(media_type="image", limit=20)
    grid = ft.GridView(expand=True, max_extent=120, spacing=5, run_spacing=5)
    
    for asset in page_data.items:
        # Load thumbnail as base64
        thumb_b64 = await media.get_thumbnail(asset.id, width=120, height=120)
        grid.controls.append(
            ft.Image(src_base64=thumb_b64, fit=ft.BoxFit.COVER, border_radius=4)
        )

    page.add(grid)

if __name__ == "__main__":
    ft.run(main)
```

---

## Demo App & APK Download

You can test `flet-media-library` immediately on your physical Android phone without setting up Flutter or Android development tools.

Pre-compiled, ready-to-sideload Android APKs (`.apk`) are automatically compiled and attached to every GitHub release:

👉 **[Download the latest Demo APK from GitHub Releases](https://github.com/fazi-gondal/Flet-media-library/releases)**

### Features in the Demo App:
- **Media Gallery**: High-performance grid with thumbnails for photos and videos.
- **In-App Media Player**: Built-in video and audio playback dialogs (`flet-video` / ExoPlayer).
- **Camera & Microphone Capture**: Live camera preview (`flet-camera`) and WAV audio recorder (`flet-audio-recorder` PCM streaming) saving directly to gallery and `Music/FletMediaLibrary`.
- **File Management**: Move files between folders, rename with extensions, and batch-delete items.
- **Automated Smoke Test**: 1-click test verifying all 8 core package APIs on actual hardware.

For instructions on building the demo from source, see [`examples/media_library_demo/README.md`](examples/media_library_demo/).

---

## Comprehensive API Reference

### Service Registration

`MediaLibrary` inherits from `ft.Service`. It must be added to `page.services`:

```python
from flet_media_library import MediaLibrary

media = MediaLibrary()
page.services.append(media)
page.update()
```

---

### Permissions APIs

#### `check_permissions(media_types: list[str] | None = None) -> MediaPermissionStatus`
Checks the current permission status without prompting the user.
- **Parameters**: `media_types` — List of types to check: `["image", "video", "audio"]` (defaults to all).
- **Returns**: `MediaPermissionStatus` with a **per-type** `states` map. On Android 13+, image/video/audio can differ (granular `READ_MEDIA_*`).

```python
status = await media.check_permissions(["image", "video", "audio"])
print("Images:", status["image"])   # granted | limited | denied | ...
print("Videos:", status["video"])
print("Audio:", status["audio"])
print("can_request:", status.can_request)
```

#### `request_permissions(media_types: list[str] | None = None) -> MediaPermissionStatus`
Prompts the OS system permission dialog requesting access for the specified media types, then **re-checks each type** so the returned map reflects actual outcomes.
- **Parameters**: `media_types` — `["image", "video", "audio"]` (request only what you need).
- **Returns**: `MediaPermissionStatus`.

```python
status = await media.request_permissions(["image", "video", "audio"])
if status.all_granted:
    print("Full media library access granted")
elif status.any_limited:
    print("User granted limited/partial media access")
```

#### `present_limited(media_types: list[str] | None = None) -> None`
Re-opens the system limited-picker on iOS 14+ or Android 14+ so the user can select additional photos/videos without having to grant full library access.

```python
await media.present_limited(["image", "video"])
```

#### `open_settings() -> None`
Navigates the user directly to the application's system settings screen (useful when permission is `denied_forever`).

```python
await media.open_settings()
```

---

### Album Queries

#### `get_albums(media_type: str = "all") -> list[MediaAlbum]`
Fetches albums/folders containing the specified media type.
- **Parameters**: `media_type` — `"all"`, `"image"`, `"video"`, or `"audio"`.
- **Returns**: `list[MediaAlbum]`.

```python
albums = await media.get_albums(media_type="image")
for album in albums:
    print(f"Album: {album.name} (ID: {album.id}) - {album.asset_count} items")
```

---

### Asset Queries & Pagination

#### `get_assets(...) -> MediaAssetPage`
Queries assets with pagination, optional album filtering, and sorting.

```python
async def get_assets(
    media_type: str = "all",           # "all" | "image" | "video" | "audio"
    album: str | None = None,           # Album ID from get_albums(), or None for root
    mime_type: str | None = None,       # Exact MIME filter (e.g. "video/mp4", Android only)
    limit: int = 50,                    # 1 to 500 items per page
    offset: int = 0,                    # Item offset to skip (re-query from 0 after change events)
    sort_by: str = "date_added",        # "date_added", "date_modified", "display_name", "size", "duration"
    sort_order: str = "desc",           # "desc" | "asc"
    min_date_added: int | None = None,  # Inclusive unix seconds (global queries only)
    max_date_added: int | None = None,  # Inclusive unix seconds (global queries only)
) -> MediaAssetPage
```

```python
# Query page 1 (first 30 videos sorted newest first)
page1 = await media.get_assets(
    media_type="video",
    limit=30,
    offset=0,
    sort_by="date_added",
    sort_order="desc",
)

print(f"Total: {page1.total}, Loaded: {len(page1.items)}, Has more: {page1.has_more}")

# Query next page
if page1.has_more:
    page2 = await media.get_assets(media_type="video", limit=30, offset=30)
```

#### `get_asset(asset_id: str) -> MediaAsset`
Retrieves detailed metadata for a single specific asset by its ID.

```python
asset = await media.get_asset("1000000032")
print(f"{asset.display_name} - {asset.width}x{asset.height} - {asset.size} bytes")
```

---

### Thumbnails

#### `get_thumbnail(asset_id: str, width: int = 200, height: int = 200, quality: int = 90) -> str`
Generates a base64-encoded JPEG thumbnail for an image or a video frame.
- **Parameters**: `asset_id`, `width`, `height`, `quality` (1–100).
- **Returns**: Base64 string suitable for `ft.Image(src_base64=...)`.
- Prefer **`get_thumbnail_path`** when rendering many items (gallery grids).

```python
thumb_b64 = await media.get_thumbnail(asset.id, width=150, height=150, quality=85)
image_ctrl = ft.Image(src_base64=thumb_b64, width=150, height=150)
```

#### `get_thumbnail_path(asset_id: str, width: int = 200, height: int = 200, quality: int = 90) -> str`
Writes a JPEG thumbnail to a stable local cache file and returns the **filesystem path**.
- Avoids shipping Base64 through the Python/Dart boundary on every scroll.
- Cache key includes `asset_id`, size, and quality; cleared by `clear_file_cache()`.
- Suitable for `ft.Image(src=path)` on mobile.

```python
path = await media.get_thumbnail_path(asset.id, width=160, height=160)
image_ctrl = ft.Image(src=path, width=160, height=160, fit=ft.BoxFit.COVER)
```

---

### Saving Media (Images, Videos, Audio)

Saves local files directly into the platform media gallery using platform MediaStore and PhotoKit insert pipelines. No broad storage permissions required.

> **Destination folder naming:** prefer keyword **`relative_path=`** (e.g. `"Pictures/MyApp"`).  
> **`album=`** remains as a backward-compatible alias for the same value.

#### `save_image(file_path: str, file_name: str | None = None, *, relative_path: str | None = None, album: str | None = None) -> MediaAsset`
Saves an image file directly into public gallery storage (**`Pictures/`** or **`DCIM/`**).
- **Public Destinations**:
  - **`Pictures/<Subfolder>`** (e.g. `relative_path="Pictures/MyApp"`)
  - **`DCIM/<Subfolder>`** (e.g. `relative_path="DCIM/Camera"`)
- **Backend**: Uses upstream `photo_manager` (`saveImageWithPath`).
- **Platform Support**: Android & iOS.
- **Parameters**:
  - `file_path`: Absolute path to source image (e.g. app scratch file or downloaded photo).
  - `file_name`: Optional target filename (e.g. `"snapshot_2026.jpg"`).
  - `relative_path`: Preferred destination folder under public storage.
  - `album`: Legacy alias for `relative_path`.

```python
asset = await media.save_image(
    "/data/user/0/com.app/cache/photo.jpg",
    file_name="snapshot_2026.jpg",
    relative_path="Pictures/MyCameraApp",
)
print("Saved image ID:", asset.id)
```

#### `save_video(file_path: str, file_name: str | None = None, *, relative_path: str | None = None, album: str | None = None) -> MediaAsset`
Saves a video file directly into public gallery storage (**`Movies/`** or **`DCIM/`**).
- **Public Destinations**:
  - **`Movies/<Subfolder>`** (e.g. `album="Movies/MyVideoApp"`)
  - **`DCIM/<Subfolder>`** (e.g. `album="DCIM/Camera"`)
- **Backend**: Uses upstream `photo_manager` (`saveVideo`).
- **Platform Support**: Android & iOS.
- **Parameters**:
  - `file_path`: Absolute path to source video file.
  - `file_name`: Optional target filename (e.g. `"clip.mp4"`).
  - `album`: Optional public folder name (defaults to `"Movies/FletMediaLibrary"`).

```python
asset = await media.save_video(
    "/path/to/recording.mp4",
    file_name="clip.mp4",
    album="Movies/MyCameraApp",
)
```

#### `save_audio(file_path: str, file_name: str | None = None, *, relative_path: str | None = None, album: str | None = None) -> MediaAsset`
Saves an audio file directly into the device's public **`Music/`** folder.
- **Public Destination**: **`Music/<Subfolder>`** (e.g. `album="Music/Recordings"` or `album="Music/MyPodcasts"`).
- **Backend**: **Custom Native Android Kotlin Implementation** (`FletMediaLibraryPlugin.kt` writing directly to `MediaStore.Audio.Media`). Upstream `photo_manager` does **not** support saving audio files.
- **Platform Support**: **Android Only** (raises `UnsupportedError` on iOS).
- **Parameters**:
  - `file_path`: Absolute path to source audio file (e.g. `.m4a`, `.mp3`, `.wav`, `.aac`).
  - `file_name`: Target filename (e.g. `"recording_01.m4a"`).
  - `album`: Target subfolder within `Music` (defaults to `"Music/FletMediaLibrary"`).

```python
asset = await media.save_audio(
    "/path/to/voice_note.m4a",
    file_name="recording_01.m4a",
    album="Music/Recordings",
)
print(f"Audio indexed in Music/Recordings: {asset.display_name} (ID: {asset.id})")
```

---

### Mutations (Rename, Move, Copy, Delete)

#### `delete_asset(asset_id: str) -> bool`
Deletes a single asset from the device gallery.
- **Backend**: `photo_manager` (`deleteWithIds`).
- **Platform Support**: Android & iOS.
- **Returns**: `True` if successfully deleted, `False` if user cancelled system dialog.

```python
ok = await media.delete_asset(asset.id)
if ok:
    print("Asset deleted successfully")
```

#### `delete_assets(asset_ids: list[str]) -> list[str]`
Batch deletes multiple assets in a single native system confirmation.
- **Backend**: `photo_manager` (`deleteWithIds`).
- **Platform Support**: Android & iOS.
- **Returns**: List of asset IDs that were successfully deleted.

```python
deleted_ids = await media.delete_assets(["id1", "id2", "id3"])
print(f"Deleted {len(deleted_ids)} items")
```

#### `rename_asset(asset_id: str, new_name: str) -> bool`
Renames an asset's display name and filename directly in the device MediaStore.
- **Backend**: **Custom Native Android Kotlin Implementation** (`FletMediaLibraryPlugin.kt`). Upstream `photo_manager` does **not** support renaming assets.
- **Platform Support**: **Android Only** (raises `UnsupportedError` on iOS). On Android 11+, the OS may present a native consent dialog for non-owned media.
- **Parameters**:
  - `asset_id`: The MediaStore ID of the item.
  - `new_name`: New filename with extension (e.g. `"vacation_sunset.jpg"`).

```python
ok = await media.rename_asset(asset.id, "vacation_sunset.jpg")
```

#### `move_asset(asset_id: str, target_relative_path: str) -> bool`
Moves an asset between public folders (e.g., moving from `DCIM/Camera` to `Pictures/Archive` or `Movies/Archive`).
- **Backend**: **Custom Native Android Kotlin Implementation** (`RELATIVE_PATH` MediaStore update). Upstream `photo_manager` does **not** support folder relocation.
- **Platform Support**: **Android 10+ Only** (raises `UnsupportedError` on iOS or older Android versions).
- **Parameters**:
  - `asset_id`: The MediaStore ID of the item.
  - `target_relative_path`: Target public relative path (e.g. `"Pictures/Archive"`).

```python
ok = await media.move_asset(asset.id, "Pictures/Archive")
if ok:
    print("Moved to archive folder")
```

#### `copy_asset(asset_id: str, target_album: str) -> MediaAsset`
Copies an asset into a target album. Platform support varies:
- **Android < 11**: Creates duplicate file.
- **Android 11+**: Scoped storage restricts arbitrary duplication; raises `UnsupportedError`.
- **iOS**: Links asset to the target album.

---

### Live Media Change Notifications

Subscribe to system media library changes (such as when new photos are taken by the camera or downloaded).

```python
def on_media_changed(e: ft.ControlEvent):
    event = e.data  # MediaChangeEvent
    print(f"Change detected: type={event.change_type}, id={event.asset_id}")

media.on_change = on_media_changed
await media.start_change_notify()

# When finished or exiting screen:
await media.stop_change_notify()
```

---

### Platform Capabilities

#### `get_capabilities() -> dict`
Returns flags so apps do not hard-code platform gaps.

| Key | Type | Meaning |
|-----|------|---------|
| `platform` | `str` | `"android"`, `"ios"`, or other |
| `supports_audio_save` | `bool` | `save_audio` available |
| `supports_move` | `bool` | `move_asset` available |
| `supports_rename` | `bool` | `rename_asset` available |
| `supports_copy` | `bool` | `copy_asset` available |
| `supports_mime_filter` | `bool` | MIME filter on `get_assets` |
| `supports_limited_access` | `bool` | Limited picker (iOS 14+ / Android 14+) |
| `supports_thumbnail_path` | `bool` | `get_thumbnail_path` available |
| `supports_change_notify` | `bool` | Change notifications |
| `android_sdk` | `int` | SDK level, or `0` if not Android |

```python
caps = await media.get_capabilities()
if caps.get("supports_audio_save"):
    await media.save_audio(path, file_name="note.m4a", relative_path="Music/Recordings")
```

---

### Cache Management

#### `clear_file_cache() -> None`
Clears internal thumbnail caches (including files created by `get_thumbnail_path`) and plugin file caches.

```python
await media.clear_file_cache()
```

---

## Data Models

### `MediaAsset`

Represents a single media item:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Platform-unique asset identifier |
| `display_name` | `str` | File name including extension (e.g. `IMG_001.jpg`) |
| `mime_type` | `str` | MIME type (e.g. `image/jpeg`, `video/mp4`, `audio/mp4`) |
| `media_type` | `str` | Broad type: `"image"`, `"video"`, or `"audio"` |
| `size` | `int` | Size in bytes |
| `width` | `int` | Pixel width (0 for audio) |
| `height` | `int` | Pixel height (0 for audio) |
| `duration_ms` | `int` | Duration in milliseconds (0 for images) |
| `date_added` | `int` | Unix timestamp (seconds) when added to library |
| `date_modified` | `int` | Unix timestamp (seconds) when last modified |
| `orientation` | `int` | EXIF orientation angle (0, 90, 180, 270) |
| `album_id` | `str` | Containing album identifier |
| `album_name` | `str` | Containing album name |
| `relative_path` | `str` | Relative directory (e.g. `DCIM/Camera/`) |
| `source_uri` | `str` | System URI (`content://...` on Android, `ph://...` on iOS) |

### `MediaAlbum`

Represents an album, bucket, or folder:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Album unique identifier |
| `name` | `str` | User-facing album title (e.g. `Camera`, `Screenshots`) |
| `asset_count` | `int` | Count of media items in this album |
| `media_types` | `list[str]` | Media types present in album (`["image", "video"]`) |
| `is_all` | `bool` | `True` if this is the "Recent" / "All Media" collection |
| `is_system_album` | `bool` | `True` for OS-managed collections |
| `platform_identifier` | `str` | Native platform identifier |

### `MediaPermissionStatus`

Snapshot of permission states:

| Property / Method | Type | Description |
|-------------------|------|-------------|
| `states` | `dict[str, str]` | Maps media type to status (`granted`, `limited`, `denied`, `denied_forever`, `restricted`, `unknown`) |
| `status[media_type]` | `str` | Shortcut for accessing status by key (e.g. `status["image"]`) |
| `all_granted` | `bool` | `True` if all requested types are `"granted"` |
| `any_limited` | `bool` | `True` if any requested type is `"limited"` |
| `can_request` | `bool` | `True` if system dialog can still be requested |

### `MediaAssetPage`

Result of a paginated `get_assets` query:

| Field | Type | Description |
|-------|------|-------------|
| `items` | `list[MediaAsset]` | List of `MediaAsset` items for this page |
| `total` | `int` | Total count matching filter |
| `offset` | `int` | Current query offset |
| `limit` | `int` | Items per page |
| `has_more` | `bool` | `True` if more items are available |

---

## Exception Hierarchy

All exceptions inherit from `MediaLibraryError`:

```
MediaLibraryError
 ├── PermissionRequiredError   # Operation attempted before permissions were granted
 ├── PermissionDeniedError     # User actively denied permission
 ├── UnsupportedError          # Method unsupported on this OS or OS version
 ├── AssetNotFoundError        # Target asset ID does not exist
 ├── AlbumNotFoundError        # Target album ID does not exist
 ├── InvalidArgumentError      # Bad arguments (e.g. limit > 500, negative offset)
 └── PlatformError             # Underlying native platform exception
```

---

## Practical Cookbooks & Examples

### Cookbook 1: Request Permissions & Load Thumbnail Grid

```python
import flet as ft
from flet_media_library import MediaLibrary, PermissionRequiredError

async def main(page: ft.Page):
    media = MediaLibrary()
    page.services.append(media)
    page.update()

    status = await media.request_permissions(["image", "video"])
    if not (status.all_granted or status.any_limited):
        page.add(ft.Text("Permissions denied. Cannot browse media."))
        return

    grid = ft.GridView(expand=True, max_extent=110, spacing=4, run_spacing=4)
    page.add(grid)

    asset_page = await media.get_assets(media_type="image", limit=40)
    for asset in asset_page.items:
        thumb = await media.get_thumbnail(asset.id, width=110, height=110)
        grid.controls.append(
            ft.Image(src_base64=thumb, fit=ft.BoxFit.COVER, border_radius=4)
        )
    page.update()

ft.run(main)
```

### Cookbook 2: Capture/Record & Save Directly to Gallery

```python
import flet as ft
from flet_media_library import MediaLibrary

async def save_captured_media(media: MediaLibrary, photo_file: str, video_file: str, audio_file: str):
    # 1. Save photo directly to public Pictures/ or DCIM/ (cross-platform via photo_manager)
    photo_asset = await media.save_image(
        photo_file,
        file_name="snapshot_2026.jpg",
        album="Pictures/MyCameraApp",  # or "DCIM/Camera"
    )
    print(f"Photo saved into Pictures: {photo_asset.display_name} (ID: {photo_asset.id})")

    # 2. Save video directly to public Movies/ or DCIM/ (cross-platform via photo_manager)
    video_asset = await media.save_video(
        video_file,
        file_name="clip_2026.mp4",
        album="Movies/MyCameraApp",    # or "DCIM/Camera"
    )
    print(f"Video saved into Movies: {video_asset.display_name} (ID: {video_asset.id})")

    # 3. Save audio directly to public Music/ (Android-only via custom Kotlin engine)
    audio_asset = await media.save_audio(
        audio_file,
        file_name="voice_note.m4a",
    )
    print(f"Audio indexed into Music: {audio_asset.display_name} (ID: {audio_asset.id})")
```

### Cookbook 3: Moving and Renaming Assets (Android)

```python
from flet_media_library import MediaLibrary, UnsupportedError

async def organize_media(media: MediaLibrary, asset_id: str):
    try:
        # Rename file
        renamed = await media.rename_asset(asset_id, "family_vacation_2026.jpg")
        print("Renamed:", renamed)

        # Move to Archive folder
        moved = await media.move_asset(asset_id, "Pictures/Archive")
        print("Moved:", moved)
    except UnsupportedError as err:
        print("Operation not supported on this platform/OS version:", err)
```

### Cookbook 4: Real-time Change Monitoring

```python
async def watch_gallery(page: ft.Page, media: MediaLibrary):
    async def on_change(e):
        ev = e.data
        print(f"Library updated! Type: {ev.change_type}, Asset: {ev.asset_id}")
        # Refresh UI
        page.snack_bar = ft.SnackBar(ft.Text("Media gallery changed!"))
        page.snack_bar.open = True
        page.update()

    media.on_change = on_change
    await media.start_change_notify()
```

---

## Building Packaged Mobile Apps

When packaging with Flet, the Flutter engine plugin is automatically linked into the mobile binary.

### Android (APK)

```bash
uv run flet build apk \
  --split-per-abi \
  --arch arm64-v8a \
  --permissions camera microphone \
  --yes
```

To build against a local development version of this repository:

```bash
uv run flet build apk \
  --source-packages /path/to/flet_media_library/src/flutter/flet_media_library \
  --permissions camera microphone \
  --yes
```

### iOS (IPA / Simulator)

```bash
# Simulator build
uv run flet build ios-simulator --permissions camera microphone --yes

# Production IPA
uv run flet build ipa \
  --permissions camera microphone \
  --info-plist NSPhotoLibraryUsageDescription="Browse and select media from device gallery" \
  --info-plist NSPhotoLibraryAddUsageDescription="Save photos and captured media to library"
```

---

## Local Development Setup

To run and contribute to `flet-media-library`:

```bash
git clone https://github.com/fazi-gondal/Flet-media-library.git
cd Flet-media-library

# Install Python package in editable mode
uv sync

# Test Python models & serialization
uv run pytest tests/

# Format Dart plugin code
cd src/flutter/flet_media_library
flutter pub get
flutter analyze
dart format --set-exit-if-changed --output=none .
```

To explore and test on a physical device or emulator, see the full-featured test harness in [`examples/media_library_demo/`](examples/media_library_demo/).

---

## Credits & Acknowledgments

- **Creator & Lead Maintainer**: [Fazi Gondal](https://github.com/fazi-gondal) ([@fazi-gondal](https://github.com/fazi-gondal))
- **Core Dependencies & Ecosystem**:
  - [Flet](https://flet.dev) — The Python framework for Flutter UI created by [Feodor Fitsner](https://github.com/FeodorFitsner) and the Flet team.
  - [`photo_manager`](https://pub.dev/packages/photo_manager) — The underlying cross-platform asset and album engine created by [CaiJingLong / Alex Li](https://github.com/CaiJingLong) and the [FlutterCandies](https://github.com/fluttercandies) team.
  - [`flet-camera`](https://pypi.org/project/flet-camera/) & [`flet-video`](https://pypi.org/project/flet-video/) — Camera preview and media player controls used in the companion demo.
  - [`flet-audio-recorder`](https://pypi.org/project/flet-audio-recorder/) — Cross-platform audio recording integration for Flet.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
