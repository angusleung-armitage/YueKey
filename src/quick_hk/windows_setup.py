"""Add/remove YueKey in a Weasel user folder, preserving user data. SPDX-License-Identifier: MIT."""
from __future__ import annotations

from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import sys

from .rime_config import configure_schema_list, schema_custom
from .settings import Settings, load_settings

FILES = ('quick_hk.schema.yaml', 'quick_hk.dict.yaml', 'lua/quick_hk.lua', 'lua/yuekey_predict.lua')
CUSTOM = 'quick_hk.windows.custom.yaml'


def data_directory() -> Path:
    return Path(os.environ['LOCALAPPDATA']) / 'YueKey'


def resources() -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2] / 'build')) / 'windows-data'


def rime_directory() -> Path:
    import winreg
    from .windows_weasel import registry_value, WEASEL_KEY
    path = registry_value(winreg.HKEY_CURRENT_USER, WEASEL_KEY, 'RimeUserDir')
    if path:
        return Path(os.path.expandvars(path))
    return Path(os.environ['APPDATA']) / 'Rime'


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.yuekey-tmp')
    temporary.write_bytes(data)
    temporary.replace(path)


def _allowed(name: str) -> bool:
    return name in (*FILES, CUSTOM, 'default.custom.yaml') or bool(
        re.fullmatch(r'yuekey-predict/[0-9a-f]{1,4}\.tsv', name))


def _record(destination: Path) -> dict:
    record = json.loads((destination / 'yuekey-install.json').read_text(encoding='utf-8'))
    backup = Path(record['backup']).resolve()
    if not backup.is_relative_to(destination / 'yuekey-backups'):
        raise ValueError('Invalid backup location')
    if record.get('format') != 1 or not isinstance(record.get('files'), dict):
        raise ValueError('Invalid installation manifest')
    for name, entry in record['files'].items():
        if (not _allowed(name) or not isinstance(entry, dict)
                or not isinstance(entry.get('installed'), str)
                or not isinstance(entry.get('existed'), bool)):
            raise ValueError('Invalid installation manifest')
        _safe_path(destination, name)
        _safe_path(backup, name)
    return record


def _safe_path(directory: Path, name: str) -> Path:
    path = directory / name
    if path.is_symlink() or not path.resolve().is_relative_to(directory):
        raise ValueError(f'Unsafe managed path: {path}')
    return path


def _update(destination: Path, payloads: dict[str, bytes], record: dict) -> Path:
    """Preflight everything; preserve the first install's backups across upgrades."""
    backup = Path(record['backup']).resolve()
    if not backup.is_relative_to(destination / 'yuekey-backups'):
        raise ValueError('Invalid backup location')
    previous = {}
    marker = destination / 'yuekey-install.json'
    old_marker = marker.read_bytes() if marker.exists() else None
    for name in payloads:
        path = _safe_path(destination, name)
        previous[name] = path.read_bytes() if path.exists() else None
        entry = record['files'].get(name)
        if entry:
            if previous[name] is None or _hash(previous[name]) != entry['installed']:
                raise ValueError(f'Preserving your changed file: {name}. Back it up and remove YueKey before reinstalling.')
            if entry['existed']:
                _safe_path(backup, name).read_bytes()  # Check restore data before any changes.
    backup.mkdir(parents=True, exist_ok=True)
    for name, content in payloads.items():
        entry = record['files'].get(name)
        if not entry and previous[name] is not None:
            _write(_safe_path(backup, name), previous[name])
        record['files'][name] = {'installed': _hash(content),
                                'existed': entry['existed'] if entry else previous[name] is not None}
    try:
        # An interrupted install remains removable; externally edited files are retained.
        _write(marker, json.dumps(record, indent=2).encode())
        for name, content in payloads.items():
            _write(destination / name, content)
    except Exception:
        for name, content in previous.items():
            if content is None:
                (destination / name).unlink(missing_ok=True)
            else:
                _write(destination / name, content)
        if old_marker is None:
            marker.unlink(missing_ok=True)
        else:
            _write(marker, old_marker)
        raise
    return backup


