"""Small shadcn/ui-style widget kit for tkinter (black & white, light + dark).

Everything is drawn on plain ``tk.Canvas`` / ``tk.Frame`` so no extra package is
needed and the PyInstaller exe stays small. Colours come from ``theme.Theme``
and every widget can be re-coloured live with ``Style.set_theme``.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Dict, List, Optional, Tuple

from .theme import Theme, mix


def _pick(available: set, candidates: Tuple[str, ...], fallback: str) -> str:
    for name in candidates:
        if name in available:
            return name
    return fallback


class Style:
    """Holds the active theme, DPI scale and fonts; re-colours tracked widgets."""

    def __init__(self, root: tk.Misc, theme: Theme) -> None:
        self.root = root
        self.theme = theme
        try:
            self.scale = max(1.0, float(root.winfo_fpixels("1i")) / 96.0)
        except tk.TclError:
            self.scale = 1.0
        families = set(tkfont.families(root))
        ui = _pick(
            families,
            ("Segoe UI Variable Text", "Segoe UI", "Inter", "SF Pro Text",
             "Helvetica Neue", "DejaVu Sans", "Arial"),
            "TkDefaultFont",
        )
        mono = _pick(
            families,
            ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo", "Courier New"),
            "TkFixedFont",
        )
        # negative size = pixels, so text scales with DPI like everything else
        self.font = tkfont.Font(root=root, family=ui, size=-self.px(13))
        self.font_small = tkfont.Font(root=root, family=ui, size=-self.px(12))
        self.font_bold = tkfont.Font(root=root, family=ui, size=-self.px(13), weight="bold")
        self.font_heading = tkfont.Font(root=root, family=ui, size=-self.px(15), weight="bold")
        self.font_title = tkfont.Font(root=root, family=ui, size=-self.px(22), weight="bold")
        self.font_mono = tkfont.Font(root=root, family=mono, size=-self.px(12))
        self.font_mono_bold = tkfont.Font(
            root=root, family=mono, size=-self.px(12), weight="bold"
        )
        self._tracked: List[Tuple[tk.Misc, Dict[str, str]]] = []
        self._custom: List[object] = []
        self._listeners: List[Callable[[], None]] = []

    # --- helpers ---------------------------------------------------------
    def px(self, n: float) -> int:
        return int(round(n * self.scale))

    def color(self, role: str) -> str:
        return getattr(self.theme, role)

    def track(self, widget: tk.Misc, **roles: str) -> None:
        """Keep ``widget.configure(option=theme.role, ...)`` in sync with the theme."""
        self._tracked.append((widget, roles))
        widget.configure(**{opt: self.color(role) for opt, role in roles.items()})

    def track_custom(self, widget: object) -> None:
        self._custom.append(widget)

    def on_theme_change(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        alive: List[Tuple[tk.Misc, Dict[str, str]]] = []
        for widget, roles in self._tracked:
            try:
                widget.configure(**{opt: self.color(r) for opt, r in roles.items()})
                alive.append((widget, roles))
            except tk.TclError:  # destroyed (e.g. closed dialog)
                pass
        self._tracked = alive
        custom: List[object] = []
        for widget in self._custom:
            try:
                widget.retheme()  # type: ignore[attr-defined]
                custom.append(widget)
            except tk.TclError:
                pass
        self._custom = custom
        for cb in self._listeners:
            cb()


def _round_rect(
    c: tk.Canvas, x1: float, y1: float, x2: float, y2: float, r: float, **kw
) -> int:
    r = max(0.0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y1 + r, x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2,
        x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r,
        x1, y1 + r, x1, y1,
    ]
    kw.setdefault("outline", "")  # Tk 9 no longer defaults to none
    return c.create_polygon(pts, smooth=True, **kw)


class _Canvas(tk.Canvas):
    """Base for the custom-drawn widgets."""

    def __init__(self, parent: tk.Misc, style: Style, w: int, h: int,
                 surface: str = "background", **kw) -> None:
        super().__init__(
            parent, width=w, height=h, highlightthickness=0, bd=0,
            bg=style.color(surface), **kw,
        )
        self.style = style
        self.surface = surface
        style.track_custom(self)

    def retheme(self) -> None:
        self.configure(bg=self.style.color(self.surface))
        self.redraw()

    def redraw(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def _size(self) -> Tuple[int, int]:
        return int(self.cget("width")), int(self.cget("height"))


class Button(_Canvas):
    """variant: ``primary`` (filled), ``secondary`` (outline) or ``ghost``."""

    def __init__(self, parent: tk.Misc, style: Style, text: str,
                 command: Callable[[], None], variant: str = "secondary",
                 surface: str = "background", small: bool = False) -> None:
        self._text = text
        self._small = small
        self._font = style.font_small if small else style.font
        self._h = style.px(30 if small else 36)
        self._pad = style.px(12 if small else 16)
        self._m = style.px(2)  # room for the focus ring
        super().__init__(parent, style, 10, 10, surface, takefocus=1, cursor="hand2")
        self.command = command
        self.variant = variant
        self._hover = self._pressed = self._focus = False
        self._enabled = True
        self._fit()
        self.bind("<Enter>", lambda e: self._set(hover=True))
        self.bind("<Leave>", lambda e: self._set(hover=False, pressed=False))
        self.bind("<ButtonPress-1>", lambda e: self._set(pressed=True))
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<FocusIn>", lambda e: self._set(focus=True))
        self.bind("<FocusOut>", lambda e: self._set(focus=False))
        self.bind("<Key-space>", lambda e: self._invoke())
        self.bind("<Key-Return>", lambda e: self._invoke())

    def _fit(self) -> None:
        w = self._font.measure(self._text) + 2 * self._pad + 2 * self._m
        self.configure(width=w, height=self._h + 2 * self._m)
        self.redraw()

    def set_text(self, text: str) -> None:
        self._text = text
        self._fit()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow",
                       takefocus=1 if enabled else 0)
        self.redraw()

    def _set(self, **state: bool) -> None:
        if "hover" in state:
            self._hover = state["hover"]
        if "pressed" in state:
            self._pressed = state["pressed"]
        if "focus" in state:
            self._focus = state["focus"]
        self.redraw()

    def _release(self, event: tk.Event) -> None:
        was = self._pressed
        self._set(pressed=False)
        w, h = self._size()
        if was and 0 <= event.x <= w and 0 <= event.y <= h:
            self._invoke()

    def _invoke(self) -> None:
        if self._enabled:
            self.command()

    def redraw(self) -> None:
        t = self.style.theme
        self.delete("all")
        w, h = self._size()
        m = self._m
        r = self.style.px(6)
        surface = self.style.color(self.surface)
        if self.variant == "primary":
            fill, border, fg = t.primary, t.primary, t.primary_foreground
            hover = mix(t.primary, surface, 0.12)
            press = mix(t.primary, surface, 0.25)
        elif self.variant == "ghost":
            fill = border = surface
            fg = t.foreground
            hover, press = t.muted, mix(t.muted, t.border, 0.6)
        else:
            fill, border, fg = surface, t.border, t.foreground
            hover, press = t.muted, mix(t.muted, t.border, 0.6)
        if self._enabled:
            if self._pressed:
                fill = press
            elif self._hover:
                fill = hover
            if self.variant == "primary" and (self._hover or self._pressed):
                border = fill
        else:
            fill, border, fg = (mix(c, surface, 0.55) for c in (fill, border, fg))
        if self._focus and self._enabled:
            _round_rect(self, 0, 0, w, h, r + m, fill=t.ring)
            _round_rect(self, 1, 1, w - 1, h - 1, r + m - 1, fill=surface)
        _round_rect(self, m, m, w - m, h - m, r, fill=border)
        _round_rect(self, m + 1, m + 1, w - m - 1, h - m - 1, r - 1, fill=fill)
        self.create_text(w / 2, h / 2, text=self._text, font=self._font, fill=fg)


class Switch(_Canvas):
    """shadcn-style toggle bound to a ``tk.BooleanVar``."""

    def __init__(self, parent: tk.Misc, style: Style, variable: tk.BooleanVar,
                 surface: str = "background") -> None:
        self._m = style.px(2)
        w, h = style.px(36), style.px(20)
        super().__init__(parent, style, w + 2 * self._m, h + 2 * self._m, surface,
                         takefocus=1, cursor="hand2")
        self.variable = variable
        self._focus = False
        self.bind("<ButtonRelease-1>", lambda e: self.toggle())
        self.bind("<Key-space>", lambda e: self.toggle())
        self.bind("<Key-Return>", lambda e: self.toggle())
        self.bind("<FocusIn>", lambda e: self._set_focus(True))
        self.bind("<FocusOut>", lambda e: self._set_focus(False))
        self._trace = variable.trace_add("write", lambda *a: self._safe_redraw())
        self.redraw()

    def _safe_redraw(self) -> None:
        try:
            self.redraw()
        except tk.TclError:
            pass

    def _set_focus(self, value: bool) -> None:
        self._focus = value
        self.redraw()

    def toggle(self) -> None:
        self.variable.set(not self.variable.get())

    def redraw(self) -> None:
        t = self.style.theme
        self.delete("all")
        w, h = self._size()
        m = self._m
        surface = self.style.color(self.surface)
        on = bool(self.variable.get())
        if self._focus:
            _round_rect(self, 0, 0, w, h, h / 2, fill=t.ring)
            _round_rect(self, 1, 1, w - 1, h - 1, h / 2, fill=surface)
        track = t.primary if on else t.input
        _round_rect(self, m, m, w - m, h - m, (h - 2 * m) / 2, fill=track)
        d = h - 2 * m - 4
        x = (w - m - 2 - d) if on else (m + 2)
        thumb = t.primary_foreground if on else t.background
        self.create_oval(x, m + 2, x + d, m + 2 + d, fill=thumb, outline=thumb)


class ToggleRow(tk.Frame):
    """Title + description on the left, a ``Switch`` on the right."""

    def __init__(self, parent: tk.Misc, style: Style, title: str, description: str,
                 variable: tk.BooleanVar, surface: str = "card") -> None:
        super().__init__(parent, bd=0, highlightthickness=0)
        style.track(self, bg=surface)
        text = tk.Frame(self, bd=0, highlightthickness=0)
        style.track(text, bg=surface)
        text.pack(side="left", fill="x", expand=True)
        self.title = tk.Label(text, text=title, font=style.font_bold, anchor="w", bd=0)
        style.track(self.title, bg=surface, fg="foreground")
        self.title.pack(anchor="w")
        self.desc = tk.Label(text, text=description, font=style.font_small, anchor="w",
                             justify="left", bd=0, wraplength=style.px(400))
        style.track(self.desc, bg=surface, fg="muted_foreground")
        self.desc.pack(anchor="w")
        self.switch = Switch(self, style, variable, surface)
        self.switch.pack(side="right", padx=(style.px(12), 0))
        for w in (self, text, self.title, self.desc):
            w.bind("<ButtonRelease-1>", lambda e: self.switch.toggle())
            w.configure(cursor="hand2")


class Badge(_Canvas):
    """Pill label. variant: ``default`` (filled), ``secondary`` or ``outline``."""

    def __init__(self, parent: tk.Misc, style: Style, text: str = "",
                 variant: str = "secondary", surface: str = "card") -> None:
        super().__init__(parent, style, 10, style.px(24), surface)
        self._text, self.variant = text, variant
        self._fit()

    def set(self, text: str, variant: Optional[str] = None) -> None:
        self._text = text
        if variant:
            self.variant = variant
        self._fit()

    def _fit(self) -> None:
        w = self.style.font_small.measure(self._text) + 2 * self.style.px(10)
        self.configure(width=max(w, self.style.px(24)))
        self.redraw()

    def redraw(self) -> None:
        t = self.style.theme
        self.delete("all")
        w, h = self._size()
        surface = self.style.color(self.surface)
        if self.variant == "default":
            fill, border, fg = t.primary, t.primary, t.primary_foreground
        elif self.variant == "outline":
            fill, border, fg = surface, t.border, t.foreground
        else:
            fill, border, fg = t.muted, t.muted, t.foreground
        _round_rect(self, 0, 0, w, h, h / 2, fill=border)
        _round_rect(self, 1, 1, w - 1, h - 1, h / 2 - 1, fill=fill)
        self.create_text(w / 2, h / 2, text=self._text, font=self.style.font_small, fill=fg)


class Progress(_Canvas):
    """Thin indeterminate bar; ``start()`` while busy, ``stop()`` when idle."""

    def __init__(self, parent: tk.Misc, style: Style, surface: str = "background") -> None:
        super().__init__(parent, style, 10, style.px(4), surface)
        self._pos = 0.0
        self._job: Optional[str] = None
        self.bind("<Configure>", lambda e: self.redraw())

    def start(self) -> None:
        if self._job is None:
            self._tick()

    def stop(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        self.redraw()

    def _tick(self) -> None:
        self._pos = (self._pos + 0.018) % 1.3
        self.redraw()
        self._job = self.after(16, self._tick)

    def redraw(self) -> None:
        t = self.style.theme
        self.delete("all")
        w, h = int(self.winfo_width()), int(self.cget("height"))
        if w <= 1:
            return
        if self._job is not None:  # idle = invisible, only the spacing remains
            _round_rect(self, 0, 0, w, h, h / 2, fill=t.muted)
            seg = w * 0.3
            x1 = self._pos * w - seg
            a, b = max(0.0, x1), min(float(w), x1 + seg)
            if b - a > 1:
                _round_rect(self, a, 0, b, h, h / 2, fill=t.primary)


class Card(tk.Frame):
    """Rounded, bordered container. Put children into ``card.body``."""

    def __init__(self, parent: tk.Misc, style: Style, surface: str = "background") -> None:
        super().__init__(parent, bd=0, highlightthickness=0)
        self.style = style
        style.track(self, bg=surface)
        self._bg = tk.Canvas(self, highlightthickness=0, bd=0)
        style.track(self._bg, bg=surface)
        self._bg.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bd=0, highlightthickness=0)
        style.track(self.body, bg="card")
        self.body.pack(fill="both", expand=True, padx=style.px(4), pady=style.px(4))
        self.bind("<Configure>", lambda e: self._draw())
        style.on_theme_change(self._draw)

    def _draw(self) -> None:
        try:
            w, h = self.winfo_width(), self.winfo_height()
            t = self.style.theme
            c = self._bg
            c.delete("all")
            r = self.style.px(10)
            _round_rect(c, 0, 0, w, h, r, fill=t.border)
            _round_rect(c, 1, 1, w - 1, h - 1, r - 1, fill=t.card)
            c.tk.call("lower", c._w)
        except tk.TclError:
            pass


class Separator(tk.Frame):
    def __init__(self, parent: tk.Misc, style: Style) -> None:
        super().__init__(parent, height=1, bd=0, highlightthickness=0)
        style.track(self, bg="border")


class Scrollbar(_Canvas):
    """Slim scrollbar that matches the theme (native ones look out of place)."""

    def __init__(self, parent: tk.Misc, style: Style, target: tk.Misc,
                 surface: str = "card") -> None:
        super().__init__(parent, style, style.px(10), 10, surface)
        self.target = target
        self._first, self._last = 0.0, 1.0
        self._grab: Optional[float] = None
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_grab", None))
        target.configure(yscrollcommand=self.set)

    def set(self, first: str, last: str) -> None:
        self._first, self._last = float(first), float(last)
        self.redraw()

    def _thumb(self) -> Tuple[float, float]:
        h = max(1, self.winfo_height())
        y1 = self._first * h
        y2 = max(self._last * h, y1 + self.style.px(24))
        return y1, min(y2, float(h))

    def _press(self, event: tk.Event) -> None:
        y1, y2 = self._thumb()
        if y1 <= event.y <= y2:
            self._grab = event.y - y1
        else:
            self.target.yview_scroll(-1 if event.y < y1 else 1, "pages")

    def _drag(self, event: tk.Event) -> None:
        if self._grab is None:
            return
        h = max(1, self.winfo_height())
        self.target.yview_moveto(max(0.0, (event.y - self._grab) / h))

    def redraw(self) -> None:
        self.delete("all")
        if self._first <= 0.0 and self._last >= 1.0:
            return  # everything fits: no thumb
        w = int(self.cget("width"))
        y1, y2 = self._thumb()
        t = self.style.theme
        _round_rect(self, w / 2 - 2, y1, w / 2 + 2, y2, 2, fill=mix(t.border, t.muted_foreground, 0.5))


# ----------------------------------------------------------------------------
def set_titlebar_dark(window: tk.Misc, dark: bool) -> None:
    """Dark title bar on Windows 10 (1809+) / 11. Silently does nothing elsewhere."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())  # type: ignore[attr-defined]
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new / old id)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(  # type: ignore[attr-defined]
                hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)
            )
    except Exception:  # cosmetic only
        pass


