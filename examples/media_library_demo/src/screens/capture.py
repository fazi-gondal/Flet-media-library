"""Camera photo + video recording + microphone audio recording → flet-media-library."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import flet as ft

from services.media import DemoSession
from services.paths import get_app_temp_dir

try:
    import flet_camera as fc

    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False
    fc = None  # type: ignore

try:
    import flet_audio_recorder as far

    HAS_RECORDER = True
except ImportError:
    HAS_RECORDER = False
    far = None  # type: ignore


def build_capture(page: ft.Page, session: DemoSession) -> ft.Control:
    media = session.media

    # ────────────────────────────────────────────────────────────────────────
    # Shared status + album field
    # ────────────────────────────────────────────────────────────────────────
    status = ft.Text(
        "Camera ready." if HAS_CAMERA else "flet-camera is not installed.",
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

    # ────────────────────────────────────────────────────────────────────────
    # Audio Recorder section (always shown if flet_audio_recorder installed)
    # ────────────────────────────────────────────────────────────────────────
    rec_status = ft.Text("Tap ● to start recording", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
    rec_timer_text = ft.Text("00:00", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
    rec_state = {"recording": False, "seconds": 0, "timer_task": None}
    rec_filename_field = ft.TextField(
        label="Recording filename",
        value=f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.m4a",
        dense=True,
        expand=True,
        hint_text="e.g. my_voice_note.m4a",
    )

    def _build_recorder_card() -> ft.Control:
        if not HAS_RECORDER:
            return ft.Card(
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                        controls=[
                            ft.Icon(ft.Icons.MIC_OFF_ROUNDED, size=40, color=ft.Colors.OUTLINE),
                            ft.Text("Audio Recorder Not Available", size=15, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "`flet-audio-recorder` is not installed.\n"
                                "Add it to pyproject.toml dependencies to enable mic recording.",
                                size=12,
                                text_align=ft.TextAlign.CENTER,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Container(
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                padding=10,
                                border_radius=8,
                                content=ft.Text(
                                    "uv add flet-audio-recorder",
                                    font_family="monospace",
                                    size=11,
                                ),
                            ),
                        ],
                    ),
                ),
            )

        recorder = next((s for s in getattr(page, "services", []) if isinstance(s, far.AudioRecorder)), None)
        if recorder is None:
            config = far.AudioRecorderConfiguration(
                encoder=far.AudioEncoder.AACLC,
                suppress_noise=True,
            )
            recorder = far.AudioRecorder(configuration=config)
            page.services.append(recorder)

        rec_btn_ref = ft.Ref[ft.IconButton]()
        level_bar = ft.ProgressBar(value=0, width=200, color=ft.Colors.PRIMARY, bgcolor=ft.Colors.OUTLINE_VARIANT)

        async def _tick_timer() -> None:
            while rec_state["recording"]:
                await asyncio.sleep(1)
                rec_state["seconds"] += 1
                m, s = divmod(rec_state["seconds"], 60)
                rec_timer_text.value = f"{m:02d}:{s:02d}"
                page.update()

        async def toggle_recording(e: ft.ControlEvent) -> None:
            if not rec_state["recording"]:
                try:
                    if hasattr(recorder, "has_permission"):
                        has_perm = await recorder.has_permission()
                        if not has_perm:
                            rec_status.value = "Microphone permission denied"
                            rec_status.color = ft.Colors.ERROR
                            page.update()
                            return
                except Exception as perm_ex:
                    rec_status.value = f"Permission check failed: {perm_ex}"
                    rec_status.color = ft.Colors.ERROR
                    page.update()
                    return

                # Start recording to a guaranteed-writable temp directory
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_dir = get_app_temp_dir()
                target_dir.mkdir(parents=True, exist_ok=True)
                tmp_path = target_dir / f"mldemo_rec_{ts}.m4a"
                rec_state["tmp_path"] = str(tmp_path)
                rec_state["seconds"] = 0
                rec_timer_text.value = "00:00"
                rec_status.value = f"Starting… ({tmp_path})"
                rec_status.color = ft.Colors.ON_SURFACE_VARIANT
                page.update()
                try:
                    await recorder.start_recording(output_path=str(tmp_path))
                    rec_state["recording"] = True
                    rec_btn_ref.current.icon = ft.Icons.STOP_CIRCLE_ROUNDED
                    rec_btn_ref.current.icon_color = ft.Colors.ERROR
                    rec_status.value = "Recording… tap ■ to stop"
                    rec_status.color = ft.Colors.ERROR
                    level_bar.value = None  # pulse progress bar
                    rec_state["timer_task"] = page.run_task(_tick_timer)
                except Exception as ex:  # noqa: BLE001
                    rec_status.value = f"Could not start recording: {ex}\nPath: {tmp_path}"
                    rec_status.color = ft.Colors.ERROR
                    rec_state["tmp_path"] = ""  # invalidate so stop path is not stale
            else:
                # Stop recording
                stop_error: str | None = None
                try:
                    out = await recorder.stop_recording()
                    if out:
                        rec_state["tmp_path"] = out
                except Exception as stop_ex:  # noqa: BLE001
                    stop_error = str(stop_ex)
                rec_state["recording"] = False
                rec_btn_ref.current.icon = ft.Icons.MIC_ROUNDED
                rec_btn_ref.current.icon_color = ft.Colors.PRIMARY
                level_bar.value = 0

                # Save to Music/Recordings via save_audio
                raw_path = rec_state.get("tmp_path", "")
                tmp_path = Path(raw_path) if raw_path else None
                if not tmp_path or not raw_path:
                    msg = f"No recording path available{': ' + stop_error if stop_error else ''}"
                    rec_status.value = msg
                    rec_status.color = ft.Colors.ERROR
                    page.update()
                    return
                if not tmp_path.exists():
                    rec_status.value = (
                        f"Recording file not found: {tmp_path}"
                        + (f"\nStop error: {stop_error}" if stop_error else "")
                    )
                    rec_status.color = ft.Colors.ERROR
                    page.update()
                    return
                rec_status.value = "Saving to Music…"
                rec_status.color = None
                page.update()

                fname = rec_filename_field.value.strip() or f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.m4a"
                # Refresh filename for next recording
                rec_filename_field.value = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.m4a"
                try:
                    asset = await media.save_audio(
                        str(tmp_path),
                        file_name=fname,
                        album="Music/Recordings",
                    )
                    session.track_owned(asset.id)
                    tmp_path.unlink(missing_ok=True)
                    rec_status.value = f"Saved to Music: {asset.display_name}"
                    rec_status.color = ft.Colors.GREEN
                    page.show_dialog(
                        ft.SnackBar(content=ft.Text(f"Recording saved to Music/Recordings: {asset.display_name}"))
                    )
                except Exception as ex:  # noqa: BLE001
                    rec_status.value = f"Save failed: {ex}"
                    rec_status.color = ft.Colors.ERROR
                    page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))

            page.update()

        return ft.Card(
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.MIC_ROUNDED, color=ft.Colors.PRIMARY, size=20),
                                ft.Text("Audio Recorder", size=15, weight=ft.FontWeight.BOLD),
                                ft.Text("(saves to Music/Recordings)", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            ],
                        ),
                        rec_filename_field,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=16,
                            controls=[
                                rec_timer_text,
                                ft.IconButton(
                                    ref=rec_btn_ref,
                                    icon=ft.Icons.MIC_ROUNDED,
                                    icon_size=56,
                                    icon_color=ft.Colors.PRIMARY,
                                    tooltip="Start / Stop Recording",
                                    style=ft.ButtonStyle(
                                        shape=ft.CircleBorder(),
                                        bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                    ),
                                    on_click=toggle_recording,
                                ),
                            ],
                        ),
                        level_bar,
                        rec_status,
                    ],
                ),
            ),
        )

    recorder_card = _build_recorder_card()

    # ────────────────────────────────────────────────────────────────────────
    # Camera section
    # ────────────────────────────────────────────────────────────────────────
    if not HAS_CAMERA:
        return ft.Column(
            expand=True,
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
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
                ),
                recorder_card,
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
            path = get_app_temp_dir() / f"mldemo_{ts}.jpg"
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
            path.unlink(missing_ok=True)
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
                path = get_app_temp_dir() / f"mldemo_{ts}.mp4"
                raw = data if isinstance(data, (bytes, bytearray)) else bytes(data)
                path.write_bytes(raw)
                album = album_field.value or None
                asset = await media.save_video(str(path), file_name=path.name, album=album)
                session.track_owned(asset.id)
                path.unlink(missing_ok=True)
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
            # Audio Recorder Card
            recorder_card,
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
