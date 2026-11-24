from datetime import datetime

from account_cleaner.backups import list_backups, new_backup_path


def test_name_format(tmp_path):
    p = new_backup_path(tmp_path, datetime(2026, 8, 23, 17, 49, 0))
    assert p.name == "netcontrolport-20260823-174900.reg"


def test_collision_gets_suffix(tmp_path):
    now = datetime(2026, 8, 23, 17, 49, 0)
    first = new_backup_path(tmp_path, now)
    first.write_text("x")
    second = new_backup_path(tmp_path, now)
    assert second != first and second.name.endswith("-2.reg")


def test_list_newest_first_and_ignores_others(tmp_path):
    for name in ("netcontrolport-20260101-000000.reg", "netcontrolport-20260301-000000.reg", "other.reg", "notes.txt"):
        (tmp_path / name).write_text("x")
    names = [p.name for p in list_backups(tmp_path)]
    assert names == ["netcontrolport-20260301-000000.reg", "netcontrolport-20260101-000000.reg"]


def test_list_missing_dir(tmp_path):
    assert list_backups(tmp_path / "nope") == []
