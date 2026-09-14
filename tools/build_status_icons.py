#!/usr/bin/env python3
"""Render legible input-mode glyphs; maintainer utility, requires Pillow.

SPDX-License-Identifier: MIT
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path,
                        default=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'))
    args = parser.parse_args()
    # HK face in the Noto Sans CJK collection; only rendered glyphs are shipped.
    font = ImageFont.truetype(str(args.font), 206, index=4)
    for mode, glyph in (('hk', '港'), ('en', 'A'), ('keyboard', '中')):
        image = Image.new('RGBA', (256, 256))
        draw = ImageDraw.Draw(image)
        if mode != 'keyboard':
            draw.rounded_rectangle((0, 0, 255, 255), radius=36, fill='#173f3a')
        left, top, right, bottom = draw.textbbox((0, 0), glyph, font=font)
        draw.text(((256 - right - left) / 2, (256 - bottom - top) / 2),
                  glyph, fill='black' if mode == 'keyboard' else 'white', font=font)
        image.save(ROOT / 'desktop/icons' / f'yuekey-{mode}.ico',
                   sizes=[(size, size) for size in (16, 20, 24, 32, 40, 48, 64, 128, 256)])


if __name__ == '__main__':
    main()
