/// Flet-owned media asset model.
///
/// This is the only asset representation exposed across the Python boundary.
/// Backend-specific identifiers (MediaStore ids, PhotoKit local identifiers)
/// are normalized into [id].
class MediaAsset {
  final String id;
  final String displayName;
  final String mimeType;
  final String mediaType; // "image" | "video" | "audio"
  final int size;
  final int width;
  final int height;
  final int durationMs;
  final int dateAdded;
  final int dateModified;
  final int orientation;
  final String albumId;
  final String albumName;
  final String relativePath;
  final String sourceUri;

  const MediaAsset({
    required this.id,
    this.displayName = "",
    this.mimeType = "",
    this.mediaType = "",
    this.size = 0,
    this.width = 0,
    this.height = 0,
    this.durationMs = 0,
    this.dateAdded = 0,
    this.dateModified = 0,
    this.orientation = 0,
    this.albumId = "",
    this.albumName = "",
    this.relativePath = "",
    this.sourceUri = "",
  });

  Map<String, dynamic> toMap() => {
    "id": id,
    "display_name": displayName,
    "mime_type": mimeType,
    "media_type": mediaType,
    "size": size,
    "width": width,
    "height": height,
    "duration_ms": durationMs,
    "date_added": dateAdded,
    "date_modified": dateModified,
    "orientation": orientation,
    "album_id": albumId,
    "album_name": albumName,
    "relative_path": relativePath,
    "source_uri": sourceUri,
  };

  static MediaAsset fromMap(Map<String, dynamic> map) => MediaAsset(
    id: map["id"] as String? ?? "",
    displayName: map["display_name"] as String? ?? "",
    mimeType: map["mime_type"] as String? ?? "",
    mediaType: map["media_type"] as String? ?? "",
    size: (map["size"] as num?)?.toInt() ?? 0,
    width: (map["width"] as num?)?.toInt() ?? 0,
    height: (map["height"] as num?)?.toInt() ?? 0,
    durationMs: (map["duration_ms"] as num?)?.toInt() ?? 0,
    dateAdded: (map["date_added"] as num?)?.toInt() ?? 0,
    dateModified: (map["date_modified"] as num?)?.toInt() ?? 0,
    orientation: (map["orientation"] as num?)?.toInt() ?? 0,
    albumId: map["album_id"] as String? ?? "",
    albumName: map["album_name"] as String? ?? "",
    relativePath: map["relative_path"] as String? ?? "",
    sourceUri: map["source_uri"] as String? ?? "",
  );
}

/// Flet-owned album model.
class MediaAlbum {
  final String id;
  final String name;
  final int assetCount;
  final List<String> mediaTypes;
  final bool isAll;
  final bool isSystemAlbum;
  final String platformIdentifier;

  const MediaAlbum({
    required this.id,
    required this.name,
    this.assetCount = 0,
    this.mediaTypes = const [],
    this.isAll = false,
    this.isSystemAlbum = false,
    this.platformIdentifier = "",
  });

  Map<String, dynamic> toMap() => {
    "id": id,
    "name": name,
    "asset_count": assetCount,
    "media_types": mediaTypes,
    "is_all": isAll,
    "is_system_album": isSystemAlbum,
    "platform_identifier": platformIdentifier,
  };
}
