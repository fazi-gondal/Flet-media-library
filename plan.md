# MASTER PROMPT — Build Flet Media Library

You are a senior Flutter/Dart, Android/Kotlin, Python and Flet framework engineer.

Build a production-quality Flet extension named:

    flet-media-library

The goal is to create a cross-platform media-library extension for Flet applications, inspired by the capabilities of Expo MediaLibrary, but designed specifically around Flet's current extension/service architecture and the Flutter ecosystem.

IMPORTANT:
Do not blindly copy the existing flet-media-scanner implementation.
Use it as a reference for API behavior, Flet integration, and Android functionality, but redesign the architecture around the Flutter package `photo_manager`.

============================================================
1. EXISTING PROJECT TO STUDY
============================================================

Existing repository:

https://github.com/fazi-gondal/flet-media-scanner

Before writing code:

1. Inspect the complete repository.
2. Inspect README.md.
3. Inspect all Python files.
4. Inspect all Dart files.
5. Inspect all Kotlin files.
6. Inspect pyproject.toml.
7. Inspect Flet extension configuration.
8. Inspect tests.
9. Inspect Git history and recent commits.
10. Understand the current v1.7 API and behavior.

The existing project is an Android MediaStore implementation and should be treated as the reference implementation.

Do NOT destroy or modify the existing repository.

The new project must be a separate project/repository:

    flet-media-library

============================================================
2. PRIMARY ARCHITECTURAL GOAL
============================================================

The old project approximately follows:

    Flet Python
        ↓
    Dart Flet extension
        ↓
    Kotlin
        ↓
    Android MediaStore

The new project must instead use:

    Flet Python
        ↓
    Flet Media Library Dart API
        ↓
    photo_manager
        ↓
    Android MediaStore / iOS PhotoKit / macOS Photos

Use `photo_manager` as the PRIMARY media backend.

Do NOT implement MediaStore/PhotoKit functionality manually when `photo_manager` already provides the required functionality.

Native platform code should exist ONLY when:

1. photo_manager does not expose a required capability;
2. photo_manager exposes the capability but cannot provide the behavior required by Flet;
3. a platform-specific operation is necessary;
4. a compatibility workaround is required.

The native implementation must therefore be a SMALL FALLBACK LAYER, not the main architecture.

============================================================
3. CORE DESIGN PRINCIPLE
============================================================

The Flet API must NOT expose photo_manager's classes directly.

Do NOT expose:

    AssetEntity
    AssetPathEntity
    PermissionState
    PhotoManager

to Python.

Instead create Flet-owned models:

    MediaAsset
    MediaAlbum
    MediaPermission
    MediaQuery
    MediaChangeEvent

Architecture:

    photo_manager
         ↓
    adapter layer
         ↓
    Flet domain models
         ↓
    Dart Flet service
         ↓
    Python API

This ensures Flet developers are not coupled to photo_manager.

If photo_manager is replaced in the future, the public Flet API should not need to change.

============================================================
4. PACKAGE NAME
============================================================

Project name:

    flet-media-library

Python package:

    flet-media-library

Python import:

    from flet_media_library import MediaLibrary

Primary Dart package/extension:

    flet_media_library

Service/control name:

    MediaLibrary

Do not use the old name:

    MediaScanner

The old repository remains:

    flet-media-scanner

The new project is:

    flet-media-library

============================================================
5. TARGET PLATFORMS
============================================================

Primary targets:

    Android
    iOS

Potential future target:

    macOS

Do not compromise Android functionality just to force macOS support.

The public API should be cross-platform where possible.

Platform-specific behavior must be documented clearly.

============================================================
6. PHOTO_MANAGER
============================================================

Use:

    photo_manager: ^3.12.0

Before implementation, inspect the actual installed/latest compatible API and documentation.

Do not assume APIs from memory.

Verify:

- permissions
- AssetEntity
- AssetPathEntity
- asset queries
- pagination
- filtering
- sorting
- thumbnails
- file access
- delete
- copy
- move
- rename
- album operations
- change notification
- save/copy APIs
- Android-specific APIs
- iOS-specific APIs

If the package version has changed, use the latest compatible stable version only if doing so does not break the requested architecture. Otherwise pin the requested version.

============================================================
7. PUBLIC PYTHON API
============================================================

Create a clean Python-first API.

Example:

    media = MediaLibrary()

    page.services.append(media)

