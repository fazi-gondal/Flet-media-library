"""Path and directory utilities for cross-platform Flet mobile apps."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any


def _is_usable_dir(p: Path) -> bool:
    """Return True if *p* is absolute, writable, and not under a read-only assets tree.

    Never call ``Path.resolve()`` on Android Flet storage paths — the process CWD
    is often under ``.../flet/app/assets/``, and resolve/abspath can produce
    doubled paths that MediaMuxer cannot open (ENOENT).
    """
    try:
        if not p.is_absolute():
            return False
        parts_lower = [x.lower() for x in p.parts]
        # Reject Flet asset bundles (read-only / wrong place for MediaMuxer output).
        if "assets" in parts_lower and "flet" in parts_lower:
            return False
        # Reject obvious doubled package paths under files/.../assets/...
        joined = str(p)
        if "/files/flet/app/assets/" in joined and (
            "/data/user/" in joined[joined.find("/files/flet/") :]
            or "/data/data/" in joined[joined.find("/files/flet/") :]
        ):
            return False
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _candidate_from_env(name: str) -> Path | None:
    """Read env path; accept only absolute strings. Do not resolve()."""
    raw = os.environ.get(name)
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        return None
    return p


def get_app_temp_dir() -> Path:
    """Return a guaranteed-writable absolute scratch directory.

    Prefer Flet-injected absolute ``FLET_APP_STORAGE_*`` values **verbatim**
    (no ``Path.resolve()``). Relative values are ignored because on Android the
    CWD is often the assets tree and relative resolution creates nested
    ``.../assets/data/data/<pkg>/cache/...`` paths that crash MediaMuxer.
    """
    env_candidates: list[Path | None] = [
        _candidate_from_env("FLET_APP_STORAGE_TEMP"),
        _candidate_from_env("FLET_APP_STORAGE_CACHE"),
    ]
    data = _candidate_from_env("FLET_APP_STORAGE_DATA")
    if data is not None:
        env_candidates.append(data / "mldemo_tmp")
    env_candidates.extend(
        [
            _candidate_from_env("TMPDIR"),
            _candidate_from_env("TEMP"),
            _candidate_from_env("TMP"),
        ]
    )

    for c in env_candidates:
        if c is None:
            continue
        if _is_usable_dir(c):
            tempfile.tempdir = str(c)
            os.environ["TMPDIR"] = str(c)
            return c

    # Absolute Android package cache fallbacks (demo applicationId).
    for c in (
        Path("/data/user/0/com.gondal.media_library_demo/cache/mldemo"),
        Path("/data/data/com.gondal.media_library_demo/cache/mldemo"),
    ):
        if _is_usable_dir(c):
            tempfile.tempdir = str(c)
            os.environ["TMPDIR"] = str(c)
            return c

    try:
        p = Path(tempfile.gettempdir())
        if p.is_absolute() and _is_usable_dir(p):
            return p
    except Exception:
        pass

    try:
        p = Path.home() / ".mldemo_cache"
        if _is_usable_dir(p if p.is_absolute() else Path("/tmp/mldemo_cache")):
            home = Path.home() / ".mldemo_cache"
            if _is_usable_dir(home):
                tempfile.tempdir = str(home)
                os.environ["TMPDIR"] = str(home)
                return home
    except Exception:
        pass

    # Last resort: absolute CWD only if not under assets.
    try:
        cwd = Path.cwd()
        if cwd.is_absolute() and _is_usable_dir(cwd):
            tempfile.tempdir = str(cwd)
            os.environ["TMPDIR"] = str(cwd)
            return cwd
    except Exception:
        pass

    emergency = Path("/data/local/tmp/mldemo")
    try:
        emergency.mkdir(parents=True, exist_ok=True)
    except Exception:
        emergency = Path("/tmp/mldemo")
        try:
            emergency.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
    tempfile.tempdir = str(emergency)
    os.environ["TMPDIR"] = str(emergency)
    return emergency


def _page_storage_paths(page: Any) -> Any | None:
    try:
        import flet as ft

        storage_paths = next(
            (s for s in getattr(page, "services", []) if isinstance(s, ft.StoragePaths)),
            None,
        )
        if storage_paths is None:
            storage_paths = ft.StoragePaths()
            page.services.append(storage_paths)
        return storage_paths
    except Exception:
        return None


async def get_app_temp_dir_for_page(page: Any) -> Path:
    """Return a writable temp/cache dir, preferring Flet's native storage service."""
    storage_paths = _page_storage_paths(page)
    if storage_paths is not None:
        for getter_name in (
            "get_temporary_directory",
            "get_application_cache_directory",
        ):
            try:
                raw = await getattr(storage_paths, getter_name)()
            except Exception:
                continue
            if not raw:
                continue
            candidate = Path(raw) / "mldemo"
            if _is_usable_dir(candidate):
                tempfile.tempdir = str(candidate)
                os.environ["TMPDIR"] = str(candidate)
                return candidate

    return get_app_temp_dir()


def recording_output_path(prefix: str = "mldemo_rec", suffix: str = ".m4a") -> Path:
    """Absolute path for a new audio recording file; parent dir is created.

    Does **not** call ``Path.resolve()`` (unsafe on Android Flet).
    """
    from datetime import datetime

    target_dir = get_app_temp_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = target_dir / f"{prefix}_{ts}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_absolute():
        # Should never happen if get_app_temp_dir is correct; refuse relative.
        raise ValueError(f"recording path must be absolute, got: {path}")
    return path


async def recording_output_path_for_page(
    page: Any,
    prefix: str = "mldemo_rec",
    suffix: str = ".m4a",
) -> Path:
    """Absolute output path for AudioRecorder, using native Flet storage first."""
    from datetime import datetime

    target_dir = await get_app_temp_dir_for_page(page)
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = target_dir / f"{prefix}_{ts}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_absolute():
        raise ValueError(f"recording path must be absolute, got: {path}")
    return path