def install(destination: Path, source: Path | None = None, settings: Settings | None = None) -> Path:
    source = source or resources()
    destination = destination.resolve()
    if not destination.is_dir():
        raise ValueError('找不到輸入資料夾，請在總覽按「設定速成」。\n'
                         'The typing folder is missing. Choose Set up typing on Overview.')
    marker = destination / 'yuekey-install.json'
    config_path = destination / 'default.custom.yaml'
    # Use the same strict parser as Ubuntu: duplicate or ambiguous patches
    # must fail before changing the user's configuration.
    original = config_path.read_bytes() if config_path.exists() else None
    config = configure_schema_list(original, config_path)
    payloads = {name: (source / name).read_bytes() for name in FILES}
    shards = sorted((source / 'yuekey-predict').glob('*.tsv'))
    if not shards:
        raise ValueError('The YueKey prediction data is missing. Reinstall the application package.')
    for shard in shards:
        name = 'yuekey-predict/' + shard.name
        if not _allowed(name):
            raise ValueError('Invalid prediction shard name')
        payloads[name] = shard.read_bytes()
    payloads[CUSTOM] = schema_custom(settings or load_settings(), 'windows')
    payloads['default.custom.yaml'] = config
    backup = destination / 'yuekey-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    record = _record(destination) if marker.exists() else {'format': 1, 'backup': str(backup), 'files': {}}
    return _update(destination, payloads, record)


def apply_settings(destination: Path, settings: Settings) -> None:
    destination = destination.resolve()
    _update(destination, {CUSTOM: schema_custom(settings, 'windows')}, _record(destination))


@contextmanager
def learning_lock(database: Path):
    """Use the same exclusive byte-range lock as LevelDB."""
    import ctypes
    from ctypes import wintypes as W
    class Overlapped(ctypes.Structure):
        _fields_ = [('Internal', ctypes.c_size_t), ('InternalHigh', ctypes.c_size_t),
                    ('Offset', W.DWORD), ('OffsetHigh', W.DWORD), ('hEvent', W.HANDLE)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, ctypes.c_void_p, W.DWORD, W.DWORD, W.HANDLE]
    kernel.CreateFileW.restype = W.HANDLE
    kernel.LockFileEx.argtypes = [W.HANDLE, W.DWORD, W.DWORD, W.DWORD, W.DWORD, ctypes.POINTER(Overlapped)]
    kernel.UnlockFileEx.argtypes = [W.HANDLE, W.DWORD, W.DWORD, W.DWORD, ctypes.POINTER(Overlapped)]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    path = _safe_path(database.resolve(), 'LOCK')
    handle = kernel.CreateFileW(str(path), 0xC0000000, 7, None, 4, 0x80, None)
    if handle == W.HANDLE(-1).value:
        raise OSError('Cannot open learning database. Exit Weasel before resetting learning.')
    overlapped = Overlapped()
    locked = False
    try:
        locked = bool(kernel.LockFileEx(handle, 3, 0, 0xFFFFFFFF, 0xFFFFFFFF, ctypes.byref(overlapped)))
        if not locked:
            raise OSError('Learning is in use. Exit Weasel from its tray menu before resetting.')
        yield
    finally:
        if locked:
            kernel.UnlockFileEx(handle, 0, 0xFFFFFFFF, 0xFFFFFFFF, ctypes.byref(overlapped))
        kernel.CloseHandle(handle)


def reset_learning(destination: Path) -> Path | None:
    destination = destination.resolve()
    database = _safe_path(destination, 'quick_hk.userdb')
    if not database.exists():
        return None
    if not database.is_dir():
        raise ValueError('The learning database is not a directory.')
    backup = destination / 'yuekey-backups' / ('learning-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    with learning_lock(database):
        if not backup.resolve().is_relative_to(destination):
            raise ValueError('Invalid backup location')
        files = [path for path in database.iterdir() if path.name != 'LOCK']
        if any(path.is_symlink() or not path.is_file() for path in files):
            raise ValueError('Unexpected learning database files; leaving the database unchanged.')
        backup.mkdir(parents=True)
        # Windows cannot rename a directory containing an open LOCK handle.
        # Keep that lock held while moving the other files; LevelDB cannot open
        # a partly reset database. The empty directory/LOCK is reusable.
        moved = []
        try:
            for path in files:
                path.rename(backup / path.name)
                moved.append(path)
        except Exception:
            for path in reversed(moved):
                (backup / path.name).rename(path)
            raise
    return backup


def uninstall(destination: Path) -> list[str]:
    destination = destination.resolve()
    marker = destination / 'yuekey-install.json'
    record = _record(destination)
    backup = Path(record['backup']).resolve()
    preserved, changes = [], []
    for name, entry in record['files'].items():
        path = destination / name
        if not path.exists() or _hash(path.read_bytes()) != entry['installed']:
            preserved.append(name)
        else:
            previous = (backup / name).read_bytes() if entry['existed'] else None
            changes.append((path, previous))
    for path, previous in changes:
        if previous is None:
            path.unlink()
        else:
            _write(path, previous)
    marker.unlink()
    return preserved