Permissions:

    permissions = await media.check_permissions()

    permissions = await media.request_permissions()

Assets:

    result = await media.get_assets(
        media_type="video",
        album=None,
        mime_type=None,
        limit=50,
        offset=0,
        sort_by="date_added",
        sort_order="desc",
    )

Albums:

    albums = await media.get_albums()

Asset operations:

    await media.delete_asset(asset_id)

    await media.delete_assets(asset_ids)

    await media.copy_asset(asset_id, destination)

    await media.move_asset(asset_id, destination)

    await media.rename_asset(asset_id, new_name)

Thumbnails:

    await media.get_thumbnail(
        asset_id,
        width=300,
        height=300,
    )

Events:

    media.on_change = callback

Saving:

    await media.save_image(...)
    await media.save_video(...)
    await media.save_audio(...)

The exact API can be improved after inspecting the existing v1.7 implementation and photo_manager APIs, but maintain a consistent Python-first design.

============================================================
8. MEDIA TYPES
============================================================

Support:

    image
    video
    audio
    all

Do not require users to know MIME types for normal use.

Example:

    media_type="video"

Internally map to photo_manager asset types.

============================================================
9. MEDIA ASSET MODEL
============================================================

Create a Flet-owned MediaAsset model.

Recommended fields:

    id
    display_name
    mime_type
    media_type
    size
    width
    height
    duration
    date_added
    date_modified
    orientation
    album_id
    album_name
    relative_path
    source_uri

IMPORTANT:

Do not make Android's `content://` URI mandatory for the cross-platform API.

The primary identifier must be:

    MediaAsset.id

On Android it may internally map to MediaStore.
On iOS it may map to PHAsset.localIdentifier.

The public API must remain platform-neutral.

If a platform-specific URI is useful, expose it as optional metadata.

============================================================
10. MEDIA ALBUM MODEL
============================================================

Create:

    MediaAlbum

Recommended fields:

    id
    name
    asset_count
    media_type
    is_system_album
    relative_path
    platform_identifier

Do not expose AssetPathEntity directly.

============================================================
11. PERMISSION SYSTEM
============================================================

Create:

    MediaPermission

Support:

    granted
    limited
    denied
    restricted
    unknown
    can_request

The API should support requesting only the required media types.

Example:

    await media.request_permissions(
        media_types=["image", "video"]
    )

Do not request audio permission when only images are needed.

Use photo_manager permission APIs as the primary implementation.

Handle Android and iOS differences internally.

The Python developer should NOT need to understand:

    READ_EXTERNAL_STORAGE
    READ_MEDIA_IMAGES
    READ_MEDIA_VIDEO
    READ_MEDIA_AUDIO
    PhotoKit authorization
    limited photo access

The extension abstracts all of this.

============================================================
12. ASSET QUERY SYSTEM
============================================================

Implement:

    get_assets()

Support:

    media_type
    album
    mime_type
    limit
    offset
    sort_by
    sort_order

Potential filters:

    date_added
    date_modified
    size
    display_name
    media type
    MIME type

Use photo_manager's query/filter APIs instead of implementing a custom MediaStore query engine.

Pagination must be efficient.

Do not load thousands of assets into memory unnecessarily.

============================================================
13. PAGINATION
============================================================

Support:

    limit
    offset

Internally use photo_manager's paged/range query APIs where possible.

Do not fetch the entire library just to return the first 50 results.

Return a structured result:

    MediaAssetPage

Recommended:

    items
    total
    offset
    limit
    has_more

============================================================
14. ALBUMS
============================================================

Implement:

    get_albums()

Support album-specific asset queries.

If photo_manager supports creating/renaming/deleting albums on a given platform, expose those capabilities only where reliable.

Do NOT pretend an operation is cross-platform if it is not.

Return meaningful unsupported errors.

============================================================
15. THUMBNAILS
============================================================

Implement:

    get_thumbnail()

Support:

    images
    videos

Use photo_manager's thumbnail APIs/caching.

Do not implement Android-only thumbnail generation unless photo_manager cannot provide the required functionality.

Return a Flet-friendly representation suitable for displaying in an Image control.

Avoid unnecessary base64 copies when a more efficient mechanism is available.

============================================================
16. CHANGE NOTIFICATIONS
============================================================

Implement:

    on_change

Use photo_manager's change notification system.

