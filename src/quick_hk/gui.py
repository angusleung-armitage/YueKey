"""GTK4 settings application; GI is imported only when the GUI is requested."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .settings import Settings, load_settings, save_settings


def run_gui(config_path: Path | None = None, frontend: str = "auto") -> None:
    """Open settings, keeping deployment subprocesses off the GTK main thread."""
    try:
        import gi

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
            self.connect("activate", self._activate)

        def _activate(self, _application) -> None:
            if self.window is not None:
                self.window.present()
                return
            self.window = Gtk.ApplicationWindow(
                application=self,
                title="粵鍵 YueKey",
                default_width=590,
                default_height=710,
            )
            self.window.connect("close-request", self._close_requested)
            header = Gtk.HeaderBar()
            header.set_title_widget(Gtk.Label(label="粵鍵設定 · Settings"))
            self.window.set_titlebar(header)
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.window.set_child(outer)
            scroller = Gtk.ScrolledWindow(
                hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True
            )
            outer.append(scroller)
            content = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=12,
                margin_top=20,
                margin_bottom=20,
                margin_start=24,
                margin_end=24,
            )
            scroller.set_child(content)
            title = Gtk.Label(label="粵鍵 YueKey", xalign=0)
            title.add_css_class("title-1")
            content.append(title)
            intro = Gtk.Label(
                label="Type the first and last Cangjie radicals.\n"
                "取首尾碼輸入；用數字鍵選字，空白鍵確認。",
                xalign=0,
                wrap=True,
            )
            intro.add_css_class("dim-label")
            content.append(intro)
            try:
                settings = load_settings(config_path)
                load_error = None
            except (OSError, ValueError) as exc:
                settings = Settings()
                load_error = str(exc)

            self.form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            content.append(self.form)
            self._heading("候選字 · Candidates")
            self._switch("horizontal", "橫排候選字 · Horizontal layout", settings.horizontal)
            self._number("page_size", "每頁候選字 · Candidates per page", settings.page_size, 1, 9)
            self._number("font_size", "字體大小 · Font size (pt)", settings.font_size, 10, 36)
            self._choice("theme", "外觀 · Appearance", settings.theme, [
                ("light", "淺色 · Light"), ("dark", "深色 · Dark"),
            ])
            self._switch("show_candidates", "輸入時顯示候選字 · Show while typing", settings.show_candidates)
            hint = Gtk.Label(
                label="關閉後，按空白鍵展開候選字。\nWhen off, press Space to open candidates.",
                xalign=0,
                wrap=True,
            )
            hint.add_css_class("dim-label")
            self.form.append(hint)
            self._heading("輸入習慣 · Typing")
            self._switch("learning", "學習選字次序 · Learn candidate choices", settings.learning)
            self._switch("prediction", "顯示關聯字 · Suggest related words", settings.prediction)
            self._switch("ascii_punctuation", "半形標點 · ASCII punctuation", settings.ascii_punctuation)
            self._choice("switch_key", "中英切換鍵 · Chinese / English key", settings.switch_key, [
                ("Shift_L", "左 Shift · Left Shift"),
                ("Shift_R", "右 Shift · Right Shift"),
                ("Control_L", "左 Ctrl · Left Ctrl"),
                ("none", "停用 · Disabled"),
            ])
            self._heading("廣東話語音輸入 · Cantonese dictation")
            from .dictation_setup import microphones, status as speech_status
            speech = speech_status()
            self.speech_hint = Gtk.Label(xalign=0, wrap=True, label=(
                "SenseVoice Small Yue · CPU · 離線\n"
                + ("已準備好 · Double-tap Ctrl to start / stop." if speech['ready']
                   else "首次使用請準備語音模型 · Download models before enabling.")))
            self.speech_hint.add_css_class("dim-label")
            self.form.append(self.speech_hint)
            self._switch("dictation_enabled", "啟用語音輸入 · Enable dictation", settings.dictation_enabled)
            self._choice("dictation_key", "連按兩次 · Double-tap key", settings.dictation_key, [
                ("Control_L", "左 Ctrl · Left Ctrl"), ("Control_R", "右 Ctrl · Right Ctrl"),
            ])
            devices = microphones()
            if settings.dictation_microphone not in {key for key, _ in devices}:
                devices.append((settings.dictation_microphone, settings.dictation_microphone))
            self._choice("dictation_microphone", "麥克風 · Microphone", settings.dictation_microphone, devices)
            self._switch("dictation_punctuation", "自動標點 · Automatic punctuation", settings.dictation_punctuation)
            key_hint = Gtk.Label(xalign=0, wrap=True, label="如左 Ctrl 用作中英切換，語音輸入會使用右 Ctrl。\nIf Left Ctrl switches language, dictation uses Right Ctrl.")
            key_hint.add_css_class("dim-label")
            self.form.append(key_hint)
            setup_button = Gtk.Button(label=("驗證語音模型 · Verify speech models" if speech.get('bundled')
                                              else "準備語音模型 · Set up speech models"))
            setup_button.connect("clicked", lambda *_: self._start_command(
                ["dictation", "setup"], "正在檢查語音模型… · Checking speech models…" if speech.get('bundled')
                else "正在下載及準備語音模型… · Preparing speech models…"))
            self.form.append(setup_button)
            local = Gtk.Label(
                label="所有學習資料保存在這部電腦。\nLearning stays on this computer.",
                xalign=0,
                wrap=True,
            )
            local.add_css_class("dim-label")
            content.append(local)
            outer.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
            footer = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=8,
                margin_start=24,
                margin_end=24,
                margin_top=12,
                margin_bottom=20,
            )
            outer.append(footer)
            self.status = Gtk.Label(xalign=0, wrap=True, selectable=True)
            self.status_scroller = Gtk.ScrolledWindow(
                hscrollbar_policy=Gtk.PolicyType.NEVER,
                max_content_height=120,
                propagate_natural_height=True,
                visible=False,
            )
            self.status_scroller.set_child(self.status)
            footer.append(self.status_scroller)
            actions = Gtk.Box(spacing=12)
            self.reset_button = Gtk.Button(label="重設學習 · Reset learning")
            self.reset_button.connect("clicked", self._reset)
            actions.append(self.reset_button)
            self.spinner = Gtk.Spinner(hexpand=True, halign=Gtk.Align.END)
            actions.append(self.spinner)
            self.apply_button = Gtk.Button(label="儲存並套用 · Apply")
            self.apply_button.add_css_class("suggested-action")
            self.apply_button.connect("clicked", self._apply)
            actions.append(self.apply_button)
            footer.append(actions)
            if load_error:
                self._status(f"Could not load settings: {load_error}\nDefaults are shown; Apply will save them.", error=True)
            self.window.present()

        def _heading(self, text: str) -> None:
            heading = Gtk.Label(label=text, xalign=0, margin_top=14, margin_bottom=3)
            heading.add_css_class("heading")
            self.form.append(heading)

        def _row(self, text: str, widget) -> None:
            row = Gtk.Box(spacing=12)
            label = Gtk.Label(label=text, xalign=0, hexpand=True, wrap=True)
            label.set_mnemonic_widget(widget)
            widget.set_valign(Gtk.Align.CENTER)
            row.append(label)
            row.append(widget)
            self.form.append(row)

        def _switch(self, name: str, text: str, value: bool) -> None:
            control = Gtk.Switch(active=value)
            self.fields[name] = control.get_active
            self._row(text, control)

        def _number(self, name: str, text: str, value: int, low: int, high: int) -> None:
            control = Gtk.SpinButton.new_with_range(low, high, 1)
            control.set_value(value)
            control.set_numeric(True)
            self.fields[name] = control.get_value_as_int
            self._row(text, control)

        def _choice(self, name: str, text: str, value: str, choices: list[tuple[str, str]]) -> None:
            control = Gtk.DropDown.new_from_strings([label for _, label in choices])
            values = [key for key, _ in choices]
            control.set_selected(values.index(value) if value in values else 0)
            self.fields[name] = lambda: values[control.get_selected()]
            self._row(text, control)

        def _status(self, message: str, *, error: bool = False) -> None:
            self.status.set_label(message)
            self.status_scroller.set_visible(bool(message))
            if error:
                self.status.add_css_class("error")
            else:
                self.status.remove_css_class("error")

        def _apply(self, _button) -> None:
            try:
                settings = Settings(**{name: get_value() for name, get_value in self.fields.items()})
                if settings.dictation_enabled:
                    from .dictation_setup import status as speech_status
                    if not speech_status()["ready"]:
                        raise ValueError("Prepare speech models before enabling dictation.")
                save_settings(settings, config_path)
            except (OSError, ValueError) as exc:
                self._status(f"Could not save settings: {exc}", error=True)
                return
            self._start_command(
                ["deploy", "--frontend", frontend],
                "已儲存，正在套用… · Saved; applying…",
            )

        def _reset(self, _button) -> None:
            self._start_command(
                ["reset-learning", "--frontend", frontend],
                "正在備份及重設學習資料… · Backing up and resetting learning…",
            )

        def _start_command(self, arguments: list[str], message: str) -> None:
            if self.process is not None:
                return
            if os.geteuid() == 0:
                self._status("Open YueKey Settings as your desktop user, without sudo.", error=True)
                return
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            )
            if config_path is not None:
                launcher.setenv("QUICK_HK_CONFIG", str(config_path.expanduser().resolve()), True)
            try:
                self.process = launcher.spawnv([sys.executable, "-m", "quick_hk", *arguments])
            except GLib.Error as exc:
                self._status(f"Could not start YueKey: {exc.message}", error=True)
                return
            self._set_busy(True)
            self._status(message)
            self.process.communicate_utf8_async(None, None, self._finished)

        def _finished(self, process, result) -> None:
            try:
                _ok, output, errors = process.communicate_utf8_finish(result)
                detail = "\n".join(part.strip() for part in (output, errors) if part and part.strip())
                if process.get_successful():
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
                from .dictation_setup import status as speech_status
                if speech_status()['ready']:
                    self.speech_hint.set_label("SenseVoice Small Yue · CPU · 離線\n已準備好 · Double-tap Ctrl to start / stop.")

        def _set_busy(self, busy: bool) -> None:
            self.form.set_sensitive(not busy)
            self.apply_button.set_sensitive(not busy)
            self.reset_button.set_sensitive(not busy)
            self.spinner.set_spinning(busy)

        def _close_requested(self, _window) -> bool:
            # Deploy writes several related files. Allow it to complete before
            # dismissing the window so its status remains visible.
            if self.process is not None:
                self._status("正在完成套用，請稍候。 · Please wait for the current operation to finish.")
                return True
            self.window = None
            return False

    SettingsApplication().run([])
