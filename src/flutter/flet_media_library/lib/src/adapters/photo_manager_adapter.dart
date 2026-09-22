import 'dart:io';

import 'package:flutter/services.dart';
import 'package:photo_manager/photo_manager.dart';

import '../models/media_errors.dart';
import '../models/media_models.dart';
import '../models/media_permissions.dart';
import '../native/native_fallback.dart';

/// Single seam between Flet domain models and the photo_manager backend.
///
/// This is the only place that imports photo_manager types; replacing the
/// backend means rewriting this class only.
class PhotoManagerAdapter {
  final NativeFallback _fallback = NativeFallback();

  // ─────────────────────────────── permissions ──────────────────────────────

  RequestType _requestTypeFromMediaTypes(List<String> mediaTypes) {
    var type = const RequestType(0);
    for (final t in mediaTypes) {
      switch (t) {
        case "image":
          type |= RequestType.image;
        case "video":
          type |= RequestType.video;
        case "audio":
          type |= RequestType.audio;
        case "all":
          return RequestType.common;
        default:
          throw MediaLibraryException(
            MediaErrorCodes.invalidArgument,
            "Unknown media type '$t'. Use 'image', 'video', 'audio' or 'all'.",
          );
      }
    }
    if (type.value == 0) {
      return RequestType.common;
    }
    return type;
  }

  MediaPermissionState _mapPermissionState(PermissionState state) =>
      switch (state) {
        PermissionState.authorized => MediaPermissionState.granted,
        PermissionState.limited => MediaPermissionState.limited,
        PermissionState.denied => MediaPermissionState.denied,
        PermissionState.restricted => MediaPermissionState.restricted,
        PermissionState.notDetermined => MediaPermissionState.unknown,
      };

  /// Expand "all" into the concrete media types so callers always receive
  /// per-type states when the platform can report them independently.
  List<String> _expandMediaTypes(List<String> mediaTypes) {
    if (mediaTypes.contains("all") || mediaTypes.isEmpty) {
      return const ["image", "video", "audio"];
    }
    // Preserve order, drop duplicates.
    final seen = <String>{};
    final out = <String>[];
    for (final t in mediaTypes) {
      if (t == "image" || t == "video" || t == "audio") {
        if (seen.add(t)) out.add(t);
      } else if (t != "all") {
        throw MediaLibraryException(
          MediaErrorCodes.invalidArgument,
          "Unknown media type '$t'. Use 'image', 'video', 'audio' or 'all'.",
        );
      }
    }
    return out.isEmpty ? const ["image", "video", "audio"] : out;
  }

  Future<MediaPermissionState> _permissionStateForType(String mediaType) async {
    final requestType = _requestTypeFromMediaTypes([mediaType]);
    final state = await PhotoManager.getPermissionState(
      requestOption: PermissionRequestOption(
        androidPermission: AndroidPermission(
          type: requestType,
          mediaLocation: false,
        ),
      ),
    );
    return _mapPermissionState(state);
  }

  Future<MediaPermissionsResult> checkPermissions(
    List<String> mediaTypes,
  ) async {
    final types = _expandMediaTypes(mediaTypes);
    // Query each type independently so Android 13+ granular READ_MEDIA_*
    // (and any future per-type states) are not collapsed into one aggregate.
    final states = <String, MediaPermissionState>{};
    for (final t in types) {
      states[t] = await _permissionStateForType(t);
    }
    return _permissionResultFromStates(states);
  }

  Future<MediaPermissionsResult> requestPermissions(
    List<String> mediaTypes,
  ) async {
    final types = _expandMediaTypes(mediaTypes);
    // Request the combined type once (single system dialog), then re-check
    // each type so the returned map reflects actual per-type outcomes.
    final requestType = _requestTypeFromMediaTypes(types);
    await PhotoManager.requestPermissionExtend(
      requestOption: PermissionRequestOption(
        androidPermission: AndroidPermission(
          type: requestType,
          mediaLocation: false,
        ),
      ),
    );
    final states = <String, MediaPermissionState>{};
    for (final t in types) {
      states[t] = await _permissionStateForType(t);
    }
    return _permissionResultFromStates(states);
  }

