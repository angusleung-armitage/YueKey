#!/usr/bin/python3
"""Install and test built packages in a disposable Ubuntu Docker container only."""
import argparse
import json
import os
from pathlib import Path
import subprocess

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
    assert len(packages) == 5, "Build the five Debian packages first"
    if args.with_desktops:
        run("apt-get", "-o", "Acquire::ForceIPv4=true", "update")
        run("apt-get", "install", "-y", "--no-install-recommends", *map(str, packages))
    else:
        core = [package for package in packages if package.name.startswith(("quick-hk-core_", "quick-hk-predict_"))]
        run("dpkg", "-i", *map(str, core))

    profiles = [Path.home() / ".config/ibus/rime", Path.home() / ".local/share/fcitx5/rime"]
    original = b"# Existing user preference; retain on uninstall.\npatch:\n  menu/page_size: 7\n"
    for profile in profiles:
        assert not profile.exists(), "Use a fresh container for package tests"
        profile.mkdir(parents=True)
        (profile / "default.custom.yaml").write_bytes(original)
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
