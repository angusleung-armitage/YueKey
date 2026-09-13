"""Add/remove YueKey in a Weasel user folder, preserving user data. SPDX-License-Identifier: MIT."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import yaml

FILES = ('quick_hk.schema.yaml', 'quick_hk.dict.yaml', 'lua/quick_hk.lua')


def data_directory() -> Path:
    return Path(os.environ['LOCALAPPDATA']) / 'YueKey'


def resources() -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2])) / 'windows-data'


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
    config = yaml.safe_load(config_path.read_text(encoding='utf-8-sig')) if config_path.exists() else {}
    config = config or {}
    if not isinstance(config, dict) or not isinstance(config.get('patch', {}), dict):
        raise ValueError('default.custom.yaml must contain a mapping with a patch mapping.')
    patch = config.setdefault('patch', {})
    # Append to an existing schema_list override, otherwise use Rime's append patch.
    key = 'schema_list' if 'schema_list' in patch else 'schema_list/+'
    schemas = patch.setdefault(key, [])
    if not isinstance(schemas, list):
        raise ValueError('The existing schema_list patch needs a list; no files were changed.')
    if not any(isinstance(item, dict) and item.get('schema') == 'quick_hk' for item in schemas):
        schemas.append({'schema': 'quick_hk'})
    payloads = {name: (source / name).read_bytes() for name in FILES}
    payloads['default.custom.yaml'] = yaml.safe_dump(config, allow_unicode=True, sort_keys=False).encode('utf-8')
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
    preserved = []
    for name, entry in record['files'].items():
        if name not in (*FILES, 'default.custom.yaml'):
            raise ValueError('Invalid installation manifest')
        path = destination / name
        if not path.exists() or _hash(path.read_bytes()) != entry['installed']:
            preserved.append(name)
        elif entry['existed']:
            _write(path, (backup / name).read_bytes())
        else:
            path.unlink()
    marker.unlink()
    return preserved
