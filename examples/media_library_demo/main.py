"""
Flet entry point for `flet build` / `flet run` from the demo root.

The actual app lives in src/main.py. This shim adds src/ to sys.path so that
`screens.*` and `services.*` imports resolve correctly, then hands off to the
real main() function.

Usage:
    uv run flet run          # desktop preview
    uv run flet build apk    # Android APK
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is importable (screens, services packages).
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import flet as ft
from src.main import main  # noqa: E402

if __name__ == "__main__":
    ft.run(main)
