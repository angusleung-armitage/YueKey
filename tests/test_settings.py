"""Preference validation and CLI isolation tests; never use the real home directory."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from quick_hk.cli import main
from quick_hk.settings import Settings, SettingsError, load_settings, save_settings, settings_path


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.environment = patch.dict(os.environ, {
            "HOME": str(self.root), "XDG_CONFIG_HOME": str(self.root / "config"),
            "QUICK_HK_CONFIG": str(self.root / "config/settings.toml"),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_missing_file_uses_defaults_without_writing(self):
        self.assertEqual(load_settings(), Settings())
        self.assertFalse(settings_path().exists())

    def test_all_settings_round_trip(self):
        settings = Settings(
            horizontal=False, page_size=5, font_size=28, learning=False,
            prediction=False, show_candidates=False, ascii_punctuation=True,
            theme="dark", switch_key="Control_L",
        )
        save_settings(settings)
        self.assertEqual(load_settings(), settings)
        self.assertEqual(settings_path().stat().st_mode & 0o777, 0o600)

    def test_environment_and_explicit_path_precedence(self):
        explicit = self.root / "explicit.toml"
        save_settings(Settings(theme="dark"), explicit)
        self.assertEqual(load_settings(explicit).theme, "dark")
        self.assertEqual(load_settings().theme, "light")
        os.environ.pop("QUICK_HK_CONFIG")
        self.assertEqual(settings_path(), self.root / "config/quick-hk/settings.toml")

    def test_rejects_bad_values_and_typo_before_saving(self):
        for values in (
            {"page_size": True}, {"page_size": 0}, {"page_size": 10},
            {"font_size": 9}, {"font_size": 37}, {"learning": "true"},
            {"theme": "auto"}, {"switch_key": "Alt_L"},
        ):
            with self.subTest(values=values), self.assertRaises(SettingsError):
                Settings(**values)
        settings_path().parent.mkdir(parents=True)
        settings_path().write_text("predicton = true\n")
        with self.assertRaisesRegex(SettingsError, "predicton"):
            load_settings()
        settings_path().write_text("theme = [")
        with self.assertRaisesRegex(SettingsError, "Invalid TOML"):
            load_settings()

    def test_atomic_save_preserves_previous_file_on_failure(self):
        save_settings(Settings())
        original = settings_path().read_bytes()
        with patch("quick_hk.settings.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                save_settings(Settings(theme="dark"))
        self.assertEqual(settings_path().read_bytes(), original)
        self.assertEqual(list(settings_path().parent.iterdir()), [settings_path()])

    def test_cli_set_without_deploy_then_show(self):
        with redirect_stdout(io.StringIO()):
            result = main(["configure", "--set", "learning=false", "--set", "theme=dark", "--no-deploy"])
        self.assertEqual(result, 0)
        self.assertEqual(load_settings(), replace(Settings(), learning=False, theme="dark"))
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["configure", "--show"]), 0)
        self.assertIn('theme = "dark"', output.getvalue())

    def test_cli_home_isolation(self):
        isolated = self.root / "isolated"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["configure", "--home", str(isolated), "--set", "page_size=7", "--no-deploy"]), 0)
        self.assertEqual(settings_path(), isolated / ".config/quick-hk/settings.toml")
        self.assertEqual(load_settings().page_size, 7)

    def test_failed_configure_deployment_does_not_save_preferences(self):
        save_settings(Settings())
        from quick_hk.deployment import DeploymentError

        with patch("quick_hk.cli.deploy", side_effect=DeploymentError("compile failed")):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["configure", "--set", "theme=dark"]), 1)
        self.assertEqual(load_settings().theme, "light")

    def test_gui_missing_dependency_is_a_clean_cli_error(self):
        output = io.StringIO()
        with patch("quick_hk.gui.run_gui", side_effect=RuntimeError("Install python3-gi")):
            with redirect_stderr(output):
                self.assertEqual(main(["configure"]), 1)
        self.assertIn("Install python3-gi", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_gui_can_open_to_recover_malformed_settings(self):
        settings_path().parent.mkdir(parents=True)
        settings_path().write_text("theme = [")
        with patch("quick_hk.gui.run_gui", return_value=None) as launch:
            self.assertEqual(main(["configure", "--frontend", "fcitx5"]), 0)
        launch.assert_called_once_with(config_path=None, frontend="fcitx5")


if __name__ == "__main__":
    unittest.main()
