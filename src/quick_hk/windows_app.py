"""YueKey Windows setup and local dictation companion. SPDX-License-Identifier: MIT."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace

from .settings import Settings, load_settings, save_settings
from .settings_choices import ACTIONS, LABELS, microphone_choices
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
import uuid
import webbrowser

from .windows_state import DoubleControl, Request


class Application:
    def __init__(self, root):
        import tkinter as tk
        from tkinter import messagebox
        from .windows_input import WindowsInput
        from .windows_setup import data_directory

        self.root, self.messagebox = root, messagebox
        self.backend = WindowsInput()
        self.queue = queue.SimpleQueue()
        self.settings = load_settings()
        self.gesture = DoubleControl(0xA2 if self.settings.effective_dictation_key == "Control_L" else 0xA3)
        self.recognizer = self.recording = self.request = None
        self.enabled = False
        self.loading = False
        self.closed = False
        self.busy = False
        self.models = data_directory() / 'dictation/models'
        self.status = tk.StringVar(value='準備就緒 · Ready')
        self.variables = {}
        from .windows_ui import build_window
        build_window(self, root)
        self.refresh_microphones()
        self.refresh_readiness()
        root.protocol('WM_DELETE_WINDOW', self.close)
        from .windows_overlay import DictationBadge
        self.badge = DictationBadge(root, self.backend.user)
        root.after(20, self.tick)
        if self.settings.dictation_enabled:
            root.after(100, self.enable)

    def set_busy(self, busy):
        self.busy = busy
        for button in (self.setup_button, self.apply_button):
            button.configure(state='disabled' if busy else 'normal')
        for control, state in self.setting_controls:
            control.configure(state='disabled' if busy else state)
        if busy:
            self.progress.grid()
            self.progress.start(15)
        else:
            self.progress.stop()
            self.progress.grid_remove()

    def run_action(self, function, success):
        if self.busy:
            return
        if self.loading:
            self.status.set('請等待語音準備完成後再套用設定。\nWait for voice setup to finish before applying changes.')
            return
        self.cancel()
        self.set_busy(True)
        self.status.set('正在處理… · Working…')

        def work():
            try:
                self.queue.put(dict(event='action-done', result=function(), callback=success))
            except Exception as error:
                self.queue.put(dict(event='action-error', message=str(error)))
        threading.Thread(target=work, daemon=True).start()

    def refresh_readiness(self):
        from .windows_setup import rime_directory
        from .windows_weasel import detect
        try:
            destination = rime_directory()
            self.folder.set(str(destination))
            engine = detect()
            ready = engine and (destination / 'yuekey-install.json').is_file() and (
                destination / 'build/quick_hk.table.bin').is_file()
            self.typing_status.set('已就緒 · Ready to type' if ready else '尚待設定 · Ready to set up')
        except Exception:
            self.typing_status.set('需要修復 · Setup needs attention')
        self.speech_status.set('已啟用 · Ready for dictation' if self.enabled else
                               '準備中… · Preparing…' if self.loading else '未啟用 · Not enabled')

    def setup_typing(self):
        from .windows_weasel import configure_typing
        settings = self.read_settings()

        def work():
            result = configure_typing(settings, lambda text: self.queue.put(dict(event='action-progress', message=text)))
            save_settings(settings)
            return result

        def done(_):
            self.settings = settings
            self.gesture = DoubleControl(0xA2 if settings.effective_dictation_key == 'Control_L' else 0xA3)
            self.refresh_readiness()
            self.status.set('速成已就緒 · Typing is ready. Win + Space → 小狼毫 · 港式速成')
        self.run_action(work, done)

    def open_folder(self):
        folder = Path(self.folder.get())
        if folder.is_dir():
            os.startfile(folder)
        else:
            self.status.set('請先在總覽設定速成。\nChoose Set up typing on Overview first.')

    def open_guide(self):
        webbrowser.open('https://github.com/angusleung-armitage/YueKey/blob/main/docs/WINDOWS.md')

    def remove_typing(self):
        from .windows_setup import uninstall
        from .windows_weasel import detect, deploy
        destination = Path(self.folder.get())

        def work():
            preserved = uninstall(destination)
            engine = detect()
            if engine:
                deploy(engine, destination, require_yuekey=False)
            return preserved

        def done(preserved):
            self.refresh_readiness()
            self.status.set('保留已修改檔案 · Preserved edits: ' + ', '.join(preserved) if preserved
                            else '速成方案已移除；學習資料保留。\nTyping removed; learned words retained.')
        self.run_action(work, done)

    def read_settings(self):
        values = asdict(self.settings)
        values.update({key: variable.get() for key, variable in self.variables.items()})
        for key in ('page_size', 'font_size'):
            values[key] = int(values[key])
        values['dictation_microphone'] = self.microphone_value
        values['dictation_enabled'] = self.enabled or (self.loading and self.settings.dictation_enabled)
        return Settings(**values)

    def select_microphone(self, _=None):
        self.microphone_value = self.devices[self.microphone_combo.current()][0]

    def refresh_microphones(self):
        from .windows_devices import microphones
        try:
            self.devices = microphones()
        except Exception:
            self.devices = [('default', '系統預設 · System default')]
        self.devices = microphone_choices(self.devices, self.microphone_value)
        self.microphone_combo.configure(values=[label for _, label in self.devices])
        self.microphone_combo.current(next(index for index, (value, _) in enumerate(self.devices) if value == self.microphone_value))

    def apply(self):
        from .windows_setup import apply_settings
        from .windows_weasel import detect, deploy
        settings = self.read_settings()
        destination = Path(self.folder.get())

        def work():
            engine = detect()
            if engine and (destination / 'yuekey-install.json').is_file():
                apply_settings(destination, settings)
                deploy(engine, destination)
            save_settings(settings)

        def done(_):
            self.settings = settings
            self.gesture = DoubleControl(0xA2 if settings.effective_dictation_key == 'Control_L' else 0xA3)
            self.refresh_readiness()
            self.status.set('設定已儲存並套用 · Your changes are saved.')
        self.run_action(work, done)

    def reset_learning(self):
        from .windows_setup import reset_learning
        destination = Path(self.folder.get())

        def done(backup):
            self.status.set('學習備份 · Learning backup: ' + str(backup) if backup else '沒有學習資料 · No learned data')
        self.run_action(lambda: reset_learning(destination), done)

    def persist_enabled(self, value):
        settings = replace(self.settings, dictation_enabled=value)
        save_settings(settings)
        self.settings = settings

    def enable(self):
        if self.busy:
            return
        if self.enabled:
            self.enabled = False
            self.cancel()
            self.enable_button.configure(text=LABELS['dictation_enabled'])
            self.status.set('語音已停用 · Dictation disabled')
            self.refresh_readiness()
            try:
                self.persist_enabled(False)
            except (OSError, ValueError) as error:
                self.status.set('語音已停用，未能儲存 · Disabled; could not save: ' + str(error))
            return
        if self.loading:
            return
        if self.recognizer:
            self.activate()
            return
        self.loading = True
        self.refresh_readiness()
        self.enable_button.configure(state='disabled')
        self.status.set('準備語音模型 · Preparing speech models…')

        def load():
            try:
                from .speech_assets import prepare_models
                from .dictation_worker import Recognizer
                prepare_models(self.models, lambda text: self.queue.put({'event': 'setup', 'message': text}))
                recognizer = Recognizer(self.models)
                if recognizer.transcribe_pcm(bytes(32000)):
                    raise RuntimeError('Speech model silence check failed')
                self.queue.put({'event': 'ready', 'recognizer': recognizer})
            except Exception as error:
                self.queue.put({'event': 'setup-error', 'message': str(error)})
        threading.Thread(target=load, daemon=True).start()

    def activate(self):
        try:
            self.persist_enabled(True)
        except (OSError, ValueError) as error:
            self.loading = False
            self.enable_button.configure(state="normal")
            self.status.set(str(error))
            self.refresh_readiness()
            return
        self.enabled = True
        self.loading = False
        self.enable_button.configure(state='normal', text=ACTIONS['disable_dictation'])
        self.status.set('語音已啟用 · Dictation ready · CPU')
        self.refresh_readiness()

    def show(self, text, level=0.0):
        self.status.set(text)
        target = self.backend.target()
        if self.request and target != self.request.target:
            self.badge.hide()
            return
        self.badge.show(target, self.request.state if self.request else 'recording', level)

    def cancel(self):
        if self.recording:
            self.recording.stop(cancel=True)
        self.request = None
        self.badge.hide()

    def toggle(self):
        if self.busy or not self.enabled or self.backend.modifiers_down():
            return
        if self.request:
            if self.request.state == 'recording':
                self.request.state = 'finishing'
                self.recording.stop()
                self.show('正在辨識 · Recognizing…')
            return
        target = self.backend.target()
        if target is None:
            self.status.set('請選擇一般文字欄 · Focus a supported, non-password text field')
            return
        if self.recording and (self.recording.thread.is_alive() or self.recording.reader.is_alive()):
            self.status.set('正在停止上一段錄音 · Previous recording is still stopping')
            return
        from .dictation_worker import WindowsRecording
        identifier = str(uuid.uuid4())
        try:
            self.request = Request(identifier, target)
            self.recording = WindowsRecording(self.recognizer, {
                'id': identifier, 'punctuation': self.settings.dictation_punctuation,
                'microphone': self.settings.dictation_microphone,
            }, self.queue.put)
            self.show('正在收音 · Listening…  Ctrl × 2 / Esc')
        except Exception as error:
            self.request = None
            self.status.set('麥克風錯誤 · Microphone error: ' + str(error))

    def tick(self):
        if self.closed:
            return
        try:
            while True:
                key, down, stamp = self.backend.events.get_nowait()
                if time.monotonic() - stamp > 1:
                    self.gesture.reset()
                elif self.gesture.feed(key, down, stamp):
                    self.toggle()
        except queue.Empty:
            pass
        if self.request and self.backend.target() != self.request.target:
            self.cancel()
            self.status.set('已取消 · Cancelled')
        try:
            while True:
                message = self.queue.get_nowait()
                kind = message['event']
                if kind == 'action-progress':
                    self.status.set(message['message'])
                elif kind == 'action-done':
                    self.set_busy(False)
                    message['callback'](message['result'])
                elif kind == 'action-error':
                    self.set_busy(False)
                    self.refresh_readiness()
                    self.status.set('未能完成，請查看詳情後重試。\nCould not complete setup. Review the details and retry.')
                    self.messagebox.showerror('粵鍵 YueKey', message['message'])
                elif kind == 'setup':
                    self.status.set('下載及驗證語音模型中… · Downloading and verifying voice models…')
                elif kind == 'ready':
                    self.recognizer = message['recognizer']
                    self.activate()
                elif kind == 'setup-error':
                    self.loading = False
                    self.enable_button.configure(state='normal')
                    self.status.set('設定失敗 · Setup failed: ' + message['message'])
                    self.refresh_readiness()
                elif self.request and message.get('id') == self.request.identifier:
                    if kind == 'finishing':
                        self.request.state = 'finishing'
                        self.show('正在辨識 · Recognizing…')
                    elif kind == 'level':
                        level = min(100, max(0, int(message.get('level', 0) * 100)))
                        self.show(f'正在收音 · Listening… {message["elapsed"]:.0f}s · {level}%', level / 100)
                    elif kind == 'error':
                        self.cancel()
                        self.status.set(message['message'])
                    elif kind == 'result':
                        target = self.backend.target()
                        allowed = self.request.consume(message['id'], target)
                        text = message.get('text', '')
                        inserted = allowed and self.backend.insert(text, target)
                        self.request = None
                        self.badge.hide()
                        self.status.set('已輸入 · Inserted' if inserted else '沒有插入文字 · No text inserted')
        except queue.Empty:
            pass
        if self.backend.error:
            self.enabled = False
            self.cancel()
            self.status.set('鍵盤監聽已停止；請重新開啟 · Keyboard listener stopped; restart YueKey')
        self.root.after(50, self.tick)

    def close(self):
        if self.busy:
            self.status.set('請等待設定完成後關閉。\nPlease wait for setup to finish before closing YueKey.')
            return
        self.closed = True
        self.cancel()
        self.backend.close()
        self.root.destroy()


def self_test(report: Path, models: Path | None):
    """Opt-in disposable-runner checks; no microphone is opened."""
    result = {'ok': False}
    root = backend = None
    parent = None
    try:
        from .windows_input import WindowsInput, Input
        from .dictation_worker import Recognizer
        import ctypes
        import comtypes.client
        import sounddevice
        import sherpa_onnx
        import tkinter as tk

        from .windows_caret import enable_dpi_awareness
        enable_dpi_awareness()

        assert ctypes.sizeof(Input) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
        import ssl
        import truststore
        from .speech_assets import https_context
        tls = https_context()
        assert isinstance(tls, truststore.SSLContext)
        assert tls.check_hostname and tls.verify_mode == ssl.CERT_REQUIRED
        result['https_validation'] = 'Windows CryptoAPI'
        if models:
            from .speech_assets import ASR_BASE, download, prepare_models
            import wave
            prepare_models(models)
            recognizer = Recognizer(models)
            assert recognizer.transcribe_pcm(bytes(32000)) == ''
            sample = models.parent / 'public-yue-test.wav'
            download(ASR_BASE + 'test_wavs/yue-0.wav', sample,
                     'd029018f0dcaf6bbd66f1f9c1633dc30846e809f4b698a14b70b0849cf77a266')
            with wave.open(str(sample)) as wav:
                assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) == (16000, 1, 2)
                text = recognizer.transcribe_pcm(wav.readframes(wav.getnframes()))
            assert '企鵝' in text, 'Public Cantonese sample did not decode correctly'
            result['cpu_models'] = True
            result['cantonese_fixture'] = True
        root = tk.Tk()
        root.title('YueKey isolated Windows smoke test')
        root.update()
        app = Application(root)
        backend = app.backend
        root.update()
        assert root.winfo_height() >= root.winfo_reqheight(), 'Setup controls do not fit in the window'
        assert root.winfo_width() >= root.winfo_reqwidth(), 'Setup controls exceed the window width'
        assert set(asdict(Settings())) == set(app.variables) | {'dictation_enabled', 'dictation_microphone'}
        from tkinter import ttk
        from .settings_choices import CHOICES, LABELS
        from .settings import NUMBER_RANGES
        assert set(LABELS) == set(asdict(Settings()))
        controls = [control for control, _state in app.setting_controls]
        for name, variable in app.variables.items():
            previous = variable.get()
            if isinstance(variable, tk.BooleanVar):
                control = next(control for control in controls if isinstance(control, ttk.Checkbutton)
                               and str(control['variable']) == str(variable))
                assert str(control['text']) == LABELS[name]
                control.invoke()
                assert getattr(app.read_settings(), name) == (not previous)
                control.invoke()
            elif name in NUMBER_RANGES:
                control = next(control for control in controls if isinstance(control, ttk.Combobox)
                               and str(control['textvariable']) == str(variable))
                low, high = NUMBER_RANGES[name]
                assert tuple(map(int, control['values'])) == tuple(range(low, high + 1))
                for value in (low, high):
                    control.set(str(value))
                    assert getattr(app.read_settings(), name) == value
                variable.set(previous)
        assert str(app.enable_button['text']) == LABELS['dictation_enabled']
        for name, choices in CHOICES.items():
            labels = tuple(label for _key, label in choices)
            combo = next(control for control, _state in app.setting_controls
                         if isinstance(control, ttk.Combobox) and tuple(control['values']) == labels)
            previous = app.variables[name].get()
            for index, (key, label) in enumerate(choices):
                combo.current(index)
                combo.event_generate('<<ComboboxSelected>>')
                assert app.variables[name].get() == key
                assert getattr(app.read_settings(), name) == key
                assert combo.get() == label
            app.variables[name].set(previous)
        # Exercise every page at the default and minimum window sizes. Capture
        # only this owned window on the disposable CI desktop for visual review.
        result['pages'] = []
        for geometry in (root.geometry().split('+')[0], '860x620'):
            root.geometry(geometry + '+0+0')
            for page, button in app.navigation.items():
                button.invoke()
                root.after(150, root.quit)
                root.mainloop()
                assert app.active_page == page and app.pages[page].winfo_ismapped()
                assert app.apply_button.winfo_rootx() + app.apply_button.winfo_width() <= root.winfo_rootx() + root.winfo_width()
                assert app.apply_button.winfo_rooty() + app.apply_button.winfo_height() <= root.winfo_rooty() + root.winfo_height()
                if os.environ.get('GITHUB_ACTIONS') == 'true':
                    from .windows_visual import capture_window
                    hwnd = backend.user.GetParent(root.winfo_id()) or root.winfo_id()
                    capture_window(hwnd, report.parent / f'ui-{page}-{geometry}.png')
                result['pages'].append(f'{page}-{geometry}')
        app.set_busy(True)
        assert str(app.apply_button['state']) == str(app.setup_button['state']) == 'disabled'
        app.set_busy(False)
        assert str(app.apply_button['state']) == str(app.setup_button['state']) == 'normal'
        original = app.read_settings()
        app.variables['switch_key'].set('Control_L')
        app.variables['page_size'].set('5')
        app.variables['theme'].set('dark')
        chosen = app.read_settings()
        assert chosen.effective_dictation_key == 'Control_R' and chosen.page_size == 5 and chosen.theme == 'dark'
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            from types import SimpleNamespace
            import yaml
            from .windows_setup import rime_directory
            failures = []
            app.messagebox = SimpleNamespace(showerror=lambda title, message: failures.append(message))

            def save_and_check(expected):
                app.apply_button.invoke()
                assert app.busy, 'Saving did not start a background action'
                deadline = time.monotonic() + 200
                while app.busy and time.monotonic() < deadline:
                    root.after(100, root.quit)
                    root.mainloop()
                assert not app.busy and not failures, f'Saving failed: {failures}'
                assert load_settings() == expected, 'Preferences were not persisted'
                compiled = yaml.safe_load((rime_directory() / 'build/quick_hk.schema.yaml').read_text(encoding='utf-8'))
                assert compiled['menu']['page_size'] == expected.page_size
                assert compiled['style']['color_scheme'] == f'yuekey_{expected.theme}'

            save_and_check(chosen)
        for name, variable in app.variables.items():
            variable.set(getattr(original, name))
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            save_and_check(original)
            result['background_save_and_deployment'] = True
        result['settings_controls'] = True
        assert backend.thread.is_alive()
        assert backend.automation is not None
        assert sounddevice.get_portaudio_version()
        assert sounddevice.WasapiSettings(auto_convert=True)
        result['wasapi_conversion_available'] = True
        from ctypes import wintypes as W
        user = backend.user
        user.CreateWindowExW.argtypes = [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD,
                                        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        W.HWND, W.HMENU, W.HINSTANCE, ctypes.c_void_p]
        user.CreateWindowExW.restype = W.HWND
        user.SetFocus.argtypes = [W.HWND]
        user.SetFocus.restype = W.HWND
        user.SetForegroundWindow.argtypes = [W.HWND]
        user.DestroyWindow.argtypes = [W.HWND]
        user.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
        user.IsWindowVisible.argtypes = [W.HWND]
        root.withdraw()
        root.update()
        parent = user.CreateWindowExW(0, 'STATIC', 'YueKey isolated test', 0x10CF0000,
                                      100, 100, 450, 220, None, None, None, None)
        assert parent, 'Could not create isolated Win32 window'
        normal = user.CreateWindowExW(0, 'EDIT', '', 0x50000080, 20, 40, 360, 30, parent, None, None, None)
        password = user.CreateWindowExW(0, 'EDIT', '', 0x500000A0, 20, 90, 360, 30, parent, None, None, None)
        assert normal and password, 'Could not create isolated Edit controls'

        def settle(milliseconds=500):
            # UIA queries the Edit controls on this GUI thread. Sleeping
            # between update() calls stalls those cross-thread requests and
            # can expire the backend's 300 ms freshness guard. Run the real
            # message loop while waiting, just as the installed application does.
            timer = root.after(milliseconds, root.quit)
            try:
                root.mainloop()
            finally:
                root.after_cancel(timer)

        user.ShowWindow(parent, 9)
        activated = bool(user.SetForegroundWindow(parent))
        result['test_activation'] = {'activated': activated}
        if not activated and os.environ.get('GITHUB_ACTIONS') == 'true':
            # Windows 11 restricts programmatic foreground activation. In the
            # disposable CI desktop, click only our verified visible Edit field.
            # Never inject a click if another window covers the target point.
            from .windows_input import MouseInput
            user.SetWindowPos.argtypes = [W.HWND, W.HWND, ctypes.c_int, ctypes.c_int,
                                          ctypes.c_int, ctypes.c_int, W.UINT]
            user.ClientToScreen.argtypes = [W.HWND, ctypes.POINTER(W.POINT)]
            user.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
            user.WindowFromPoint.argtypes = [W.POINT]
            user.WindowFromPoint.restype = W.HWND
            assert user.SetWindowPos(parent, W.HWND(-1), 0, 0, 0, 0, 0x53), 'Could not expose test window'
            point = W.POINT(10, 10)
            assert user.ClientToScreen(normal, ctypes.byref(point))
            assert user.WindowFromPoint(point) == normal, 'Test field is covered; refusing to click'
            assert user.SetCursorPos(point.x, point.y), 'Could not move within the test field'
            clicks = (Input * 2)(Input(type=0, mi=MouseInput(dwFlags=2)),
                                 Input(type=0, mi=MouseInput(dwFlags=4)))
            assert user.SendInput(2, clicks, ctypes.sizeof(Input)) == 2, 'Test click was rejected'
            result['test_activation']['clicked_own_field'] = True
        else:
            user.SetFocus(normal)
        # UIA can report the new field before the asynchronous WinEvent and
        # mouse hooks have delivered all notifications from our setup click.
        # Establish a quiet baseline before testing the overlay; never replace
        # that baseline after showing it, which would hide a focus regression.
        target = None
        started = stable_since = time.monotonic()
        deadline = started + 10
        result['focus_setup'] = []
        while time.monotonic() < deadline:
            settle(10)
            candidate = backend.target()
            candidate = candidate if candidate and candidate.window == parent else None
            if candidate != target:
                stable_since = time.monotonic()
                target = candidate
                result['focus_setup'].append({
                    'elapsed': stable_since - started,
                    'target': asdict(target) if target else None,
                    'activity': backend.activity,
                })
            if target is not None and time.monotonic() - stable_since >= 1:
                break
        else:
            target = None
        result['focus_diagnostic'] = backend.focus_diagnostic
        result['foreground_matches_test_window'] = user.GetForegroundWindow() == parent
        foreground_title = ctypes.create_unicode_buffer(256)
        user.GetWindowTextW(user.GetForegroundWindow(), foreground_title, len(foreground_title))
        result['test_foreground_title'] = foreground_title.value
        result['snapshot_age'] = time.monotonic() - backend.snapshot[1]
        result['activity'] = backend.activity
        assert target is not None, 'UI Automation did not settle on the isolated Edit control'
        assert target.window == parent, 'Accessibility target is not the isolated test window'
        assert target.anchor is not None, 'The isolated Edit control did not report an anchor'

        def check_overlay(stage):
            current = backend.target()
            result['overlay_checks'].append({
                'stage': stage,
                'expected': asdict(target),
                'current': asdict(current) if current else None,
                'snapshot': asdict(backend.snapshot[0]) if backend.snapshot[0] else None,
                'snapshot_age': time.monotonic() - backend.snapshot[1],
                'activity': backend.activity,
                'foreground_matches': user.GetForegroundWindow() == parent,
                'focus_diagnostic': backend.focus_diagnostic,
            })
            assert user.GetForegroundWindow() == parent, f'Dictation overlay stole focus ({stage})'
            assert current == target, f'Dictation overlay invalidated the input field ({stage})'

        result['overlay_checks'] = []
        for cycle in range(5):
            app.show('YueKey test · No microphone is open')
            settle()
            check_overlay(f'show-{cycle + 1}')
            rect = W.RECT()
            assert user.GetWindowRect(app.badge.hwnd, ctypes.byref(rect))
            x, y, w, h = target.anchor
            assert abs((rect.left + rect.right) / 2 - x) <= 2, 'Badge is not centred on the caret'
            assert 0 <= rect.top - (y + h) <= 24, 'Badge is not below the caret'
            assert rect.right - rect.left <= 72, 'Dictation badge is unexpectedly wide'
            if cycle == 0:
                from .windows_visual import capture_window
                capture_window(app.badge.hwnd, report.parent / 'dictation-badge.png')
            app.cancel()
            settle()
            check_overlay(f'hide-{cycle + 1}')
            assert not user.IsWindowVisible(app.badge.hwnd), 'Cancelled badge is still visible'
        assert backend.insert('我，𨋢', target), 'Unicode SendInput failed'
        settle()
        value = ctypes.create_unicode_buffer(100)
        user.GetWindowTextW(normal, value, len(value))
        assert value.value == '我，𨋢', 'Unicode did not reach the isolated control exactly once'
        user.SetFocus(password)
        settle()
        assert backend.target() is None, 'Password control was not rejected'
        assert not backend.insert('forbidden', target), 'Stale target was not rejected'
        result['unicode_and_password_guards'] = True
        from .windows_arch import package_architecture
        result.update(ok=True, input_size=ctypes.sizeof(Input), rime_payload=True,
                      architecture=package_architecture())
        from .windows_setup import resources, FILES
        assert all((resources() / name).is_file() for name in FILES)
    except Exception as error:
        import traceback
        result.update(ok=False, error=str(error), traceback=traceback.format_exc())
    finally:
        if backend:
            backend.close()
        if parent:
            user.DestroyWindow(parent)
        if root:
            root.destroy()
        report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['ok'] else 1


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    os.environ['OMP_NUM_THREADS'] = '4'
    parser = argparse.ArgumentParser(description='粵鍵 YueKey for Windows')
    parser.add_argument('--self-test', type=Path, metavar='REPORT')
    parser.add_argument('--models', type=Path)
    parser.add_argument('--background', action='store_true', help='Start minimized for login startup')
    parser.add_argument('--setup-typing', action='store_true', help='Configure typing after prerequisite installation')
    parser.add_argument('--setup-report', type=Path, help='Write installation result as JSON')
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.self_test, args.models)
    if sys.platform != 'win32':
        raise SystemExit('Use quick-hk on Ubuntu. This companion is for Windows.')
    if args.setup_typing:
        from .windows_setup import data_directory
        from .windows_weasel import configure_typing
        report = args.setup_report or data_directory() / 'setup-report.json'
        try:
            result = configure_typing(install_missing=False)
        except Exception as error:
            result = dict(ok=False, error=str(error))
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2), encoding='utf-8')
        return 0 if result['ok'] else 1
    import ctypes
    from ctypes import wintypes
    import tkinter as tk
    from tkinter import messagebox
    from .windows_caret import enable_dpi_awareness
    enable_dpi_awareness()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel.CreateMutexW(None, False, r'Local\YueKey.Companion')
    root = tk.Tk()
    if not handle or ctypes.get_last_error() == 183:
        messagebox.showinfo('YueKey', '粵鍵已在執行 · YueKey is already running')
        root.destroy()
        return 1
    try:
        Application(root)
        if args.background:
            root.iconify()
        root.mainloop()
    except Exception as error:
        messagebox.showerror('YueKey', str(error))
        return 1
    finally:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)
    return 0
