"""Add/remove YueKey in a Weasel user folder, preserving user data. SPDX-License-Identifier: MIT."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from .rime_config import merge_schema_list

FILES = ('quick_hk.schema.yaml', 'quick_hk.dict.yaml', 'lua/quick_hk.lua')


def data_directory() -> Path:
    return Path(os.environ['LOCALAPPDATA']) / 'YueKey'


def resources() -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2] / 'build')) / 'windows-data'


def rime_directory() -> Path:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Rime\Weasel') as key:
            path, _ = winreg.QueryValueEx(key, 'RimeUserDir')
            if path:
                return Path(os.path.expandvars(path))
    except OSError:
        pass
    return Path(os.environ['APPDATA']) / 'Rime'


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.yuekey-tmp')
    temporary.write_bytes(data)
    temporary.replace(path)


def install(destination: Path, source: Path | None = None) -> Path:
    source = source or resources()
    destination = destination.resolve()
    if not destination.is_dir():
        raise ValueError('Install Weasel first, then choose its existing user folder.')
    marker = destination / 'yuekey-install.json'
    if marker.exists():
        raise ValueError('YueKey is already installed here. Remove it in this window before reinstalling.')
    config_path = destination / 'default.custom.yaml'
    # Use the same strict parser as Ubuntu: duplicate or ambiguous patches
    # must fail before changing the user's configuration.
    original = config_path.read_bytes() if config_path.exists() else None
    config = merge_schema_list(original, config_path)
    payloads = {name: (source / name).read_bytes() for name in FILES}
    payloads['default.custom.yaml'] = config
    backup = destination / 'yuekey-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True)
    record = {'format': 1, 'backup': str(backup), 'files': {}}
    for name, content in payloads.items():
        path = destination / name
        previous = path.read_bytes() if path.exists() else None
        record['files'][name] = {'installed': _hash(content), 'existed': previous is not None}
        if previous is not None:
            _write(backup / name, previous)
    # Record before writing files: an interrupted install is removable/recoverable.
    _write(marker, json.dumps(record, indent=2).encode())
    for name, content in payloads.items():
        _write(destination / name, content)
    return backup


def uninstall(destination: Path) -> list[str]:
    destination = destination.resolve()
    marker = destination / 'yuekey-install.json'
    record = json.loads(marker.read_text(encoding='utf-8'))
    backup = Path(record['backup']).resolve()
    if not backup.is_relative_to(destination / 'yuekey-backups'):
        raise ValueError('Invalid backup location')
    if record.get('format') != 1 or not isinstance(record.get('files'), dict):
        raise ValueError('Invalid installation manifest')
    preserved, changes = [], []
    for name, entry in record['files'].items():
        if (name not in (*FILES, 'default.custom.yaml') or not isinstance(entry, dict)
                or not isinstance(entry.get('installed'), str)
                or not isinstance(entry.get('existed'), bool)):
            raise ValueError('Invalid installation manifest')
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
