# flet-media-library

**Flet service extension** for reading and managing the device media library from Python
(Android + iOS). Public API is Flet-owned; the Flutter side is powered mainly by
[`photo_manager`](https://pub.dev/packages/photo_manager), with a small Android native
fallback for save-audio, rename, and Android 10 move.

**Version:** `0.1.0` (alpha)  
**Platforms:** Android, iOS (not Web / Windows / macOS)

---

## Permissions: purpose-specific, not broad storage

You do **not** need (and this package does **not** request)
`MANAGE_EXTERNAL_STORAGE` or permanent “all files access”.

| Approach | Used? | Notes |
|----------|-------|--------|
| **Broad storage** (`MANAGE_EXTERNAL_STORAGE`, full `WRITE_EXTERNAL_STORAGE`) | **No** | Play Store restricted; not required for gallery apps |
| **Legacy read** (`READ_EXTERNAL_STORAGE`, `maxSdkVersion=32`) | Yes (API ≤32 only) | Covers Android 6–12 gallery read |
| **Granular media** (`READ_MEDIA_IMAGES` / `VIDEO` / `AUDIO`) | Yes (API 33+) | Purpose-specific; request only what you need |
| **User-selected** (`READ_MEDIA_VISUAL_USER_SELECTED`) | Yes (API 34+) | Supports limited / partial access |
| **Write into gallery** | Via MediaStore / PhotoKit APIs | Saving uses system insert APIs, not broad write |

### Runtime vs manifest

1. **Manifest** (declared by this package’s `AndroidManifest.xml`) only lists what the app *may* request.
2. **Runtime:** your app must call `await media.request_permissions([...])`. That shows the **system dialog**.
3. Request **only the types you need**, e.g. `["image", "video"]` does not prompt for audio.

### Android permissions declared by the package

```xml
READ_EXTERNAL_STORAGE          (maxSdkVersion=32)
READ_MEDIA_IMAGES              (API 33+)
READ_MEDIA_VIDEO               (API 33+)
READ_MEDIA_AUDIO               (API 33+)
READ_MEDIA_VISUAL_USER_SELECTED (API 34+, limited access)
```

Not declared: `MANAGE_EXTERNAL_STORAGE`, `ACCESS_MEDIA_LOCATION` (EXIF GPS off by default).

### Host app extras (demo / camera apps)

| Need | How |
|------|-----|
| Camera / mic | `flet build … --permissions camera microphone` (or explicit CAMERA / RECORD_AUDIO) |
| iOS photo library | Info.plist: `NSPhotoLibraryUsageDescription`, `NSPhotoLibraryAddUsageDescription` |
| iOS camera / mic | `NSCameraUsageDescription`, `NSMicrophoneUsageDescription` |

---

## Current status

| Area | Status |
|------|--------|
| Python public API | Implemented |
| Flet service bridge | Implemented |
| `photo_manager` adapter | Implemented |
| Android native fallback | save audio, rename, Android 10 move |
| Android manifest (granular) | Implemented |
| iOS plugin registrant | Minimal stub (behavior via photo_manager) |
| Python tests | Models + validation |
| Dart tests / device matrix | Not fully verified yet |

---

## Installation


### From PyPI

```bash
pip install flet-media-library
# or
uv add flet-media-library
```

```toml
[project]
dependencies = [
    "flet>=0.86.5",
    "flet-media-library>=0.1.0",
]
```

Then register the service in your app:

```python
import flet as ft
from flet_media_library import MediaLibrary

media = MediaLibrary()

def main(page: ft.Page):
    page.services.append(media)
    # request permissions before querying/saving
    ...

ft.run(main)
```

Build mobile apps as usual (`flet build apk` / `ipa`). The Flutter plugin ships
inside the Python wheel; Flet resolves it when packaging. Host apps still need
runtime permission prompts and iOS Info.plist purpose strings (see Permissions).

**PyPI:** https://pypi.org/project/flet-media-library/

### From source (development)

