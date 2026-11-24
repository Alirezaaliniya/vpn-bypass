"""Runs against the REAL registry. Only on Windows and only when
ARC_INTEGRATION=1 (CI sets it) - it creates and removes the actual key."""

import os
import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or os.environ.get("ARC_INTEGRATION") != "1",
    reason="real-registry test (Windows + ARC_INTEGRATION=1 only)",
)


def _create_key():
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\NetControlPort") as k:
        winreg.SetValueEx(k, "Version", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "State", 0, winreg.REG_BINARY, bytes(range(32)))


def test_real_clean_and_restore(tmp_path):
    from account_cleaner.backends import WinRegistryBackend
    from account_cleaner.core import clean, restore
    from account_cleaner.processes import ClientProcess

    b = WinRegistryBackend()
    _create_key()
    assert b.key_exists()
    assert clean(b, backup_dir=tmp_path, client=ClientProcess()) == 0
    assert not b.key_exists()
    assert len(list(tmp_path.glob("*.reg"))) == 1
    assert restore(b, backup_dir=tmp_path, client=ClientProcess()) == 0
    assert b.read_values()["State"] == bytes(range(32))
    clean(b, backup=False, client=ClientProcess())
    assert not b.key_exists()
