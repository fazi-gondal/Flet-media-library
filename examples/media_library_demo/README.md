# Media Library Demo

Full-feature **demo + manual integration test** for [`flet-media-library`](../../).

Built for **Flet 1.0** with a **local editable** dependency on the package source so every change to the library is what the demo runs.

---

## Permissions policy (important)

### You do **not** need broad storage access

This demo and the package use **purpose-specific media permissions**, not “all files” storage.

| Permission style | Used? |
|------------------|--------|
| `MANAGE_EXTERNAL_STORAGE` / all-files access | **No** |
| Legacy `READ_EXTERNAL_STORAGE` (API ≤32 only) | Yes, for old Android |
| `READ_MEDIA_IMAGES` / `VIDEO` / `AUDIO` (API 33+) | Yes — request only what you need |
| `READ_MEDIA_VISUAL_USER_SELECTED` (API 34+) | Yes — limited access |
| Camera / microphone | Only if you use **Capture** (`--permissions camera microphone`) |

Saving into the gallery uses **MediaStore / PhotoKit insert APIs**, not broad write storage.

### Runtime dialogs

1. **Manifest** (from the package + `flet build --permissions …`) only *declares* capabilities.
2. **Home → Request permissions** calls  
   `await media.request_permissions(["image", "video", "audio"])`  
   → **system permission dialog** appears.
3. Until the user allows (or grants limited access), gallery/save APIs raise `PermissionRequiredError`.
4. **Limited** → use **Present limited**. **Denied forever** → **Open settings**.
5. Camera/mic prompts appear separately when using the Capture tab.

**First-run flow**

1. Install APK  
2. Home → **Request permissions** → Allow  
3. Optional: **Start notify**  
4. Gallery / Capture / Tools  

---

## Setup

```bash
cd examples/media_library_demo
uv sync
uv run flet run src/main.py
```

```toml
[tool.uv.sources]
flet-media-library = { path = "../../", editable = true }

[project]
dependencies = [
  "flet>=1.0.0",
  "flet-camera>=0.1.0",
  "flet-video>=1.0.0",
  "flet-media-library",
]
```

---

## Screens → package APIs exercised

| Tab | UI actions | Package / related APIs |
|-----|------------|-------------------------|
| **Home** | Request / re-check / present limited / open settings / start·stop notify | `check_permissions`, `request_permissions`, `present_limited`, `open_settings`, `start_change_notify`, `stop_change_notify`, `on_change` |
| **Gallery** | Albums, load/more, thumbs, detail, rename, delete, **Select + batch delete**, **Play** video | `get_albums`, `get_assets`, `get_thumbnail`, `get_asset`, `rename_asset`, `delete_asset`, `delete_assets` + `flet-video` |
| **Capture** | Init camera, photo, record video | `flet-camera` → `save_image`, `save_video` |
| **Tools** | Move, rename, copy, **pick & save audio**, clear cache, smoke checklist | `move_asset`, `rename_asset`, `copy_asset`, `save_audio`, `clear_file_cache`, plus permission/album/asset/thumb/notify smoke |

---

## Package API quick reference (what the demo is testing)

### Permissions

```python
status = await media.check_permissions(["image", "video", "audio"])
status = await media.request_permissions(["image", "video"])  # least privilege
await media.present_limited(["image", "video"])
await media.open_settings()
# status.states["image"] in {granted, limited, denied, denied_forever, ...}
# status.all_granted / status.any_limited / status.can_request
```

### Query

```python
albums = await media.get_albums(media_type="image")
page = await media.get_assets(
    media_type="video", album=None, limit=30, offset=0,
    sort_by="date_added", sort_order="desc",
)
asset = await media.get_asset(asset_id)
thumb_b64 = await media.get_thumbnail(asset_id, width=160, height=160)
```

### Save

```python
await media.save_image(path, file_name="x.jpg", album="MediaLibraryDemo")
await media.save_video(path, file_name="x.mp4", album="MediaLibraryDemo")
await media.save_audio(path, file_name="x.mp3", album="MediaLibraryDemo")  # Android
```

