#!/usr/bin/env python3
"""Build the data-only Windows keyboard branding resource with GNU binutils.

No code or entry point is included. Windows loads this PE as icon data on all
three architectures. SPDX-License-Identifier: MIT
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build():
    output = ROOT / 'build/windows-data/YueKeyKeyboard.dll'
    output.parent.mkdir(parents=True, exist_ok=True)
    intermediate = ROOT / 'build/keyboard-resource'
    intermediate.mkdir(parents=True, exist_ok=True)
    rc = intermediate / 'keyboard.rc'
    rc.write_text('1 ICON "' + (ROOT / 'desktop/icons/yuekey-keyboard.ico').as_posix() + '"\n',
                  encoding='utf-8')
    obj = intermediate / 'keyboard.o'
    subprocess.run(['i686-w64-mingw32-windres', '--preprocessor=/usr/bin/cpp',
                    '-O', 'coff', str(rc), str(obj)], check=True)
    subprocess.run(['i686-w64-mingw32-ld', '--shared', '--entry=0',
                    '--no-insert-timestamp', '--subsystem', 'windows',
                    '-o', str(output), str(obj)], check=True)
    print(output)


if __name__ == '__main__':
    build()
