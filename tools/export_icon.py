#!/usr/bin/env python3
"""Export platform sizes from the generated master without changing its artwork.

Maintainer-only utility: requires Pillow; not used at build time or runtime.
SPDX-License-Identifier: MIT
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'docs/images/yuekey-icon.png'
    target = ROOT / 'desktop/icons'
    with Image.open(source) as original:
        icon = original.convert('RGBA')
        if icon.width != icon.height:
            raise ValueError('Expected a square master')
        target.mkdir(parents=True, exist_ok=True)
        for size in (16, 24, 32, 48, 64, 128, 256, 512):
            exported = icon.resize((size, size), Image.Resampling.LANCZOS)
            folder = target / 'hicolor' / f'{size}x{size}' / 'apps'
            folder.mkdir(parents=True, exist_ok=True)
            exported.save(folder / 'yuekey.png', optimize=True)
            if size in (64, 256):
                exported.save(target / ('yuekey-64.png' if size == 64 else 'yuekey.png'), optimize=True)
        icon.resize((256, 256), Image.Resampling.LANCZOS).save(
            target / 'yuekey.ico', sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)])


if __name__ == '__main__':
    main()