### Mutate

```python
ok = await media.delete_asset(id)
ids = await media.delete_assets([id1, id2])
copied = await media.copy_asset(id, target_album_id)   # limited platforms
ok = await media.move_asset(id, "Pictures/Archive")    # Android
ok = await media.rename_asset(id, "new-name.jpg")      # Android
```

### Notify / cache

```python
media.on_change = handler
await media.start_change_notify()
await media.stop_change_notify()
await media.clear_file_cache()
```

### Models

- **MediaPermissionStatus** — `states`, `can_request`, `all_granted`, `any_limited`
- **MediaAlbum** — `id`, `name`, `asset_count`, `media_types`, `is_all`, `is_system_album`, …
- **MediaAsset** — `id`, `display_name`, `mime_type`, `media_type`, `size`, `width`/`height`, `duration_ms`, `source_uri`, …
- **MediaAssetPage** — `items`, `total`, `offset`, `limit`, `has_more`
- **MediaChangeEvent** — `change_type`, `asset_id`, `media_type`, `timestamp`

### Errors (demo shows these honestly)

`PermissionRequiredError`, `PermissionDeniedError`, `UnsupportedError`, `AssetNotFoundError`, `InvalidArgumentError`, `PlatformError`, …

---

## Android build (unsigned — no keystore)

Local:

```bash
uv run flet build apk \
  --split-per-abi \
  --arch arm64-v8a \
  --source-packages ../../src/flutter/flet_media_library \
  --permissions camera microphone \
  --yes
```

**CI:** [`.github/workflows/build-demo-apk.yml`](../../.github/workflows/build-demo-apk.yml)  
Modeled on [Vidsaver `all-builds.yml`](https://github.com/fazi-gondal/Vidsaver/blob/main/.github/workflows/all-builds.yml) but **without** signing secrets.

| Trigger | What you get |
|---------|----------------|
| Push / PR / `workflow_dispatch` | Actions artifact `media-library-demo-apk-arm64` (`.apk` + `.zip`) |
| Git tag `v*` (e.g. `git tag v0.1.0 && git push --tags`) | **GitHub Release** with: |
| | `MediaLibraryDemo-vX.Y.Z-Android-arm64-v8a.apk` |
| | `MediaLibraryDemo-vX.Y.Z-Android-arm64-v8a.zip` (**zip -9** full compression) |

---

## iOS

```bash
uv run flet build ios-simulator --permissions camera microphone --yes

uv run flet build ipa --permissions camera microphone \
  --info-plist NSPhotoLibraryUsageDescription="Demo needs photo library access" \
  --info-plist NSPhotoLibraryAddUsageDescription="Demo saves captures to the library" \
  --info-plist NSCameraUsageDescription="Demo captures photos and video" \
  --info-plist NSMicrophoneUsageDescription="Demo records video with audio"
```

---

## Suggested device test checklist

1. Home → Request permissions → dialog appears → Allow  
2. Home → Start notify  
3. Capture → Init camera → Take photo → see snackbar with asset id  
4. Capture → Record short video → stop → saved  
5. Gallery → Load → thumbs → open item → Rename / Delete  
6. Gallery → Select → multi-select → Delete selected  
7. Gallery → open a **video** → Play (needs `flet-video`; uses `source_uri`)  
8. Tools → Pick & save audio (Android)  
9. Tools → Run smoke checklist (all green / intentional SKIP)  

---

## Notes

- Prefer deleting **owned** assets created by this demo (session tracks ids after save).
- `save_audio` / `move` / `rename` are Android-focused; UI surfaces `UnsupportedError` on other platforms.
- Video Play uses `MediaAsset.source_uri` (often `content://…` on Android). If a device cannot open that URI, playback may fail until a resolved file-path API is added to the package.
- For Flet 1.0 API accuracy in your editor, run `flet mcp` (Flet MCP server).