  MediaPermissionsResult _permissionResultFromStates(
    Map<String, MediaPermissionState> states,
  ) {
    final canRequest = states.values.any(
      (s) =>
          s == MediaPermissionState.denied ||
          s == MediaPermissionState.unknown,
    );
    return MediaPermissionsResult(states: states, canRequest: canRequest);
  }

  Future<void> openSettings() => PhotoManager.openSetting();

  Future<void> presentLimited(List<String> mediaTypes) async {
    if (!(Platform.isIOS || Platform.isAndroid)) {
      throw const MediaLibraryException(
        MediaErrorCodes.unsupported,
        "present_limited() is only available on iOS and Android 14+.",
      );
    }
    await PhotoManager.presentLimited(
      type: _requestTypeFromMediaTypes(mediaTypes),
    );
  }

  /// Throws unless access has been granted (fully or limited).
  Future<void> ensureAccess({String mediaType = "all"}) async {
    final result = await checkPermissions([mediaType]);
    final state = result.states.values.first;
    if (state != MediaPermissionState.granted &&
        state != MediaPermissionState.limited) {
      throw const MediaLibraryException(
        MediaErrorCodes.permissionRequired,
        "Media library access has not been granted. "
        "Call request_permissions() first.",
      );
    }
  }

  // ───────────────────────────────── albums ──────────────────────────────────

  Future<List<MediaAlbum>> getAlbums({
    List<String> mediaTypes = const ["all"],
  }) async {
    await ensureAccess(
      mediaType: mediaTypes.contains("all") ? "all" : mediaTypes.first,
    );
    final requestType = _requestTypeFromMediaTypes(mediaTypes);
    final paths = await PhotoManager.getAssetPathList(
      hasAll: true,
      type: requestType,
    );
    return Future.wait(paths.map((p) => _mapAlbum(p, mediaTypes)));
  }

  Future<MediaAlbum> _mapAlbum(
    AssetPathEntity path,
    List<String> requestedTypes,
  ) async {
    // System albums are the "All" bucket and other non-user collections.
    // photo_manager does not expose a dedicated flag, so treat isAll as system.
    final isSystem = path.isAll;
    final types = requestedTypes.contains("all")
        ? const ["image", "video", "audio"]
        : List<String>.from(requestedTypes);
    return MediaAlbum(
      id: path.id,
      name: path.name,
      assetCount: await path.assetCountAsync,
      mediaTypes: types,
      isAll: path.isAll,
      isSystemAlbum: isSystem,
      platformIdentifier: path.id,
    );
  }

  Future<AssetPathEntity> _loadAlbum(String albumId, RequestType type) async {
    try {
      return await AssetPathEntity.fromId(albumId, type: type);
    } catch (_) {
      throw MediaLibraryException(
        MediaErrorCodes.albumNotFound,
        "Album '$albumId' does not exist or is not accessible.",
      );
    }
  }

  // ───────────────────────────────── assets ──────────────────────────────────

  static const int maxPageLimit = 500;