Do not recreate the entire Android ContentObserver implementation unless photo_manager does not provide the required behavior.

Create:

    MediaChangeEvent

Possible fields:

    change_type
    asset_id
    media_type
    timestamp

Support:

    added
    modified
    deleted

If photo_manager only provides a broader change notification, document that accurately instead of pretending exact change details exist.

============================================================
17. DELETE
============================================================

Implement:

    delete_asset()
    delete_assets()

Use photo_manager's deletion APIs.

Support batch deletion.

Handle platform authorization requirements correctly.

Never silently claim success if Android/iOS requires user confirmation.

Return structured results.

============================================================
18. MOVE
============================================================

Implement:

    move_asset()

Use photo_manager first.

IMPORTANT:

Android may impose platform-specific restrictions depending on:

    Android version
    ownership of the media
    target location
    permission state
    scoped storage rules

Do not assume move is universally available.

If photo_manager can perform the operation:

    use photo_manager

If it cannot:

    use a minimal Android native fallback

The fallback must be isolated.

Do NOT recreate the entire MediaStore implementation.

Return structured result:

    success
    unsupported
    requires_permission
    failed

============================================================
19. RENAME
============================================================

Implement:

    rename_asset()

Prefer photo_manager.

If unavailable for a platform/version:

    use native fallback only where required.

Keep the fallback isolated.

============================================================
20. COPY
============================================================

Implement:

    copy_asset()

Prefer photo_manager.

Document platform-specific behavior.

============================================================
21. SAVE MEDIA
============================================================

Implement:

    save_image()
    save_video()
    save_audio()

Use photo_manager APIs where possible.

Support:

    source file
    destination album
    display name

Avoid hard-coded Android filesystem paths.

Use Flet StoragePaths where appropriate for locating application-generated files.

============================================================
22. STORAGE PATHS
============================================================

Use Flet's StoragePaths APIs instead of hardcoded paths.

The extension must not assume:

    /data/data/...
    /storage/emulated/0/...

Use platform-safe paths.

============================================================
23. ERROR HANDLING
============================================================

Never silently fail.

Create structured errors.

Recommended categories:

    permission_denied
    permission_required
    unsupported
    asset_not_found
    album_not_found
    invalid_argument
    platform_error
    operation_failed

Error messages must be useful to Python developers.

Do not leak unnecessary Android stack traces to normal users.

============================================================
24. NATIVE FALLBACK ARCHITECTURE
============================================================

If Kotlin is required, isolate it:

    android/
        src/main/kotlin/
            .../fallback/

Do NOT recreate:

    entire MediaStore query system
    entire permission system
    entire asset model
    entire album system
    entire thumbnail system

Only implement missing capabilities.

Use the smallest possible MethodChannel interface.

Example:

    Flet Dart
       ↓
    NativeFallback
       ↓
    Kotlin
       ↓
    Android API

Native code should be considered an escape hatch.

============================================================
25. DART ARCHITECTURE
============================================================

Use a proper structure.

Example:

    lib/
        flet_media_library.dart

        src/
            media_library.dart
            models/
                media_asset.dart
                media_album.dart
                media_permission.dart
                media_asset_page.dart
                media_change_event.dart

            adapters/
                photo_manager_adapter.dart

            services/
                permission_service.dart
                asset_service.dart
                album_service.dart
                thumbnail_service.dart
                media_service.dart
                change_service.dart

            native/
                native_fallback.dart

Do not put the entire implementation in one Dart file.

============================================================
26. PYTHON ARCHITECTURE
============================================================

Use multiple files.

Example:

    flet_media_library/
        __init__.py
        media_library.py
        models.py
        permissions.py
        exceptions.py

Keep Python thin.

Python should primarily:

    expose the Flet API
    serialize arguments
    receive results
    expose events

Do not put Android implementation logic into Python.

============================================================
27. FLET EXTENSION ARCHITECTURE
============================================================

Use the current Flet extension/service architecture.

Before implementation:

1. Inspect the latest Flet repository.
2. Inspect current extension examples.
3. Inspect Flet 0.86+ extension/service APIs.
4. Follow the actual current API rather than relying on old tutorials.

Do not invent APIs.

Verify:

    pyproject.toml
    tool.flet.extensions
    Dart package structure
    service registration
    event handling
    async calls
    serialization

============================================================
28. PERFORMANCE
============================================================

