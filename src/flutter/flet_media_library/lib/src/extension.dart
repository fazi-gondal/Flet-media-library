import 'package:flet/flet.dart';

import 'media_library_service.dart';

class Extension extends FletExtension {
  @override
  FletService? createService(Control control) {
    switch (control.type) {
      case "MediaLibrary":
        return MediaLibraryService(control: control);
      default:
        return null;
    }
  }
}
