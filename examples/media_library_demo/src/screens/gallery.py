"""Albums, asset grid, multi-select delete, detail, rename, move, audio/video play."""

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

# Common Android relative-path destinations shown in the move picker
_COMMON_PATHS = [
    "Pictures",
    "Pictures/Archive",
    "Pictures/Screenshots",
    "DCIM",
    "DCIM/Camera",
    "Movies",
    "Music",
    "Music/FletMediaLibrary",
    "Downloads",
]


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
    selected: dict[str, bool] = {}
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
                ft.Button("Load Assets", icon=ft.Icons.DOWNLOAD_ROUNDED, on_click=lambda e: page.run_task(load_assets)),
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

        # Media type badge
        badge = None
        if asset.media_type == "video":
            badge = ft.Container(
                content=ft.Icon(ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED, size=28, color=ft.Colors.WHITE),
                alignment=ft.Alignment.CENTER,
            )
        elif asset.media_type == "audio":
            badge = ft.Container(
                content=ft.Icon(ft.Icons.MUSIC_NOTE_ROUNDED, size=24, color=ft.Colors.WHITE),
                alignment=ft.Alignment.CENTER,
                bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.BLACK),
                border_radius=8,
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
                ("Dimensions", f"{a.width} x {a.height}" if a.width else "n/a"),
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

            # ── Rename field (pre-filled with current name) ──────────────────
            rename_field = ft.TextField(
                label="New filename",
                value=a.display_name,
                dense=True,
                autofocus=True,
                suffix_icon=ft.Icons.EDIT_ROUNDED,
                hint_text="e.g. my_photo.jpg",
            )

            # ── Move: common-path dropdown + optional custom override ─────────
            move_dd = ft.Dropdown(
                label="Move to folder",
                dense=True,
                value=_COMMON_PATHS[0],
                options=[ft.DropdownOption(key=p, text=p) for p in _COMMON_PATHS]
                + [ft.DropdownOption(key="__custom__", text="Custom path…")],
            )
            custom_path_field = ft.TextField(
                label="Custom path",
                value="",
                dense=True,
                visible=False,
                hint_text="Pictures/MyAlbum",
            )

            def on_move_dd_change(e: ft.ControlEvent) -> None:
                custom_path_field.visible = move_dd.value == "__custom__"
                page.update()

            move_dd.on_change = on_move_dd_change

            async def do_delete(e: ft.ControlEvent) -> None:
                page.pop_dialog()
                try:
                    deleted = await media.delete_assets([asset_id])
                    for did in deleted:
                        session.untrack(did)
                    page.show_dialog(
                        ft.SnackBar(content=ft.Text(f"Deleted {len(deleted)} asset(s)"))
                    )
                    await load_assets(None, more=False)
                except Exception as ex:  # noqa: BLE001
                    page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))

            async def do_rename(e: ft.ControlEvent) -> None:
                new_name = rename_field.value.strip()
                if not new_name:
                    page.show_dialog(ft.SnackBar(content=ft.Text("Please enter a file name.")))
                    return
                try:
                    ok = await media.rename_asset(asset_id, new_name)
                    if ok:
                        page.pop_dialog()
                        page.show_dialog(ft.SnackBar(content=ft.Text(f"Renamed to: {new_name}")))
                        await load_assets(None, more=False)
                    else:
                        page.show_dialog(
                            ft.SnackBar(content=ft.Text("Rename returned false — permission may be denied or file not owned."))
                        )
                except Exception as ex:  # noqa: BLE001
                    page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))

            async def do_move(e: ft.ControlEvent) -> None:
                target = (
                    custom_path_field.value.strip()
                    if move_dd.value == "__custom__"
                    else (move_dd.value or "")
                )
                if not target:
                    page.show_dialog(ft.SnackBar(content=ft.Text("Please choose or enter a destination folder.")))
                    return
                try:
                    ok = await media.move_asset(asset_id, target)
                    if ok:
                        page.pop_dialog()
                        page.show_dialog(ft.SnackBar(content=ft.Text(f"Moved to: {target}")))
                        await load_assets(None, more=False)
                    else:
                        page.show_dialog(
                            ft.SnackBar(content=ft.Text("Move returned false — device may require Android 10+ or user denied."))
                        )
                except UnsupportedError as ex:
                    page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))
                except Exception as ex:  # noqa: BLE001
                    page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))

            async def do_play_video(e: ft.ControlEvent) -> None:
                page.pop_dialog()
                await play_video(a.source_uri or "", a.display_name)

            async def do_play_audio(e: ft.ControlEvent) -> None:
                page.pop_dialog()
                await play_audio(a.source_uri or "", a.display_name)

            actions = [
                ft.TextButton("Rename", icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE_ROUNDED, on_click=do_rename),
                ft.TextButton("Move", icon=ft.Icons.DRIVE_FILE_MOVE_ROUNDED, on_click=do_move),
                ft.TextButton("Delete", icon=ft.Icons.DELETE_OUTLINE_ROUNDED, on_click=do_delete),
                ft.TextButton("Close", on_click=lambda e: page.pop_dialog()),
            ]
            if a.media_type == "video":
                actions.insert(0, ft.TextButton("▶ Play Video", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=do_play_video))
            elif a.media_type == "audio":
                actions.insert(0, ft.TextButton("▶ Play Audio", icon=ft.Icons.HEADPHONES_ROUNDED, on_click=do_play_audio))

            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINED, color=ft.Colors.PRIMARY),
                        ft.Text("Asset Details", size=16, weight=ft.FontWeight.BOLD),
                    ]),
                    content=ft.Column(
                        tight=True,
                        scroll=ft.ScrollMode.AUTO,
                        spacing=8,
                        controls=[
                            *info_rows,
                            ft.Divider(),
                            ft.Text("Rename", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                            rename_field,
                            ft.Divider(),
                            ft.Text("Move to folder", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                            move_dd,
                            custom_path_field,
                        ],
                    ),
                    actions=actions,
                    actions_alignment=ft.MainAxisAlignment.START,
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

    async def play_audio(uri: str, title: str) -> None:
        """Simple audio player using flet-video's Audio widget (or fallback message)."""
        if not uri:
            page.show_dialog(
                ft.SnackBar(content=ft.Text("No source URI available for this audio file."))
            )
            return

        # flet-video uses media_kit / ExoPlayer which plays audio files directly
        if HAS_VIDEO:
            player = ftv.Video(
                playlist=[ftv.VideoMedia(uri)],
                autoplay=True,
                height=60,
                fill_color=ft.Colors.TRANSPARENT,
            )

            def close_audio(e: ft.ControlEvent) -> None:
                try:
                    player.pause()
                except Exception:  # noqa: BLE001
                    pass
                page.pop_dialog()

            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Row([
                        ft.Icon(ft.Icons.HEADPHONES_ROUNDED, color=ft.Colors.PRIMARY),
                        ft.Text(title or "Audio Playback", size=15, weight=ft.FontWeight.BOLD),
                    ]),
                    content=ft.Column(
                        tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=16,
                        controls=[
                            ft.Icon(ft.Icons.MUSIC_NOTE_ROUNDED, size=64, color=ft.Colors.PRIMARY),
                            ft.Text(title, size=13, text_align=ft.TextAlign.CENTER),
                            ft.Container(content=player, height=60),
                        ],
                    ),
                    actions=[ft.TextButton("Close", on_click=close_audio)],
                )
            )
        else:
            # Fallback: flet_video not installed or Audio not available
            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text("Audio Playback"),
                    content=ft.Column(
                        tight=True,
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.HEADPHONES_ROUNDED, size=48, color=ft.Colors.PRIMARY),
                            ft.Text(f"File: {title}", size=13),
                            ft.Text(
                                "Install flet-video >= 1.0.0 and run on Android for in-app audio playback.",
                                size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.SelectionArea(
                                content=ft.Text(uri, size=10, font_family="monospace", selectable=True)
                            ),
                        ],
                    ),
                    actions=[ft.TextButton("Close", on_click=lambda e: page.pop_dialog())],
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
