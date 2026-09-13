#!/usr/bin/env python3
"""Hash the final, merged download assets; excludes previous checksum files."""
import hashlib
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
version = (Path(__file__).resolve().parents[1] / 'VERSION').read_text().strip()
expected = {f'YueKey-{version}-source.tar.gz'}
expected.update(f'YueKey-{version}-windows-{arch}{suffix}'
                for arch in ('x64', 'x86', 'arm64') for suffix in ('.zip', '-setup.exe'))
expected.update(f'yuekey_{version}-1_{arch}.deb' for arch in ('amd64', 'arm64'))
assets = sorted(p for p in root.iterdir() if p.is_file() and p.suffix in ('.deb', '.zip', '.gz', '.exe'))
if {p.name for p in assets} != expected:
    raise SystemExit('Release needs exactly two architecture DEBs, three Windows EXE/ZIP pairs and source archive')
lines = []
for path in assets:
    with path.open('rb') as stream:
        lines.append(f'{hashlib.file_digest(stream, "sha256").hexdigest()}  {path.name}\n')
(root / 'SHA256SUMS').write_text(''.join(lines), encoding='utf-8')