  Future<Map<String, dynamic>> getAssets({
    String mediaType = "all",
    String? albumId,
    String? mimeType,
    int limit = 50,
    int offset = 0,
    String sortBy = "date_added",
    String sortOrder = "desc",
    int? minDateAdded,
    int? maxDateAdded,
  }) async {
    if (limit < 1 || limit > maxPageLimit) {
      throw MediaLibraryException(
        MediaErrorCodes.invalidArgument,
        "limit must be between 1 and $maxPageLimit.",
      );
    }
    if (offset < 0) {
      throw const MediaLibraryException(
        MediaErrorCodes.invalidArgument,
        "offset must be >= 0.",
      );
    }
    await ensureAccess(mediaType: mediaType);
    // Album queries go through AssetPathEntity, which only supports the
    // classical FilterOptionGroup orders (create/update date).
    final dateSort = sortBy == "date_added" || sortBy == "date_modified";
    if (albumId != null && albumId.isNotEmpty && !dateSort) {
      throw MediaLibraryException(
        MediaErrorCodes.unsupported,
        "Sorting by '$sortBy' is only available when querying all assets "
        "(no album), because it relies on platform SQL columns.",
      );
    }

    final requestType = _requestTypeFromMediaTypes([mediaType]);

    final int total;
    List<AssetEntity> entities;
    if (albumId != null && albumId.isNotEmpty) {
      if (mimeType != null && mimeType.isNotEmpty) {
        throw const MediaLibraryException(
          MediaErrorCodes.unsupported,
          "mime_type filtering is not available inside a single album. "
          "Query the album without mime_type and filter afterwards.",
        );
      }
      final path = await AssetPathEntity.fromId(
        albumId,
        type: requestType,
        filterOption: FilterOptionGroup(
          orders: [
            OrderOption(
              type: sortBy == "date_modified"
                  ? OrderOptionType.updateDate
                  : OrderOptionType.createDate,
              asc: sortOrder == "asc",
            ),
          ],
        ),
      );
      total = await path.assetCountAsync;
      entities = await path.getAssetListRange(
        start: offset,
        end: offset + limit,
      );
    } else {
      final filter = _buildGlobalFilter(
        sortBy: sortBy,
        sortOrder: sortOrder,
        mimeType: mimeType,
        minDateAdded: minDateAdded,
        maxDateAdded: maxDateAdded,
      );
      total = await PhotoManager.getAssetCount(
        type: requestType,
        filterOption: filter,
      );
      entities = await PhotoManager.getAssetListRange(
        start: offset,
        end: offset + limit,
        type: requestType,
        filterOption: filter,
      );
    }

    final assets = <Map<String, dynamic>>[];
    for (final entity in entities) {
      assets.add((await _mapAsset(entity)).toMap());
    }

    return {
      "items": assets,
      "total": total,
      "offset": offset,
      "limit": limit,
      "has_more": offset + entities.length < total,
    };
  }

  Future<MediaAsset> getAsset(String assetId) async {
    await ensureAccess();
    return _mapAsset(await _requireAsset(assetId));
  }

  /// Global (no-album) filter: SQL-based, so MIME filtering and
  /// display_name/size/duration sorts are Android-only; PhotoKit exposes no
  /// equivalent columns.
  PMFilter _buildGlobalFilter({
    required String sortBy,
    required String sortOrder,
    required String? mimeType,
    int? minDateAdded,
    int? maxDateAdded,
  }) {
    final asc = sortOrder == "asc";
    final filter = AdvancedCustomFilter();

    if (mimeType != null && mimeType.isNotEmpty) {
      if (!Platform.isAndroid) {
        throw const MediaLibraryException(
          MediaErrorCodes.unsupported,
          "mime_type filtering is only supported on Android. "
          "PhotoKit does not expose a MIME column.",
        );
      }
      filter.addWhereCondition(
        ColumnWhereCondition(
          column: CustomColumns.android.mimeType,
          value: mimeType,
          operator: "=",
        ),
      );
    }

    // date_added is unix seconds, matching MediaAsset.date_added.
    if (minDateAdded != null) {
      filter.addWhereCondition(
        ColumnWhereCondition(
          column: CustomColumns.base.createDate,
          value: "$minDateAdded",
          operator: ">=",
        ),
      );
    }
    if (maxDateAdded != null) {
      filter.addWhereCondition(
        ColumnWhereCondition(
          column: CustomColumns.base.createDate,
          value: "$maxDateAdded",
          operator: "<=",
        ),
      );
    }

    filter.addOrderBy(column: _orderColumn(sortBy), isAsc: asc);
    return filter;
  }

