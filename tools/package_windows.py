#!/usr/bin/env python3
"""Build the portable Windows x64 ZIP on a Windows runner."""
from importlib import metadata
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / 'VERSION').read_text().strip()


def build():
    if sys.platform != 'win32' or sys.maxsize <= 2**32:
        raise SystemExit('Build this package on Windows with Python 3.12 x64.')
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
        '--name', 'YueKey', '--paths', str(ROOT / 'src'),
        '--distpath', str(ROOT / 'build/windows-dist'), '--workpath', str(ROOT / 'build/pyinstaller'),
        '--specpath', str(ROOT / 'build'),
        '--add-data', f'{ROOT / "build/windows-data"}:windows-data',
        '--collect-all', 'sherpa_onnx', '--collect-all', 'opencc',
        '--collect-all', 'comtypes', '--collect-all', 'sounddevice',
        str(ROOT / 'desktop/windows/yuekey.py'),
    ], check=True)
    bundle = ROOT / 'build/windows-dist/YueKey'
    for name in ('LICENSE', 'THIRD_PARTY.md', 'README.md'):
        shutil.copyfile(ROOT / name, bundle / name)
    shutil.copytree(ROOT / 'LICENSES', bundle / 'LICENSES', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'docs', bundle / 'docs', dirs_exist_ok=True)
    shutil.copyfile(ROOT / 'desktop/windows/requirements.txt', bundle / 'requirements.txt')
    # Retain the complete license/notice files shipped by every wheel.
    licenses = bundle / 'LICENSES/runtime'
    for distribution in metadata.distributions():
        name = distribution.metadata['Name']
        for file in distribution.files or []:
            if any(part.lower().startswith(('license', 'copying', 'notice', 'copyright')) for part in file.parts):
                original = Path(distribution.locate_file(file))
                if original.is_file():
                    destination = licenses / name / Path(*[p for p in file.parts if p not in ('.', '..')])
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(original, destination)
    for file in Path(sys.base_prefix).rglob('license*'):
        if file.is_file() and 'site-packages' not in file.parts:
            destination = licenses / 'python-tcl-tk' / file.relative_to(sys.base_prefix)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, destination)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.exists():
        licenses.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(python_license, licenses / 'PYTHON-LICENSE.txt')
    (ROOT / 'dist').mkdir(exist_ok=True)
    shutil.make_archive(str(ROOT / 'dist' / f'YueKey-{VERSION}-windows-x64'), 'zip', bundle.parent, bundle.name)


if __name__ == '__main__':
    build()
