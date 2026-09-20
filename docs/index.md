# flet-media-library

Cross-platform media library extension for Flet, powered by
[`photo_manager`](https://pub.dev/packages/photo_manager).

See the [README](https://github.com/fazi-gondal/flet-media-library) and
[ARCHITECTURE.md](https://github.com/fazi-gondal/flet-media-library/blob/main/ARCHITECTURE.md)
for full documentation.

## Quick start

```python
import flet as ft
from flet_media_library import MediaLibrary

media = MediaLibrary()

def main(page: ft.Page):
    page.services.append(media)

    async def load(e):
        status = await media.request_permissions(["image", "video"])
        if status.all_granted:
            result = await media.get_assets(media_type="image", limit=20)
            for asset in result.items:
                thumb = await media.get_thumbnail(asset.id)
                page.add(ft.Image(src=thumb))

    page.add(ft.Button("Load", on_click=load))

ft.run(main)
```
