"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .backends import RegistryBackend, RegistryError, WinRegistryBackend
from .backups import default_backup_dir, list_backups
from .constants import EXIT_OK, EXIT_UNSUPPORTED
from .core import clean, restore
from .processes import ClientProcess

_PREFIX = {"info": "  ", "ok": "  [OK] ", "warn": "  [!]  ", "error": "  [X]  "}


def console_log(level: str, message: str) -> None:
    stream = sys.stderr if level in ("warn", "error") else sys.stdout
    print(f"{_PREFIX.get(level, '  ')}{message}", file=stream)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="account-record-cleaner",
        description="Back up and delete the local expired-account record "
        "stored by the Windscribe Windows client (HKCU only).",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--no-backup", action="store_true", help="delete without a .reg backup")
    p.add_argument("--backup-dir", type=Path, help="where backups are written/read")
    p.add_argument(
        "--kill-client",
        action="store_true",
        help="close Windscribe first (polite close, then force)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would happen without changing anything",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--restore",
        nargs="?",
        const="latest",
        metavar="FILE",
        help="import a backup (default: the newest one) instead of cleaning",
    )
    mode.add_argument("--list-backups", action="store_true", help="list backups and exit")
    return p


def main(
    argv: Optional[List[str]] = None,
    backend: Optional[RegistryBackend] = None,
    client: Optional[ClientProcess] = None,
) -> int:
    args = build_parser().parse_args(argv)

    if args.list_backups:
        directory = args.backup_dir or default_backup_dir()
        found = list_backups(directory)
        print(f"  {directory}")
        for path in found:
            print(f"    {path.name}")
        if not found:
            print("    (no backups)")
        return EXIT_OK

    if backend is None:
        try:
            backend = WinRegistryBackend()
        except RegistryError as exc:
            console_log("error", str(exc))
            return EXIT_UNSUPPORTED

    print("Windscribe - Account Record Cleaner")
    print("===================================")

    if args.restore is not None:
        target = None if args.restore == "latest" else Path(args.restore)
        return restore(
            backend,
            file=target,
            backup_dir=args.backup_dir,
            client=client,
            log=console_log,
        )

    return clean(
        backend,
        backup=not args.no_backup,
        backup_dir=args.backup_dir,
        kill_client=args.kill_client,
        dry_run=args.dry_run,
        client=client,
        log=console_log,
    )


if __name__ == "__main__":
    sys.exit(main())
