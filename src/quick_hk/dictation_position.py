"""Place a small status indicator below a caret, within its monitor work area.

Coordinates are (x, y, width, height) in the desktop's coordinate system.
SPDX-License-Identifier: MIT
"""
import math


def valid_rect(rect) -> bool:
    return (rect is not None and len(rect) == 4
            and all(isinstance(n, (int, float)) and math.isfinite(n) for n in rect)
            and rect[2] >= 0 and rect[3] > 0)


def indicator_position(rect, area, width, height, gap=6) -> tuple[int, int]:
    left, top, wide, high = area
    x, y, w, h = rect
    px, py = x + (gap if w > 4 * gap else 0) - width / 2, y + h + gap
    if py + height > top + high - gap:
        py = y - height - gap
    return (round(max(left + gap, min(px, left + wide - width - gap))),
            round(max(top + gap, min(py, top + high - height - gap))))