This is a media library and may contain:

    10,000+
    50,000+
    100,000+

assets.

Design accordingly.

Requirements:

- paginated queries
- no full-library loading
- avoid unnecessary serialization
- avoid large base64 payloads
- thumbnail caching
- efficient event handling
- asynchronous operations
- avoid blocking Flet UI
- avoid repeated permission queries
- avoid repeated album queries when unnecessary

============================================================
29. CROSS-PLATFORM DESIGN
============================================================

The public API should be platform-neutral.

Do NOT expose:

    MediaStore
    ContentResolver
    PHAsset
    PHAssetCollection
    Android URI

as primary Flet API concepts.

Internally these are allowed.

Public API:

    MediaAsset
    MediaAlbum
    MediaPermission
    MediaLibrary

============================================================
30. ANDROID COMPATIBILITY
============================================================

Test at minimum:

    Android 10
    Android 11
    Android 12
    Android 13
    Android 14
    Android 15
    current Android version available in the development environment

Pay special attention to:

    scoped storage
    READ_MEDIA_*
    photo picker
    user authorization
    MediaStore
    relative paths
    deletion
    moving
    renaming

============================================================
31. IOS COMPATIBILITY
============================================================

Implement iOS through photo_manager.

Test:

    permission request
    limited access
    albums
    images
    videos
    assets
    thumbnails
    deletion
    change notification

Do not write Swift unless photo_manager does not provide the required capability.

============================================================
32. TESTING
============================================================

Create tests.

Python:

    API serialization
    validation
    result parsing
    error handling

Dart:

    adapter tests
    model tests
    serialization tests
    mock photo_manager behavior

Android:

    permissions
    querying
    saving
    deletion
    rename
    move
    thumbnails
    observer

iOS:

    permissions
    assets
    albums
    thumbnails
    deletion
    observer

Do not claim platform functionality is tested if it has not actually been tested.

============================================================
33. COMPATIBILITY TEST
============================================================

The new project must be compared against the old:

    flet-media-scanner v1.7

Create a compatibility checklist.

For every old feature:

    implemented
    replaced
    improved
    unsupported
    platform-specific

Nothing should be accidentally lost.

============================================================
34. DOCUMENTATION
============================================================

Create a professional README.

Include:

- What is Flet Media Library?
- Why it exists
- Architecture
- Installation
- Android setup
- iOS setup
- Permissions
- Basic usage
- Querying assets
- Albums
- Pagination
- Thumbnails
- Save
- Delete
- Move
- Rename
- Copy
- Change notifications
- Platform differences
- Android restrictions
- iOS limited access
- API reference
- Examples
- Troubleshooting
- Development
- Testing
- Contributing
- License

Clearly explain that the library is powered primarily by `photo_manager`.

Do not advertise unsupported functionality.

============================================================
35. DOCUMENTATION STYLE
============================================================

Write documentation like a senior open-source maintainer.

Do not use marketing language such as:

    "revolutionary"
    "best"
    "perfect"
    "zero limitations"

Be technically accurate.

Explain platform limitations honestly.

============================================================
36. VERSIONING
============================================================

Start the new project at:

    0.1.0

Do NOT start at 1.0.0.

Reason:

This is a new architecture.

Use semantic versioning.

Suggested:

    0.1.x development
    0.2.x API stabilization
    0.9.x release candidate
    1.0.0 stable

============================================================
37. LICENSE AND ATTRIBUTION
============================================================

Inspect the existing project's license.

Preserve appropriate licensing.

Check photo_manager's license and requirements.

Do not copy source code from photo_manager.

Use it as a dependency.

Add appropriate attribution where required.

============================================================
38. SECURITY AND PRIVACY
============================================================

Media libraries access sensitive user content.

Follow least privilege.

Do not request:

    image
    video
    audio

permissions unless required.

Do not upload media anywhere.

Do not copy media unnecessarily.

Do not expose raw filesystem paths unless needed.

Do not log sensitive media information.

============================================================
39. CODE QUALITY
============================================================

Use:

    Dart formatter
    Dart analyzer
    Python formatter
    Python type checking where appropriate
    linting
    tests

No:

    dead code
    duplicated implementations
    unnecessary platform code
    hard-coded paths
    magic constants
    huge files
    God classes
    TODO placeholders for core functionality

============================================================
40. DEVELOPMENT WORKFLOW
============================================================

Before implementing:

