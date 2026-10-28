from account_cleaner.core import clean, describe_value, restore
from account_cleaner.constants import EXIT_FAIL, EXIT_OK

from conftest import FakeBackend, FakeClient


def test_clean_when_missing_is_ok(tmp_path, logs):
    b = FakeBackend(None)
    assert clean(b, backup_dir=tmp_path, client=FakeClient(), log=logs) == EXIT_OK
    assert logs.has("ok", "already clean")
    assert list(tmp_path.iterdir()) == []


def test_clean_backs_up_then_deletes(tmp_path, record, logs):
    b = FakeBackend(record)
    assert clean(b, backup_dir=tmp_path, client=FakeClient(), log=logs) == EXIT_OK
    assert b.values is None
    assert len(list(tmp_path.glob("netcontrolport-*.reg"))) == 1


def test_backup_failure_deletes_nothing(tmp_path, record, logs):
    b = FakeBackend(record)
    b.fail_export = True
    assert clean(b, backup_dir=tmp_path, client=FakeClient(), log=logs) == EXIT_FAIL
    assert b.values == record
    assert logs.has("error", "Backup failed")


def test_no_backup_flag(tmp_path, record, logs):
    b = FakeBackend(record)
    assert clean(b, backup=False, backup_dir=tmp_path, client=FakeClient(), log=logs) == EXIT_OK
    assert b.values is None
    assert list(tmp_path.iterdir()) == []
    assert logs.has("warn", "No backup")


def test_delete_failure_reports_error(tmp_path, record, logs):
    b = FakeBackend(record)
    b.fail_delete = True
    assert clean(b, backup_dir=tmp_path, client=FakeClient(), log=logs) == EXIT_FAIL
    assert logs.has("error", "Delete failed")


def test_key_surviving_delete_is_failure(tmp_path, record, logs):
    b = FakeBackend(record)
    b.delete_is_noop = True
    assert clean(b, backup_dir=tmp_path, client=FakeClient(), log=logs) == EXIT_FAIL
    assert logs.has("error", "still exists")


def test_dry_run_changes_nothing(tmp_path, record, logs):
    b = FakeBackend(record)
    assert clean(b, dry_run=True, backup_dir=tmp_path, client=FakeClient(), log=logs) == EXIT_OK
    assert b.values == record
    assert list(tmp_path.iterdir()) == []


def test_kill_client_closes_before_delete(tmp_path, record, logs):
    b, c = FakeBackend(record), FakeClient(running=True)
    assert clean(b, kill_client=True, backup_dir=tmp_path, client=c, log=logs) == EXIT_OK
    assert c.close_calls == 1 and b.values is None


def test_kill_client_failure_aborts_without_touching_key(tmp_path, record, logs):
    b, c = FakeBackend(record), FakeClient(running=True, can_close=False)
    assert clean(b, kill_client=True, backup_dir=tmp_path, client=c, log=logs) == EXIT_FAIL
    assert b.values == record


def test_running_client_without_flag_warns(tmp_path, record, logs):
    b, c = FakeBackend(record), FakeClient(running=True)
    assert clean(b, backup_dir=tmp_path, client=c, log=logs) == EXIT_OK
    assert c.close_calls == 0
    assert logs.has("warn", "is running")


def test_two_runs_same_second_keep_both_backups(tmp_path, record):
    for _ in range(2):
        clean(FakeBackend(dict(record)), backup_dir=tmp_path, client=FakeClient())
    assert len(list(tmp_path.glob("*.reg"))) == 2


def test_restore_latest_roundtrip(tmp_path, record, logs):
    clean(FakeBackend(dict(record)), backup_dir=tmp_path, client=FakeClient())
    b = FakeBackend(None)
    assert restore(b, backup_dir=tmp_path, client=FakeClient(), log=logs) == EXIT_OK
    assert b.values == record


def test_restore_without_backups_fails(tmp_path, logs):
    b = FakeBackend(None)
    assert restore(b, backup_dir=tmp_path, client=FakeClient(), log=logs) == EXIT_FAIL
    assert logs.has("error", "No backups")


def test_restore_missing_file_fails(tmp_path, logs):
    b = FakeBackend(None)
    r = restore(b, file=tmp_path / "nope.reg", client=FakeClient(), log=logs)
    assert r == EXIT_FAIL


def test_restore_import_error(tmp_path, record, logs):
    clean(FakeBackend(dict(record)), backup_dir=tmp_path, client=FakeClient())
    b = FakeBackend(None)
    b.fail_import = True
    assert restore(b, backup_dir=tmp_path, client=FakeClient(), log=logs) == EXIT_FAIL


def test_describe_value():
    assert describe_value(1) == "0x1"
    out = describe_value(bytes(range(40)))
    assert out.endswith("(40 bytes, encrypted)") and "..." in out
