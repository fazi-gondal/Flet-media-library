# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Broader device matrix verification (Android 10–15, iOS)
- Dart unit tests with mocked `photo_manager`
- Physical/emulator integration tests for MediaStore, PhotoKit, permissions, delete confirmation
- Optional resolved original file-path API for in-app playback

## [1.1.0] - 2026-09-22

### Fixed
- **Permissions**: query and return per-media-type states (image/video/audio) instead of mirroring one aggregate state across all requested types.
- **Native concurrency**: Android write-consent flows (rename/move) reject concurrent pending operations instead of overwriting the first `MethodChannel.Result`; pending state is cleared cleanly on activity detach.
- **Demo recording path**: absolute writable temp only via `recording_output_path()` / `get_app_temp_dir()`; never `Path.resolve()` on `FLET_APP_STORAGE_*` (fixes MediaMuxer doubled-path `ENOENT`). Demo-only — not a library package bug.

### Added
- `get_thumbnail_path()` — cached local JPEG path for gallery-scale use without Base64 over the Flet boundary.
- `get_capabilities()` — explicit platform capability flags (`supports_audio_save`, `supports_move`, `supports_rename`, `supports_limited_access`, etc.).
- Optional `min_date_added` / `max_date_added` filters on `get_assets` (global queries).
- `relative_path` keyword on save APIs (preferred over the legacy `album` alias).

### Changed
- Android plugin toolchain: AGP 8.7.3, Kotlin 2.0.21, Java 17, compileSdk 35.
- Permission results always serialize via `toMap()` on the Dart service boundary.
- Documentation: root README, demo README, and API reference updated for 1.1.0 APIs.

## [1.0.2] - 2026-09-22

### Documentation & Architecture
- Documented public storage destination directories: photos to `DCIM/` & `Pictures/`, videos to `Movies/` & `DCIM/`, and audio directly to `Music/`.
- Clarified native architecture: `save_audio`, `rename_asset`, and `move_asset` are powered by dedicated custom Android Kotlin implementations (`FletMediaLibraryPlugin.kt`) because upstream `photo_manager` lacks these capabilities.
- Synchronized updated documentation, cookbooks, and storage architecture matrix to PyPI.

## [1.0.1] - 2026-09-21

### Documentation & Packaging
- Expanded Python compatibility constraint to `requires-python = ">=3.10"` supporting Python 3.10 through 3.14.
- Added Credits & Acknowledgments section honoring project author and upstream dependencies.
- Added direct download link for pre-compiled demo APK releases.
- Synchronized README rendering for PyPI distribution.

## [1.0.0] - 2026-09-21

First stable production release.

### Added
- Full compatibility with Flet 1.0.0 and Python 3.14.
- In-app video and audio playback support via `flet-video` integration.
- Microphone audio recording with `flet-audio-recorder` and saving directly to `Music/FletMediaLibrary`.
- Streamlined asset move & rename workflows for Android scoped storage.
- Comprehensive end-to-end demo and integration test suite.

## [0.1.0] - 2026-09-20

First public alpha on PyPI.

### Added

- **`MediaLibrary`** Flet service with a platform-neutral Python API (no
  `photo_manager` types exposed).
- **Permissions:** `check_permissions`, `request_permissions`, `open_settings`,
  `present_limited` (iOS 14+ / Android 14+ limited access).
  Purpose-specific media permissions only — **not** broad
  `MANAGE_EXTERNAL_STORAGE`.
- **Albums:** `get_albums(media_type=…)`.
- **Assets:** `get_assets` (pagination, sort, Android MIME filter), `get_asset`.
- **Thumbnails:** `get_thumbnail` → base64 JPEG for `ft.Image`.
- **Save:** `save_image`, `save_video` (Android + iOS via `photo_manager`);
  `save_audio` (Android MediaStore fallback). Inserts into the system library
  (MediaStore / PhotoKit), so a separate media-scanner step is not required for
  normal gallery saves.
- **Delete:** `delete_asset`, `delete_assets`.
- **Copy / move / rename:** platform-limited; see README matrix.
- **Change notifications:** `start_change_notify`, `stop_change_notify`,
  `on_change` → `MediaChangeEvent`.
- **Utility:** `clear_file_cache`.
- Structured errors: `PermissionRequiredError`, `PermissionDeniedError`,
  `UnsupportedError`, `AssetNotFoundError`, `AlbumNotFoundError`,
  `InvalidArgumentError`, `PlatformError`.
- Flutter plugin (`photo_manager` + small Android Kotlin fallback).
- Minimal iOS plugin registrant for Flet packaging.
- Examples: `media_library_example`, full `media_library_demo` harness.
- CI: Python tests; optional unsigned demo APK workflow.

### Fixed (pre-release hardening)

- `move_asset` / `rename_asset` return `{ok: bool}` consistently to Python.
- Validate `limit` (1–500) and `offset` (>= 0) on the Python side.
- `ensureAccess()` before query/save/delete paths.
- Richer asset/album mapping (`source_uri`, `media_types`, …).
- Soft host-side file existence check for mobile `save_*` paths.

### Notes

- Alpha quality: verify on real Android/iOS devices before production use.
- Format support follows the OS media library (not every container/codec).
- Prefer mainstream formats for saves (e.g. MP4, JPEG/PNG, MP3/M4A).

[Unreleased]: https://github.com/fazi-gondal/Flet-media-library/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/fazi-gondal/Flet-media-library/releases/tag/v0.1.0
