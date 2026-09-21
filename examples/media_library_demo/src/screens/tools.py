"""Move / copy / rename / save_audio / cache / smoke checklist with modern UI."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from flet_media_library import UnsupportedError
from services.media import DemoSession


def build_tools(page: ft.Page, session: DemoSession) -> ft.Control:
    media = session.media
    file_picker = next((s for s in page.services if isinstance(s, ft.FilePicker)), None)
    if file_picker is None:
        file_picker = ft.FilePicker()
        page.services.append(file_picker)

    log = ft.ListView(expand=True, spacing=3, auto_scroll=True)
    asset_id_field = ft.TextField(
        label="Asset ID",
        dense=True,
        expand=True,
        prefix_icon=ft.Icons.TAG_ROUNDED,
    )
    path_field = ft.TextField(
        label="Target Relative Path",
        value="Pictures/Archive",
        dense=True,
        expand=True,
    )
    name_field = ft.TextField(
        label="New Name",
        value="renamed.jpg",
        dense=True,
        expand=True,
    )
    album_id_field = ft.TextField(
        label="Target Album ID",
        dense=True,
        expand=True,
    )
    audio_album_field = ft.TextField(
        label="Audio Album (optional)",
        value="",
        dense=True,
        expand=True,
    )

    def line(msg: str, ok: bool | None = None) -> None:
        color = None
        icon = ft.Icons.INFO_OUTLINE
        if ok is True:
            color = ft.Colors.GREEN
            icon = ft.Icons.CHECK_CIRCLE_OUTLINE
        elif ok is False:
            color = ft.Colors.ERROR
            icon = ft.Icons.ERROR_OUTLINE
        log.controls.append(
            ft.Row(
                spacing=6,
                controls=[
                    ft.Icon(icon, size=14, color=color or ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(msg, size=11, color=color, selectable=True, expand=True, font_family="monospace"),
                ],
            )
        )
        page.update()

    def clear_log(e: ft.ControlEvent) -> None:
        log.controls.clear()
        page.update()

    async def do_move(e: ft.ControlEvent) -> None:
        aid = asset_id_field.value or ""
        tpath = path_field.value or ""
        if not aid:
            line("move_asset: Asset ID cannot be empty", False)
            return
        try:
            ok = await media.move_asset(aid, tpath)
            line(f"move_asset({aid}) → {ok}", ok)
        except Exception as ex:  # noqa: BLE001
            line(f"move_asset FAIL: {ex}", False)

    async def do_rename(e: ft.ControlEvent) -> None:
        aid = asset_id_field.value or ""
        nname = name_field.value or ""
        if not aid:
            line("rename_asset: Asset ID cannot be empty", False)
            return
        try:
            ok = await media.rename_asset(aid, nname)
            line(f"rename_asset({aid}) → {ok}", ok)
        except Exception as ex:  # noqa: BLE001
            line(f"rename_asset FAIL: {ex}", False)

    async def do_copy(e: ft.ControlEvent) -> None:
        aid = asset_id_field.value or ""
        albid = album_id_field.value or ""
        if not aid:
            line("copy_asset: Asset ID cannot be empty", False)
            return
        try:
            asset = await media.copy_asset(aid, albid)
            session.track_owned(asset.id)
            line(f"copy_asset({aid}) → new_id={asset.id}", True)
        except UnsupportedError as ex:
            line(f"copy_asset SKIP: {ex}", None)
        except Exception as ex:  # noqa: BLE001
            line(f"copy_asset FAIL: {ex}", False)

    async def clear_cache(e: ft.ControlEvent) -> None:
        try:
            await media.clear_file_cache()
            line("clear_file_cache OK", True)
        except Exception as ex:  # noqa: BLE001
            line(f"clear_file_cache FAIL: {ex}", False)

    async def pick_and_save_audio(e: ft.ControlEvent) -> None:
        """Pick an audio file via system picker, then save_audio into the library."""
        try:
            files = await file_picker.pick_files(
                allow_multiple=False,
                file_type=ft.FilePickerFileType.AUDIO,
                dialog_title="Pick audio to save into media library",
            )
        except Exception as ex:  # noqa: BLE001
            line(f"FilePicker FAIL: {ex}", False)
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))
            return

        if not files:
            line("save_audio cancelled (no file picked)", None)
            return

        f = files[0]
        file_path = getattr(f, "path", None) or ""
        if not file_path:
            line("save_audio needs a local path; FilePicker did not return path.", False)
            return

        album = audio_album_field.value or None
        try:
            asset = await media.save_audio(
                file_path,
                file_name=Path(file_path).name or f.name,
                album=album,
            )
            session.track_owned(asset.id)
            line(f"save_audio OK: id={asset.id} name={asset.display_name}", True)
            page.show_dialog(ft.SnackBar(content=ft.Text(f"Audio saved: {asset.display_name}")))
        except UnsupportedError as ex:
            line(f"save_audio SKIP (platform): {ex}", None)
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))
        except Exception as ex:  # noqa: BLE001
            line(f"save_audio FAIL: {ex}", False)
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))

    async def smoke(e: ft.ControlEvent) -> None:
        log.controls.clear()
        line("=== STARTING SMOKE CHECKLIST ===")
        try:
            st = await media.request_permissions(["image", "video", "audio"])
            line(f"1. Permissions: states={st.states}", True)
        except Exception as ex:  # noqa: BLE001
            line(f"1. Permissions FAIL: {ex}", False)
            return
        try:
            albums = await media.get_albums(media_type="image")
            line(f"2. Get Albums: count={len(albums)}", True)
        except Exception as ex:  # noqa: BLE001
            line(f"2. Get Albums FAIL: {ex}", False)
        first_id = ""
        try:
            page_res = await media.get_assets(media_type="image", limit=5)
            first_id = page_res.items[0].id if page_res.items else ""
            line(f"3. Get Assets: total={page_res.total} fetched={len(page_res.items)}", True)
        except Exception as ex:  # noqa: BLE001
            line(f"3. Get Assets FAIL: {ex}", False)
        if first_id:
            try:
                thumb = await media.get_thumbnail(first_id, width=64, height=64)
                line(f"4. Get Thumbnail: len={len(thumb or '')}", bool(thumb))
            except Exception as ex:  # noqa: BLE001
                line(f"4. Get Thumbnail FAIL: {ex}", False)
            try:
                a = await media.get_asset(first_id)
                line(f"5. Get Asset: name={a.display_name}", True)
            except Exception as ex:  # noqa: BLE001
                line(f"5. Get Asset FAIL: {ex}", False)
        else:
            line("4/5. Skip thumbnail/details (no assets found)", None)
        try:
            await media.start_change_notify()
            line("6. Start Change Notify OK", True)
        except Exception as ex:  # noqa: BLE001
            line(f"6. Start Change Notify FAIL: {ex}", False)
        line("=== SMOKE CHECKLIST COMPLETE ===")

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            # Asset Operations Card
            ft.Card(
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Icon(ft.Icons.HANDYMAN_ROUNDED, color=ft.Colors.PRIMARY, size=20),
                                    ft.Text("Asset Management", size=15, weight=ft.FontWeight.BOLD),
                                ],
                            ),
                            ft.Row([asset_id_field]),
                            ft.Row([path_field, ft.Button("Move", icon=ft.Icons.DRIVE_FILE_MOVE_ROUNDED, on_click=do_move)]),
                            ft.Row([name_field, ft.Button("Rename", icon=ft.Icons.EDIT_ROUNDED, on_click=do_rename)]),
                            ft.Row([album_id_field, ft.Button("Copy", icon=ft.Icons.CONTENT_COPY_ROUNDED, on_click=do_copy)]),
                        ],
                    ),
                ),
            ),
            # Audio Importer Card
            ft.Card(
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Icon(ft.Icons.AUDIOTRACK_ROUNDED, color=ft.Colors.PRIMARY, size=20),
                                    ft.Text("Audio Importer (Android)", size=15, weight=ft.FontWeight.BOLD),
                                ],
                            ),
                            ft.Row([
                                audio_album_field,
                                ft.Button(
                                    "Pick & Save Audio",
                                    icon=ft.Icons.AUDIO_FILE_ROUNDED,
                                    on_click=pick_and_save_audio,
                                ),
                            ]),
                        ],
                    ),
                ),
            ),
            # Diagnostics Card
            ft.Card(
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Icon(ft.Icons.CHECKLIST_ROUNDED, color=ft.Colors.PRIMARY, size=20),
                                            ft.Text("Diagnostics & Tests", size=15, weight=ft.FontWeight.BOLD),
                                        ],
                                    ),
                                    ft.Text(f"Owned assets: {len(session.owned_asset_ids)}", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                ],
                            ),
                            ft.Row(
                                wrap=True,
                                spacing=8,
                                controls=[
                                    ft.Button("Run Smoke Test", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=smoke),
                                    ft.Button("Clear File Cache", icon=ft.Icons.CLEANING_SERVICES_ROUNDED, on_click=clear_cache),
                                ],
                            ),
                        ],
                    ),
                ),
            ),
            # Output Console Card
            ft.Card(
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Row([
                                        ft.Icon(ft.Icons.TERMINAL_ROUNDED, size=18, color=ft.Colors.PRIMARY),
                                        ft.Text("Diagnostics Log", weight=ft.FontWeight.BOLD, size=14),
                                    ]),
                                    ft.TextButton("Clear", icon=ft.Icons.CLEAR_ALL_ROUNDED, on_click=clear_log),
                                ],
                            ),
                            ft.Container(
                                height=160,
                                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                                border_radius=8,
                                padding=8,
                                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                                content=log,
                            ),
                        ],
                    ),
                ),
            ),
        ],
    )
