"""Path and directory utilities for cross-platform Flet mobile apps."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _is_usable_dir(p: Path) -> bool:
    """Return True if *p* is absolute, writable, and not under a read-only assets tree."""
    try:
        if not p.is_absolute():
            return False
        # Reject Flet asset bundles and other read-only trees that cause
        # MediaMuxer ENOENT when a relative env path is resolved against cwd.
        parts = {x.lower() for x in p.parts}
        if "assets" in parts and "flet" in parts:
            return False
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _candidate_from_env(name: str) -> Path | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    # Never resolve relative env values against process cwd (on Android that
    # is often the Flet assets dir, producing paths like
    # .../flet/app/assets/data/data/<pkg>/cache/...).
    p = Path(raw)
    if not p.is_absolute():
        return None
    return p


def get_app_temp_dir() -> Path:
    """Resolve a guaranteed-writable scratch/temp directory.

    On packaged Android/iOS Flet apps, ``tempfile.gettempdir()`` and relative
    paths are unsafe: cwd may be the assets tree, and ``/tmp`` may not exist.
    Prefer absolute ``FLET_APP_STORAGE_*`` dirs, then a few absolute fallbacks.
    """
    env_candidates = [
        _candidate_from_env("FLET_APP_STORAGE_TEMP"),
        _candidate_from_env("FLET_APP_STORAGE_CACHE"),
        # Durable data dir is still writable; use a dedicated subfolder.
        (
            (_candidate_from_env("FLET_APP_STORAGE_DATA") / "mldemo_tmp")
            if _candidate_from_env("FLET_APP_STORAGE_DATA")
            else None
        ),
        _candidate_from_env("TMPDIR"),
        _candidate_from_env("TEMP"),
        _candidate_from_env("TMP"),
    ]

    for c in env_candidates:
        if c is None:
            continue
        if _is_usable_dir(c):
            tempfile.tempdir = str(c)
            os.environ["TMPDIR"] = str(c)
            return c

    # Absolute Android-style fallbacks when env vars are missing or relative.
    # Package id matches [tool.flet] org + product in the demo pyproject.
    android_fallbacks = [
        Path("/data/user/0/com.gondal.media_library_demo/cache/mldemo"),
        Path("/data/data/com.gondal.media_library_demo/cache/mldemo"),
    ]
    for c in android_fallbacks:
        if _is_usable_dir(c):
            tempfile.tempdir = str(c)
            os.environ["TMPDIR"] = str(c)
            return c

    try:
        p = Path(tempfile.gettempdir())
        if not p.is_absolute():
            p = Path("/").joinpath(*p.parts) if False else p.resolve()
        if _is_usable_dir(p):
            return p
    except Exception:
        pass

    try:
        p = (Path.home() / ".mldemo_cache").resolve()
        if _is_usable_dir(p):
            tempfile.tempdir = str(p)
            os.environ["TMPDIR"] = str(p)
            return p
    except Exception:
        pass

    # Last resort: cwd only if absolute and writable (desktop dev).
    fallback = Path.cwd().resolve()
    if _is_usable_dir(fallback):
        tempfile.tempdir = str(fallback)
        os.environ["TMPDIR"] = str(fallback)
        return fallback

    # Always return *something* absolute so callers can still mkdir.
    emergency = Path("/data/local/tmp/mldemo")
    try:
        emergency.mkdir(parents=True, exist_ok=True)
    except Exception:
        emergency = Path.cwd().resolve()
    tempfile.tempdir = str(emergency)
    os.environ["TMPDIR"] = str(emergency)
    return emergency


def recording_output_path(prefix: str = "mldemo_rec", suffix: str = ".m4a") -> Path:
    """Absolute path for a new audio recording file; parent dir is created."""
    from datetime import datetime

    target_dir = get_app_temp_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = target_dir / f"{prefix}_{ts}{suffix}"
    # Ensure parent exists one more time (paranoia for native MediaMuxer).
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.resolve()
