"""Path and directory utilities for cross-platform Flet mobile apps."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def get_app_temp_dir() -> Path:
    """Resolve a guaranteed-writable scratch/temp directory across Android, iOS, and Desktop.

    On Android in production (Serious Python / Flet), standard `tempfile.gettempdir()`
    defaults to `/tmp`, which does not exist and causes native crashes when passed to
    plugins like `AudioRecorder` (MediaRecorder/AudioRecord).
    Flet runtime provides `FLET_APP_STORAGE_TEMP` and `FLET_APP_STORAGE_CACHE`.
    """
    candidates = [
        os.environ.get("FLET_APP_STORAGE_TEMP"),
        os.environ.get("FLET_APP_STORAGE_CACHE"),
        os.environ.get("TMPDIR"),
        os.environ.get("TEMP"),
        os.environ.get("TMP"),
    ]
    for c in candidates:
        if c:
            p = Path(c).resolve()
            try:
                p.mkdir(parents=True, exist_ok=True)
                test_file = p / ".write_probe"
                test_file.write_text("ok", encoding="utf-8")
                test_file.unlink(missing_ok=True)
                tempfile.tempdir = str(p)
                os.environ["TMPDIR"] = str(p)
                return p
            except Exception:
                continue

    try:
        p = Path(tempfile.gettempdir()).resolve()
        p.mkdir(parents=True, exist_ok=True)
        test_file = p / ".write_probe"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return p
    except Exception:
        pass

    # Fallback to user home directory cache or current working directory
    try:
        p = (Path.home() / ".mldemo_cache").resolve()
        p.mkdir(parents=True, exist_ok=True)
        tempfile.tempdir = str(p)
        os.environ["TMPDIR"] = str(p)
        return p
    except Exception:
        pass

    fallback = Path(".").resolve()
    tempfile.tempdir = str(fallback)
    os.environ["TMPDIR"] = str(fallback)
    return fallback
