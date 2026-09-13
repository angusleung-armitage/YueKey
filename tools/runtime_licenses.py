"""Retain dependency notices in frozen application distributions."""
from importlib import metadata
from pathlib import Path
import shutil
import sys
import subprocess


def collect_licenses(target: Path) -> None:
    for distribution in metadata.distributions():
        name = distribution.metadata['Name']
        for file in distribution.files or []:
            if any(part.lower().startswith(('license', 'copying', 'notice', 'copyright')) for part in file.parts):
                original = Path(distribution.locate_file(file))
                if original.is_file():
                    destination = target / name / Path(*[p for p in file.parts if p not in ('.', '..')])
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(original, destination)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.exists():
        python_license = Path('/usr/share/doc/python3.14/copyright')
    if not python_license.is_file():
        raise RuntimeError('Python license file is required in the runtime bundle')
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(python_license, target / 'PYTHON-LICENSE.txt')
    if sys.platform == 'linux':
        # PyInstaller's analysis records the original paths of copied system
        # libraries. Include Debian copyright notices for every owned binary.
        import ast
        analysis = target.parents[2] / 'linux-pyinstaller/yuekey-speech/Analysis-00.toc'
        def paths(value):
            if isinstance(value, (list, tuple)):
                for item in value:
                    yield from paths(item)
            elif isinstance(value, str) and value.startswith('/usr/lib/'):
                yield value
        packages = set()
        for original in set(paths(ast.literal_eval(analysis.read_text()))):
            query = subprocess.run(['dpkg-query', '-S', original], capture_output=True, text=True)
            if query.returncode == 0:
                packages.update(line.rsplit(': ', 1)[0].split(':')[0] for line in query.stdout.splitlines())
        for package in packages:
            notice = Path('/usr/share/doc') / package / 'copyright'
            if notice.is_file():
                destination = target / 'system' / package / 'copyright'
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(notice, destination)
        shutil.copytree('/usr/share/common-licenses', target / 'common-licenses', dirs_exist_ok=True)
