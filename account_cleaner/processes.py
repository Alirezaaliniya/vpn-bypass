"""Detect and close the Windscribe client.

Closing is done in two stages: a polite close request first (so the client can
disconnect the VPN and release its firewall rules), then a forced kill only if
the process is still alive after a grace period. After either stage we *wait*
until the process is really gone, so the registry key cannot be rewritten
during the delete.
"""

from __future__ import annotations

import csv
import io
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional

from .constants import CLIENT_EXE

Runner = Callable[[List[str]], "subprocess.CompletedProcess[str]"]


def _default_runner(args: List[str]) -> "subprocess.CompletedProcess[str]":
    kwargs: Dict[str, Any] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(
        args, capture_output=True, text=True, errors="replace", **kwargs
    )


class ClientProcess:
    def __init__(
        self,
        exe: str = CLIENT_EXE,
        runner: Optional[Runner] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.exe = exe
        self._run = runner or _default_runner
        self._sleep = sleep
        self._clock = clock

    def pids(self) -> List[int]:
        """PIDs of running client processes (empty if none or tasklist fails)."""
        try:
            proc = self._run(
                ["tasklist", "/FI", f"IMAGENAME eq {self.exe}", "/FO", "CSV", "/NH"]
            )
        except OSError:
            return []
        found: List[int] = []
        for row in csv.reader(io.StringIO(proc.stdout or "")):
            if len(row) >= 2 and row[0].lower() == self.exe.lower():
                try:
                    found.append(int(row[1]))
                except ValueError:
                    pass
        return found

    def is_running(self) -> bool:
        return bool(self.pids())

    def _wait_gone(self, timeout: float) -> bool:
        deadline = self._clock() + timeout
        while self.is_running():
            if self._clock() >= deadline:
                return False
            self._sleep(0.25)
        return True

    def close(self, grace: float = 4.0, force_timeout: float = 6.0) -> bool:
        """Close the client; returns True once no process remains."""
        if not self.is_running():
            return True
        # Stage 1: polite request (WM_CLOSE) - lets the client clean up.
        try:
            self._run(["taskkill", "/IM", self.exe])
        except OSError:
            pass
        if self._wait_gone(grace):
            return True
        # Stage 2: force.
        try:
            self._run(["taskkill", "/F", "/T", "/IM", self.exe])
        except OSError:
            pass
        return self._wait_gone(force_timeout)
