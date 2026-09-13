#!/usr/bin/env python3
"""Build local Debian packages. Never install or publish them."""
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text().strip() + "-1"
STAGE = ROOT / "build/packages"
DIST = ROOT / "dist"


def copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
    else:
        shutil.copyfile(source, target)


def control(name: str, architecture: str, depends: str, description: str) -> Path:
    path = STAGE / name
    shutil.rmtree(path, ignore_errors=True)
    (path / "DEBIAN").mkdir(parents=True)
    (path / "DEBIAN/control").write_text(
        f"Package: {name}\nVersion: {VERSION}\nArchitecture: {architecture}\n"
        "Maintainer: YueKey contributors <quick-hk@users.noreply.github.com>\n"
        f"Section: utils\nPriority: optional\nDepends: {depends}\n"
        f"Description: {description}\n YueKey provides local Cantonese input for Ubuntu 26.04.\n"
    )
    docs = path / "usr/share/doc" / name
    docs.mkdir(parents=True)
    for filename in ("LICENSE", "THIRD_PARTY.md"):
        copy(ROOT / filename, docs / filename)
    copy(ROOT / "LICENSES", docs / "licenses")
    (docs / "copyright").write_text((ROOT / "THIRD_PARTY.md").read_text())
    changelog = f"quick-hk ({VERSION}) resolute; urgency=medium\n\n  * Initial Cantonese Quick implementation.\n\n -- YueKey contributors <quick-hk@users.noreply.github.com>  Sat, 12 Sep 2026 00:00:00 +0000\n"
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
            file.chmod(0o755 if file.parent == path / "usr/bin" else 0o644)
    md5 = []
    for file in sorted((path / "usr").rglob("*")):
        if file.is_file():
            md5.append(f"{hashlib.md5(file.read_bytes()).hexdigest()}  {file.relative_to(path)}")
    (path / "DEBIAN/md5sums").write_text("\n".join(md5) + "\n")
    destination = DIST / f"{path.name}_{VERSION}_{architecture}.deb"
    env = dict(os.environ, SOURCE_DATE_EPOCH="1789171200")
    subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(path), str(destination)], check=True, env=env)


