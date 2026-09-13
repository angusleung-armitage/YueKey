#!/usr/bin/env python3
"""Build local Debian packages. Never install or publish them."""
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from quick_hk.speech_assets import digest, model_hashes

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text().strip() + "-1"
STAGE = ROOT / "build/packages"
DIST = ROOT / "dist"


def copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
    else:
        shutil.copy2(source, target)


def control(name: str, architecture: str, depends: str, description: str) -> Path:
    path = STAGE / name
    shutil.rmtree(path, ignore_errors=True)
    (path / "DEBIAN").mkdir(parents=True)
    (path / "DEBIAN/control").write_text(
        f"Package: {name}\nVersion: {VERSION}\nArchitecture: {architecture}\n"
        "Maintainer: YueKey contributors <quick-hk@users.noreply.github.com>\n"
        f"Section: utils\nPriority: optional\nDepends: {depends}\n"
        "Conflicts: quick-hk-core, quick-hk-predict, quick-hk-dictation, quick-hk-gnome, quick-hk-kde\n"
        "Replaces: quick-hk-core, quick-hk-predict, quick-hk-dictation, quick-hk-gnome, quick-hk-kde\n"
        "Homepage: https://github.com/angusleung-armitage/YueKey\n"
        f"Description: {description}\n Includes typing, settings and offline CPU Cantonese speech with models.\n"
    )
    docs = path / "usr/share/doc" / name
    docs.mkdir(parents=True)
    for filename in ("LICENSE", "THIRD_PARTY.md"):
        copy(ROOT / filename, docs / filename)
    copy(ROOT / "LICENSES", docs / "licenses")
    (docs / "copyright").write_text((ROOT / "THIRD_PARTY.md").read_text())
    changelog = f"yuekey ({VERSION}) resolute; urgency=medium\n\n  * All-in-one Cantonese input and speech distribution.\n\n -- YueKey contributors <quick-hk@users.noreply.github.com>  Sat, 12 Sep 2026 00:00:00 +0000\n"
    (docs / "changelog.Debian.gz").write_bytes(gzip.compress(changelog.encode(), mtime=0))
    return path


def finish(path: Path, architecture: str) -> None:
    for filename in ("quick-hk", "quick-hk-deployer"):
        if (path / "usr/bin" / filename).is_file():
            manual = path / "usr/share/man/man1" / f"{filename}.1.gz"
            manual.parent.mkdir(parents=True, exist_ok=True)
            manual.write_bytes(gzip.compress((ROOT / "docs/man" / f"{filename}.1").read_bytes(), mtime=0))
    for file in path.rglob("*"):
        if file.is_dir():
            file.chmod(0o755)
        elif file.is_file():
            file.chmod(0o755 if (file.parent == path / "usr/bin" or file == path / "usr/lib/yuekey/speech/yuekey-speech") else 0o644)
    md5 = []
    for file in sorted((path / "usr").rglob("*")):
        if file.is_file():
            md5.append(f"{hashlib.md5(file.read_bytes()).hexdigest()}  {file.relative_to(path)}")
    (path / "DEBIAN/md5sums").write_text("\n".join(md5) + "\n")
    installed_size = sum((file.stat().st_size + 1023) // 1024
                         for file in (path / 'usr').rglob('*') if file.is_file())
    with (path / 'DEBIAN/control').open('a') as metadata:
        metadata.write(f'Installed-Size: {installed_size}\n')
    destination = DIST / f"{path.name}_{VERSION}_{architecture}.deb"
    env = dict(os.environ, SOURCE_DATE_EPOCH="1789171200")
    subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(path), str(destination)], check=True, env=env)


