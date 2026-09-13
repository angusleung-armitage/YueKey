#!/usr/bin/python3
"""Install and test built packages in a disposable Ubuntu Docker container only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*arguments):
    subprocess.run(arguments, check=True, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-desktops", action="store_true",
                        help="Also install GNOME/KDE integration packages and their dependencies")
    args = parser.parse_args()
    if not Path("/.dockerenv").exists() or os.geteuid() != 0:
        raise SystemExit("Run as root only inside a disposable Docker container; see docs/compatibility.md")
    version = (ROOT / 'VERSION').read_text().strip()
    packages = sorted((ROOT / "dist").glob(f"*_{version}-1_*.deb"))
    architecture = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
    packages = [ROOT / f'dist/yuekey_{version}-1_{architecture}.deb']
    assert packages[0].is_file(), 'Build the all-in-one DEB first'
    profiles = [Path.home() / ".config/ibus/rime", Path.home() / ".local/share/fcitx5/rime"]
    original = b"# Existing user preference; retain on uninstall.\npatch:\n  menu/page_size: 7\n"
    for profile in profiles:
        assert not profile.exists(), "Use a fresh container for package tests"
        profile.mkdir(parents=True)
        (profile / "default.custom.yaml").write_bytes(original)
    # Model the old five-package ownership/dependency graph. apt must replace
    # them in one transaction without conflicting files or leftover packages.
    legacy = ['quick-hk-' + name for name in ('predict', 'core', 'gnome', 'kde', 'dictation')]
    if args.with_desktops:
        run("apt-get", "-o", "Acquire::ForceIPv4=true", "update")
        with tempfile.TemporaryDirectory(prefix='yuekey-upgrade-') as temporary:
            for name in legacy:
                stage = Path(temporary) / name
                (stage / 'DEBIAN').mkdir(parents=True)
                dependency = '' if name == 'quick-hk-predict' else 'Depends: quick-hk-predict (= 0.4.1-1)\n'
                (stage / 'DEBIAN/control').write_text(
                    f'Package: {name}\nVersion: 0.4.1-1\nArchitecture: {architecture}\n'
                    f'Maintainer: Test <test@example.invalid>\n{dependency}Description: upgrade fixture\n')
                if name == 'quick-hk-core':
                    overlap = stage / 'usr/bin/quick-hk'
                    overlap.parent.mkdir(parents=True)
                    overlap.write_text('#!/bin/sh\nexit 0\n')
                    overlap.chmod(0o755)
                run('dpkg-deb', '--build', str(stage), str(stage) + '.deb')
            run('dpkg', '-i', *map(str, Path(temporary).glob('*.deb')))
        run("apt-get", "install", "-y", "--no-install-recommends", *map(str, packages))
        for name in legacy:
            state = subprocess.run(['dpkg-query', '-W', '-f=${db:Status-Status}', name], capture_output=True, text=True)
            assert state.stdout != 'installed', f'Legacy package survived migration: {name}'
        assert subprocess.check_output(['dpkg-query', '-S', '/usr/bin/quick-hk'], text=True).startswith('yuekey:')
    else:
        run('dpkg-deb', '--extract', str(packages[0]), '/')

    for profile in profiles:
        assert (profile / 'default.custom.yaml').read_bytes() == original, 'Package upgrade changed user settings'

    # The installed speech worker and weights run with the container network
    # unavailable too; this command never opens an audio device.
    run('/usr/lib/yuekey/speech/yuekey-speech', '--models', '/usr/share/yuekey/models', '--check')
    run('runuser', '-u', 'nobody', '--', 'quick-hk', 'dictation', 'setup')
    speech = json.loads(subprocess.check_output(['quick-hk', 'dictation', 'status', '--json']))
    assert speech['ready'] and speech['bundled'] and speech['provider'] == 'cpu'

    run("quick-hk", "setup", "--frontend", "both")
    run("quick-hk", "deploy", "--frontend", "both")
    status = json.loads(subprocess.check_output(["quick-hk", "doctor", "--frontend", "both", "--json"]))
    assert status["ok"] and all(item["compiled"] for item in status["frontends"].values())
    for profile in profiles:
        (profile / "user.yaml").write_text("var:\n  previously_selected_schema: quick_hk\n")
    for frontend in ("ibus", "fcitx5"):
        run("dbus-run-session", "--", "xvfb-run", "-a", "python3", str(ROOT / "tools" / f"smoke_{frontend}.py"))
    run("quick-hk", "uninstall", "--frontend", "both")
    for profile in profiles:
        assert (profile / "default.custom.yaml").read_bytes() == original
        assert (profile / "quick_hk.userdb").is_dir(), "Uninstall removed learning"
        assert (profile / "user.yaml").is_file(), "Uninstall removed frontend user state"
        assert not (profile / "quick_hk.schema.yaml").exists()
    print("PASS packages: installation, both profiles, repeated deployment, doctor, frontend input, uninstall preservation")


if __name__ == "__main__":
    main()
