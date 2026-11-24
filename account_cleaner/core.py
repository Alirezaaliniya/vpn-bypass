"""Main logic: clean and restore. No printing, no OS calls except through the
injected ``backend`` and ``client`` - everything is reported via ``log``."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from .backends import RegistryBackend, RegistryError
from .backups import default_backup_dir, list_backups, new_backup_path
from .constants import EXIT_FAIL, EXIT_OK, KEY_FULL
from .processes import ClientProcess

# level is one of: "info", "ok", "warn", "error"
Log = Callable[[str, str], None]


def _silent(level: str, message: str) -> None:
    pass


def describe_value(data: Any) -> str:
    if isinstance(data, (bytes, bytearray)):
        hexstr = bytes(data).hex().upper()
        if len(hexstr) > 64:
            hexstr = hexstr[:64] + "..."
        return f"{hexstr} ({len(data)} bytes, encrypted)"
    if isinstance(data, int):
        return f"0x{data:X}"
    return str(data)


def _ensure_client_closed(
    client: ClientProcess, kill_client: bool, log: Log
) -> bool:
    """Returns False only if we were asked to close it and could not."""
    if not client.is_running():
        if kill_client:
            log("info", "Windscribe is not running.")
        return True
    if not kill_client:
        log(
            "warn",
            "Windscribe is running - it may rewrite the record right after "
            "this. Close it first, or use --kill-client.",
        )
        return True
    log("info", "Closing Windscribe ...")
    if client.close():
        log("ok", "Windscribe closed.")
        return True
    log("error", "Could not close Windscribe. Close it manually and retry.")
    return False


def clean(
    backend: RegistryBackend,
    *,
    backup: bool = True,
    backup_dir: Optional[Path] = None,
    kill_client: bool = False,
    dry_run: bool = False,
    client: Optional[ClientProcess] = None,
    log: Log = _silent,
) -> int:
    client = client or ClientProcess()
    log("info", f"target: {KEY_FULL}")

    if not dry_run:
        if not _ensure_client_closed(client, kill_client, log):
            return EXIT_FAIL
    elif client.is_running():
        log("info", "(dry run) Windscribe is running.")

    try:
        exists = backend.key_exists()
    except RegistryError as exc:
        log("error", str(exc))
        return EXIT_FAIL
    if not exists:
        log("ok", "No record found - already clean.")
        return EXIT_OK

    log("info", "Record found. Current contents:")
    try:
        for name, data in backend.read_values().items():
            log("info", f"    {name or '(default)'} = {describe_value(data)}")
    except RegistryError as exc:
        log("warn", f"Could not read values: {exc}")

    if dry_run:
        log("info", "(dry run) Would back up and delete the key. Nothing changed.")
        return EXIT_OK

    if backup:
        try:
            directory = Path(backup_dir) if backup_dir else default_backup_dir()
            directory.mkdir(parents=True, exist_ok=True)
            target = new_backup_path(directory)
            backend.export_key(str(target))
            if not target.is_file() or target.stat().st_size == 0:
                raise RegistryError("backup file was not created")
        except (OSError, RegistryError) as exc:
            log("error", f"Backup failed, nothing was deleted: {exc}")
            log("error", "Use --no-backup to delete without a backup.")
            return EXIT_FAIL
        log("ok", f"Backup: {target}")
    else:
        log("warn", "No backup taken (--no-backup).")

    try:
        backend.delete_key()
    except RegistryError as exc:
        log("error", f"Delete failed: {exc}")
        return EXIT_FAIL
    try:
        still_there = backend.key_exists()
    except RegistryError:
        still_there = False
    if still_there:
        log("error", "Delete reported success but the key still exists.")
        return EXIT_FAIL

    log("ok", "Record deleted.")
    log(
        "info",
        "Note: this cleanup is local only. If the client sees an expired "
        "account again it recreates the key; server-side state is unchanged.",
    )
    return EXIT_OK


def restore(
    backend: RegistryBackend,
    *,
    file: Optional[Path] = None,
    backup_dir: Optional[Path] = None,
    client: Optional[ClientProcess] = None,
    log: Log = _silent,
) -> int:
    """Import a backup. *file* None means the newest backup in *backup_dir*."""
    client = client or ClientProcess()
    if file is None:
        directory = Path(backup_dir) if backup_dir else default_backup_dir()
        available = list_backups(directory)
        if not available:
            log("error", f"No backups found in {directory}")
            return EXIT_FAIL
        file = available[0]
    file = Path(file)
    if not file.is_file():
        log("error", f"Backup file not found: {file}")
        return EXIT_FAIL

    if client.is_running():
        log("warn", "Windscribe is running; it may overwrite the restored record.")
    try:
        backend.import_file(str(file))
        if not backend.key_exists():
            raise RegistryError("import finished but the key is still missing")
    except RegistryError as exc:
        log("error", f"Restore failed: {exc}")
        return EXIT_FAIL
    log("ok", f"Restored from {file}")
    return EXIT_OK