def build() -> None:
    DIST.mkdir(exist_ok=True)
    architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    if architecture not in ('amd64', 'arm64'):
        raise SystemExit('All-in-one Ubuntu 26.04 builds require amd64 or arm64. '
                         'Ubuntu has no i386 desktop; the pinned speech runtime has no Linux i386 wheels.')
    multiarch = subprocess.check_output(['dpkg-architecture', '-qDEB_HOST_MULTIARCH'], text=True).strip()
    rime_version = subprocess.check_output(['dpkg-query', '-W', '-f=${Version}', 'librime1t64'], text=True).strip()
    models = ROOT / 'build/speech-models'
    speech = ROOT / 'build/linux-dist/yuekey-speech'
    if not (speech / 'yuekey-speech').is_file():
        raise SystemExit('Build the bundled speech runtime first: see desktop/linux/requirements.txt and make speech')
    for name, expected in model_hashes().items():
        if not (models / name).is_file() or digest(models / name) != expected:
            raise SystemExit(f'Missing or invalid bundled speech model: {name}')
    target = control('yuekey', architecture,
        f'librime1t64 (= {rime_version}), libc6 (>= 2.43), libstdc++6 (>= 15), '
        'libgoogle-glog0v6t64, libmarisa1, libglib2.0-0t64, '
        'python3 (>= 3.11), python3-yaml, python3-gi, gir1.2-gtk-4.0, '
        'librime-plugin-lua, librime-data, fonts-noto-cjk, '
        'ibus-rime, gir1.2-ibus-1.0, fcitx5-rime, fcitx5, fcitx5-config-qt, '
        'fcitx5-frontend-gtk3, fcitx5-frontend-gtk4, fcitx5-frontend-qt6, '
        'libfcitx5core7 (>= 5.1.19), libfcitx5utils2 (>= 5.1.19), pipewire-bin, libnotify-bin',
        'all-in-one Cantonese Quick input and CPU dictation')
    docs = target / 'usr/share/doc/yuekey'
    copy(ROOT / 'src/quick_hk', target / 'usr/lib/python3/dist-packages/quick_hk')
    launcher = target / 'usr/bin/quick-hk'
    launcher.parent.mkdir(parents=True)
    launcher.write_text('#!/usr/bin/python3\nfrom quick_hk.cli import main\nraise SystemExit(main())\n')
    for name in ('quick_hk.schema.yaml', 'quick_hk.dict.yaml', 'quick_hk.predict.db', 'coverage.json', 'lua/quick_hk.lua'):
        copy(ROOT / 'build/data' / name, target / 'usr/share/quick-hk/rime' / name)
    copy(ROOT / 'desktop/quick-hk.desktop', target / 'usr/share/applications/quick-hk.desktop')
    for name in ('README.md', 'docs'):
        copy(ROOT / name, docs / name)
    copy(ROOT / 'data/sources.lock.json', docs / 'sources.lock.json')
    for dataset in ('cangjie', 'quick', 'cantonese'):
        for license_file in (ROOT / 'build/sources' / dataset).glob('LICENSE*'):
            copy(license_file, docs / 'licenses' / dataset / license_file.name)
    copy(ROOT / 'build/libcangjie/usr/share/doc/libcangjie3-data/copyright', docs / 'licenses/libcangjie-copyright')
    copy(ROOT / 'vendor/librime-predict', docs / 'source/librime-predict')
    binaries = {
        'quick-hk-deployer': 'usr/bin/quick-hk-deployer',
        'librime-quick-hk-predict.so': f'usr/lib/{multiarch}/rime-plugins/librime-quick-hk-predict.so',
        'librime-quick-hk-dictation.so': f'usr/lib/{multiarch}/rime-plugins/librime-quick-hk-dictation.so',
        'yuekey-dictation.so': f'usr/lib/{multiarch}/fcitx5/yuekey-dictation.so',
    }
    for name, destination in binaries.items():
        binary = target / destination
        copy(ROOT / 'build/native' / name, binary)
        with binary.open('rb') as stream:
            header = stream.read(20)
        if header[:4] != b'\x7fELF' or int.from_bytes(header[18:20], 'little') != {'amd64': 62, 'arm64': 183}[architecture]:
            raise SystemExit(f'Wrong native architecture for {architecture}: {name}; use a clean native build directory')
        subprocess.run(['strip', '--strip-unneeded', str(binary)], check=True)
    for assets in ('dictation', 'gnome', 'fcitx5'):
        copy(ROOT / 'desktop' / assets, target / 'usr/share/quick-hk/desktop' / assets)
    copy(ROOT / 'desktop/fcitx5/yuekey-dictation.conf', target / 'usr/share/fcitx5/addon/yuekey-dictation.conf')
    copy(speech, target / 'usr/lib/yuekey/speech')
    for file in (target / 'usr/lib/yuekey/speech').rglob('*'):
        if file.is_file():
            with file.open('rb') as stream:
                elf = stream.read(4) == b'\x7fELF'
            if elf:
                with file.open('rb') as stream:
                    header = stream.read(20)
                if int.from_bytes(header[18:20], 'little') != {'amd64': 62, 'arm64': 183}[architecture]:
                    raise SystemExit(f'Wrong speech runtime architecture: {file}')
                subprocess.run(['strip', '--strip-unneeded', str(file)], check=True)
    overrides = target / 'usr/share/lintian/overrides/yuekey'
    overrides.parent.mkdir(parents=True)
    overrides.write_text(
        '# Frozen, private CPU worker runtime; never installed as system libraries.\n'
        '# Python wheels are hash locked; system-library versions and licenses accompany the bundle.\n'
        'yuekey: embedded-library * [usr/lib/yuekey/speech/_internal/*]\n')
    copy(ROOT / 'desktop/linux/requirements.txt', docs / 'speech-requirements.txt')
    for name in model_hashes():
        copy(models / name, target / 'usr/share/yuekey/models' / name)
    finish(target, architecture)
    checksums = [f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.name}" for file in sorted(DIST.glob(f"*_{VERSION}_*.deb"))]
    (DIST / "SHA256SUMS").write_text("\n".join(checksums) + "\n")


if __name__ == "__main__":
    build()
