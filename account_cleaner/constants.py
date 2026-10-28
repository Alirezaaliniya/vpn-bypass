"""Shared constants."""

KEY_SUBPATH = r"Software\Microsoft\Windows\CurrentVersion\NetControlPort"
KEY_FULL = "HKCU\\" + KEY_SUBPATH

CLIENT_EXE = "Windscribe.exe"

BACKUP_PREFIX = "netcontrolport-"
BACKUP_SUFFIX = ".reg"

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_UNSUPPORTED = 2
