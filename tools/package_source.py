#!/usr/bin/env python3
"""Ship corresponding source and all pinned dictionary inputs with each release."""
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def build():
    version = (ROOT / 'VERSION').read_text().strip()
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    if 'LICENSE' not in files:
        raise SystemExit('Source releases must be built from a committed checkout.')
    inputs = [p for p in (ROOT / 'build/sources').rglob('*') if p.is_file()]
    if not inputs:
        raise SystemExit('Fetch verified dictionary inputs first.')
    (ROOT / 'dist').mkdir(exist_ok=True)
    with tarfile.open(ROOT / 'dist' / f'YueKey-{version}-source.tar.gz', 'w:gz') as archive:
        for path in sorted([ROOT / name for name in files if name] + inputs):
            archive.add(path, arcname=f'YueKey-{version}/{path.relative_to(ROOT)}', recursive=False)


if __name__ == '__main__':
    build()
