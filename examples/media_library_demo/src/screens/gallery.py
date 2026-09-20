"""Albums, asset grid, multi-select delete, detail, rename, video play with modern design."""

from __future__ import annotations

import flet as ft

from flet_media_library import UnsupportedError
from services.media import DemoSession

try:
    import flet_video as ftv

    HAS_VIDEO = True
except ImportError:
    HAS_VIDEO = False
    ftv = None  # type: ignore


def build_gallery(page: ft.Page, session: DemoSession) -> ft.Control:
    media = session.media
    status = ft.Text("Ready. Load albums or assets below.", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
    albums_dd = ft.Dropdown(
        label="Album",
        dense=True,
        width=200,
        options=[ft.DropdownOption(key="", text="(All Albums)")],
    )
    type_dd = ft.Dropdown(
        label="Type",
        dense=True,
        width=110,
        value="all",
        options=[
            ft.DropdownOption(key="all", text="All"),
            ft.DropdownOption(key="image", text="Images"),
            ft.DropdownOption(key="video", text="Videos"),
            ft.DropdownOption(key="audio", text="Audio"),
        ],
    )
    grid = ft.GridView(
        expand=True,
        max_extent=120,
        child_aspect_ratio=1,
        spacing=8,
        run_spacing=8,
    )
    # asset_id -> selected
    selected: dict[str, bool] = {}
    # asset_id -> MediaAsset-like snapshot for play
    asset_meta: dict[str, object] = {}
    select_mode = {"on": False}
    offset = {"n": 0}
    page_size = 30
    sel_label = ft.Text("0 selected", size=12, weight=ft.FontWeight.W_500, visible=False)

    empty_placeholder = ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.PHOTO_LIBRARY_OUTLINED, size=56, color=ft.Colors.OUTLINE),
                ft.Text("No media loaded yet", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text("Tap 'Load Assets' or select an album above.", size=12, color=ft.Colors.OUTLINE),
                ft.Button("Load Assets", icon=ft.Icons.DOWNLOAD_ROUNDED, on_click=lambda e: load_assets()),
            ],
        ),
    )

    grid_container = ft.Container(
        expand=True,
        content=empty_placeholder,
    )

    def refresh_sel_label() -> None:
        n = sum(1 for v in selected.values() if v)
        sel_label.value = f"{n} selected"
        sel_label.visible = select_mode["on"]
        delete_btn.visible = select_mode["on"] and n > 0
        page.update()

    async def load_albums(e: ft.ControlEvent | None = None) -> None:
        try:
            mt = type_dd.value or "all"
            albums = await media.get_albums(media_type=mt if mt != "all" else "all")
            albums_dd.options = [
                ft.DropdownOption(key="", text="(All Albums)"),
                *[
                    ft.DropdownOption(key=a.id, text=f"{a.name} ({a.asset_count})")
                    for a in albums
                ],
            ]
            status.value = f"Found {len(albums)} album(s)"
            status.color = ft.Colors.GREEN
        except Exception as ex:  # noqa: BLE001
            status.value = f"Albums error: {ex}"
            status.color = ft.Colors.ERROR
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))
        page.update()

    def tile_for(asset, thumb: str) -> ft.Control:
        img = (
            ft.Image(src=thumb, fit=ft.BoxFit.COVER, border_radius=8)
            if thumb
            else ft.Container(
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=8,
                content=ft.Icon(ft.Icons.IMAGE_OUTLINED, color=ft.Colors.OUTLINE),
                alignment=ft.Alignment.CENTER,
            )
        )
        check = ft.Checkbox(
            value=selected.get(asset.id, False),
            visible=select_mode["on"],
        )

        def on_check(e: ft.ControlEvent, aid=asset.id) -> None:
            selected[aid] = bool(e.control.value)
            refresh_sel_label()

        check.on_change = on_check

        async def on_tap(e: ft.ControlEvent, a=asset) -> None:
            if select_mode["on"]:
                selected[a.id] = not selected.get(a.id, False)
                check.value = selected[a.id]
                refresh_sel_label()
            else:
                await show_detail(a.id)

        badge = None
        if asset.media_type == "video":
            badge = ft.Container(
                content=ft.Icon(ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED, size=28, color=ft.Colors.WHITE),
                alignment=ft.Alignment.CENTER,
            )

        stack_children = [img]
        if badge is not None:
            stack_children.append(badge)
        stack_children.append(
            ft.Container(content=check, alignment=ft.Alignment.TOP_LEFT, padding=2)
        )

        return ft.GestureDetector(
            on_tap=on_tap,
            content=ft.Container(
                width=110,
                height=110,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=ft.Stack(controls=stack_children, expand=True),
            ),
        )

    async def load_assets(e: ft.ControlEvent | None = None, more: bool = False) -> None:
        if not more:
            offset["n"] = 0
            grid.controls.clear()
            if not select_mode["on"]:
                selected.clear()
            asset_meta.clear()
        try:
            status.value = "Loading assets…"
            page.update()

            result = await media.get_assets(
                media_type=type_dd.value or "all",
                album=albums_dd.value or None,
                limit=page_size,
                offset=offset["n"],
                sort_by="date_added",
                sort_order="desc",
            )
            for asset in result.items:
                asset_meta[asset.id] = asset
                if asset.id not in selected:
                    selected[asset.id] = False
                thumb = ""
                try:
                    thumb = await media.get_thumbnail(asset.id, width=160, height=160)
                except Exception:  # noqa: BLE001
                    pass
                grid.controls.append(tile_for(asset, thumb))

            offset["n"] += len(result.items)
            status.value = (
                f"{len(grid.controls)} of {result.total} shown "
                f"(has_more={result.has_more})"
            )
            status.color = None
            grid_container.content = grid if grid.controls else empty_placeholder
            more_btn.visible = result.has_more
            refresh_sel_label()
        except UnsupportedError as ex:
            status.value = str(ex)
            status.color = ft.Colors.ERROR
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))
        except Exception as ex:  # noqa: BLE001
            status.value = f"Assets error: {ex}"
            status.color = ft.Colors.ERROR
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))
        page.update()

    def toggle_select_mode(e: ft.ControlEvent) -> None:
        select_mode["on"] = not select_mode["on"]
        if not select_mode["on"]:
            for k in selected:
                selected[k] = False
        # Rebuild tiles so checkboxes show/hide
        page.run_task(load_assets, None, False)
        mode_btn.content = "Cancel Select" if select_mode["on"] else "Select Mode"
        mode_btn.icon = ft.Icons.CLOSE if select_mode["on"] else ft.Icons.CHECK_BOX_OUTLINED
        refresh_sel_label()
        page.update()

    async def batch_delete(e: ft.ControlEvent) -> None:
        ids = [aid for aid, on in selected.items() if on]
        if not ids:
            page.show_dialog(ft.SnackBar(content=ft.Text("Nothing selected")))
            return

        async def confirm_yes(ev: ft.ControlEvent) -> None:
            page.pop_dialog()
            try:
                deleted = await media.delete_assets(ids)
                for did in deleted:
                    session.untrack(did)
                page.show_dialog(
                    ft.SnackBar(content=ft.Text(f"Deleted {len(deleted)} of {len(ids)} asset(s)"))
                )
                for did in deleted:
                    selected.pop(did, None)
                await load_assets(None, more=False)
            except Exception as ex:  # noqa: BLE001
                page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))

        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Delete Selected Assets?"),
                content=ft.Text(f"Are you sure you want to delete {len(ids)} asset(s)? This cannot be undone."),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda ev: page.pop_dialog()),
                    ft.TextButton("Delete", on_click=confirm_yes),
                ],
            )
        )

    async def show_detail(asset_id: str) -> None:
        try:
            a = await media.get_asset(asset_id)
            detail_items = [
                ("ID", a.id),
                ("Name", a.display_name),
                ("Type", a.media_type),
                ("MIME", a.mime_type or "unknown"),
                ("Dimensions", f"{a.width} x {a.height}" if a.width else "unknown"),
                ("Duration", f"{a.duration_ms / 1000:.1f}s" if a.duration_ms else "n/a"),
                ("Album", a.album_name or "(none)"),
                ("Path", a.relative_path or "(none)"),
            ]

            info_rows = [
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Text(label, size=11, weight=ft.FontWeight.BOLD, width=80, color=ft.Colors.PRIMARY),
                        ft.Text(str(val), size=11, selectable=True, expand=True),
                    ],
                )
                for label, val in detail_items
            ]

            async def do_delete(e: ft.ControlEvent) -> None:
                ok = await media.delete_asset(asset_id)
                session.untrack(asset_id)
                page.pop_dialog()
                page.show_dialog(ft.SnackBar(content=ft.Text(f"Deleted asset: {ok}")))
                await load_assets(None, more=False)

            async def do_rename(e: ft.ControlEvent) -> None:
                new_name = rename_field.value or ""
                try:
                    ok = await media.rename_asset(asset_id, new_name)
                    page.show_dialog(ft.SnackBar(content=ft.Text(f"Rename: ok={ok}")))
                    page.pop_dialog()
                    await show_detail(asset_id)
                except Exception as ex:  # noqa: BLE001
                    page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))

            async def do_play(e: ft.ControlEvent) -> None:
                page.pop_dialog()
                await play_video(a.source_uri or "", a.display_name)

            rename_field = ft.TextField(label="Rename File", value=a.display_name, dense=True, width=240)
            actions = [
                ft.TextButton("Rename", on_click=do_rename),
                ft.TextButton("Delete", on_click=do_delete),
                ft.TextButton("Close", on_click=lambda e: page.pop_dialog()),
            ]
            if a.media_type == "video":
                actions.insert(0, ft.TextButton("Play Video", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=do_play))

            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINED, color=ft.Colors.PRIMARY),
                        ft.Text("Asset Details", size=16, weight=ft.FontWeight.BOLD),
                    ]),
                    content=ft.Column(
                        tight=True,
                        scroll=ft.ScrollMode.AUTO,
                        spacing=6,
                        controls=[
                            *info_rows,
                            ft.Divider(),
                            rename_field,
                        ],
                    ),
                    actions=actions,
                )
            )
        except Exception as ex:  # noqa: BLE001
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))

    async def play_video(uri: str, title: str) -> None:
        if not HAS_VIDEO:
            page.show_dialog(
                ft.SnackBar(content=ft.Text("Install flet-video for in-app video playback"))
            )
            return
        if not uri:
            page.show_dialog(
                ft.SnackBar(content=ft.Text("No source URI available for video playback"))
            )
            return

        player = ftv.Video(
            expand=True,
            autoplay=True,
            playlist=[ftv.VideoMedia(uri)],
            aspect_ratio=16 / 9,
        )

        def close_player(e: ft.ControlEvent) -> None:
            try:
                player.pause()
            except Exception:  # noqa: BLE001
                pass
            page.pop_dialog()

        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(title or "Video Playback"),
                content=ft.Container(content=player, width=340, height=220),
                actions=[ft.TextButton("Close", on_click=close_player)],
            )
        )

    mode_btn = ft.Button("Select Mode", icon=ft.Icons.CHECK_BOX_OUTLINED, on_click=toggle_select_mode)
    delete_btn = ft.Button("Delete Selected", icon=ft.Icons.DELETE_FOREVER_ROUNDED, on_click=batch_delete, visible=False)
    more_btn = ft.Button("More", icon=ft.Icons.EXPAND_MORE_ROUNDED, on_click=lambda e: page.run_task(load_assets, e, True), visible=False)

    return ft.Column(
        expand=True,
        spacing=10,
        controls=[
            # Filter Card
            ft.Card(
                content=ft.Container(
                    padding=12,
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(
                                wrap=True,
                                spacing=8,
                                controls=[
                                    type_dd,
                                    albums_dd,
                                    ft.IconButton(ft.Icons.FOLDER_OPEN_ROUNDED, tooltip="Fetch Albums", on_click=load_albums),
                                    ft.Button("Load", icon=ft.Icons.REFRESH_ROUNDED, on_click=load_assets),
                                    more_btn,
                                    mode_btn,
                                    delete_btn,
                                ],
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    status,
                                    sel_label,
                                ],
                            ),
                        ],
                    ),
                ),
            ),
            # Media Grid
            grid_container,
        ],
    )
