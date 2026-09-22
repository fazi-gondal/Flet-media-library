"""Path and directory utilities for cross-platform Flet mobile apps."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _probe_writable(p: Path) -> bool:
    """Return True if *p* exists (or can be created) and is writable."""
    try:
        p.mkdir(parents=True, exist_ok=True)
        test_file = p / ".write_probe"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def get_app_temp_dir() -> Path:
    """Return a guaranteed-writable scratch directory for Android, iOS, and Desktop.

    ### Why not `tempfile.gettempdir()` or `Path.resolve()`?

    On Android (Serious Python / Flet production builds) `tempfile.gettempdir()`
    defaults to `/tmp` which does not exist → native MediaRecorder crash.

    Flet injects `FLET_APP_STORAGE_TEMP`, `FLET_APP_STORAGE_CACHE`, and
    `FLET_APP_STORAGE_DATA` as **absolute** paths into the process environment.
    However, calling `Path(value).resolve()` is **wrong** on Android because the
    Flet Python runtime's CWD is deep inside the APK assets directory:

        /data/user/0/<pkg>/files/flet/app/assets/

    When `FLET_APP_STORAGE_CACHE` contains the raw string returned by Android's
    `Context.getCacheDir()` (e.g. `/data/user/0/<pkg>/cache`), `.resolve()` can
    in some builds produce a doubled path:

        /data/user/0/<pkg>/files/flet/app/assets/data/user/0/<pkg>/cache

    …because `os.path.abspath` can behave unexpectedly when the underlying
    filesystem exposes the path through a bind-mount visible inside the CWD.

    **Fix**: use the env-var value verbatim (as an absolute `Path`) without
    `.resolve()`, and only accept it if it is already absolute.
    """
    # Priority: Flet-injected dirs first (most reliable on Android/iOS)
    flet_candidates = [
        os.environ.get("FLET_APP_STORAGE_TEMP"),
        os.environ.get("FLET_APP_STORAGE_CACHE"),
        os.environ.get("FLET_APP_STORAGE_DATA"),  # persistent, falls back here
    ]
    for c in flet_candidates:
        if not c:
            continue
        p = Path(c)
        # Only accept paths that are already absolute to avoid CWD-relative
        # resolution bugs on Android.
        if not p.is_absolute():
            continue
        if _probe_writable(p):
            tempfile.tempdir = str(p)
            os.environ["TMPDIR"] = str(p)
            return p

    # Standard OS temp vars (work on Linux/macOS/Windows desktops)
    for var in ("TMPDIR", "TEMP", "TMP"):
        c = os.environ.get(var)
        if not c:
            continue
        p = Path(c)
        if not p.is_absolute():
            continue
        if _probe_writable(p):
            return p

    # Last resort: ask tempfile (safe on desktop, may fail on Android /tmp)
    try:
        p = Path(tempfile.gettempdir())
        if _probe_writable(p):
            return p
    except Exception:
        pass

    # Ultimate fallback: home-dir scratch folder
    try:
        p = Path.home() / ".mldemo_cache"
        if _probe_writable(p):
            tempfile.tempdir = str(p)
            os.environ["TMPDIR"] = str(p)
            return p
    except Exception:
        pass

    # If everything else fails return CWD (should never happen in practice)
    fallback = Path(".").absolute()
    tempfile.tempdir = str(fallback)
    os.environ["TMPDIR"] = str(fallback)
    return fallback
