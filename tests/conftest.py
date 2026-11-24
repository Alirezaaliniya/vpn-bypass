import json
from pathlib import Path

import pytest

from account_cleaner.backends import RegistryBackend, RegistryError


class FakeBackend(RegistryBackend):
    """In-memory registry key. Backups are JSON files."""

    def __init__(self, values=None):
        self.values = values  # None = key missing
        self.fail_export = False
        self.fail_delete = False
        self.delete_is_noop = False
        self.fail_import = False

    def key_exists(self):
        return self.values is not None

    def read_values(self):
        if self.values is None:
            raise RegistryError("missing")
        return dict(self.values)

    def export_key(self, path):
        if self.fail_export:
            raise RegistryError("export failed")
        data = {k: (v.hex() if isinstance(v, bytes) else v) for k, v in self.values.items()}
        Path(path).write_text(json.dumps(data))

    def delete_key(self):
        if self.fail_delete:
            raise RegistryError("access denied")
        if not self.delete_is_noop:
            self.values = None

    def import_file(self, path):
        if self.fail_import:
            raise RegistryError("import failed")
        raw = json.loads(Path(path).read_text())
        self.values = {k: (bytes.fromhex(v) if k == "State" else v) for k, v in raw.items()}


class FakeClient:
    def __init__(self, running=False, can_close=True):
        self.running = running
        self.can_close = can_close
        self.close_calls = 0

    def is_running(self):
        return self.running

    def close(self):
        self.close_calls += 1
        if self.can_close:
            self.running = False
        return self.can_close


@pytest.fixture
def record():
    return {"Version": 1, "State": bytes(range(40))}


@pytest.fixture
def logs():
    class Collector(list):
        def __call__(self, level, message):
            self.append((level, message))

        def has(self, level, text=""):
            return any(l == level and text in m for l, m in self)

    return Collector()
