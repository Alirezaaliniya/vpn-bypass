"""Design tokens for the window: shadcn/ui "zinc" palette, black & white only.

No tkinter in here, so it can be imported and tested anywhere.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Theme:
    name: str
    background: str
    foreground: str
    card: str
    muted: str  # subtle fills (hover, track)
    muted_foreground: str
    border: str
    input: str  # unchecked switch track / input border
    primary: str
    primary_foreground: str
    ring: str


# Values are the shadcn/ui zinc tokens (hex equivalents of its HSL variables).
LIGHT = Theme(
    name="light",
    background="#ffffff",
    foreground="#09090b",
    card="#ffffff",
    muted="#f4f4f5",
    muted_foreground="#71717a",
    border="#e4e4e7",
    input="#e4e4e7",
    primary="#18181b",
    primary_foreground="#fafafa",
    ring="#a1a1aa",
)

DARK = Theme(
    name="dark",
    background="#09090b",
    foreground="#fafafa",
    card="#09090b",
    muted="#27272a",
    muted_foreground="#a1a1aa",
    border="#27272a",
    input="#3f3f46",
    primary="#fafafa",
    primary_foreground="#18181b",
    ring="#d4d4d8",
)


def mix(c1: str, c2: str, t: float) -> str:
    """Blend ``c1`` towards ``c2`` by ``t`` (0 -> c1, 1 -> c2); ``#rrggbb`` in/out."""
    t = max(0.0, min(1.0, t))
    a = _rgb(c1)
    b = _rgb(c2)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _rgb(color: str) -> Tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def system_prefers_dark() -> bool:
    """True if Windows is set to dark app mode. Anything unknown -> light."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _type = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except OSError:
        return False


# Log levels -> (glyph, label). Colour is not used for meaning (black & white
# theme): the glyph and the text weight carry it.
LEVEL_GLYPH = {
    "info": "·",  # ·
    "ok": "✓",  # ✓
    "warn": "!",
    "error": "✕",  # ✕
}


def format_log_line(level: str, message: str) -> str:
    """One line for the activity log, with a leading glyph for the level.

    Continuation lines of a multi-line message are indented under the text.
    """
    glyph = LEVEL_GLYPH.get(level, LEVEL_GLYPH["info"])
    first, *rest = message.split("\n")
    lines = [f"{glyph}  {first}"] + [f"   {line}" for line in rest]
    return "\n".join(lines)
