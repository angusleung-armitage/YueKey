"""The Windows keyboard identifier, separate from Rime's 港/A mode icons.

Only the bundled, hash-verified machine installer changes the shared profile.
SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

INSTALLER_NAME = 'yuekey-keyboard-icon-installer.exe'
STATE_KEY = r'Software\YueKey\KeyboardIcon'
LANGUAGES = ('0404', '0804', '0c04', '1004', '1404')


def assets() -> tuple[Path, dict]:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2] / 'build'))
    directory = base / 'prerequisites'
    manifest = json.loads((directory / 'keyboard-icon.json').read_text(encoding='utf-8'))
    for field in ('installer_sha256', 'resource_sha256'):
        value = manifest.get(field, '')
        if len(value) != 64 or any(char not in '0123456789abcdef' for char in value):
            raise RuntimeError('Invalid bundled keyboard icon metadata. Reinstall YueKey.')
    return directory / INSTALLER_NAME, manifest


def profile_keys():
    from .windows_weasel import TIP_CLSID, TIP_PROFILE
    return tuple(rf'Software\Microsoft\CTF\TIP\{TIP_CLSID}\LanguageProfile\0x0000{lang}\{TIP_PROFILE}'
                 for lang in LANGUAGES)


def ready(resource_sha256: str) -> bool:
    import winreg
    from .windows_weasel import registry_value
    path = registry_value(winreg.HKEY_LOCAL_MACHINE, STATE_KEY, 'IconFile')
    if not isinstance(path, str):
        return False
    try:
        with Path(path).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != resource_sha256:
                return False
        found = False
        for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            for key in profile_keys():
                try:
                    handle = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key, 0, winreg.KEY_READ | view)
                except FileNotFoundError:
                    continue
                with handle:
                    found = True
                    value, kind = winreg.QueryValueEx(handle, 'IconFile')
                    index, index_kind = winreg.QueryValueEx(handle, 'IconIndex')
                    if (kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) or value.casefold() != path.casefold()
                            or index_kind != winreg.REG_DWORD or index != 0):
                        return False
        return found
    except (OSError, ValueError, TypeError):
        return False


def ensure(progress=lambda message: None, *, install_missing=True) -> dict:
    from .windows_weasel import _run_installer
    installer, manifest = assets()
    checksum = manifest['resource_sha256']
    if not ready(checksum):
        if not install_missing:
            raise RuntimeError('鍵盤識別圖示尚未完成設定，請重新執行粵鍵安裝程式。\n'
                               'The keyboard identifier needs setup. Run the YueKey installer again.')
        with installer.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != manifest['installer_sha256']:
                raise RuntimeError('Keyboard icon installer checksum mismatch. Reinstall YueKey.')
        progress('正在設定 Windows 鍵盤識別「中」，請允許管理員提示。\n'
                 'Setting the Windows keyboard identifier to 中. Approve the administrator prompt.')
        _run_installer(installer, parameters='/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-',
                       component='YueKey Keyboard Icon')
        if not ready(checksum):
            raise RuntimeError('Windows keyboard icon setup did not complete. Choose Set up typing to retry.')
    return dict(ready=True, glyph='中', scope='machine', resource_sha256=checksum)