def build() -> None:
    DIST.mkdir(exist_ok=True)
    architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    if architecture != "amd64":
        raise SystemExit("This release is validated for Ubuntu 26.04 amd64; build in Dockerfile.dev")
    multiarch = subprocess.check_output(["dpkg-architecture", "-qDEB_HOST_MULTIARCH"], text=True).strip()
    rime_version = subprocess.check_output(["dpkg-query", "-W", "-f=${Version}", "librime1t64"], text=True).strip()

    native = control("quick-hk-predict", architecture,
                     f"librime1t64 (= {rime_version}), libc6 (>= 2.43), libstdc++6 (>= 15), libgoogle-glog0v6t64, libmarisa1",
                     "Cantonese prediction plugin and scoped Rime deployer")
    copy(ROOT / "build/native/librime-quick-hk-predict.so", native / f"usr/lib/{multiarch}/rime-plugins/librime-quick-hk-predict.so")
    copy(ROOT / "build/native/quick-hk-deployer", native / "usr/bin/quick-hk-deployer")
    for binary in (native / "usr/bin/quick-hk-deployer", native / f"usr/lib/{multiarch}/rime-plugins/librime-quick-hk-predict.so"):
        subprocess.run(["strip", "--strip-unneeded", str(binary)], check=True)
    # Ship modified plugin source alongside its attribution, without requiring a network fetch.
    copy(ROOT / "vendor/librime-predict", native / "usr/share/doc/quick-hk-predict/source")
    finish(native, architecture)

    core = control("quick-hk-core", "all",
                   f"quick-hk-predict (= {VERSION}), python3 (>= 3.11), python3-yaml, python3-gi, gir1.2-gtk-4.0, librime-plugin-lua, librime-data, fonts-noto-cjk",
                   "港式速成 Cantonese Quick scheme, settings and setup tools")
    copy(ROOT / "src/quick_hk", core / "usr/lib/python3/dist-packages/quick_hk")
    launcher = core / "usr/bin/quick-hk"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/usr/bin/python3\nfrom quick_hk.cli import main\nraise SystemExit(main())\n")
    for name in ("quick_hk.schema.yaml", "quick_hk.dict.yaml", "quick_hk.predict.db", "coverage.json", "lua/quick_hk.lua"):
        copy(ROOT / "build/data" / name, core / "usr/share/quick-hk/rime" / name)
    copy(ROOT / "desktop/quick-hk.desktop", core / "usr/share/applications/quick-hk.desktop")
    copy(ROOT / "README.md", core / "usr/share/doc/quick-hk-core/README.md")
    copy(ROOT / "docs", core / "usr/share/doc/quick-hk-core/docs")
    copy(ROOT / "data/sources.lock.json", core / "usr/share/doc/quick-hk-core/sources.lock.json")
    for dataset in ("cangjie", "quick", "cantonese"):
        for license_file in (ROOT / "build/sources" / dataset).glob("LICENSE*"):
            copy(license_file, core / "usr/share/doc/quick-hk-core/licenses" / dataset / license_file.name)
    copy(ROOT / "build/libcangjie/usr/share/doc/libcangjie3-data/copyright", core / "usr/share/doc/quick-hk-core/licenses/libcangjie-copyright")
    finish(core, "all")

    speech = control("quick-hk-dictation", architecture,
                     f"quick-hk-core (= {VERSION}), quick-hk-gnome (= {VERSION}) | quick-hk-kde (= {VERSION}), libglib2.0-0t64, librime1t64 (= {rime_version}), libc6 (>= 2.43), libstdc++6 (>= 15), pipewire-bin, gir1.2-ibus-1.0, libnotify-bin",
                     "Offline CPU-only Cantonese dictation with double Ctrl")
    copy(ROOT / "build/native/librime-quick-hk-dictation.so", speech / f"usr/lib/{multiarch}/rime-plugins/librime-quick-hk-dictation.so")
    subprocess.run(["strip", "--strip-unneeded", str(speech / f"usr/lib/{multiarch}/rime-plugins/librime-quick-hk-dictation.so")], check=True)
    copy(ROOT / "desktop/dictation", speech / "usr/share/quick-hk/desktop/dictation")
    finish(speech, architecture)

    for desktop, dependency, assets in (
        ("gnome", "ibus-rime, gnome-shell (>= 50), gnome-shell (<< 51)", "gnome"),
        ("kde", "fcitx5-rime, fcitx5, fcitx5-config-qt, fcitx5-frontend-gtk3, fcitx5-frontend-gtk4, fcitx5-frontend-qt6", "fcitx5"),
    ):
        package_arch = architecture if desktop == "kde" else "all"
        if desktop == "kde":
            dependency += ", libfcitx5core7 (>= 5.1.19), libfcitx5utils2 (>= 5.1.19), libglib2.0-0t64, libc6 (>= 2.43), libstdc++6 (>= 15)"
        target = control(f"quick-hk-{desktop}", package_arch, f"quick-hk-core (= {VERSION}), {dependency}", f"港式速成 integration for {desktop.upper()}")
        copy(ROOT / "desktop" / assets, target / "usr/share/quick-hk/desktop" / assets)
        if desktop == "kde":
            binary = target / f"usr/lib/{multiarch}/fcitx5/yuekey-dictation.so"
            copy(ROOT / "build/native/yuekey-dictation.so", binary)
            subprocess.run(["strip", "--strip-unneeded", str(binary)], check=True)
            copy(ROOT / "desktop/fcitx5/yuekey-dictation.conf", target / "usr/share/fcitx5/addon/yuekey-dictation.conf")
        finish(target, package_arch)
    checksums = [f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.name}" for file in sorted(DIST.glob(f"*_{VERSION}_*.deb"))]
    (DIST / "SHA256SUMS").write_text("\n".join(checksums) + "\n")


if __name__ == "__main__":
    build()