  String _orderColumn(String sortBy) {
    switch (sortBy) {
      case "date_added":
        return CustomColumns.base.createDate;
      case "date_modified":
        return CustomColumns.base.modifiedDate;
      case "duration":
        return CustomColumns.base.duration;
      case "display_name":
        if (!Platform.isAndroid) {
          throw const MediaLibraryException(
            MediaErrorCodes.unsupported,
            "Sorting by display_name is only supported on Android.",
          );
        }
        return CustomColumns.android.displayName;
      case "size":
        if (!Platform.isAndroid) {
          throw const MediaLibraryException(
            MediaErrorCodes.unsupported,
            "Sorting by size is only supported on Android.",
          );
        }
        return CustomColumns.android.size;
      default:
        throw MediaLibraryException(
          MediaErrorCodes.invalidArgument,
          "Unknown sort_by value '$sortBy'. Use date_added, date_modified, "
          "display_name, size or duration.",
        );
    }
  }

  Future<MediaAsset> _mapAsset(AssetEntity entity) async {
    // fileSize is a separate native lookup; tolerate failures per-asset.
    int size = 0;
    try {
      size = await entity.fileSize;
    } catch (_) {}

    final relativePath = entity.relativePath ?? "";
    final albumSegments = relativePath
        .split("/")
        .where((s) => s.isNotEmpty)
        .toList();
    final albumName = albumSegments.isNotEmpty ? albumSegments.last : "";

    // Prefer a stable platform URI when available (Android content://,
    // iOS localIdentifier-style id). Never required by the public API.
    String sourceUri = "";
    try {
      // entity.id is the canonical cross-platform identifier.
      // On Android it maps to MediaStore _id; expose a content URI hint.
      if (Platform.isAndroid && entity.id.isNotEmpty) {
        final typeDir = switch (entity.type) {
          AssetType.image => "images/media",
          AssetType.video => "video/media",
          AssetType.audio => "audio/media",
          AssetType.other => "file/media",
        };
        sourceUri = "content://media/external/$typeDir/${entity.id}";
      } else if (entity.id.isNotEmpty) {
        sourceUri = entity.id;
      }
    } catch (_) {}

    return MediaAsset(
      id: entity.id,
      displayName: await entity.titleAsync,
      mimeType: entity.mimeType ?? "",
      mediaType: switch (entity.type) {
        AssetType.image => "image",
        AssetType.video => "video",
        AssetType.audio => "audio",
        AssetType.other => "",
      },
      size: size,
      width: entity.width,
      height: entity.height,
      // photo_manager reports duration in seconds; Python API uses ms.
      durationMs: entity.duration * 1000,
      dateAdded: entity.createDateSecond ?? 0,
      dateModified: entity.modifiedDateSecond ?? 0,
      orientation: entity.orientation,
      // photo_manager does not expose a single parent album id on AssetEntity;
      // relative path last segment is the best portable album name hint.
      albumId: "",
      albumName: albumName,
      relativePath: relativePath,
      sourceUri: sourceUri,
    );
  }

  // ─────────────────────────────── thumbnails ────────────────────────────────

  Future<Uint8List?> getThumbnail(
    String assetId, {
    int width = 200,
    int height = 200,
    int quality = 90,
  }) async {
    await ensureAccess();
    final entity = await _requireAsset(assetId);
    return entity.thumbnailDataWithSize(
      ThumbnailSize(width, height),
      format: ThumbnailFormat.jpeg,
      quality: quality.clamp(0, 100),
    );
  }

  /// Writes a JPEG thumbnail to a stable cache path and returns that path.
  ///
  /// Prefer this over [getThumbnail] for large galleries: the path can be
  /// handed to native image widgets without shipping Base64 through the
  /// Flet/Python boundary on every scroll.
  Future<String?> getThumbnailPath(
    String assetId, {
    int width = 200,
    int height = 200,
    int quality = 90,
  }) async {
    await ensureAccess();
    final entity = await _requireAsset(assetId);
    final bytes = await entity.thumbnailDataWithSize(
      ThumbnailSize(width, height),
      format: ThumbnailFormat.jpeg,
      quality: quality.clamp(0, 100),
    );
    if (bytes == null || bytes.isEmpty) return null;

    final cacheDir = Directory(
      '${Directory.systemTemp.path}/flet_media_library_thumbs',
    );
    if (!await cacheDir.exists()) {
      await cacheDir.create(recursive: true);
    }
    // Include size/quality in the key so different request params do not collide.
    final file = File(
      '${cacheDir.path}/${assetId}_${width}x${height}_q$quality.jpg',
    );
    if (!await file.exists()) {
      await file.writeAsBytes(bytes, flush: true);
    }
    return file.path;
  }

