"""YueKey Windows setup and local dictation companion. SPDX-License-Identifier: MIT."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace

from .settings import Settings, load_settings, save_settings
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
        from tkinter import filedialog, messagebox, ttk
        from .windows_input import WindowsInput
        from .windows_setup import data_directory, install, rime_directory, uninstall

        self.root, self.messagebox = root, messagebox
        self.backend = WindowsInput()
        self.queue = queue.SimpleQueue()
        self.settings = load_settings()
        self.gesture = DoubleControl(0xA2 if self.settings.effective_dictation_key == "Control_L" else 0xA3)
        self.recognizer = self.recording = self.request = None
        self.enabled = False
        self.loading = False
        self.closed = False
        self.models = data_directory() / 'dictation/models'
        self.status = tk.StringVar(value='準備就緒 · Ready')
        self.variables = {}
        root.title('粵鍵 YueKey')
        root.geometry('760x720')
        root.minsize(740, 690)
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='粵鍵 YueKey', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='速成輸入 · 廣東話語音 · CPU only').pack(anchor='w', pady=(0, 12))
        book = ttk.Notebook(frame)
        book.pack(fill='both', expand=True)
        setup, typing, speech = [ttk.Frame(book, padding=16) for _ in range(3)]
        for tab, title in [(setup, '安裝 · Setup'), (typing, '輸入設定 · Typing'), (speech, '語音 · Speech')]:
            book.add(tab, text=title)
        self.folder = tk.StringVar(value=str(rime_directory()))
        ttk.Label(setup, text='小狼毫使用者資料夾 · Weasel user folder').pack(anchor='w')
        ttk.Entry(setup, textvariable=self.folder).pack(fill='x', pady=6)
        ttk.Button(setup, text='選擇資料夾 · Browse', command=lambda: self.folder.set(
            filedialog.askdirectory() or self.folder.get())).pack(anchor='w')
        ttk.Button(setup, text='安裝／更新速成 · Install / Update typing', command=lambda: self.action(
            lambda: install(Path(self.folder.get()), settings=self.read_settings()),
            '已備份並安裝。請在小狼毫選單按「重新部署」，再按 F4 選港式速成。\n'
            'Installed with backup. Choose Weasel → Deploy, then F4 → 港式速成.')).pack(anchor='w', pady=12)
        ttk.Button(setup, text='下載小狼毫 · Get Weasel', command=lambda: webbrowser.open(
            'https://github.com/rime/weasel/releases/tag/0.17.4')).pack(anchor='w')
        ttk.Button(setup, text='移除速成 · Remove typing', command=lambda: self.remove(uninstall)).pack(anchor='w', pady=12)
        ttk.Label(setup, text='試打 hi1 → 我、zb1 → ，、zd1 → 。\nType hi1 → 我, zb1 → ，, zd1 → 。', wraplength=630).pack(anchor='w', pady=8)
        ttk.Label(setup, text='所有學習資料及語音辨識均留在本機。\nLearning and speech recognition stay on this computer.', wraplength=630).pack(anchor='w')

        def check(parent, name, label):
            variable = tk.BooleanVar(value=getattr(self.settings, name))
            self.variables[name] = variable
            ttk.Checkbutton(parent, text=label, variable=variable).pack(anchor='w', pady=4)
        def choice(parent, name, label, values):
            row = ttk.Frame(parent)
            row.pack(fill='x', pady=5)
            ttk.Label(row, text=label).pack(side='left')
            variable = tk.StringVar(value=str(getattr(self.settings, name)))
            self.variables[name] = variable
            combo = ttk.Combobox(row, textvariable=variable, values=values, state='readonly', width=18)
            combo.pack(side='right')
            return combo
        check(typing, 'horizontal', '橫向候選字 · Horizontal candidates')
        choice(typing, 'page_size', '每頁候選字 · Candidates per page', list(range(1, 10)))
        choice(typing, 'font_size', '字體大小 · Font size', list(range(10, 37)))
        choice(typing, 'theme', '主題 · Theme (light 淺色 / dark 深色)', ['light', 'dark'])
        check(typing, 'learning', '學習選字習慣 · Learn candidate choices')
        check(typing, 'prediction', '關聯字建議 · Word continuations')
        check(typing, 'show_candidates', '顯示候選字 · Show candidates')
        check(typing, 'ascii_punctuation', '英文標點 · English punctuation')
        choice(typing, 'switch_key', '中英切換 · Language switch', ['Shift_L', 'Shift_R', 'Control_L', 'none'])
        ttk.Button(typing, text='備份並重設學習 · Back up / Reset learning', command=self.reset_learning).pack(anchor='w', pady=8)
        ttk.Label(typing, text='重設前請先在系統匣退出小狼毫。\nExit Weasel from its tray menu before resetting learning.').pack(anchor='w')
        self.enable_button = ttk.Button(speech, text='啟用語音／下載模型 · Enable dictation / Get models', command=self.enable)
        self.enable_button.pack(anchor='w', pady=8)
        ttk.Label(speech, text='首次下載約 302 MB；之後離線使用。\nFirst use downloads about 302 MB; recognition then works offline.').pack(anchor='w')
        choice(speech, 'dictation_key', '連按兩次 · Double-tap key', ['Control_L', 'Control_R'])
        check(speech, 'dictation_punctuation', '自動標點 · Automatic punctuation')
        self.microphone_value = self.settings.dictation_microphone
        self.microphone = tk.StringVar()
        ttk.Label(speech, text='麥克風 · Microphone').pack(anchor='w', pady=(12, 0))
        self.microphone_combo = ttk.Combobox(speech, textvariable=self.microphone, state='readonly')
        self.microphone_combo.pack(fill='x', pady=6)
        self.microphone_combo.bind('<<ComboboxSelected>>', self.select_microphone)
        ttk.Button(speech, text='重新整理麥克風 · Refresh microphones', command=self.refresh_microphones).pack(anchor='w')
        self.refresh_microphones()
        ttk.Label(speech, wraplength=620, text='如左 Ctrl 用作中英切換，語音會使用右 Ctrl。\nIf Left Ctrl switches language, dictation uses Right Ctrl.\n\n連按兩次 Ctrl 開始／停止；Esc 取消。\nDouble Ctrl starts/stops; Esc cancels.\n\n保持程式開啟，可縮小視窗。下次開啟會記住語音狀態。\nKeep YueKey running; minimizing is fine. Speech enablement is remembered.').pack(anchor='w', pady=12)
        ttk.Button(frame, text='儲存並套用 · Save / Apply', command=self.apply).pack(anchor='e', pady=10)
        ttk.Label(frame, textvariable=self.status, wraplength=690).pack(anchor='w')
        root.protocol('WM_DELETE_WINDOW', self.close)
        # A non-activating status window: showing it must not steal the target field.
        self.overlay = tk.Toplevel(root)
        self.overlay.withdraw()
        self.overlay.overrideredirect(True)
        self.overlay.attributes('-topmost', True)
        self.overlay.geometry(f'400x60+{max(0, root.winfo_screenwidth() // 2 - 200)}+40')
        tk.Label(self.overlay, textvariable=self.status, bg='#173f3a', fg='white',
                 font=('Segoe UI', 11), wraplength=380).pack(fill='both', expand=True)
        self.overlay.update_idletasks()
        self.overlay_id = self.backend.user.GetParent(self.overlay.winfo_id()) or self.overlay.winfo_id()
        root.after(20, self.tick)
        if self.settings.dictation_enabled:
            root.after(100, self.enable)

    def action(self, function, message):
        try:
            function()
            self.messagebox.showinfo('YueKey', message)
        except Exception as error:
            self.messagebox.showerror('YueKey', str(error))

    def remove(self, function):
        def work():
            preserved = function(Path(self.folder.get()))
            self.status.set('保留已修改檔案 · Preserved edits: ' + ', '.join(preserved) if preserved else '已移除；學習資料保留 · Removed; learned data retained')
        self.action(work, '請在小狼毫選單按「重新部署」。\nChoose Weasel → Deploy to apply the change.')

    def read_settings(self):
        values = asdict(self.settings)
        values.update({key: variable.get() for key, variable in self.variables.items()})
        for key in ('page_size', 'font_size'):
            values[key] = int(values[key])
        values['dictation_microphone'] = self.microphone_value
        values['dictation_enabled'] = self.enabled
        return Settings(**values)

    def select_microphone(self, _=None):
        self.microphone_value = self.devices[self.microphone_combo.current()][0]

    def refresh_microphones(self):
        from .windows_devices import microphones
        try:
            self.devices = microphones()
        except Exception:
            self.devices = [('default', '系統預設 · System default')]
        if self.microphone_value not in {value for value, _ in self.devices}:
            self.devices.append((self.microphone_value, '未連接 · Unavailable: ' + self.microphone_value))
        self.microphone_combo.configure(values=[label for _, label in self.devices])
        self.microphone_combo.current(next(index for index, (value, _) in enumerate(self.devices) if value == self.microphone_value))

    def apply(self):
        def work():
            from .windows_setup import apply_settings
            settings = self.read_settings()
            self.cancel()
            apply_settings(Path(self.folder.get()), settings)
            save_settings(settings)
            self.settings = settings
            self.gesture = DoubleControl(0xA2 if settings.effective_dictation_key == 'Control_L' else 0xA3)
        self.action(work, '設定已儲存。請在小狼毫選單按「重新部署」。\nSettings saved. Choose Weasel → Deploy to apply typing changes.')

    def reset_learning(self):
        def work():
            from .windows_setup import reset_learning
            self.cancel()
            backup = reset_learning(Path(self.folder.get()))
            self.status.set('學習備份 · Learning backup: ' + str(backup) if backup else '沒有學習資料 · No learned data')
        self.action(work, '重設完成；原有學習資料已備份。請重新開啟小狼毫。\nReset complete; existing learning was backed up. Start Weasel again.')

    def persist_enabled(self, value):
        settings = replace(self.settings, dictation_enabled=value)
        save_settings(settings)
        self.settings = settings

    def enable(self):
        if self.enabled:
            self.persist_enabled(False)
            self.enabled = False
            self.cancel()
            self.enable_button.configure(text='啟用語音 · Enable dictation')
            self.status.set('語音已停用 · Dictation disabled')
            return
        if self.loading:
            return
        if self.recognizer:
            self.activate()
            return
        self.loading = True
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
            return
        self.enabled = True
        self.loading = False
        self.enable_button.configure(state='normal', text='停用語音 · Disable dictation')
        self.status.set('語音已啟用 · Dictation ready · CPU')

    def show(self, text):
        self.status.set(text)
        self.backend.user.ShowWindow(self.overlay_id, 4)  # SW_SHOWNOACTIVATE

    def cancel(self):
        if self.recording:
            self.recording.stop(cancel=True)
        self.request = None
        self.backend.user.ShowWindow(self.overlay_id, 0)

    def toggle(self):
        if not self.enabled or self.backend.modifiers_down():
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
                if kind == 'setup':
                    self.status.set(message['message'])
                elif kind == 'ready':
                    self.recognizer = message['recognizer']
                    self.activate()
                elif kind == 'setup-error':
                    self.loading = False
                    self.enable_button.configure(state='normal')
                    self.status.set('設定失敗 · Setup failed: ' + message['message'])
                elif self.request and message.get('id') == self.request.identifier:
                    if kind == 'finishing':
                        self.request.state = 'finishing'
                        self.show('正在辨識 · Recognizing…')
                    elif kind == 'level':
                        level = min(100, max(0, int(message.get('level', 0) * 100)))
                        self.show(f'正在收音 · Listening… {message["elapsed"]:.0f}s · {level}%')
                    elif kind == 'error':
                        self.cancel()
                        self.status.set(message['message'])
                    elif kind == 'result':
                        target = self.backend.target()
                        allowed = self.request.consume(message['id'], target)
                        text = message.get('text', '')
                        inserted = allowed and self.backend.insert(text, target)
                        self.request = None
                        self.backend.user.ShowWindow(self.overlay_id, 0)
                        self.status.set('已輸入 · Inserted' if inserted else '沒有插入文字 · No text inserted')
        except queue.Empty:
            pass
        if self.backend.error:
            self.enabled = False
            self.cancel()
            self.status.set('鍵盤監聽已停止；請重新開啟 · Keyboard listener stopped; restart YueKey')
        self.root.after(50, self.tick)

    def close(self):
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

        assert ctypes.sizeof(Input) == 40
        root = tk.Tk()
        root.title('YueKey isolated Windows smoke test')
        root.update()
        app = Application(root)
        backend = app.backend
        root.update()
        assert root.winfo_height() >= root.winfo_reqheight(), 'Setup controls do not fit in the window'
        assert backend.thread.is_alive()
        assert backend.automation is not None
        assert sounddevice.get_portaudio_version()
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
        root.withdraw()
        root.update()
        parent = user.CreateWindowExW(0, 'STATIC', 'YueKey isolated test', 0x10CF0000,
                                      100, 100, 450, 220, None, None, None, None)
        assert parent, 'Could not create isolated Win32 window'
        normal = user.CreateWindowExW(0, 'EDIT', '', 0x50000080, 20, 40, 360, 30, parent, None, None, None)
        password = user.CreateWindowExW(0, 'EDIT', '', 0x500000A0, 20, 90, 360, 30, parent, None, None, None)
        assert normal and password, 'Could not create isolated Edit controls'

        def settle():
            for _ in range(20):
                root.update()
                time.sleep(0.025)

        user.SetForegroundWindow(parent)
        user.SetFocus(normal)
        target = None
        deadline = time.monotonic() + 5
        while target is None and time.monotonic() < deadline:
            root.update()
            time.sleep(0.01)
            target = backend.target()
        result['focus_diagnostic'] = backend.focus_diagnostic
        result['foreground_matches_test_window'] = user.GetForegroundWindow() == parent
        result['snapshot_age'] = time.monotonic() - backend.snapshot[1]
        result['activity'] = backend.activity
        assert target is not None, 'UI Automation did not identify the isolated Edit control'
        app.show('YueKey test · No microphone is open')
        settle()
        assert user.GetForegroundWindow() == parent, 'Dictation overlay stole focus'
        assert backend.target() == target, 'Dictation overlay invalidated the input field'
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
        result.update(ok=True, input_size=ctypes.sizeof(Input), rime_payload=True)
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
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.self_test, args.models)
    if sys.platform != 'win32':
        raise SystemExit('Use quick-hk on Ubuntu. This companion is for Windows.')
    import ctypes
    from ctypes import wintypes
    import tkinter as tk
    from tkinter import messagebox
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
