"""Registry access.

``RegistryBackend`` is the small interface the rest of the code relies on, so
the logic can be unit-tested on any OS with an in-memory fake.
``WinRegistryBackend`` is the real implementation (``winreg`` + ``reg.exe``).

Failures of ``reg.exe`` are reported through
``RegistryError`` with the tool's own message instead of crashing the script.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict, List

from .constants import KEY_FULL, KEY_SUBPATH


class RegistryError(RuntimeError):
    """A registry operation failed."""


class RegistryBackend:
    """Interface: implemented by WinRegistryBackend and by test fakes."""

    def key_exists(self) -> bool:
        raise NotImplementedError

    def read_values(self) -> Dict[str, Any]:
        raise NotImplementedError

    def export_key(self, path: str) -> None:
        raise NotImplementedError

    def delete_key(self) -> None:
        raise NotImplementedError

    def import_file(self, path: str) -> None:
        raise NotImplementedError


def _run_reg(args: List[str]) -> str:
    kwargs: Dict[str, Any] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.run(
            ["reg.exe", *args],
            capture_output=True,
            text=True,
            errors="replace",
            **kwargs,
        )
    except OSError as exc:  # reg.exe missing / cannot be started
        raise RegistryError(f"cannot run reg.exe: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RegistryError(
            f"reg.exe {args[0]} failed (exit {proc.returncode}): {detail}"
        )
    return proc.stdout


class WinRegistryBackend(RegistryBackend):
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RegistryError("the Windows registry is only available on Windows")
        import winreg

        self._winreg = winreg

    def key_exists(self) -> bool:
        w = self._winreg
        try:
            with w.OpenKey(w.HKEY_CURRENT_USER, KEY_SUBPATH, 0, w.KEY_READ):
                return True
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise RegistryError(f"cannot open key: {exc}") from exc

    def read_values(self) -> Dict[str, Any]:
        w = self._winreg
        values: Dict[str, Any] = {}
        try:
            with w.OpenKey(w.HKEY_CURRENT_USER, KEY_SUBPATH, 0, w.KEY_READ) as key:
                index = 0
                while True:
                    try:
                        name, data, _type = w.EnumValue(key, index)
                    except OSError:  # no more values
                        break
                    values[name] = data
                    index += 1
        except OSError as exc:
            raise RegistryError(f"cannot read key: {exc}") from exc
        return values

    def export_key(self, path: str) -> None:
        _run_reg(["export", KEY_FULL, path, "/y"])

    def delete_key(self) -> None:
        _run_reg(["delete", KEY_FULL, "/f"])

    def import_file(self, path: str) -> None:
        _run_reg(["import", path])
