"""Shared visual language: colours, fonts and DPI-aware spacing."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
BG = "#F3F0E8"
BG_SOFT = "#F9F7F1"
CARD = "#FFFDF8"
CARD_TINT = "#FBF8F1"
SIDEBAR = "#19261F"
SIDEBAR_2 = "#213127"
SIDEBAR_ACTIVE = "#2B4233"
SIDEBAR_TEXT = "#F4F1E8"
SIDEBAR_MUTED = "#95A398"
SIDEBAR_LINE = "#304236"

INK = "#1F2A23"
TEXT = "#26322A"
SUBTEXT = "#657066"
MUTED = "#899188"
FAINT = "#B4BAB2"
BORDER = "#E7E0D3"
BORDER_STRONG = "#D8CFBE"
TRACK = "#ECE6DA"

GREEN = "#2F7A57"
GREEN_DARK = "#235C42"
GREEN_SOFT = "#E5F0E8"
GREEN_PALE = "#F1F7F3"

ORANGE = "#D57845"
ORANGE_DARK = "#B45F34"
ORANGE_SOFT = "#F8EADF"

AMBER = "#D89A3F"
AMBER_SOFT = "#FBF0DD"
BLUE = "#527191"
BLUE_SOFT = "#E9EFF5"
RED = "#B85448"
RED_SOFT = "#F7E8E4"

WHITE = "#FFFFFF"
BLACK = "#000000"

# ---------------------------------------------------------------------------
# Font family and DPI helpers
# ---------------------------------------------------------------------------
_scale = 1.0
_font_family = "Microsoft YaHei UI"


def configure_theme(root: tk.Misc) -> None:
    """Pick a Chinese font and derive spacing from the window's real DPI."""
    global _scale, _font_family

    dpi = float(root.winfo_fpixels("1i"))
    _scale = max(0.85, min(3.0, dpi / 96.0))

    available = set(tkfont.families(root))
    for candidate in (
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "Segoe UI",
    ):
        if candidate in available:
            _font_family = candidate
            break

    root.option_add("*tearOff", False)
    root.option_add("*Font", (get_font_family(), 10))


def S(value: float) -> int:
    """Scale a design pixel value for the current display DPI."""
    return int(round(value * _scale))


def get_font_family() -> str:
    return _font_family


def font(size: int = 10, weight: str = "normal") -> tuple[str, int, str]:
    return (_font_family, int(size), weight)


def blend(color_a: str, color_b: str, amount: float) -> str:
    """Mix two #RRGGBB colours. ``amount`` 0 returns A, 1 returns B."""
    amount = max(0.0, min(1.0, float(amount)))
    a = color_a.lstrip("#")
    b = color_b.lstrip("#")
    if len(a) != 6 or len(b) != 6:
        return color_a
    channels = []
    for index in range(0, 6, 2):
        left = int(a[index : index + 2], 16)
        right = int(b[index : index + 2], 16)
        channels.append(round(left + (right - left) * amount))
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def tint(color: str, amount: float = 0.86) -> str:
    return blend(color, WHITE, amount)


def shade(color: str, amount: float = 0.12) -> str:
    return blend(color, BLACK, amount)


def draw_round_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    *,
    fill: str,
    outline: str = "",
    width: float = 0,
    tags: str | tuple[str, ...] = (),
):
    """Draw a smooth rounded rectangle and return the canvas item id."""
    radius = max(0, min(float(radius), (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2 - radius * 0.45,
        y1,
        x2,
        y1 + radius * 0.45,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2 - radius * 0.45,
        x2 - radius * 0.45,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1 + radius * 0.45,
        y2,
        x1,
        y2 - radius * 0.45,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1 + radius * 0.45,
        x1 + radius * 0.45,
        y1,
    ]
    return canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=24,
        fill=fill,
        outline=outline,
        width=width,
        tags=tags,
    )
