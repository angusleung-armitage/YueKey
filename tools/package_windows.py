#!/usr/bin/env python3
"""Build native Windows x86, x64 or ARM64 setup EXE and portable ZIP."""
from importlib import metadata
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / 'VERSION').read_text().strip()
sys.path.insert(0, str(ROOT / 'src'))
from quick_hk.windows_arch import package_architecture
from quick_hk.windows_weasel import INSTALLER_NAME, INSTALLER_SHA256, fetch_installer, installer_path
from quick_hk.windows_keyboard import INSTALLER_NAME as KEYBOARD_INSTALLER_NAME


def build():
    if sys.platform != 'win32':
        raise SystemExit('Build this package on Windows with Python 3.12.')
    architecture = package_architecture()
    compiler = shutil.which('ISCC.exe') or str(
        Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Inno Setup 6/ISCC.exe')
    if not Path(compiler).is_file():
        raise SystemExit('Install Inno Setup 6.7+ from https://jrsoftware.org/isdl.php and add ISCC.exe to PATH.')
    prerequisite = installer_path()
    fetch_installer(prerequisite)
    resource = ROOT / 'build/windows-data/YueKeyKeyboard.dll'
    resource_hash = hashlib.sha256(resource.read_bytes()).hexdigest()
    subprocess.run([compiler, '/Qp', f'/DRepoRoot={ROOT}', f'/DResourceSHA256={resource_hash}',
                    str(ROOT / 'desktop/windows/keyboard-icon.iss')], check=True)
    keyboard_installer = prerequisite.parent / KEYBOARD_INSTALLER_NAME
    keyboard_hash = hashlib.sha256(keyboard_installer.read_bytes()).hexdigest()
    keyboard_metadata = prerequisite.parent / 'keyboard-icon.json'
    keyboard_metadata.write_text(json.dumps(dict(installer_sha256=keyboard_hash,
                                                resource_sha256=resource_hash)), encoding='utf-8')
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
        '--name', 'YueKey', '--paths', str(ROOT / 'src'),
        '--icon', str(ROOT / 'desktop/icons/yuekey.ico'),
        '--distpath', str(ROOT / 'build/windows-dist'), '--workpath', str(ROOT / 'build/pyinstaller'),
        '--specpath', str(ROOT / 'build'),
        '--add-data', f'{ROOT / "build/windows-data"}:windows-data',
        '--add-data', f'{prerequisite}:prerequisites',
        '--add-data', f'{keyboard_installer}:prerequisites',
        '--add-data', f'{keyboard_metadata}:prerequisites',
        '--add-data', f'{ROOT / "desktop/icons"}:app-icons',
        '--collect-all', 'sherpa_onnx', '--collect-all', 'opencc',
        '--collect-all', 'comtypes', '--collect-all', 'sounddevice',
        '--collect-all', 'truststore',
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
    shutil.make_archive(str(ROOT / 'dist' / f'YueKey-{VERSION}-windows-{architecture}'), 'zip', bundle.parent, bundle.name)
    subprocess.run([
        compiler, '/Qp', f'/DAppVersion={VERSION}', f'/DRepoRoot={ROOT}', f'/DAppArch={architecture}',
        f'/DWeaselName={INSTALLER_NAME}', f'/DWeaselSHA256={INSTALLER_SHA256}',
        f'/DKeyboardName={KEYBOARD_INSTALLER_NAME}', f'/DKeyboardSHA256={keyboard_hash}',
        f'/DKeyboardResourceSHA256={resource_hash}',
        str(ROOT / 'desktop/windows/yuekey.iss'),
    ], check=True)


if __name__ == '__main__':
    build()
