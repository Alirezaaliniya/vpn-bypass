"""Builds dist/AccountRecordCleaner.exe (GUI) and dist/AccountRecordCleaner-cli.exe (console).

Usage (on Windows):  python -m pip install -e ".[dev]"  &&  python packaging/build.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    ("AccountRecordCleaner", "entry_gui.py", "--windowed"),
    ("AccountRecordCleaner-cli", "entry_cli.py", "--console"),
]


def main() -> int:
    for name, entry, mode in TARGETS:
        subprocess.check_call(
            [
                sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                "--onefile", mode, "--name", name,
                "--paths", str(ROOT), str(ROOT / "packaging" / entry),
            ],
            cwd=ROOT,
        )
    print("\nBuilt: dist/AccountRecordCleaner.exe, dist/AccountRecordCleaner-cli.exe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