def confirm(
    style: Style, parent: tk.Tk, title: str, message: str,
    confirm_text: str = "Continue", cancel_text: str = "Cancel",
) -> bool:
    """Modal alert-dialog. Returns True when the user confirms."""
    result = {"ok": False}
    dlg = tk.Toplevel(parent)
    dlg.withdraw()
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.transient(parent)
    style.track(dlg, bg="background")
    set_titlebar_dark(dlg, style.theme.name == "dark")

    body = tk.Frame(dlg, bd=0, highlightthickness=0)
    style.track(body, bg="background")
    body.pack(fill="both", expand=True, padx=style.px(24), pady=style.px(22))
    heading = tk.Label(body, text=title, font=style.font_heading, anchor="w", bd=0)
    style.track(heading, bg="background", fg="foreground")
    heading.pack(anchor="w")
    text = tk.Label(body, text=message, font=style.font, anchor="w", justify="left",
                    bd=0, wraplength=style.px(380))
    style.track(text, bg="background", fg="muted_foreground")
    text.pack(anchor="w", pady=(style.px(8), style.px(20)))

    row = tk.Frame(body, bd=0, highlightthickness=0)
    style.track(row, bg="background")
    row.pack(anchor="e")

    def close(ok: bool) -> None:
        result["ok"] = ok
        dlg.destroy()

    cancel_btn = Button(row, style, cancel_text, lambda: close(False), "secondary")
    ok_btn = Button(row, style, confirm_text, lambda: close(True), "primary")
    cancel_btn.pack(side="left", padx=(0, style.px(8)))
    ok_btn.pack(side="left")
    dlg.bind("<Escape>", lambda e: close(False))
    dlg.protocol("WM_DELETE_WINDOW", lambda: close(False))

    dlg.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dlg.winfo_reqwidth()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dlg.winfo_reqheight()) // 3
    dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
    dlg.deiconify()
    ok_btn.focus_set()
    try:
        dlg.grab_set()
    except tk.TclError:  # window not viewable yet on some platforms
        pass
    parent.wait_window(dlg)
    return result["ok"]
