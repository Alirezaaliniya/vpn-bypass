"""Backup file naming, location and listing."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .constants import BACKUP_PREFIX, BACKUP_SUFFIX


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    return os.access(path, os.W_OK)


def default_backup_dir() -> Path:
    """``backups`` next to the exe/script, or a per-user fallback if that
    location is read-only (zip preview, Program Files, ...)."""
    primary = _app_dir() / "backups"
    if _writable_dir(primary):
        return primary
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    fallback = Path(base) / "AccountRecordCleaner" / "backups"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def new_backup_path(directory: Path, now: Optional[datetime] = None) -> Path:
    """Unique ``netcontrolport-YYYYMMDD-HHMMSS[-N].reg`` inside *directory*.

    Never reuses an existing name, so two runs in the same second cannot
    overwrite each other's backup.
    """
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    candidate = directory / f"{BACKUP_PREFIX}{stamp}{BACKUP_SUFFIX}"
    n = 1
    while candidate.exists():
        n += 1
        candidate = directory / f"{BACKUP_PREFIX}{stamp}-{n}{BACKUP_SUFFIX}"
    return candidate


def list_backups(directory: Path) -> List[Path]:
    """Backups in *directory*, newest first (by file name = by timestamp)."""
    if not directory.is_dir():
        return []
    files = [
        p
        for p in directory.iterdir()
        if p.is_file()
        and p.name.startswith(BACKUP_PREFIX)
        and p.name.endswith(BACKUP_SUFFIX)
    ]
    return sorted(files, key=lambda p: p.name, reverse=True)