  Future<AssetEntity> _requireAsset(String assetId) async {
    final entity = await AssetEntity.fromId(assetId);
    if (entity == null) {
      throw MediaLibraryException(
        MediaErrorCodes.assetNotFound,
        "Asset '$assetId' does not exist or is not accessible.",
      );
    }
    return entity;
  }

  // ──────────────────────────────── saving ───────────────────────────────────

  Future<MediaAsset> saveImage(
    String filePath, {
    String? filename,
    String? relativePath,
  }) async {
    try {
      // Write access is gated by the add-only / full library permission.
      await ensureAccess(mediaType: "image");
      final entity = await PhotoManager.editor.saveImageWithPath(
        filePath,
        title: filename,
        relativePath: relativePath,
      );
      return await _mapAsset(entity);
    } on MediaLibraryException {
      rethrow;
    } catch (e) {
      throw MediaLibraryException(MediaErrorCodes.operationFailed, "$e");
    }
  }

  Future<MediaAsset> saveImageBytes(
    Uint8List data, {
    required String filename,
    String? relativePath,
  }) async {
    try {
      final entity = await PhotoManager.editor.saveImage(
        data,
        filename: filename,
        relativePath: relativePath,
      );
      return await _mapAsset(entity);
    } catch (e) {
      throw MediaLibraryException(MediaErrorCodes.operationFailed, "$e");
    }
  }

  Future<MediaAsset> saveVideo(
    String filePath, {
    String? filename,
    String? relativePath,
  }) async {
    try {
      await ensureAccess(mediaType: "video");
      final entity = await PhotoManager.editor.saveVideo(
        File(filePath),
        title: filename,
        relativePath: relativePath,
      );
      return await _mapAsset(entity);
    } on MediaLibraryException {
      rethrow;
    } catch (e) {
      throw MediaLibraryException(MediaErrorCodes.operationFailed, "$e");
    }
  }

  /// photo_manager has no save-audio API; Android uses the small native
  /// fallback. Other platforms are unsupported.
  Future<MediaAsset> saveAudio(
    String filePath, {
    String? filename,
    String? relativePath,
  }) async {
    if (!Platform.isAndroid) {
      throw const MediaLibraryException(
        MediaErrorCodes.unsupported,
        "save_audio is currently supported on Android only.",
      );
    }
    await ensureAccess(mediaType: "audio");
    final id = await _fallback.saveAudio(filePath, filename, relativePath);
    return getAsset(id);
  }

  // ──────────────────────────── delete / copy / move ─────────────────────────

  /// Returns the ids that were actually deleted. Platforms may show a system
  /// confirmation dialog; an empty result means nothing was deleted.
  Future<List<String>> deleteAssets(List<String> assetIds) async {
    try {
      await ensureAccess();
      return await PhotoManager.editor.deleteWithIds(assetIds);
    } on MediaLibraryException {
      rethrow;
    } catch (e) {
      throw MediaLibraryException(MediaErrorCodes.operationFailed, "$e");
    }
  }

  /// Copy semantics differ by platform: a real duplicate on Android (<30),
  /// an album link on iOS. Blocked entirely on Android 30+ by the system.
  Future<MediaAsset> copyAsset(String assetId, String targetAlbumId) async {
    await ensureAccess();
    if (Platform.isAndroid && await _sdkInt() >= 30) {
      throw const MediaLibraryException(
        MediaErrorCodes.unsupported,
        "copy_asset is blocked by Android 11+ scoped storage restrictions.",
      );
    }
    final entity = await _requireAsset(assetId);
    final target = await _loadAlbum(targetAlbumId, entity.type.requestType);
    try {
      final copied = await PhotoManager.editor.copyAssetToPath(
        asset: entity,
        pathEntity: target,
      );
      return await _mapAsset(copied);
    } catch (e) {
      throw MediaLibraryException(MediaErrorCodes.operationFailed, "$e");
    }
  }

