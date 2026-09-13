"""Transactional deployment and preservation behavior using isolated fake frontends."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from quick_hk import deployment as d
from quick_hk.settings import Settings


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "payload"
        for name in d.REQUIRED_DATA:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"schema:\n  schema_id: quick_hk\n" if name.endswith("schema.yaml") else b"test payload\n")
        shared = self.root / "shared"
        shared.mkdir()
        (shared / "default.yaml").write_text("schema_list:\n  - schema: cangjie5\n")
        script = self.root / "deployer.py"
        script.write_text(
            "import pathlib,sys\n"
            "assert sys.argv[1] == '--build'\n"
            "stage,shared,build = map(pathlib.Path, sys.argv[2:])\n"
            "assert (shared / 'default.yaml').is_file()\n"
            "build.mkdir(exist_ok=True)\n"
            "(build / 'quick_hk.schema.yaml').write_bytes((stage / 'quick_hk.custom.yaml').read_bytes())\n"
            "(build / 'quick_hk.table.bin').write_bytes(b'compiled table')\n"
            "(build / 'default.yaml').write_bytes((stage / 'default.custom.yaml').read_bytes())\n"
        )
        self.environment = patch.dict(os.environ, {
            "HOME": str(self.root), "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_DATA_HOME": str(self.root / "data"), "XDG_STATE_HOME": str(self.root / "state"),
            "QUICK_HK_DATA_DIR": str(self.source), "QUICK_HK_DESKTOP_DIR": str(self.root / "desktop"),
            "QUICK_HK_CONFIG": str(self.root / "preferences.toml"),
            "QUICK_HK_RIME_SHARED_DIR": str(shared),
            "QUICK_HK_DEPLOYER": f"{sys.executable} {script}", "XDG_CURRENT_DESKTOP": "GNOME",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def write(self, path, contents):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)

    def test_schema_list_append_preserves_existing_patches(self):
        path = Path("default.custom.yaml")
        for key in ("schema_list", "schema_list/+"):
            with self.subTest(key=key):
                raw = yaml.safe_dump({"patch": {key: [{"schema": "cangjie5"}], "menu/page_size": 5}}).encode()
                result = d.merge_schema_list(raw, path)
                document = yaml.safe_load(result)
                self.assertEqual(document["patch"][key], [{"schema": "cangjie5"}, {"schema": "quick_hk"}])
                self.assertEqual(document["patch"]["menu/page_size"], 5)
                self.assertEqual(d.merge_schema_list(result, path), result)
        result = yaml.safe_load(d.merge_schema_list(None, path))
        self.assertEqual(result["patch"]["schema_list/+"], [{"schema": "quick_hk"}])

    def test_rejects_ambiguous_yaml_without_changing_it(self):
        for raw in (
            b"patch:\n  schema_list: []\n  schema_list/+: []\n",
            b"patch:\n  schema_list/@0: {schema: other}\n",
            b"patch:\n  schema_list: unknown\n",
            b"patch: {}\npatch: {}\n",
            b"patch: [invalid]\n",
        ):
            with self.subTest(raw=raw), self.assertRaises(d.DeploymentError):
                d.merge_schema_list(raw, Path("default.custom.yaml"))

    def test_setup_repeated_configuration_and_uninstall_restore_original(self):
        directory = d.frontend_directory("ibus")
        default = directory / "default.custom.yaml"
        original = b"# user's exact original formatting\npatch:\n  schema_list:\n    - schema: cangjie5\n  menu/page_size: 5\n"
        self.write(default, original)
        self.write(directory / "unrelated.schema.yaml", b"schema: {schema_id: unrelated}\n")
        self.write(directory / "quick_hk.userdb/CURRENT", b"user learning")
        d.deploy("ibus")
        manifest_path = d.state_home() / "ibus.json"
        first_manifest = json.loads(manifest_path.read_text())
        d.deploy("ibus", Settings(theme="dark", learning=False, switch_key="Shift_R"))
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(first_manifest["files"][str(default)]["backup"], manifest["files"][str(default)]["backup"])
        custom = yaml.safe_load((directory / "quick_hk.custom.yaml").read_bytes())["patch"]
        self.assertFalse(custom["translator/enable_user_dict"])
        self.assertEqual(custom["ascii_composer/switch_key"]["Shift_R"], "commit_code")
        self.assertEqual(custom["ascii_composer/switch_key"]["Shift_L"], "noop")
        d.uninstall("ibus")
        self.assertEqual(default.read_bytes(), original)
        self.assertEqual((directory / "quick_hk.userdb/CURRENT").read_bytes(), b"user learning")
        self.assertTrue((directory / "unrelated.schema.yaml").exists())
        self.assertFalse((directory / "quick_hk.schema.yaml").exists())
        self.assertFalse(manifest_path.exists())

    def test_both_frontends_are_prepared_before_any_live_write(self):
        real_compile = d._compile
        calls = []

        def compile_stage(stage):
            calls.append(stage.name)
            if stage.name == "fcitx5":
                raise d.DeploymentError("second frontend compilation failed")
            real_compile(stage)

        with patch.object(d, "_compile", side_effect=compile_stage):
            with self.assertRaisesRegex(d.DeploymentError, "second frontend"):
                d.deploy("both")
        self.assertEqual(calls, ["ibus", "fcitx5"])
        self.assertFalse(d.frontend_directory("ibus").exists())
        self.assertFalse(d.frontend_directory("fcitx5").exists())
        self.assertFalse((d.state_home() / "ibus.json").exists())

    def test_failed_compiler_leaves_live_files_untouched(self):
        directory = d.frontend_directory("ibus")
        default = directory / "default.custom.yaml"
        self.write(default, b"patch: {}\n")
        os.environ["QUICK_HK_DEPLOYER"] = "/bin/false"
        with self.assertRaisesRegex(d.DeploymentError, "compilation failed"):
            d.deploy("ibus")
        self.assertEqual(default.read_bytes(), b"patch: {}\n")
        self.assertEqual(list(directory.iterdir()), [default])

    def test_mid_commit_error_rolls_back_live_files_and_manifest(self):
        directory = d.frontend_directory("ibus")
        original = directory / "quick_hk.schema.yaml"
        self.write(original, b"prior schema")
        real_write = d._atomic_write
        failed = False

        def fail_once(path, contents, mode=0o600):
            nonlocal failed
            if path == directory / "lua/quick_hk.lua" and not failed:
                failed = True
                raise OSError("simulated full disk")
            return real_write(path, contents, mode)

        with patch.object(d, "_atomic_write", side_effect=fail_once):
            with self.assertRaisesRegex(d.DeploymentError, "rolled back"):
                d.deploy("ibus")
        self.assertEqual(original.read_bytes(), b"prior schema")
        self.assertFalse((directory / "quick_hk.dict.yaml").exists())
        self.assertFalse((d.state_home() / "ibus.json").exists())

    def test_uninstall_keeps_user_edits_and_new_deploy_refuses_clobber(self):
        d.deploy("ibus")
        path = d.frontend_directory("ibus") / "quick_hk.custom.yaml"
        edited = path.read_bytes() + b"# user's edit\n"
        path.write_bytes(edited)
        with self.assertRaisesRegex(d.DeploymentError, "changed outside"):
            d.deploy("ibus", Settings(page_size=5))
        d.uninstall("ibus")
        self.assertEqual(path.read_bytes(), edited)
        self.assertIn(str(path), json.loads((d.state_home() / "ibus.json").read_text())["files"])

    def test_missing_backup_prevents_partial_removal_of_either_frontend(self):
        default = d.frontend_directory('fcitx5') / 'default.custom.yaml'
        self.write(default, b'# existing KDE preferences\npatch: {}\n')
        d.deploy('both')
        manifest = json.loads((d.state_home() / 'fcitx5.json').read_text())
        Path(manifest['files'][str(default)]['backup']).unlink()
        before = {}
        for frontend in ('ibus', 'fcitx5'):
            marker = d.state_home() / f'{frontend}.json'
            before[marker] = marker.read_bytes()
            for filename in json.loads(before[marker])['files']:
                before[Path(filename)] = Path(filename).read_bytes()
        with self.assertRaisesRegex(d.DeploymentError, 'backup missing'):
            d.uninstall('both')
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_shared_default_edited_by_user_survives_repeat_and_uninstall(self):
        d.deploy("ibus")
        path = d.frontend_directory("ibus") / "default.custom.yaml"
        edited = path.read_bytes() + b"# later user change\n"
        path.write_bytes(edited)
        d.deploy("ibus", Settings(page_size=5))
        d.uninstall("ibus")
        self.assertEqual(path.read_bytes(), edited)

    def test_uninstall_preserves_replacement_symlink_and_continues(self):
        d.deploy("ibus")
        path = d.frontend_directory("ibus") / "quick_hk.custom.yaml"
        path.unlink()
        target = self.root / "user-custom.yaml"
        target.write_bytes(b"user configuration")
        path.symlink_to(target)
        d.uninstall("ibus")
        self.assertTrue(path.is_symlink())
        self.assertEqual(target.read_bytes(), b"user configuration")
        self.assertFalse((d.frontend_directory("ibus") / "quick_hk.schema.yaml").exists())

    def test_desktop_assets_and_classicui_restore_without_touching_sections(self):
        extension = d.desktop_directory() / "gnome" / d.EXTENSION_UUID / "metadata.json"
        launcher = d.desktop_directory() / "gnome/ibus-setup-rime.desktop"
        installed_launcher = d.data_home() / "applications/ibus-setup-rime.desktop"
        theme = d.desktop_directory() / "fcitx5/quick-hk-dark/theme.conf"
        self.write(extension, b'{"shell-version":["50"]}')
        self.write(launcher, b"[Desktop Entry]\nExec=quick-hk configure --frontend ibus\n")
        original_launcher = b"[Desktop Entry]\nExec=existing-rime-settings\n"
        self.write(installed_launcher, original_launcher)
        self.write(theme, b"[Metadata]\nName=Quick HK\n")
        classicui = d.config_home() / "fcitx5/conf/classicui.conf"
        original = b"# Keep comments\nTheme=original\nOther=unchanged\n[Section]\nFont=special\n"
        self.write(classicui, original)
        d.deploy("both", Settings(theme="dark", font_size=24))
        self.assertIn(b"Theme=quick-hk-dark\n", classicui.read_bytes())
        self.assertIn(b"Font=Noto Sans CJK HK 24\n", classicui.read_bytes())
        self.assertIn(b"[Section]\nFont=special\n", classicui.read_bytes())
        self.assertTrue((d.data_home() / "gnome-shell/extensions" / d.EXTENSION_UUID / "metadata.json").exists())
        self.assertEqual(installed_launcher.read_bytes(), launcher.read_bytes())
        presentation = json.loads((d.config_home() / "quick-hk/presentation.json").read_bytes())
        self.assertEqual(presentation, {"theme": "dark", "font_size": 24, "dictation_enabled": False})
        d.uninstall("both")
        self.assertEqual(classicui.read_bytes(), original)
        self.assertEqual(installed_launcher.read_bytes(), original_launcher)

    def test_reset_learning_requires_stopped_frontend_and_keeps_backup(self):
        database = d.frontend_directory("ibus") / "quick_hk.userdb"
        self.write(database / "CURRENT", b"learned data")
        with patch.object(d, "_active_frontends", return_value={"ibus"}):
            with self.assertRaisesRegex(d.DeploymentError, "Stop ibus"):
                d.reset_learning("ibus")
        self.assertTrue(database.exists())
        with patch.object(d, "_active_frontends", return_value=set()):
            d.reset_learning("ibus")
        self.assertFalse(database.exists())
        backup = list((d.state_home() / "learning-backups").glob("*/ibus/quick_hk.userdb/CURRENT"))
        self.assertEqual(len(backup), 1)
        self.assertEqual(backup[0].read_bytes(), b"learned data")

    def test_reset_learning_respects_leveldb_lock_even_if_frontend_is_unknown(self):
        database = d.frontend_directory("ibus") / "quick_hk.userdb"
        self.write(database / "CURRENT", b"learned data")
        script = (
            "import fcntl,sys; "
            "stream=open(sys.argv[1], 'a+b'); "
            "fcntl.lockf(stream, fcntl.LOCK_EX); "
            "print('locked', flush=True); sys.stdin.read(1)"
        )
        with subprocess.Popen(
            [sys.executable, "-c", script, str(database / "LOCK")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        ) as process:
            try:
                self.assertEqual(process.stdout.readline().strip(), "locked")
                with patch.object(d, "_active_frontends", return_value=set()):
                    with self.assertRaisesRegex(d.DeploymentError, "dictionary is locked"):
                        d.reset_learning("ibus")
                self.assertTrue(database.exists())
            finally:
                process.communicate("x", timeout=5)

    def test_frontend_detection_uses_existing_managed_targets_then_desktop(self):
        self.assertEqual(d.resolve_frontends(), ["ibus"])
        os.environ["XDG_CURRENT_DESKTOP"] = "KDE"
        self.assertEqual(d.resolve_frontends(), ["fcitx5"])
        d.deploy("both")
        self.assertEqual(d.resolve_frontends(), ["ibus", "fcitx5"])
        self.assertEqual(d.frontend_directory("ibus"), self.root / ".config/ibus/rime")
        self.assertEqual(d.frontend_directory("fcitx5"), self.root / "data/fcitx5/rime")

    def test_payload_missing_and_symlink_fail_safely(self):
        (self.source / "quick_hk.dict.yaml").unlink()
        with self.assertRaisesRegex(d.DeploymentError, "Incomplete Rime data"):
            d.deploy("ibus")
        (self.source / "quick_hk.dict.yaml").write_bytes(b"dictionary")
        path = d.frontend_directory("ibus") / "default.custom.yaml"
        target = self.root / "original.yaml"
        target.write_bytes(b"patch: {}\n")
        path.parent.mkdir(parents=True)
        path.symlink_to(target)
        with self.assertRaisesRegex(d.DeploymentError, "symlink"):
            d.deploy("ibus")
        self.assertEqual(target.read_bytes(), b"patch: {}\n")


if __name__ == "__main__":
    unittest.main()
