import 'package:flet/flet.dart';

import 'adapters/photo_manager_adapter.dart';
import 'models/media_errors.dart';

class MediaLibraryService extends FletService {
  final PhotoManagerAdapter _adapter = PhotoManagerAdapter();

  MediaLibraryService({required super.control});

  @override
  void init() {
    super.init();
    control.addInvokeMethodListener(_onInvokeMethod);
  }

  Future<dynamic> _onInvokeMethod(String methodName, dynamic args) async {
    final arguments = (args != null && args is Map)
        ? Map<String, dynamic>.from(args)
        : <String, dynamic>{};
    return switch (methodName) {
      // permissions
      "check_permissions" => _guard(
        () => _adapter.checkPermissions(_mediaTypes(arguments)),
      ),
      "request_permissions" => _guard(
        () => _adapter.requestPermissions(_mediaTypes(arguments)),
      ),
      "open_settings" => _guard(() => _adapter.openSettings()),
      "present_limited" => _guard(
        () => _adapter.presentLimited(_mediaTypes(arguments)),
      ),
      // albums & assets
      "get_albums" => _guard(() async {
        final albums = await _adapter.getAlbums(
          mediaTypes: _mediaTypes(arguments),
        );
        return {
          "albums": [for (final a in albums) a.toMap()],
        };
      }),
      "get_assets" => _guard(
        () => _adapter.getAssets(
          mediaType: arguments["media_type"] as String? ?? "all",
          albumId: arguments["album"] as String?,
          mimeType: arguments["mime_type"] as String?,
          limit: (arguments["limit"] as num?)?.toInt() ?? 50,
          offset: (arguments["offset"] as num?)?.toInt() ?? 0,
          sortBy: arguments["sort_by"] as String? ?? "date_added",
          sortOrder: arguments["sort_order"] as String? ?? "desc",
        ),
      ),
      "get_asset" => _guard(() async {
        final asset = await _adapter.getAsset(
          arguments["asset_id"] as String? ?? "",
        );
        return asset.toMap();
      }),
      "get_thumbnail" => _guard(() async {
        final bytes = await _adapter.getThumbnail(
          arguments["asset_id"] as String? ?? "",
          width: (arguments["width"] as num?)?.toInt() ?? 200,
          height: (arguments["height"] as num?)?.toInt() ?? 200,
          quality: (arguments["quality"] as num?)?.toInt() ?? 90,
        );
        return {"data": bytes};
      }),
      // saving
      "save_image" => _validateAndSave(
        arguments,
        (path, rel) => _adapter.saveImage(
          path,
          filename: arguments["filename"] as String?,
          relativePath: rel,
        ),
      ),
      "save_video" => _validateAndSave(
        arguments,
        (path, rel) => _adapter.saveVideo(
          path,
          filename: arguments["filename"] as String?,
          relativePath: rel,
        ),
      ),
      "save_audio" => _validateAndSave(
        arguments,
        (path, rel) => _adapter.saveAudio(
          path,
          filename: arguments["filename"] as String?,
          relativePath: rel,
        ),
      ),
      // mutations
      "delete_assets" => _guard(() async {
        final ids =
            (arguments["asset_ids"] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            const [];
        if (ids.isEmpty) {
          throw const MediaLibraryException(
            MediaErrorCodes.invalidArgument,
            "asset_ids must be a non-empty list.",
          );
        }
        final deleted = await _adapter.deleteAssets(ids);
        return {"deleted": deleted};
      }),
      "copy_asset" => _guard(() async {
        final asset = await _adapter.copyAsset(
          arguments["asset_id"] as String? ?? "",
          arguments["target_album"] as String? ?? "",
        );
        return asset.toMap();
      }),
      "move_asset" => _guard(() async {
        final ok = await _adapter.moveAsset(
          arguments["asset_id"] as String? ?? "",
          arguments["target_relative_path"] as String? ?? "",
        );
        // Always return a map so the Python layer can parse consistently.
        return {"ok": ok};
      }),
      "rename_asset" => _guard(() async {
        final ok = await _adapter.renameAsset(
          arguments["asset_id"] as String? ?? "",
          arguments["new_name"] as String? ?? "",
        );
        return {"ok": ok};
      }),
      // change notifications
      "start_change_notify" => _guard(() async {
        _adapter.onChange = (event) =>
            control.triggerEvent("change", event.toMap());
        await _adapter.startChangeNotify();
        return null;
      }),
      "stop_change_notify" => _guard(() async {
        await _adapter.stopChangeNotify();
        _adapter.onChange = null;
        return null;
      }),
      "clear_file_cache" => _guard(() => _adapter.clearFileCache()),
      _ => throw MediaLibraryException(
        MediaErrorCodes.invalidArgument,
        "MediaLibraryService: unknown method '$methodName'.",
      ),
    };
  }

  /// Wraps adapter calls so unexpected backend errors still surface as
  /// structured platform errors instead of crashing the channel.
  Future<dynamic> _guard(Future<dynamic> Function() action) async {
    try {
      return await action();
    } on MediaLibraryException {
      rethrow;
    } catch (e) {
      throw MediaLibraryException(MediaErrorCodes.platformError, e.toString());
    }
  }

  /// Validates the source path, then delegates to the adapter.
  Future<dynamic> _validateAndSave(
    Map<String, dynamic> arguments,
    Future<dynamic> Function(String filePath, String? relativePath) action,
  ) {
    return _guard(() async {
      final filePath = arguments["file_path"] as String? ?? "";
      if (filePath.isEmpty) {
        throw const MediaLibraryException(
          MediaErrorCodes.invalidArgument,
          "file_path is required.",
        );
      }
      return action(filePath, arguments["album"] as String?);
    });
  }

  List<String> _mediaTypes(Map<String, dynamic> args) {
    final raw = args["media_types"];
    if (raw is List && raw.isNotEmpty) {
      return raw.map((e) => e.toString()).toList();
    }
    return const ["all"];
  }

  @override
  void dispose() {
    control.removeInvokeMethodListener(_onInvokeMethod);
    super.dispose();
  }
}
