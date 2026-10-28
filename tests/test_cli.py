import pytest

from account_cleaner.cli import main

from conftest import FakeBackend, FakeClient


def test_default_run_cleans(tmp_path, record, capsys):
    b = FakeBackend(record)
    rc = main(["--backup-dir", str(tmp_path)], backend=b, client=FakeClient())
    assert rc == 0 and b.values is None
    assert "[OK] Record deleted." in capsys.readouterr().out


def test_dry_run(tmp_path, record):
    b = FakeBackend(record)
    assert main(["--dry-run", "--backup-dir", str(tmp_path)], backend=b, client=FakeClient()) == 0
    assert b.values == record


def test_restore_flow(tmp_path, record):
    main(["--backup-dir", str(tmp_path)], backend=FakeBackend(dict(record)), client=FakeClient())
    b = FakeBackend(None)
    assert main(["--restore", "--backup-dir", str(tmp_path)], backend=b, client=FakeClient()) == 0
    assert b.values == record


def test_list_backups(tmp_path, record, capsys):
    main(["--backup-dir", str(tmp_path)], backend=FakeBackend(dict(record)), client=FakeClient())
    assert main(["--list-backups", "--backup-dir", str(tmp_path)]) == 0
    assert "netcontrolport-" in capsys.readouterr().out


def test_restore_and_list_are_exclusive():
    with pytest.raises(SystemExit):
        main(["--restore", "--list-backups"])


def test_unsupported_platform_exit_code(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    assert main([]) == 2