PHASE 1:
Inspect old repository.

PHASE 2:
Inspect Flet extension architecture.

PHASE 3:
Inspect photo_manager 3.12.0 APIs.

PHASE 4:
Create architecture document.

PHASE 5:
Create new project skeleton.

PHASE 6:
Implement permissions.

PHASE 7:
Implement assets and pagination.

PHASE 8:
Implement albums.

PHASE 9:
Implement thumbnails.

PHASE 10:
Implement change notifications.

PHASE 11:
Implement save/delete/copy.

PHASE 12:
Implement rename/move.

PHASE 13:
Add native fallback only for missing capabilities.

PHASE 14:
Implement iOS.

PHASE 15:
Testing.

PHASE 16:
Documentation.

============================================================
41. IMPORTANT: DO NOT OVERENGINEER
============================================================

Do not implement native functionality simply because it is possible.

Before writing Kotlin/Swift:

Ask:

    Does photo_manager already provide this?

If yes:

    use photo_manager.

If partially:

    wrap photo_manager and add only the missing behavior.

If no:

    implement a minimal native fallback.

============================================================
42. IMPORTANT: DO NOT BREAK THE PUBLIC API
============================================================

The Flet API should be stable and intuitive.

Prefer:

    MediaLibrary
    MediaAsset
    MediaAlbum
    MediaPermission

Avoid leaking implementation details.

============================================================
43. FINAL ARCHITECTURE TARGET
============================================================

The desired final architecture is:

                         Python
                           │
                           ▼
                  Flet MediaLibrary
                           │
                           ▼
                         Dart
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
          photo_manager       Native fallback
                 │                   │
        ┌────────┴────────┐         │
        ▼                 ▼         ▼
     Android             iOS     Android
    MediaStore          PhotoKit  API gaps


The majority of the platform functionality must come from
photo_manager.

Native Kotlin must be a targeted fallback, not the primary
implementation.

============================================================
44. FINAL DELIVERABLE
============================================================

Produce a complete working repository.

Expected structure:

    flet-media-library/
    ├── .github/
    │   └── workflows/
    ├── flet_media_library/
    ├── lib/
    ├── android/
    ├── ios/
    ├── test/
    ├── example/
    ├── pyproject.toml
    ├── pubspec.yaml
    ├── README.md
    ├── CHANGELOG.md
    ├── LICENSE
    └── ...

Do not stop at a skeleton.

Implement the actual functionality.

============================================================
45. FINAL QUALITY GATE
============================================================

Before declaring the project complete, verify:

[ ] Flet extension builds
[ ] Python package builds
[ ] Dart analyzer passes
[ ] Dart formatter passes
[ ] Python tests pass
[ ] Dart tests pass
[ ] Android build succeeds
[ ] iOS project integrates correctly
[ ] photo_manager is correctly integrated
[ ] Permissions work
[ ] Images work
[ ] Videos work
[ ] Audio works
[ ] Albums work
[ ] Pagination works
[ ] Filtering works
[ ] Sorting works
[ ] Metadata works
[ ] Thumbnails work
[ ] Video thumbnails work
[ ] Change notifications work
[ ] Delete works
[ ] Batch delete works
[ ] Copy works
[ ] Rename works where supported
[ ] Move works where supported
[ ] Native fallback only exists where necessary
[ ] No unnecessary Kotlin implementation remains
[ ] No unnecessary Swift implementation remains
[ ] Android version differences are documented
[ ] iOS permission differences are documented
[ ] README is complete
[ ] Old v1.7 functionality has been audited
[ ] No platform-specific implementation is exposed unnecessarily
[ ] No hard-coded filesystem paths
[ ] No large unnecessary base64 transfers
[ ] No unhandled permission failures
[ ] No fake/placeholder APIs

============================================================
46. MOST IMPORTANT INSTRUCTION
============================================================

Do not rush into implementation.

First inspect:

1. flet-media-scanner
2. current Flet extension architecture
3. current Flet 0.86+ APIs
4. photo_manager 3.12.0 APIs

Then produce a concise implementation plan.

After the plan, implement the project incrementally.

When a photo_manager feature is available, USE IT.

When it is not available, implement the smallest possible native fallback.

The final result should feel like an official-quality Flet ecosystem package rather than a Python wrapper around an Android application.

The project must be maintainable by future Flet contributors and should minimize platform-specific code.