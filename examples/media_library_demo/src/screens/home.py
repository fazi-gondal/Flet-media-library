"""Permissions + change-notification screen with modern Material 3 design."""

from __future__ import annotations

import flet as ft

from services.media import DemoSession


def build_home(page: ft.Page, session: DemoSession) -> ft.Control:
    # State controls
    images_chip = ft.Chip(
        label=ft.Text("Images: Unknown", size=11),
        leading=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16),
    )
    videos_chip = ft.Chip(
        label=ft.Text("Videos: Unknown", size=11),
        leading=ft.Icon(ft.Icons.VIDEOCAM_OUTLINED, size=16),
    )
    audio_chip = ft.Chip(
        label=ft.Text("Audio: Unknown", size=11),
        leading=ft.Icon(ft.Icons.AUDIOTRACK_OUTLINED, size=16),
    )
    summary_text = ft.Text(
        "Permissions not checked yet. Tap 'Request Access' or 'Check Status'.",
        size=12,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )

    observer_status = ft.Text("Observer: Stopped", size=12, weight=ft.FontWeight.W_500)
    observer_badge = ft.Container(
        width=10,
        height=10,
        border_radius=5,
        bgcolor=ft.Colors.GREY_500,
    )

    log_count_text = ft.Text("0 events", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
    log_view = ft.ListView(expand=True, spacing=4, auto_scroll=True)

    def append_log(msg: str, icon_name: str = ft.Icons.INFO_OUTLINE) -> None:
        session.change_log.append(msg)
        item = ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=6,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(icon_name, size=16, color=ft.Colors.PRIMARY),
                    ft.Text(msg, size=12, selectable=True, expand=True, font_family="monospace"),
                ],
            ),
        )
        log_view.controls.append(item)
        if len(log_view.controls) > 100:
            log_view.controls.pop(0)
        log_count_text.value = f"{len(log_view.controls)} events"
        page.update()

    def clear_log(e: ft.ControlEvent) -> None:
        log_view.controls.clear()
        session.change_log.clear()
        log_count_text.value = "0 events"
        page.update()

    def on_library_change(e) -> None:
        change_type = getattr(e, "change_type", "?")
        aid = getattr(e, "asset_id", "")
        mt = getattr(e, "media_type", "")
        msg = f"[{change_type.upper()}] type={mt} asset={aid or 'n/a'}"
        append_log(msg, ft.Icons.NOTIFICATIONS_ACTIVE)

    session.media.on_change = on_library_change

    def update_chips(st) -> None:
        states = st.states or {}
        for chip, key, label in [
            (images_chip, "image", "Images"),
            (videos_chip, "video", "Videos"),
            (audio_chip, "audio", "Audio"),
        ]:
            val = states.get(key, "unknown")
            chip.label = ft.Text(f"{label}: {val.capitalize()}", size=11)
            if val == "authorized":
                chip.leading = ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=ft.Colors.GREEN)
            elif val == "limited":
                chip.leading = ft.Icon(ft.Icons.PIE_CHART_OUTLINED, size=16, color=ft.Colors.AMBER)
            elif val in ("denied", "restricted"):
                chip.leading = ft.Icon(ft.Icons.CANCEL, size=16, color=ft.Colors.ERROR)
            else:
                chip.leading = ft.Icon(ft.Icons.HELP_OUTLINE, size=16, color=ft.Colors.GREY_500)

        if st.all_granted:
            summary_text.value = "All media permissions fully granted."
            summary_text.color = ft.Colors.GREEN
        elif st.any_limited:
            summary_text.value = "Limited / partial media access granted."
            summary_text.color = ft.Colors.AMBER
        else:
            summary_text.value = f"can_request={st.can_request} states={states}"
            summary_text.color = ft.Colors.ON_SURFACE_VARIANT

    async def refresh_status(e: ft.ControlEvent | None = None) -> None:
        try:
            st = await session.media.check_permissions(["image", "video", "audio"])
            session.last_permission = st
            update_chips(st)
        except Exception as ex:  # noqa: BLE001
            summary_text.value = f"Check failed: {ex}"
            summary_text.color = ft.Colors.ERROR
        page.update()

    async def request_perms(e: ft.ControlEvent) -> None:
        try:
            st = await session.media.request_permissions(["image", "video", "audio"])
            session.last_permission = st
            update_chips(st)
            append_log(f"Permissions requested: all_granted={st.all_granted} any_limited={st.any_limited}")
        except Exception as ex:  # noqa: BLE001
            summary_text.value = f"Request failed: {ex}"
            summary_text.color = ft.Colors.ERROR
            append_log(f"Request error: {ex}", ft.Icons.ERROR)
        page.update()

    async def present_limited(e: ft.ControlEvent) -> None:
        try:
            await session.media.present_limited(["image", "video"])
            append_log("Present limited picker opened")
            await refresh_status()
        except Exception as ex:  # noqa: BLE001
            append_log(f"Present limited error: {ex}", ft.Icons.ERROR)
            page.show_dialog(ft.SnackBar(content=ft.Text(str(ex))))

    async def open_settings(e: ft.ControlEvent) -> None:
        try:
            await session.media.open_settings()
            append_log("Opened system app settings")
        except Exception as ex:  # noqa: BLE001
            append_log(f"Open settings error: {ex}", ft.Icons.ERROR)

    async def start_notify(e: ft.ControlEvent) -> None:
        try:
            await session.media.start_change_notify()
            observer_status.value = "Observer: Active"
            observer_status.color = ft.Colors.GREEN
            observer_badge.bgcolor = ft.Colors.GREEN
            append_log("Change observer STARTED", ft.Icons.PLAY_ARROW)
        except Exception as ex:  # noqa: BLE001
            append_log(f"Start observer error: {ex}", ft.Icons.ERROR)
        page.update()

    async def stop_notify(e: ft.ControlEvent) -> None:
        try:
            await session.media.stop_change_notify()
            observer_status.value = "Observer: Stopped"
            observer_status.color = None
            observer_badge.bgcolor = ft.Colors.GREY_500
            append_log("Change observer STOPPED", ft.Icons.STOP)
        except Exception as ex:  # noqa: BLE001
            append_log(f"Stop observer error: {ex}", ft.Icons.ERROR)
        page.update()

    # Initial check (best-effort).
    page.run_task(refresh_status)

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            # Permission Status Hero Card
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
                                            ft.Icon(ft.Icons.SECURITY_ROUNDED, color=ft.Colors.PRIMARY, size=22),
                                            ft.Text("Permissions & Access", size=16, weight=ft.FontWeight.BOLD),
                                        ],
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.REFRESH_ROUNDED,
                                        tooltip="Re-check status",
                                        on_click=lambda e: page.run_task(refresh_status),
                                    ),
                                ],
                            ),
                            summary_text,
                            ft.Row(
                                wrap=True,
                                spacing=8,
                                controls=[images_chip, videos_chip, audio_chip],
                            ),
                            ft.Row(
                                wrap=True,
                                spacing=8,
                                controls=[
                                    ft.Button(
                                        "Request Access",
                                        icon=ft.Icons.LOCK_OPEN_ROUNDED,
                                        on_click=request_perms,
                                    ),
                                    ft.Button(
                                        "Present Limited Picker",
                                        icon=ft.Icons.PHOTO_LIBRARY_ROUNDED,
                                        on_click=present_limited,
                                    ),
                                    ft.Button(
                                        "App Settings",
                                        icon=ft.Icons.SETTINGS_ROUNDED,
                                        on_click=open_settings,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ),
            # Observer & Realtime Card
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
                                            observer_badge,
                                            observer_status,
                                        ],
                                    ),
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Button("Start", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=start_notify),
                                            ft.Button("Stop", icon=ft.Icons.STOP_ROUNDED, on_click=stop_notify),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ),
            # Activity Log Card
            ft.Card(
                expand=True,
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        expand=True,
                        spacing=8,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Icon(ft.Icons.HISTORY_ROUNDED, size=20, color=ft.Colors.PRIMARY),
                                            ft.Text("Live Library Events", weight=ft.FontWeight.BOLD, size=15),
                                            log_count_text,
                                        ],
                                    ),
                                    ft.TextButton("Clear", icon=ft.Icons.CLEAR_ALL_ROUNDED, on_click=clear_log),
                                ],
                            ),
                            ft.Container(
                                expand=True,
                                height=180,
                                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                                border_radius=10,
                                padding=8,
                                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                                content=log_view,
                            ),
                        ],
                    ),
                ),
            ),
        ],
    )
