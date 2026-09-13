#!/usr/bin/env python3
"""Hash the final, merged download assets; excludes previous checksum files."""
import hashlib
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
assets = sorted(p for p in root.iterdir() if p.is_file() and p.suffix in ('.deb', '.zip', '.gz'))
if not assets:
    raise SystemExit('No release assets found')
(root / 'SHA256SUMS').write_text(''.join(
    f'{hashlib.file_digest(path.open("rb"), "sha256").hexdigest()}  {path.name}\n' for path in assets))
