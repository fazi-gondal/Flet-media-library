/// Permission state for a single media type.
enum MediaPermissionState {
  granted,
  limited,
  denied,
  deniedForever,
  restricted,
  unknown;

  String get value => switch (this) {
        granted => "granted",
        limited => "limited",
        denied => "denied",
        deniedForever => "denied_forever",
        restricted => "restricted",
        unknown => "unknown",
      };

  static MediaPermissionState fromValue(String? value) =>
      MediaPermissionState.values.firstWhere(
        (s) => s.value == value,
        orElse: () => MediaPermissionState.unknown,
      );
}

/// Structured permission snapshot exposed to Python.
class MediaPermissionsResult {
  final Map<String, MediaPermissionState> states; // keyed by media type
  final bool canRequest;

  const MediaPermissionsResult({required this.states, required this.canRequest});

  Map<String, dynamic> toMap() => {
        "permissions": {
          for (final entry in states.entries) entry.key: entry.value.value,
        },
        "can_request": canRequest,
      };
}

/// Change event forwarded to Python.
class MediaChangeEvent {
  /// Coarse change classification: "added", "modified", "removed" or "other".
  ///
  /// The underlying backend does not always distinguish these precisely;
  /// consumers must treat "other" as "something changed".
  final String changeType;
  final String assetId;
  final String mediaType;
  final int timestampMs;

  const MediaChangeEvent({
    required this.changeType,
    this.assetId = "",
    this.mediaType = "",
    required this.timestampMs,
  });

  Map<String, dynamic> toMap() => {
        "change_type": changeType,
        "asset_id": assetId,
        "media_type": mediaType,
        "timestamp": timestampMs,
      };
}
