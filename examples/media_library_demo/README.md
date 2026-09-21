# Media Library Demo & Integration Test Harness

A complete, full-featured **demo application and manual test harness** for [`flet-media-library`](../../).

Built for **Flet 1.0** with a **local editable** dependency on the package source, ensuring every feature, fix, and optimization in the library can be tested immediately on real devices.

---

## Table of Contents

- [Overview of Demo Features](#overview-of-demo-features)
- [Screens & Tested APIs](#screens--tested-apis)
  - [1. Home Screen (Permissions & Live Observer)](#1-home-screen-permissions--live-observer)
  - [2. Gallery Screen (Media Browser, Player, Batch Delete, Move & Rename)](#2-gallery-screen-media-browser-player-batch-delete-move--rename)
  - [3. Capture Screen (Camera & Microphone Recording)](#3-capture-screen-camera--microphone-recording)
  - [4. Tools Screen (File Mutations & Smoke Checklist)](#4-tools-screen-file-mutations--smoke-checklist)
- [Permissions Architecture](#permissions-architecture)
- [Running Locally](#running-locally)
  - [With Flet Mobile Client (Live Preview)](#with-flet-mobile-client-live-preview)
  - [Desktop Preview](#desktop-preview)
- [Building Standalone Mobile Binaries](#building-standalone-mobile-binaries)
  - [Android APK Build](#android-apk-build)
  - [Automated CI / GitHub Actions](#automated-ci--github-actions)
  - [Pushing & Managing Build Tags](#pushing--managing-build-tags)
  - [iOS Build](#ios-build)
- [Key Package APIs Quick Reference](#key-package-apis-quick-reference)
- [Important Platform Notes](#important-platform-notes)

---

## Overview of Demo Features

| Capability | Supported | Description |
|---|---|---|
| **Media Browsing** | ✅ Photos, Videos, Audio | Filter by type, browse albums, inspect full metadata |
| **Thumbnails** | ✅ Images & Videos | Fast base64 thumbnail rendering in responsive grid |
| **In-App Playback** | ✅ Video & Audio | ExoPlayer playback directly inside modal dialogs |
| **Camera Capture** | ✅ Photos & Video | Shoot photos or record videos and save directly to gallery |
| **Mic Recording** | ✅ Audio Notes (.m4a) | Record voice notes with timer and save to `Music/Recordings` |
| **File Mutations** | ✅ Move, Rename, Delete | Move between folders, rename with extension, batch delete |
| **Permissions** | ✅ Granular & Limited | Check, request, limited picker (Android 14+ / iOS 14+), settings |
| **Live Updates** | ✅ Real-time Listener | Detect external library changes and refresh automatically |
| **Smoke Suite** | ✅ 1-Click Verification | Automated checklist verifying all endpoints on physical device |

---

## Screens & Tested APIs

### 1. Home Screen (Permissions & Live Observer)

The Home screen acts as the application's control center and permission supervisor.

- **Check Permissions** (`media.check_permissions`): Queries current authorization state without showing dialogs.
- **Request Permissions** (`media.request_permissions`): Triggers the native system permission dialog. Exercises least privilege (`["image", "video", "audio"]`).
- **Present Limited Picker** (`media.present_limited`): On iOS 14+ and Android 14+, opens the OS limited-access photo picker so users can select additional media without granting full gallery access.
- **Open Settings** (`media.open_settings`): Directly opens the app's permission page in system settings.
- **Start / Stop Change Notifications** (`media.start_change_notify`, `media.stop_change_notify`): Listens for `media.on_change` events in real-time and logs event timestamps and asset IDs.

---

### 2. Gallery Screen (Media Browser, Player, Batch Delete, Move & Rename)

The Gallery tab is a high-performance visual browser for device media.

- **Album Filtering** (`media.get_albums`): Populates dropdown with actual device albums (`Camera`, `Screenshots`, `Download`, `WhatsApp`, etc.).
- **Media Type Filtering** (`media.get_assets`): Seamlessly switch between **All**, **Images**, **Videos**, and **Audio**.
- **Pagination**: Supports high-volume libraries with page-by-page fetching (`limit`, `offset`, and "Load More" button).
- **Base64 Thumbnails** (`media.get_thumbnail`): Asynchronously fetches JPEG thumbnails for images and video frames.
- **In-App Video Player** (`flet-video`): Tap any video to launch an embedded video player dialog.
- **In-App Audio Player** (`flet-video` ExoPlayer): Tap any audio asset to play `.mp3`, `.m4a`, `.wav`, or `.aac` files directly within the app.
- **Streamlined Move Dialog** (`media.move_asset`): Select any media item and move it to standard directories (`Pictures/Archive`, `DCIM/Camera`, `Music/Recordings`, `Download`, `Movies`) or enter a custom relative path.
- **Streamlined Rename Dialog** (`media.rename_asset`): Rename display names and extensions with safety checks.
- **Single & Batch Deletion** (`media.delete_asset`, `media.delete_assets`): Toggle multi-select mode, select multiple items with checkboxes, and batch-delete them with system confirmation.

---

### 3. Capture Screen (Camera & Microphone Recording)

Demonstrates taking new media and saving it directly into the device library using MediaStore / PhotoKit insert pipelines.

- **Camera Preview & Snapshot** (`flet-camera` + `media.save_image`): Live viewfinder to take photos and immediately register them in the gallery.
- **Video Recording** (`flet-camera` + `media.save_video`): Record video clips with a live recording indicator, then save directly into `Movies/MediaLibraryDemo`.
- **Microphone Audio Recorder** (`flet-audio-recorder` + `media.save_audio`):
  - In-app microphone recording with live elapsed timer (`00:00`).
  - Encodes cleanly with `AudioEncoder.AACLC` (`.m4a`).
  - Pulsing recording activity indicator.
  - Automatically saves output into Android's shared system `Music/Recordings` directory.

---

### 4. Tools Screen (File Mutations & Smoke Checklist)

Designed for developer diagnostics, stress-testing, and compliance verification.

- **Move Asset Test**: Test moving specific asset IDs to designated target paths.
- **Rename Asset Test**: Test renaming display names.
- **Copy Asset Test** (`media.copy_asset`): Test copying an asset into an album.
- **Pick & Save Audio**: Pick any local audio file and insert it into the Android MediaStore.
- **Clear File Cache** (`media.clear_file_cache`): Clears thumbnail and temporary caches.
- **Automated Smoke Test Suite**: Executes 8 continuous automated tests in sequence:
  1. Check permissions
  2. Request permissions
  3. Fetch albums
  4. Query assets
  5. Thumbnail generation
  6. Asset detail lookup
  7. Start & stop change notification
  8. Cache purge

---

## Permissions Architecture

This demo strictly avoids requesting `MANAGE_EXTERNAL_STORAGE` ("All files access").

### Declared Manifest Permissions

```xml
<!-- Android <= 12 (API <= 32) -->
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />

<!-- Android 13+ (API 33+) -->
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
<uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />

<!-- Android 14+ (API 34+) -->
<uses-permission android:name="android.permission.READ_MEDIA_VISUAL_USER_SELECTED" />

<!-- Demo Capture Hardware -->
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

---

## Running Locally

### With Flet Mobile Client (Live Preview)

Run the local development server:

```bash
cd examples/media_library_demo
uv sync
uv run flet run src/main.py --android
```

Scan the printed QR code or enter the server address in the Flet client mobile app.

> [!TIP]
> The Flet client mobile app provides hot-reloading for rapid UI development. However, custom Flutter platform plugins (`flet_media_library`, `flet_audio_recorder`) require compiling a **standalone APK** to invoke native Android Kotlin platform channels.

### Desktop Preview

```bash
uv run flet run src/main.py
```

---

## Building Standalone Mobile Binaries

### Android APK Build

To compile a standalone APK containing all native Kotlin & Flutter plugins:

```bash
cd examples/media_library_demo

uv run flet build apk \
  --split-per-abi \
  --arch arm64-v8a \
  --source-packages ../../src/flutter/flet_media_library \
  --permissions camera microphone \
  --yes
```

The compiled APK will be output to:
`build/apk/Media Library Demo-arm64-v8a-release.apk`

### Automated CI / GitHub Actions

This repository includes an automated workflow in [`.github/workflows/build-demo-apk.yml`](../../.github/workflows/build-demo-apk.yml) with network retry handling:

- **Git Tags (`v*`)**: Automatically compiles the demo APK, packages a `.zip` archive, and publishes them directly to a **GitHub Release**.
- **Manual Dispatch (`workflow_dispatch`)**: Can be triggered on-demand from the GitHub Actions tab anytime without creating a release.

---

### Pushing & Managing Build Tags

To trigger or manage automated demo APK builds on GitHub, use the following `git` commands:

#### 1. Push a Tag to Trigger Build & Release

```bash
# Create an annotated tag (e.g. v1.0.1)
git tag -a v1.0.1 -m "Release v1.0.1"

# Push the tag to GitHub (this triggers the APK build workflow)
git push origin v1.0.1
```

> [!TIP]
> Pushing any tag matching `v*` runs `.github/workflows/build-demo-apk.yml`, compiles the `arm64-v8a` APK, and attaches the APK and ZIP files to the corresponding GitHub Release automatically.

#### 2. Delete a Tag (Cancel or Retract Build)

If you created a tag by mistake or need to delete a release tag:

```bash
# Step 1: Delete the tag locally
git tag -d v1.0.1

# Step 2: Delete the tag from the remote GitHub repository
git push origin --delete v1.0.1
```

#### 3. Update / Move an Existing Tag

If you made a commit and need to point an existing tag to the latest commit and re-trigger CI:

```bash
# Force-update the tag locally to the current commit
git tag -fa v1.0.1 -m "Release v1.0.1 (updated)"

# Force-push the updated tag to GitHub (re-triggers build)
git push origin -f v1.0.1
```


### iOS Build

```bash
uv run flet build ipa \
  --permissions camera microphone \
  --info-plist NSPhotoLibraryUsageDescription="Demo needs access to browse photos and videos." \
  --info-plist NSPhotoLibraryAddUsageDescription="Demo saves captured media to your photo library." \
  --info-plist NSCameraUsageDescription="Demo captures photos and video with your camera." \
  --info-plist NSMicrophoneUsageDescription="Demo records audio notes with your microphone."
```

---

## Key Package APIs Quick Reference

```python
# Permissions
status = await media.check_permissions(["image", "video", "audio"])
status = await media.request_permissions(["image", "video", "audio"])
await media.present_limited(["image", "video"])
await media.open_settings()

# Query & Thumbnails
albums = await media.get_albums(media_type="image")
page = await media.get_assets(media_type="image", limit=30, offset=0, sort_by="date_added", sort_order="desc")
asset = await media.get_asset(asset_id)
thumb_b64 = await media.get_thumbnail(asset_id, width=150, height=150)

# Saving Media
img_asset = await media.save_image(temp_path, file_name="photo.jpg", album="Pictures/Demo")
vid_asset = await media.save_video(temp_path, file_name="clip.mp4", album="Movies/Demo")
aud_asset = await media.save_audio(temp_path, file_name="audio.m4a", album="Music/Recordings")

# Mutations
ok = await media.rename_asset(asset_id, "new_title.jpg")
ok = await media.move_asset(asset_id, "Pictures/Archive")
ok = await media.delete_asset(asset_id)
deleted_ids = await media.delete_assets([id1, id2, id3])

# Monitoring & Maintenance
media.on_change = handle_change_event
await media.start_change_notify()
await media.stop_change_notify()
await media.clear_file_cache()
```

---

## Important Platform Notes

1. **Android 11+ Scoped Storage**:
   - `move_asset` and `rename_asset` on Android 11+ may cause the system to display a modal prompt: *"Allow Media Library Demo to modify this item?"*. This is expected Android security behavior.
2. **Audio Saving & Playback**:
   - `save_audio` inserts into `MediaStore.Audio.Media.EXTERNAL_CONTENT_URI` on Android. Audio saving is unsupported on iOS PhotoKit.
   - In-app playback uses `flet-video` (backed by ExoPlayer / media_kit), which natively supports `.mp3`, `.m4a`, `.wav`, and `.aac` files.
3. **Tracking Owned Assets**:
   - The demo application tracks asset IDs that were created or captured within the current session, displaying an `[owned]` tag in the Gallery and Tools tabs to ensure safe testing.
