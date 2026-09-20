# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Broader device matrix verification (Android 10–15, iOS)
- Dart unit tests with mocked `photo_manager`
- Optional resolved file-path API for in-app playback of library assets

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
