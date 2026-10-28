"""Small tkinter window for double-click use (no console needed).

Look & feel: shadcn/ui "zinc" design system, black & white, light and dark.
The window only reflects state and forwards clicks - all real work is done by
``core.clean`` / ``core.restore`` on a worker thread.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from typing import Any, Callable, Optional, Tuple

from . import __version__
from .backends import RegistryBackend, RegistryError, WinRegistryBackend
from .backups import default_backup_dir
from .constants import KEY_FULL
from .core import clean, restore
from .processes import ClientProcess
from .theme import DARK, LIGHT, Theme, format_log_line, system_prefers_dark
from .ui import (
    Badge, Button, Card, Progress, Scrollbar, Separator, Style, ToggleRow,
    confirm, set_titlebar_dark,
)

APP_TITLE = "Account Record Cleaner"
POLL_MS = 4000  # how often the status badges refresh while idle


class App:
    def __init__(
        self,
        root: tk.Tk,
        backend: RegistryBackend,
        client: Optional[Any] = None,
        theme: Optional[Theme] = None,
        poll: bool = True,
    ) -> None:
        self.root = root
        self.backend = backend
        self.client = client or ClientProcess()
        self.style = Style(root, theme or (DARK if system_prefers_dark() else LIGHT))
        st = self.style
        self.events: "queue.Queue[Tuple[Any, ...]]" = queue.Queue()
        self.busy = False
        self.exists: Optional[bool] = None  # None = not checked yet
        self.kill_var = tk.BooleanVar(value=True)
        self.backup_var = tk.BooleanVar(value=True)
        self.dry_var = tk.BooleanVar(value=False)

        root.title(f"{APP_TITLE} {__version__}")
        root.geometry(f"{st.px(640)}x{st.px(740)}")
        root.minsize(st.px(520), st.px(360))
        st.track(root, bg="background")
        set_titlebar_dark(root, st.theme.name == "dark")

        self._build()
        self._bind_keys()
        self.dry_var.trace_add("write", lambda *a: self._update_primary())
        self.refresh_status()
        root.after(100, self._pump)
        if poll:
            root.after(POLL_MS, self._poll)

    # --- layout ----------------------------------------------------------
    def _frame(self, parent: tk.Misc, bg: str = "background") -> tk.Frame:
        f = tk.Frame(parent, bd=0, highlightthickness=0)
        self.style.track(f, bg=bg)
        return f

    def _label(self, parent: tk.Misc, text: str, font: Any, fg: str = "foreground",
               bg: str = "background", **kw: Any) -> tk.Label:
        lbl = tk.Label(parent, text=text, font=font, bd=0, anchor="w", **kw)
        self.style.track(lbl, bg=bg, fg=fg)
        return lbl

    def _build(self) -> None:
        st = self.style
        outer = self._frame(self.root)
        outer.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(outer, highlightthickness=0, bd=0, yscrollincrement=st.px(24))
        st.track(self.canvas, bg="background")
        self.vscroll = Scrollbar(outer, st, self.canvas, surface="background")
        self.vscroll.pack(side="right", fill="y", padx=(0, st.px(2)))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.shell = self._frame(self.canvas)
        self._win = self.canvas.create_window(0, 0, window=self.shell, anchor="nw")
        self.canvas.bind("<Configure>", self._sync_scroll)
        self.shell.bind("<Configure>", self._sync_scroll)
        page = self._frame(self.shell)
        page.pack(fill="both", expand=True, padx=st.px(24), pady=(st.px(22), st.px(18)))
        self.page = page
        gap = st.px(14)

        # header --------------------------------------------------------
        header = self._frame(page)
        header.pack(fill="x")
        titles = self._frame(header)
        titles.pack(side="left", fill="x", expand=True)
        self._label(titles, APP_TITLE, st.font_title).pack(anchor="w")
        self._label(
            titles,
            "Remove the local “expired account” record of the Windscribe client.",
            st.font_small, "muted_foreground",
        ).pack(anchor="w", pady=(st.px(2), 0))
        tools = self._frame(header)
        tools.pack(side="right", anchor="n")
        self.theme_btn = Button(tools, st, "", self.toggle_theme, "ghost", small=True)
        self.theme_btn.pack(side="right")
        Badge(tools, st, f"v{__version__}", "outline", "background").pack(
            side="right", padx=(0, st.px(4)), pady=st.px(3)
        )

        # status card ---------------------------------------------------
        status = Card(page, st)
        status.pack(fill="x", pady=(gap + st.px(4), 0))
        body = status.body
        top = self._frame(body, "card")
        top.pack(fill="x", padx=st.px(14), pady=(st.px(12), st.px(6)))
        self._label(top, "Status", st.font_bold, bg="card").pack(side="left")
        Button(top, st, "Refresh", self.refresh_status, "ghost", "card", small=True).pack(side="right")
        Separator(body, st).pack(fill="x")
        rows = self._frame(body, "card")
        rows.pack(fill="x", padx=st.px(14), pady=st.px(10))
        self.record_badge = self._status_row(rows, "Account record", "Checking…", "outline")
        self.client_badge = self._status_row(rows, "Windscribe client", "Checking…", "outline")
        key = self._label(rows, KEY_FULL, st.font_mono, "muted_foreground", "card")
        key.pack(anchor="w", pady=(st.px(6), 0))

        # options card --------------------------------------------------
        options = Card(page, st)
        options.pack(fill="x", pady=(gap, 0))
        ob = options.body
        self._label(ob, "Options", st.font_bold, bg="card").pack(
            anchor="w", padx=st.px(14), pady=(st.px(12), st.px(6))
        )
        for i, (title, desc, var) in enumerate((
            ("Close Windscribe first",
             "Stops the app so it cannot rewrite the record right after cleaning.",
             self.kill_var),
            ("Back up before deleting",
             "Saves a .reg file you can restore with one click.",
             self.backup_var),
            ("Preview only (dry run)",
             "Shows what would happen without changing anything.",
             self.dry_var),
        )):
            Separator(ob, st).pack(fill="x")
            ToggleRow(ob, st, title, desc, var).pack(
                fill="x", padx=st.px(14), pady=st.px(10)
            )

        # actions -------------------------------------------------------
        actions = self._frame(page)
        actions.pack(fill="x", pady=(gap + st.px(2), 0))
        self.b_clean = Button(actions, st, "Clear account record", self.on_clean, "primary")
        self.b_restore = Button(actions, st, "Restore latest backup", self.on_restore, "secondary")
        self.b_open = Button(actions, st, "Open backups folder", self.on_open, "ghost")
        self.buttons = [self.b_clean, self.b_restore, self.b_open]
        for b in self.buttons:
            b.pack(side="left", padx=(0, st.px(6)))

        self.progress = Progress(page, st)
        self.progress.pack(fill="x", pady=(st.px(10), 0))

        # result banner (hidden until a job finishes) --------------------
        self.slot = self._frame(page)
        self.slot.pack(fill="x")
        self.alert = Card(self.slot, st)
        ab = self.alert.body
        self.alert_title = self._label(ab, "", st.font_bold, bg="card")
        self.alert_title.pack(anchor="w", padx=st.px(14), pady=(st.px(10), 0))
        self.alert_text = self._label(
            ab, "", st.font_small, "muted_foreground", "card",
            justify="left", wraplength=st.px(540),
        )
        self.alert_text.pack(anchor="w", padx=st.px(14), pady=(st.px(2), st.px(10)))

        # activity log --------------------------------------------------
        log_head = self._frame(page)
        log_head.pack(fill="x", pady=(gap, st.px(6)))
        self._label(log_head, "Activity", st.font_bold).pack(side="left")
        Button(log_head, st, "Clear", self.clear_log, "ghost", small=True).pack(side="right")
        Button(log_head, st, "Copy", self.copy_log, "ghost", small=True).pack(side="right")

        log_card = Card(page, st)
        log_card.pack(fill="both", expand=True)
        wrap = self._frame(log_card.body, "card")
        wrap.pack(fill="both", expand=True, padx=(st.px(12), st.px(6)), pady=st.px(8))
        self.text = tk.Text(
            wrap, height=6, wrap="word", state="disabled", font=st.font_mono,
            bd=0, highlightthickness=0, relief="flat", padx=0, pady=st.px(2),
            spacing1=st.px(1), spacing3=st.px(1), cursor="arrow",
            insertwidth=0, takefocus=0,
        )
        st.track(self.text, bg="card", fg="foreground", selectbackground="muted",
                 selectforeground="foreground", inactiveselectbackground="muted")
        sb = Scrollbar(wrap, st, self.text)
        sb.pack(side="right", fill="y", padx=(st.px(4), 0))
        self.text.pack(side="left", fill="both", expand=True)
        self._style_log_tags()
        st.on_theme_change(self._style_log_tags)

        self._label(
            page,
            "Local cleanup only — server-side state is not changed.",
            st.font_small, "muted_foreground",
        ).pack(anchor="w", pady=(st.px(10), 0))

        self._update_theme_button()
        self._update_primary()
        self.append("info", "Ready. Local cleanup only - server-side state is not changed.")

    def _status_row(self, parent: tk.Misc, name: str, text: str, variant: str) -> Badge:
        st = self.style
        row = self._frame(parent, "card")
        row.pack(fill="x", pady=st.px(3))
        self._label(row, name, st.font, bg="card").pack(side="left")
        badge = Badge(row, st, text, variant, "card")
        badge.pack(side="right")
        return badge

    def _style_log_tags(self) -> None:
        t = self.style.theme
        w = self.text
        w.tag_configure("info", foreground=t.muted_foreground)
        w.tag_configure("ok", foreground=t.foreground)
        w.tag_configure("warn", foreground=t.foreground, font=self.style.font_mono_bold)
        w.tag_configure("error", foreground=t.background, background=t.foreground,
                        font=self.style.font_mono_bold)

    def _sync_scroll(self, _event: Any = None) -> None:
        """Content is at least as tall as the window (so the log can stretch)
        and scrolls when the window is smaller than the content."""
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        height = max(ch, self.shell.winfo_reqheight())
        self.canvas.itemconfigure(self._win, width=cw, height=height)
        self.canvas.configure(scrollregion=(0, 0, cw, height))

    def _wheel(self, event: Any) -> None:
        target = self.root.winfo_containing(event.x_root, event.y_root)
        if target is None or target.winfo_toplevel() is not self.root:
            return  # a dialog is on top
        if target is self.text:
            return  # the log scrolls itself
        if self.canvas.yview() == (0.0, 1.0):
            return  # everything fits
        delta = getattr(event, "delta", 0)
        if delta:
            steps = int(-delta / 120) or (-1 if delta > 0 else 1)
        else:  # X11: Button-4 / Button-5
            steps = -1 if event.num == 4 else 1
        self.canvas.yview_scroll(steps * 2, "units")

    def _bind_keys(self) -> None:
        self.root.bind_all("<MouseWheel>", self._wheel)
        self.root.bind_all("<Button-4>", self._wheel)
        self.root.bind_all("<Button-5>", self._wheel)
        self.root.bind("<Prior>", lambda e: self.canvas.yview_scroll(-1, "pages"))
        self.root.bind("<Next>", lambda e: self.canvas.yview_scroll(1, "pages"))
        self.root.bind("<F5>", lambda e: self.refresh_status())
        self.root.bind("<Control-r>", lambda e: self.refresh_status())
        self.root.bind("<Control-t>", lambda e: self.toggle_theme())

    # --- theme -----------------------------------------------------------
    def toggle_theme(self) -> None:
        new = LIGHT if self.style.theme.name == "dark" else DARK
        self.style.set_theme(new)
        set_titlebar_dark(self.root, new.name == "dark")
        self._update_theme_button()

    def _update_theme_button(self) -> None:
        self.theme_btn.set_text("Light" if self.style.theme.name == "dark" else "Dark")

    # --- log / status ----------------------------------------------------
    def append(self, level: str, message: str) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", format_log_line(level, message) + "\n", level)
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear_log(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def copy_log(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.text.get("1.0", "end").strip())
        self.show_alert("ok", "Copied", "The activity log is on your clipboard.")

    def show_alert(self, level: str, title: str, text: str) -> None:
        glyph = {"ok": "✓", "error": "✕", "warn": "!"}.get(level, "·")
        self.alert_title.configure(text=f"{glyph}  {title}")
        self.alert_text.configure(text=text)
        if not self.alert.winfo_ismapped():
            self.alert.pack(fill="x", pady=(self.style.px(10), 0))
        self._alert_gen = getattr(self, "_alert_gen", 0) + 1
        gen = self._alert_gen
        if level == "ok":  # success banners fade away; problems stay until the next run
            self.root.after(8000, lambda: self._hide_alert(gen))

    def _hide_alert(self, gen: int) -> None:
        if gen == getattr(self, "_alert_gen", 0):
            self.alert.pack_forget()

    def refresh_status(self) -> None:
        def probe() -> None:
            try:
                exists: Optional[bool] = self.backend.key_exists()
            except RegistryError:
                exists = None
            try:
                running = bool(self.client.is_running())
            except Exception:
                running = False
            self.events.put(("status", exists, running))

        threading.Thread(target=probe, daemon=True).start()

    def _apply_status(self, exists: Optional[bool], running: bool) -> None:
        self.exists = exists
        if exists is None:
            self.record_badge.set("Unavailable", "outline")
        elif exists:
            self.record_badge.set("Record found", "default")
        else:
            self.record_badge.set("Not found", "secondary")
        self.client_badge.set("Running" if running else "Closed",
                              "default" if running else "secondary")
        self._update_primary()

    def _update_primary(self) -> None:
        self.b_clean.set_text("Preview (dry run)" if self.dry_var.get() else "Clear account record")
        # never gated on the status badge: it can be stale or unreadable, and
        # clicking with nothing to delete just reports "already clean".
        self.b_clean.set_enabled(not self.busy)

    def _poll(self) -> None:
        if not self.busy:
            self.refresh_status()
        self.root.after(POLL_MS, self._poll)

    def _pump(self) -> None:
        try:
            while True:
                kind, *args = self.events.get_nowait()
                if kind == "log":
                    self.append(*args)
                elif kind == "status":
                    self._apply_status(*args)
                elif kind == "done":
                    self._finish(*args)
        except queue.Empty:
            pass
        self.root.after(100, self._pump)

    # --- actions ---------------------------------------------------------
    def log(self, level: str, message: str) -> None:  # called from the worker thread
        self.events.put(("log", level, message))

    def run(self, job: Callable[[], int], title: str, ok_text: str) -> None:
        if self.busy:
            return
        self.busy = True
        self.alert.pack_forget()
        for b in self.buttons:
            b.set_enabled(False)
        self.progress.start()

        def worker() -> None:
            try:
                code = job()
            except Exception as exc:  # never leave the UI stuck
                self.log("error", f"Unexpected error: {exc}")
                code = 1
            self.events.put(("done", code, title, ok_text))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, code: int, title: str, ok_text: str) -> None:
        self.busy = False
        self.progress.stop()
        for b in self.buttons:
            b.set_enabled(True)
        if code == 0:
            self.append("ok", f"{title}: finished (success)")
            self.show_alert("ok", f"{title} complete", ok_text)
        else:
            self.append("error", f"{title}: finished (failed)")
            self.show_alert("error", f"{title} failed", "See the activity log below for details.")
        self._update_primary()
        self.refresh_status()

    def on_clean(self) -> None:
        dry = self.dry_var.get()
        backup = self.backup_var.get()
        kill = self.kill_var.get()
        if not dry:
            message = "This deletes the local account record of the Windscribe client."
            message += (
                "\n\nA backup will be created first, so you can undo it."
                if backup else "\n\nNo backup will be created — this cannot be undone."
            )
            if not confirm(self.style, self.root, "Clear account record?", message, "Clear record"):
                return
        self.run(
            lambda: clean(self.backend, backup=backup, kill_client=kill, dry_run=dry,
                          client=self.client, log=self.log),
            "Preview" if dry else "Clean",
            "Nothing was changed." if dry
            else "You can reopen Windscribe now. Use “Restore latest backup” to undo.",
        )

    def on_restore(self) -> None:
        if not confirm(
            self.style, self.root, "Restore latest backup?",
            "The newest backup will be imported into the registry and replace the current record.",
            "Restore",
        ):
            return
        self.run(lambda: restore(self.backend, client=self.client, log=self.log),
                 "Restore", "The previous record is back in place.")

    def on_open(self) -> None:
        try:
            folder = default_backup_dir()
            if sys.platform == "win32":
                os.startfile(str(folder))  # type: ignore[attr-defined]
            else:
                self.append("info", f"Backups folder: {folder}")
        except OSError as exc:
            self.append("error", f"Cannot open the backups folder: {exc}")


def _enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # type: ignore[attr-defined]
        except Exception:
            pass


def main() -> int:
    from tkinter import messagebox

    try:
        backend = WinRegistryBackend()
    except RegistryError as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_TITLE, str(exc))
        return 2

    _enable_dpi_awareness()
    root = tk.Tk()
    App(root, backend)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
