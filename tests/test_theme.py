import re

from account_cleaner.theme import DARK, LIGHT, format_log_line, mix, system_prefers_dark

HEX = re.compile(r"^#[0-9a-f]{6}$")


def _is_grey(color):
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b) <= 12  # zinc has a tiny blue tint


def test_palettes_are_valid_black_and_white():
    for theme in (LIGHT, DARK):
        for field, value in vars(theme).items():
            if field == "name":
                continue
            assert HEX.match(value), (theme.name, field, value)
            assert _is_grey(value), (theme.name, field, value)


def test_primary_contrasts_with_background():
    assert LIGHT.primary < LIGHT.background  # dark on light
    assert DARK.primary > DARK.background  # light on dark


def test_mix_endpoints_and_middle():
    assert mix("#000000", "#ffffff", 0) == "#000000"
    assert mix("#000000", "#ffffff", 1) == "#ffffff"
    assert mix("#000000", "#ffffff", 0.5) == "#808080"
    assert mix("#000000", "#ffffff", 5) == "#ffffff"  # clamped


def test_system_prefers_dark_returns_bool():
    assert isinstance(system_prefers_dark(), bool)


def test_format_log_line_levels_and_multiline():
    assert format_log_line("ok", "done") == "✓  done"
    assert format_log_line("error", "bad").startswith("✕")
    assert format_log_line("weird", "x").startswith("·")
    assert format_log_line("info", "a\nb") == "·  a\n   b"
