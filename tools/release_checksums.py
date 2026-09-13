#!/usr/bin/env python3
"""Hash the final, merged download assets; excludes previous checksum files."""
import hashlib
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
version = (Path(__file__).resolve().parents[1] / 'VERSION').read_text().strip()
expected = {f'YueKey-{version}-windows-x64.zip', f'YueKey-{version}-windows-x64-setup.exe',
            f'YueKey-{version}-source.tar.gz'}
expected.update(f'quick-hk-{name}_{version}-1_{architecture}.deb' for name, architecture in (
    ('core', 'all'), ('gnome', 'all'), ('kde', 'amd64'), ('dictation', 'amd64'), ('predict', 'amd64')))
assets = sorted(p for p in root.iterdir() if p.is_file() and p.suffix in ('.deb', '.zip', '.gz', '.exe'))
if {p.name for p in assets} != expected:
    raise SystemExit('Release needs exactly the current five DEBs, Windows setup EXE, ZIP and source archive')
lines = []
for path in assets:
    with path.open('rb') as stream:
        lines.append(f'{hashlib.file_digest(stream, "sha256").hexdigest()}  {path.name}\n')
(root / 'SHA256SUMS').write_text(''.join(lines), encoding='utf-8')
