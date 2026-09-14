"""GTK4 settings application; GI is imported only when the GUI is requested."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .settings import Settings, load_settings, save_settings
from .settings_choices import ACTIONS, LABELS, microphone_choices


def run_gui(config_path: Path | None = None, frontend: str = "auto") -> None:
    """Open settings, keeping deployment subprocesses off the GTK main thread."""
    try:
        import gi

        # Gtk.Application owns initialization. Import-time legacy initialization
        # can cache a failed display check before application startup on ARM64.
        gi.disable_legacy_autoinit()
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gio, GLib, Gtk
    except (ImportError, ValueError) as exc:
        raise RuntimeError(
            "The settings window needs python3-gi and gir1.2-gtk-4.0. "
            "Install those Ubuntu packages, then use /usr/bin/python3."
        ) from exc

    class SettingsApplication(Gtk.Application):
        def __init__(self) -> None:
            super().__init__(
                application_id="org.quick_hk.Settings",
                flags=Gio.ApplicationFlags.NON_UNIQUE,
            )
            self.window = None
            self.process = None
            self.fields = {}
            self.controls = {}
            self.choice_values = {}
            self.connect("activate", self._activate)

        def _activate(self, _application) -> None:
            if self.window is not None:
                self.window.present()
                return
            self.window = Gtk.ApplicationWindow(
                application=self,
                title="粵鍵 YueKey",
            )
            self.window.connect("close-request", self._close_requested)
            try:
                settings = load_settings(config_path)
                load_error = None
            except (OSError, ValueError) as exc:
                settings = Settings()
                load_error = str(exc)
            from .deployment import resolve_frontends
            from .gtk_ui import build_window
            self.frontend = frontend
            self.frontends = resolve_frontends(frontend)
            self.dictation_enabled = settings.dictation_enabled
            self.pending_enable = False
            build_window(self, settings)
            self._refresh_readiness()
            if load_error:
                self._status(f"Could not load settings: {load_error}\nDefaults are shown; Save changes will save them.", error=True)
            self.window.present()

        def _refresh_microphones(self, _button) -> None:
            from .dictation_setup import microphones
            name = "dictation_microphone"
            selected = self.fields[name]()
            choices = microphone_choices(microphones(), selected)
            self.choice_values[name] = [value for value, _label in choices]
            self.controls[name].set_model(Gtk.StringList.new([label for _value, label in choices]))
            self.controls[name].set_selected(self.choice_values[name].index(selected))

        def _status(self, message: str, *, error: bool = False) -> None:
            self.status.set_label(message)
            self.status_scroller.set_visible(bool(message))
            if error:
                self.status.add_css_class("error")
            else:
                self.status.remove_css_class("error")

        def _setup_typing(self, _button) -> None:
            self._apply(_button, command="setup")

        def _toggle_dictation(self, _button) -> None:
            if self.process is not None:
                return
            from .dictation_setup import status as speech_status
            if not self.dictation_enabled and not speech_status()['ready']:
                self.pending_enable = self._start_command(
                    ["dictation", "setup"], "正在準備語音模型… · Preparing speech models…")
            else:
                self._apply(_button, enabled=not self.dictation_enabled)

        def _apply(self, _button, *, command="deploy", enabled=None) -> None:
            if self.process is not None:
                return
            try:
                values = {name: get_value() for name, get_value in self.fields.items()}
                if enabled is not None:
                    values['dictation_enabled'] = enabled
                settings = Settings(**values)
                if settings.dictation_enabled:
                    from .dictation_setup import status as speech_status
                    if not speech_status()["ready"]:
                        raise ValueError("Prepare speech models before enabling dictation.")
                save_settings(settings, config_path)
                self.dictation_enabled = settings.dictation_enabled
            except (OSError, ValueError) as exc:
                self._status(f"Could not save settings: {exc}", error=True)
                return
            self._start_command(
                [command, "--frontend", frontend],
                "已儲存，正在套用… · Saved; applying…",
            )

        def _reset(self, _button) -> None:
            self._start_command(
                ["reset-learning", "--frontend", frontend],
                "正在備份及重設學習資料… · Backing up and resetting learning…",
            )

        def _start_command(self, arguments: list[str], message: str) -> bool:
            if self.process is not None:
                return False
            if os.geteuid() == 0:
                self._status("Open YueKey Settings as your desktop user, without sudo.", error=True)
                return False
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            )
            if config_path is not None:
                launcher.setenv("QUICK_HK_CONFIG", str(config_path.expanduser().resolve()), True)
            try:
                self.process = launcher.spawnv([sys.executable, "-m", "quick_hk", *arguments])
            except GLib.Error as exc:
                self._status(f"Could not start YueKey: {exc.message}", error=True)
                return False
            self._set_busy(True)
            self._status(message)
            self.process.communicate_utf8_async(None, None, self._finished)
            return True

        def _finished(self, process, result) -> None:
            succeeded = False
            try:
                _ok, output, errors = process.communicate_utf8_finish(result)
                detail = "\n".join(part.strip() for part in (output, errors) if part and part.strip())
                succeeded = process.get_successful()
                if succeeded:
                    self._status(detail or "完成 · Done")
                else:
                    self._status(
                        "YueKey could not finish. Settings remain saved.\n" + (detail or "See quick-hk doctor for details."),
                        error=True,
                    )
            except GLib.Error as exc:
                self._status(f"Could not read YueKey result: {exc.message}", error=True)
            finally:
                self.process = None
                self._set_busy(False)
                self._refresh_readiness()
                enable = self.pending_enable and succeeded
                self.pending_enable = False
                if enable:
                    self._apply(None, enabled=True)

        def _refresh_readiness(self) -> None:
            from .deployment import frontend_directory, state_home
            from .dictation_setup import status as speech_status
            from .dictation_service import live_status
            ready = all((state_home() / f"{name}.json").is_file() and
                        (frontend_directory(name) / "build/quick_hk.schema.yaml").is_file()
                        for name in self.frontends)
            self.typing_status.set_label("已就緒 · Ready to type" if ready else "尚待設定 · Ready to set up")
            speech = speech_status()
            if not speech['ready']:
                text = "模型尚未準備 · Models need setup"
            elif not self.dictation_enabled:
                text = "未啟用 · Not enabled"
            else:
                service = live_status()
                ready = all(service.get(key) for key in ('ready', 'desktop_ready', 'rime_ready'))
                text = "已啟用 · Ready for dictation" if ready else "已啟用 · Reload the input method"
            for widget in self.readiness_labels:
                widget.set_label(text)
            self.enable_button.set_label(ACTIONS['disable_dictation'] if self.dictation_enabled
                                         else LABELS['dictation_enabled'])
            self._refresh_extension_hint()

        def _open_folder(self, path) -> None:
            if not path.is_dir():
                self._status("請先在總覽設定速成。 · Choose Set up typing on Overview first.")
                return
            self._open_uri(path.as_uri())

        def _open_guide(self, _button) -> None:
            self._open_uri("https://github.com/angusleung200/YueKey/blob/main/docs/INSTALL.md")

        def _open_uri(self, uri) -> None:
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
            except GLib.Error as exc:
                self._status(f"未能開啟 · Could not open: {exc.message}", error=True)

        def _refresh_extension_hint(self) -> None:
            from .dictation_service import gnome_extension_status
            self.extension_hint.set_visible(bool(gnome_extension_status().get('update_pending')))

        def _set_busy(self, busy: bool) -> None:
            self.form.set_sensitive(not busy)
            self.apply_button.set_sensitive(not busy)
            self.reset_button.set_sensitive(not busy)
            self.setup_button.set_sensitive(not busy)
            self.enable_button.set_sensitive(not busy)
            self.spinner.set_spinning(busy)

        def _close_requested(self, _window) -> bool:
            # Deploy writes several related files. Allow it to complete before
            # dismissing the window so its status remains visible.
            if self.process is not None:
                self._status("正在完成套用，請稍候。 · Please wait for the current operation to finish.")
                return True
            Gtk.StyleContext.remove_provider_for_display(self.window.get_display(), self.css_provider)
            self.window = None
            return False

    SettingsApplication().run([])
