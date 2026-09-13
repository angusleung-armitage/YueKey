"""GTK integration smoke test.

Run: PYTHONPATH=src xvfb-run -a python3 -m unittest discover -s tests -p test_gui.py

This renders real GTK widgets and uses real asynchronous Gio child processes.
Only the deployment command is substituted, so no desktop input files change.
The test skips when GTK4 or a graphical display is unavailable.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quick_hk import gui
from quick_hk.settings import Settings, load_settings, save_settings


class GuiTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"),
        "A display is required; run this test under xvfb-run",
    )
    def test_settings_window_apply_failure_and_reset(self):
        try:
            import gi

            gi.require_version("Gtk", "4.0")
            from gi.repository import Gio, GLib, Gtk
        except (ImportError, ValueError) as error:
            self.skipTest(f"GTK4 is unavailable: {error}")

        with tempfile.TemporaryDirectory(prefix="quick-hk-gui-test-") as temporary:
            root = Path(temporary)
            config_path = root / "preferences.toml"
            save_settings(Settings(theme="dark", font_size=24), config_path)
            launches = []
            real_new = Gio.SubprocessLauncher.new

            class Launcher:
                def __init__(self, flags):
                    self.inner = real_new(flags)
                    self.environment = {}

                def setenv(self, name, value, overwrite):
                    self.environment[name] = value
                    self.inner.setenv(name, value, overwrite)

                def spawnv(self, arguments):
                    launches.append((arguments, self.environment))
                    if len(launches) == 2:
                        code = (
                            "import sys,time; time.sleep(.08); "
                            "print('simulated deployment failure', file=sys.stderr); "
                            "sys.exit(3)"
                        )
                    else:
                        code = "import time; time.sleep(.08); print('operation completed')"
                    return self.inner.spawnv([sys.executable, "-c", code])

            state = 0
            failures = []
            completed = False
            font_control = None

            def descendants(widget):
                child = widget.get_first_child()
                while child:
                    yield child
                    yield from descendants(child)
                    child = child.get_next_sibling()

            def tick():
                nonlocal state, completed, font_control
                application = Gtk.Application.get_default()
                if not application or not application.window:
                    return GLib.SOURCE_CONTINUE
                if not application.window.get_width():
                    return GLib.SOURCE_CONTINUE
                try:
                    if state == 0:
                        self.assertEqual(len(application.fields), 13)
                        self.assertEqual(application.fields["theme"](), "dark")
                        self.assertEqual(application.fields["font_size"](), 24)
                        self.assertGreaterEqual(application.window.get_width(), 500)
                        font_control = next(
                            child for child in descendants(application.form)
                            if isinstance(child, Gtk.SpinButton)
                            and child.get_value_as_int() == 24
                        )
                        font_control.set_value(27)
                        application.apply_button.emit("clicked")
                        self.assertIsNotNone(application.process)
                        self.assertFalse(application.apply_button.get_sensitive())
                        self.assertFalse(application.reset_button.get_sensitive())
                        self.assertTrue(application._close_requested(application.window))
                        state = 1
                    elif state == 1 and application.process is None:
                        self.assertEqual(application.status.get_label(), "operation completed")
                        self.assertTrue(application.apply_button.get_sensitive())
                        self.assertEqual(load_settings(config_path).font_size, 27)
                        self.assertEqual(
                            launches[0][0],
                            [sys.executable, "-m", "quick_hk", "deploy", "--frontend", "fcitx5"],
                        )
                        self.assertEqual(
                            launches[0][1]["QUICK_HK_CONFIG"], str(config_path.resolve())
                        )
                        font_control.set_value(30)
                        application.apply_button.emit("clicked")
                        state = 2
                    elif state == 2 and application.process is None:
                        self.assertIn("simulated deployment failure", application.status.get_label())
                        self.assertIn("Settings remain saved", application.status.get_label())
                        self.assertTrue(application.status.has_css_class("error"))
                        self.assertTrue(application.apply_button.get_sensitive())
                        self.assertEqual(load_settings(config_path).font_size, 30)
                        application.reset_button.emit("clicked")
                        state = 3
                    elif state == 3 and application.process is None:
                        self.assertEqual(
                            launches[2][0],
                            [sys.executable, "-m", "quick_hk", "reset-learning", "--frontend", "fcitx5"],
                        )
                        self.assertEqual(application.status.get_label(), "operation completed")
                        self.assertFalse(application.status.has_css_class("error"))
                        self.assertTrue(application.form.get_sensitive())
                        self.assertEqual(load_settings(config_path).font_size, 30)
                        completed = True
                        application.quit()
                        return GLib.SOURCE_REMOVE
                except BaseException as error:
                    failures.append(error)
                    application.quit()
                    return GLib.SOURCE_REMOVE
                return GLib.SOURCE_CONTINUE

            def timeout():
                failures.append(AssertionError("GTK smoke test timed out after 20 seconds"))
                application = Gtk.Application.get_default()
                if application:
                    if application.process:
                        application.process.force_exit()
                    application.quit()
                return GLib.SOURCE_REMOVE

            timer = GLib.timeout_add(25, tick)
            watchdog = GLib.timeout_add_seconds(20, timeout)
            environment = {
                "HOME": str(root),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_DATA_HOME": str(root / "data"),
                "XDG_STATE_HOME": str(root / "state"),
                "GTK_USE_PORTAL": "0",
                "GTK_A11Y": "none",
                "GIO_USE_VFS": "local",
                "GSK_RENDERER": "cairo",
            }
            try:
                with patch.dict(os.environ, environment):
                    # Container runs may use root. The child only executes the
                    # test's tiny Python scripts, never the real deployment CLI.
                    with patch.object(gui.os, "geteuid", return_value=1000):
                        with patch.object(Gio.SubprocessLauncher, "new", Launcher):
                            gui.run_gui(config_path, frontend="fcitx5")
            finally:
                context = GLib.MainContext.default()
                for source_id in (timer, watchdog):
                    source = context.find_source_by_id(source_id)
                    if source:
                        source.destroy()
            if failures:
                raise failures[0]
            self.assertTrue(completed)


if __name__ == "__main__":
    unittest.main()
