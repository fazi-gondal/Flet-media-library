"""Camera photo + video recording → save via flet-media-library with modern UI."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import flet as ft

from services.media import DemoSession

try:
    import flet_camera as fc

    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False
    fc = None  # type: ignore


def build_capture(page: ft.Page, session: DemoSession) -> ft.Control:
    media = session.media
    status = ft.Text(
        "Camera ready. Tap 'Init camera' or take a shot." if HAS_CAMERA else "flet-camera is not installed.",
        size=12,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )
    album_field = ft.TextField(
        label="Target Album",
        value="DCIM",
        dense=True,
        width=200,
        prefix_icon=ft.Icons.FOLDER_SPECIAL_ROUNDED,
    )
    preview_img = ft.Image("", width=140, height=140, fit=ft.BoxFit.COVER, border_radius=8, visible=False)
    preview_info = ft.Text("No capture yet", size=11, color=ft.Colors.OUTLINE)

    if not HAS_CAMERA:
        return ft.Column(
            expand=True,
            spacing=16,
            controls=[
                ft.Card(
                    content=ft.Container(
                        padding=24,
                        content=ft.Column(
                            spacing=12,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.NO_PHOTOGRAPHY_ROUNDED, size=56, color=ft.Colors.OUTLINE),
                                ft.Text("Camera Not Available", size=18, weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    "`flet-camera` is not installed or current platform has no camera driver.",
                                    size=13,
                                    text_align=ft.TextAlign.CENTER,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Container(
                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                    padding=12,
                                    border_radius=8,
                                    content=ft.Text(
                                        "Build with camera permission:\n"
                                        "uv run flet build apk --permissions camera microphone",
                                        font_family="monospace",
                                        size=11,
                                    ),
                                ),
                            ],
                        ),
                    ),
                )
            ],
        )

    cam = fc.Camera(
        expand=True,
        preview_enabled=True,
        height=320,
        content=ft.Container(
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
                controls=[
                    ft.Icon(ft.Icons.PHOTO_CAMERA, size=48, color=ft.Colors.WHITE_70),
                    ft.Text("Camera Viewfinder", size=12, color=ft.Colors.WHITE_70),
                ],
            ),
        ),
    )
    cam_state = {"initialized": False, "recording": False, "description": None}

    async def list_and_init(e: ft.ControlEvent | None = None) -> None:
        try:
            cameras = await cam.get_available_cameras()
            if not cameras:
                status.value = "No cameras found on device."
                status.color = ft.Colors.ERROR
                page.update()
                return
            desc = cameras[0]
            cam_state["description"] = desc
            status.value = f"Initializing {desc.name}…"
            page.update()
            await cam.initialize(
                description=desc,
                resolution_preset=fc.ResolutionPreset.MEDIUM,
                enable_audio=True,
                image_format_group=fc.ImageFormatGroup.JPEG,
            )
            cam_state["initialized"] = True
            status.value = f"Ready: {desc.name}"
            status.color = ft.Colors.GREEN
        except Exception as ex:  # noqa: BLE001
            status.value = f"Init failed: {ex}"
            status.color = ft.Colors.ERROR
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))
        page.update()

    async def take_photo(e: ft.ControlEvent) -> None:
        if not cam_state["initialized"]:
            await list_and_init()
        if not cam_state["initialized"]:
            return
        try:
            data = await cam.take_picture()
            if not data:
                status.value = "Empty photo data returned."
                page.update()
                return
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = Path(tempfile.gettempdir()) / f"mldemo_{ts}.jpg"
            raw = data if isinstance(data, (bytes, bytearray)) else bytes(data)
            path.write_bytes(raw)
            album = album_field.value or None
            asset = await media.save_image(str(path), file_name=path.name, album=album)
            session.track_owned(asset.id)
            preview_img.src = ""
            try:
                thumb = await media.get_thumbnail(asset.id, width=280, height=280)
                if thumb:
                    preview_img.src = thumb
                    preview_img.visible = True
            except Exception:  # noqa: BLE001
                pass
            preview_info.value = f"Saved Image: {asset.display_name}\nID: {asset.id}\nSize: {path.stat().st_size} bytes"
            status.value = f"Photo saved to {album or 'gallery'}: {asset.id}"
            status.color = ft.Colors.GREEN
            page.show_dialog(ft.SnackBar(content=ft.Text(f"Photo saved: {asset.display_name}")))
        except Exception as ex:  # noqa: BLE001
            status.value = f"Photo error: {ex}"
            status.color = ft.Colors.ERROR
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))
        page.update()

    async def toggle_record(e: ft.ControlEvent) -> None:
        if not cam_state["initialized"]:
            await list_and_init()
        if not cam_state["initialized"]:
            return
        try:
            if not cam_state["recording"]:
                await cam.prepare_for_video_recording()
                await cam.start_video_recording()
                cam_state["recording"] = True
                status.value = "Recording video…"
                status.color = ft.Colors.ERROR
                record_btn.content = "Stop Recording"
                record_btn.icon = ft.Icons.STOP_CIRCLE_ROUNDED
            else:
                data = await cam.stop_video_recording()
                cam_state["recording"] = False
                record_btn.content = "Record Video"
                record_btn.icon = ft.Icons.VIDEOCAM_ROUNDED
                if not data:
                    status.value = "No video data returned."
                    page.update()
                    return
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = Path(tempfile.gettempdir()) / f"mldemo_{ts}.mp4"
                raw = data if isinstance(data, (bytes, bytearray)) else bytes(data)
                path.write_bytes(raw)
                album = album_field.value or None
                asset = await media.save_video(str(path), file_name=path.name, album=album)
                session.track_owned(asset.id)
                preview_info.value = f"Saved Video: {asset.display_name}\nID: {asset.id}"
                status.value = f"Video saved to {album or 'gallery'}: {asset.id}"
                status.color = ft.Colors.GREEN
                page.show_dialog(ft.SnackBar(content=ft.Text(f"Video saved: {asset.display_name}")))
        except Exception as ex:  # noqa: BLE001
            cam_state["recording"] = False
            record_btn.content = "Record Video"
            record_btn.icon = ft.Icons.VIDEOCAM_ROUNDED
            status.value = f"Video error: {ex}"
            status.color = ft.Colors.ERROR
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))
        page.update()

    record_btn = ft.Button("Record Video", icon=ft.Icons.VIDEOCAM_ROUNDED, on_click=toggle_record)

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            # Camera Viewfinder Card
            ft.Card(
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    album_field,
                                    ft.Button("Switch Camera", icon=ft.Icons.CAMERASWITCH_ROUNDED, on_click=list_and_init),
                                ],
                            ),
                            ft.Container(
                                height=260,
                                border_radius=12,
                                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                                bgcolor=ft.Colors.BLACK,
                                content=cam,
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=12,
                                controls=[
                                    ft.Button("Capture Photo", icon=ft.Icons.CAMERA_ALT_ROUNDED, on_click=take_photo),
                                    record_btn,
                                ],
                            ),
                            status,
                        ],
                    ),
                ),
            ),
            # Latest Capture Card
            ft.Card(
                content=ft.Container(
                    padding=16,
                    content=ft.Row(
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            preview_img,
                            ft.Column(
                                expand=True,
                                spacing=4,
                                controls=[
                                    ft.Text("Last Capture Preview", weight=ft.FontWeight.BOLD, size=14),
                                    preview_info,
                                ],
                            ),
                        ],
                    ),
                ),
            ),
        ],
    )