  /// Move via plugin on Android 11+ (createWriteRequest flow).
  /// Android 10 uses the tiny native RELATIVE_PATH fallback.
  Future<bool> moveAsset(String assetId, String targetRelativePath) async {
    if (!Platform.isAndroid) {
      throw const MediaLibraryException(
        MediaErrorCodes.unsupported,
        "move_asset is currently supported on Android only.",
      );
    }
    final sdkInt = await _sdkInt();
    if (sdkInt >= 30) {
      final entity = await _requireAsset(assetId);
      return PhotoManager.editor.android.moveAssetsToPath(
        entities: [entity],
        targetPath: targetRelativePath,
      );
    }
    if (sdkInt == 29) {
      return _fallback.moveAsset(assetId, targetRelativePath);
    }
    throw const MediaLibraryException(
      MediaErrorCodes.unsupported,
      "move_asset requires Android 10 (API 29) or newer.",
    );
  }

  /// Rename via native fallback (photo_manager gained this API only after
  /// 3.12.0). Android only.
  Future<bool> renameAsset(String assetId, String newName) async {
    if (!Platform.isAndroid) {
      throw const MediaLibraryException(
        MediaErrorCodes.unsupported,
        "rename_asset is currently supported on Android only.",
      );
    }
    return _fallback.renameAsset(assetId, newName);
  }

  Future<int> _sdkInt() async {
    if (!Platform.isAndroid) return 0;
    try {
      final version = await PhotoManager.systemVersion();
      return int.tryParse(version) ?? 0;
    } catch (_) {
      return 0;
    }
  }

  // ───────────────────────────── change notify ───────────────────────────────

  void Function(MediaChangeEvent event)? onChange;

  void _handleChange(MethodCall call) {
    if (onChange == null) return;
    final args = Map<String, dynamic>.from(call.arguments ?? {});
    onChange!(
      MediaChangeEvent(
        changeType: switch (call.method) {
          "created" || "insert" => "added",
          "update" || "_update" || "modified" => "modified",
          "remove" || "deleted" => "removed",
          _ => "other",
        },
        assetId: args["id"]?.toString() ?? "",
        timestampMs: DateTime.now().millisecondsSinceEpoch,
      ),
    );
  }

  Future<void> startChangeNotify() async {
    PhotoManager.addChangeCallback(_handleChange);
    await PhotoManager.startChangeNotify();
  }

  Future<void> stopChangeNotify() async {
    await PhotoManager.stopChangeNotify();
    PhotoManager.removeChangeCallback(_handleChange);
  }

  Future<void> clearFileCache() async {
    await PhotoManager.clearFileCache();
    // Also clear our thumbnail path cache.
    final cacheDir = Directory(
      '${Directory.systemTemp.path}/flet_media_library_thumbs',
    );
    if (await cacheDir.exists()) {
      await cacheDir.delete(recursive: true);
    }
  }

  /// Platform capability flags so callers do not hard-code Android/iOS gaps.
  Future<Map<String, dynamic>> getCapabilities() async {
    final isAndroid = Platform.isAndroid;
    final isIOS = Platform.isIOS;
    final sdk = isAndroid ? await _sdkInt() : 0;
    return {
      "platform": isAndroid
          ? "android"
          : isIOS
              ? "ios"
              : Platform.operatingSystem,
      "supports_audio_save": isAndroid,
      "supports_move": isAndroid && sdk >= 29,
      "supports_rename": isAndroid,
      "supports_copy": !(isAndroid && sdk >= 30),
      "supports_mime_filter": true,
      "supports_limited_access": isIOS || (isAndroid && sdk >= 34),
      "supports_thumbnail_path": true,
      "supports_change_notify": isAndroid || isIOS,
      "android_sdk": sdk,
    };
  }
}

extension on AssetType {
  RequestType get requestType => switch (this) {
    AssetType.image => RequestType.image,
    AssetType.video => RequestType.video,
    AssetType.audio => RequestType.audio,
    AssetType.other => RequestType.common,
  };
}
