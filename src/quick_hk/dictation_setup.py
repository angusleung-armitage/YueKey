"""Explicit, checksum-verified setup for the optional local speech runtime."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

from .deployment import data_home, _atomic_write, _state_lock

from .speech_assets import ASSETS, PUNCT_HASH, digest, download, model_hashes, prepare_models

BUNDLED_RUNTIME = Path('/usr/lib/yuekey/speech')
BUNDLED_MODELS = Path('/usr/share/yuekey/models')


def bundled() -> bool:
    return (BUNDLED_RUNTIME / 'yuekey-speech').is_file()


def runtime_directory() -> Path:
    return data_home() / "quick-hk/dictation"


def status(*, verify: bool = False) -> dict:
    if bundled():
        checks = {name: (BUNDLED_MODELS / name).is_file() and (
            not verify or digest(BUNDLED_MODELS / name) == expected)
            for name, expected in model_hashes().items()}
        return {'ready': all(checks.values()), 'model': 'SenseVoice Small Yue INT8 (2025-09-09)',
                'provider': 'cpu', 'directory': str(BUNDLED_MODELS), 'models': checks,
                'bundled': True}
    root = runtime_directory()
    checks = {}
    for name, expected in model_hashes().items():
        path = root / 'models' / name
        checks[name] = path.is_file() and (not verify or digest(path) == expected)
    requirements = Path(__file__).with_name('dictation-requirements.txt')
    try:
        marker = json.loads((root / 'ready.json').read_text())
    except (OSError, ValueError):
        marker = {}
    ready = (all(checks.values()) and (root / 'venv/bin/python').is_file()
             and marker.get('requirements_sha256') == digest(requirements)
             and marker.get('models') == model_hashes())
    return {'ready': ready, 'model': 'SenseVoice Small Yue INT8 (2025-09-09)',
            'provider': 'cpu', 'directory': str(root), 'models': checks}


def setup() -> list[str]:
    if os.geteuid() == 0:
        raise RuntimeError('Run dictation setup as your desktop user, without sudo.')
    if bundled():
        if not status(verify=True)['ready']:
            raise RuntimeError('Bundled speech models are missing or damaged. Reinstall the YueKey DEB.')
        subprocess.run([*worker_command(), '--check'], check=True,
                       env=worker_environment(), timeout=120)
        return ['Bundled CPU speech is ready; no download is needed.',
                'Enable 語音輸入 in quick-hk configure, then reload Rime.']
    root = runtime_directory()
    uv = shutil.which('uv') or str(Path.home() / '.local/bin/uv')
    if not Path(uv).is_file():
        raise RuntimeError('Dictation setup needs uv to create its isolated Python 3.12 runtime.')
    requirements = Path(__file__).with_name('dictation-requirements.txt')
    with _state_lock():
        models = root / 'models'
        prepare_models(models, lambda message: print(message, flush=True))
        if not (root / 'venv/bin/python').is_file():
            subprocess.run([uv, 'venv', '--python', '3.12', str(root / 'venv')], check=True)
        subprocess.run([uv, 'pip', 'sync', '--python', str(root / 'venv/bin/python'),
                        '--require-hashes', str(requirements)], check=True)
        # Actual CPU model initialization and a silence check before readiness.
        code = ('from pathlib import Path; import runpy,sys; '
                'Recognizer=runpy.run_path(sys.argv[2])["Recognizer"]; r=Recognizer(Path(sys.argv[1])); '
                'assert r.transcribe_pcm(bytes(32000)) == ""')
        env = worker_environment()
        subprocess.run([str(root / 'venv/bin/python'), '-I', '-c', code, str(models),
                        str(Path(__file__).with_name('dictation_worker.py'))],
                       env=env, check=True, timeout=60)
        _atomic_write(root / 'ready.json', (json.dumps({
            'requirements_sha256': digest(requirements), 'models': model_hashes(),
        }, indent=2) + '\n').encode())
    return ['SenseVoice Small Yue INT8 is ready. All recognition uses the CPU.',
            'Enable 語音輸入 in quick-hk configure, then reload Rime.']


def worker_environment() -> dict[str, str]:
    return {**os.environ, 'CUDA_VISIBLE_DEVICES': '', 'OMP_NUM_THREADS': '4',
            'PYTHONPATH': '',
            'PYTHONNOUSERSITE': '1'}


def worker_command() -> list[str]:
    if bundled():
        return [str(BUNDLED_RUNTIME / 'yuekey-speech'), '--models', str(BUNDLED_MODELS)]
    root = runtime_directory()
    return [str(root / 'venv/bin/python'), '-I', str(Path(__file__).with_name('dictation_worker.py')),
            '--models', str(root / 'models')]


def microphones() -> list[tuple[str, str]]:
    result = [('default', '系統預設 · System default')]
    try:
        nodes = json.loads(subprocess.check_output(['pw-dump'], text=True, timeout=3))
        for node in nodes:
            props = node.get('info', {}).get('props', {})
            if props.get('media.class') == 'Audio/Source' and props.get('node.name'):
                result.append((props['node.name'], props.get('node.description', props['node.name'])))
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return result
