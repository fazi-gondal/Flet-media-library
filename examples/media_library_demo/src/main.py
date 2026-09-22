"""
Media Library Demo — full-feature harness for flet-media-library.

Uses Flet 1.0 (ft.run, NavigationBar, Button, services).
Local package is resolved via pyproject [tool.uv.sources] path dependency.

Run (from this directory):
    uv sync
    uv run flet run src/main.py

Android APK (tests real MediaStore + camera):
    uv run flet build apk --permissions camera microphone --yes
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `screens` / `services` imports when launched via `flet run src/main.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import flet as ft
from flet_media_library import MediaLibrary

from screens.capture import build_capture
from screens.gallery import build_gallery
from screens.home import build_home
from screens.tools import build_tools
import traceback
from services.media import DemoSession
from services.paths import get_app_temp_dir

# Initialize guaranteed writable temp directory for Android/iOS/Desktop
get_app_temp_dir()


def main(page: ft.Page) -> None:
    page.title = "Media Library Demo"
    page.padding = 12
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO, use_material3=True)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO, use_material3=True)

    # Surface any uncaught Flet page errors directly in the terminal
    def on_page_error(e: ft.ControlEvent) -> None:
        err_msg = getattr(e, "data", str(e))
        print(f"\n{'='*25} [FLET PAGE ERROR] {'='*25}", file=sys.stderr)
        print(f"{err_msg}", file=sys.stderr)
        print(f"{'='*69}\n", file=sys.stderr, flush=True)

    page.on_error = on_page_error

    try:
        media = MediaLibrary()
        page.services.append(media)
        session = DemoSession(media=media)
    except Exception as ex:
        err_tb = traceback.format_exc()
        print(f"\n{'='*25} [INIT ERROR] {'='*25}", file=sys.stderr)
        print(err_tb, file=sys.stderr)
        print(f"{'='*62}\n", file=sys.stderr, flush=True)
        page.add(
            ft.Container(
                padding=20,
                content=ft.Card(
                    content=ft.Container(
                        padding=20,
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.ERROR_ROUNDED, color=ft.Colors.ERROR, size=32),
                                        ft.Text("Initialization Failed", size=18, weight=ft.FontWeight.BOLD),
                                    ]
                                ),
                                ft.Text(str(ex)),
                                ft.Text(err_tb, font_family="monospace", size=11),
                            ]
                        ),
                    )
                ),
            )
        )
        return

    # Theme toggle action
    def toggle_theme(e: ft.ControlEvent) -> None:
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            theme_btn.icon = ft.Icons.DARK_MODE_OUTLINED
            theme_btn.tooltip = "Switch to dark mode"
        else:
            page.theme_mode = ft.ThemeMode.DARK
            theme_btn.icon = ft.Icons.LIGHT_MODE_OUTLINED
            theme_btn.tooltip = "Switch to light mode"
        page.update()

    theme_btn = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE_OUTLINED if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.DARK_MODE_OUTLINED,
        tooltip="Toggle theme",
        on_click=toggle_theme,
    )

    page.appbar = ft.AppBar(
        leading=ft.Container(
            content=ft.Icon(ft.Icons.PHOTO_LIBRARY_ROUNDED, color=ft.Colors.PRIMARY, size=24),
            padding=ft.Padding.only(left=12),
        ),
        leading_width=36,
        title=ft.Column(
            spacing=0,
            controls=[
                ft.Text("Media Library", weight=ft.FontWeight.BOLD, size=18),
                ft.Text("Flet 1.0 Demo", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
        ),
        center_title=False,
        actions=[theme_btn],
    )

    body = ft.Container(expand=True)

    screens = {
        0: lambda: build_home(page, session),
        1: lambda: build_gallery(page, session),
        2: lambda: build_capture(page, session),
        3: lambda: build_tools(page, session),
    }

    def show(index: int) -> None:
        try:
            body.content = screens[index]()
        except Exception as ex:
            err_tb = traceback.format_exc()
            # Prominently print the error and full stack trace in the terminal of the app!
            print(f"\n{'='*25} [SCREEN {index} RENDER ERROR] {'='*25}", file=sys.stderr)
            print(f"Exception: {ex}", file=sys.stderr)
            print(f"Traceback:\n{err_tb}", file=sys.stderr)
            print(f"{'='*72}\n", file=sys.stderr, flush=True)

            # And show a detailed error card in the app body
            body.content = ft.Container(
                padding=16,
                alignment=ft.Alignment.CENTER,
                content=ft.Card(
                    bgcolor=ft.Colors.ERROR_CONTAINER,
                    content=ft.Container(
                        padding=16,
                        content=ft.Column(
                            spacing=12,
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=ft.Colors.ERROR, size=28),
                                        ft.Text("Screen Render Error", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_ERROR_CONTAINER),
                                    ]
                                ),
                                ft.Text(str(ex), weight=ft.FontWeight.W_600, color=ft.Colors.ON_ERROR_CONTAINER),
                                ft.Container(
                                    bgcolor=ft.Colors.SURFACE,
                                    border_radius=8,
                                    padding=10,
                                    content=ft.Text(err_tb, size=11, selectable=True, font_family="monospace"),
                                ),
                                ft.Button(
                                    "Retry",
                                    icon=ft.Icons.REFRESH,
                                    on_click=lambda _: show(index),
                                ),
                            ],
                            scroll=ft.ScrollMode.AUTO,
                        ),
                    ),
                ),
            )
        page.update()

    def on_nav(e: ft.Event[ft.NavigationBar]) -> None:
        show(e.control.selected_index or 0)

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME_ROUNDED,
                label="Home",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.PHOTO_LIBRARY_OUTLINED,
                selected_icon=ft.Icons.PHOTO_LIBRARY_ROUNDED,
                label="Gallery",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.PHOTO_CAMERA_OUTLINED,
                selected_icon=ft.Icons.PHOTO_CAMERA_ROUNDED,
                label="Capture",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.BUILD_OUTLINED,
                selected_icon=ft.Icons.BUILD_ROUNDED,
                label="Tools",
            ),
        ],
    )

    show(0)
    page.add(body)


if __name__ == "__main__":
    ft.run(main)

