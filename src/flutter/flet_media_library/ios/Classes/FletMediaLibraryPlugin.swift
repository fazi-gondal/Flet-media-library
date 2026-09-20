import Flutter
import UIKit

/// Minimal iOS plugin registrant.
///
/// All media-library behavior is provided by the `photo_manager` dependency.
/// This class exists only so Flet/Flutter packaging includes the package on iOS.
public class FletMediaLibraryPlugin: NSObject, FlutterPlugin {
  public static func register(with registrar: FlutterPluginRegistrar) {
    // No custom method channel on iOS — photo_manager handles the platform side.
  }
}
