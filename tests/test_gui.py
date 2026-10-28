"""Smoke tests for the window. Skipped when there is no display / tkinter."""

import time

import pytest

tk = pytest.importorskip("tkinter")

from account_cleaner import gui  # noqa: E402
from account_cleaner.theme import DARK, LIGHT  # noqa: E402

from conftest import FakeBackend, FakeClient  # noqa: E402


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    r.withdraw()
    yield r
    r.destroy()


def _wait(root, app, timeout=5.0):
    end = time.time() + timeout
    while app.busy and time.time() < end:
        root.update()
        time.sleep(0.02)
    for _ in range(10):  # let the "done" event be handled
        root.update()
        time.sleep(0.02)
    assert not app.busy


def _app(root, record, **kw):
    backend = FakeBackend(record)
    app = gui.App(root, backend, kw.pop("client", FakeClient()), LIGHT, poll=False)
    return app, backend


def test_status_badges_follow_the_registry(root, record):
    app, _ = _app(root, record)
    for _ in range(20):
        root.update()
        time.sleep(0.02)
    assert app.exists is True
    assert app.b_clean._enabled


def test_clean_button_stays_enabled_even_without_a_record(root):
    app, _ = _app(root, None)
    for _ in range(20):
        root.update()
        time.sleep(0.02)
    assert app.exists is False
    assert app.b_clean._enabled  # never blocked by a (possibly stale) status


def test_page_scrolls_when_window_is_small(root, record):
    app, _ = _app(root, record)
    root.geometry("560x300")
    root.deiconify()
    for _ in range(20):
        root.update()
        time.sleep(0.02)
    first, last = app.canvas.yview()
    assert last < 1.0  # content taller than the window
    app.canvas.yview_scroll(1, "pages")
    root.update()
    assert app.canvas.yview()[0] > first


def test_clean_flow_deletes_record(root, record, monkeypatch, tmp_path):
    monkeypatch.setattr(gui, "confirm", lambda *a, **k: True)
    monkeypatch.setattr(gui, "default_backup_dir", lambda: tmp_path)
    monkeypatch.setattr("account_cleaner.core.default_backup_dir", lambda: tmp_path)
    app, backend = _app(root, record)
    app.on_clean()
    _wait(root, app)
    assert backend.values is None
    assert list(tmp_path.glob("netcontrolport-*.reg"))
    assert "finished (success)" in app.text.get("1.0", "end")


def test_declined_confirmation_changes_nothing(root, record, monkeypatch):
    monkeypatch.setattr(gui, "confirm", lambda *a, **k: False)
    app, backend = _app(root, record)
    app.on_clean()
    assert not app.busy and backend.values == record


def test_dry_run_changes_nothing(root, record):
    app, backend = _app(root, record)
    app.dry_var.set(True)
    app.on_clean()
    _wait(root, app)
    assert backend.values == record


def test_failure_is_reported_and_ui_recovers(root, record, monkeypatch, tmp_path):
    monkeypatch.setattr(gui, "confirm", lambda *a, **k: True)
    app, backend = _app(root, record)
    backend.fail_export = True
    app.backup_var.set(True)
    monkeypatch.setattr("account_cleaner.core.default_backup_dir", lambda: tmp_path)
    app.on_clean()
    _wait(root, app)
    assert backend.values == record  # nothing deleted without a backup
    assert "finished (failed)" in app.text.get("1.0", "end")
    assert app.b_open._enabled  # buttons are usable again


def test_theme_toggle_recolors_widgets(root, record):
    app, _ = _app(root, record)
    assert app.style.theme is LIGHT
    app.toggle_theme()
    assert app.style.theme is DARK
    assert app.text.cget("bg") == DARK.card
    assert app.theme_btn._text == "Light"
    app.toggle_theme()
    assert app.text.cget("bg") == LIGHT.card
