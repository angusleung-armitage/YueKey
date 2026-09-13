"""Windows keyboard/focus adapter. Never records key contents. SPDX-License-Identifier: MIT."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
import queue
import threading
import time

from .windows_state import Target, editable

ULONG_PTR = C.c_size_t
LRESULT = C.c_ssize_t


class KeyboardEvent(C.Structure):
    _fields_ = [('vkCode', W.DWORD), ('scanCode', W.DWORD), ('flags', W.DWORD),
                ('time', W.DWORD), ('dwExtraInfo', ULONG_PTR)]


class KeyInput(C.Structure):
    _fields_ = [('wVk', W.WORD), ('wScan', W.WORD), ('dwFlags', W.DWORD),
                ('time', W.DWORD), ('dwExtraInfo', ULONG_PTR)]


class MouseInput(C.Structure):
    _fields_ = [('dx', W.LONG), ('dy', W.LONG), ('mouseData', W.DWORD),
                ('dwFlags', W.DWORD), ('time', W.DWORD), ('dwExtraInfo', ULONG_PTR)]


class InputUnion(C.Union):
    _fields_ = [('ki', KeyInput), ('mi', MouseInput)]


class Input(C.Structure):
    _anonymous_ = ('data',)
    _fields_ = [('type', W.DWORD), ('data', InputUnion)]


class WindowsInput:
    def __init__(self):
        import comtypes.client  # import on the UI thread; create UIA objects in the MTA worker
        self.automation = None
        self.user = C.WinDLL('user32', use_last_error=True)
        self.kernel = C.WinDLL('kernel32', use_last_error=True)
        self.user.GetForegroundWindow.restype = W.HWND
        self.user.GetParent.argtypes = [W.HWND]
        self.user.GetParent.restype = W.HWND
        self.user.ShowWindow.argtypes = [W.HWND, C.c_int]
        self.user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
        self.user.CallNextHookEx.argtypes = [W.HHOOK, C.c_int, W.WPARAM, W.LPARAM]
        self.user.CallNextHookEx.restype = LRESULT
        self.user.SetWindowsHookExW.argtypes = [C.c_int, C.c_void_p, W.HINSTANCE, W.DWORD]
        self.user.SetWindowsHookExW.restype = W.HHOOK
        self.user.UnhookWindowsHookEx.argtypes = [W.HHOOK]
        self.user.SetWinEventHook.argtypes = [W.DWORD, W.DWORD, W.HMODULE, C.c_void_p, W.DWORD, W.DWORD, W.DWORD]
        self.user.SetWinEventHook.restype = W.HANDLE
        self.user.UnhookWinEvent.argtypes = [W.HANDLE]
        self.user.SendInput.argtypes = [W.UINT, C.POINTER(Input), C.c_int]
        self.user.SendInput.restype = W.UINT
        self.kernel.GetModuleHandleW.argtypes = [W.LPCWSTR]
        self.kernel.GetModuleHandleW.restype = W.HMODULE
        self.events = queue.SimpleQueue()
        self.activity = 0
        self.ready = threading.Event()
        self.error = None
        self.thread_id = None
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        if not self.ready.wait(5) or self.error:
            raise RuntimeError(self.error or 'Windows keyboard listener did not start')
        self.snapshot = (None, 0.0)
        self.stopping = threading.Event()
        self.focus_ready = threading.Event()
        self.focus_thread = threading.Thread(target=self._watch_focus, daemon=True)
        self.focus_thread.start()
        if not self.focus_ready.wait(10) or self.error:
            self.close()
            raise RuntimeError(self.error or 'Windows accessibility service did not start')

    def _listen(self):
        hook_type = C.WINFUNCTYPE(LRESULT, C.c_int, W.WPARAM, W.LPARAM)
        event_type = C.WINFUNCTYPE(None, W.HANDLE, W.DWORD, W.HWND, W.LONG, W.LONG, W.DWORD, W.DWORD)
        hooks, focus_hooks = [], []
        self.thread_id = self.kernel.GetCurrentThreadId()

        @hook_type
        def keyboard(code, message, data):
            if code >= 0:
                event = C.cast(data, C.POINTER(KeyboardEvent)).contents
                if not event.flags & 0x10:  # ignore injected events, including our Unicode output
                    down = message in (0x100, 0x104)
                    if down and event.vkCode not in (0xA2, 0xA3):
                        self.activity += 1
                    # Queue only Ctrl transitions; all other keys become an anonymous cancellation.
                    key = event.vkCode if event.vkCode in (0xA2, 0xA3) else 0
                    self.events.put((key, down, time.monotonic()))
            return self.user.CallNextHookEx(None, code, message, data)

        @hook_type
        def mouse(code, message, data):
            if code >= 0 and message != 0x200:  # mouse movement alone is harmless
                self.activity += 1
            return self.user.CallNextHookEx(None, code, message, data)

        @event_type
        def focus(*_):
            self.activity += 1

        try:
            instance = self.kernel.GetModuleHandleW(None)
            hooks = [self.user.SetWindowsHookExW(13, keyboard, instance, 0),
                     self.user.SetWindowsHookExW(14, mouse, instance, 0)]
            focus_hooks = [self.user.SetWinEventHook(n, n, None, focus, 0, 0, 0)
                           for n in (0x0003, 0x8005)]  # foreground and focused control
            if not all(hooks + focus_hooks):
                raise C.WinError(C.get_last_error())
            self.ready.set()
            message = W.MSG()
            while self.user.GetMessageW(C.byref(message), None, 0, 0) > 0:
                self.user.TranslateMessage(C.byref(message))
                self.user.DispatchMessageW(C.byref(message))
        except Exception as error:
            self.error = str(error)
            self.ready.set()
        finally:
            for hook in hooks:
                if hook:
                    self.user.UnhookWindowsHookEx(hook)
            for hook in focus_hooks:
                if hook:
                    self.user.UnhookWinEvent(hook)

    def _watch_focus(self):
        # UI Automation must run off the UI thread in an MTA apartment. A stuck
        # provider cannot freeze our controls; stale snapshots fail closed.
        import comtypes.client
        comtypes.CoInitializeEx(0)
        try:
            module = comtypes.client.GetModule('UIAutomationCore.dll')
            self.automation = comtypes.client.CreateObject(
                '{ff48dba4-60ef-4201-aa87-54103eef594e}', interface=module.IUIAutomation)
            self.focus_ready.set()
            while not self.stopping.is_set():
                self.snapshot = (self._read_target(), time.monotonic())
                self.stopping.wait(0.05)
        except Exception as error:
            self.error = str(error)
            self.focus_ready.set()
        finally:
            self.automation = None
            comtypes.CoUninitialize()

    def _read_target(self) -> Target | None:
        try:
            generation = self.activity
            window = self.user.GetForegroundWindow()
            element = self.automation.GetFocusedElement()
            if not window or not element or not editable(
                control_type=element.GetCurrentPropertyValueEx(30003, True),
                password=element.GetCurrentPropertyValueEx(30019, True),
                focused=element.GetCurrentPropertyValueEx(30008, True),
                enabled=element.GetCurrentPropertyValueEx(30010, True),
            ):
                return None
            process = W.DWORD()
            self.user.GetWindowThreadProcessId(window, C.byref(process))
            if element.CurrentProcessId != process.value:
                return None
            identifier = tuple(element.GetRuntimeId())
            if not identifier or self.activity != generation:
                return None
            return Target(int(window), process.value, identifier, generation)
        except Exception:
            return None

    def target(self) -> Target | None:
        target, checked = self.snapshot
        if (target is None or time.monotonic() - checked > 0.3
                or target.activity != self.activity
                or target.window != self.user.GetForegroundWindow()):
            return None
        return target

    def modifiers_down(self) -> bool:
        return any(self.user.GetAsyncKeyState(key) & 0x8000
                   for key in (0x10, 0x11, 0x12, 0x5B, 0x5C))

    def insert(self, text: str, target: Target) -> bool:
        if not text or self.modifiers_down() or self.target() != target:
            return False
        units = text.encode('utf-16-le')
        inputs = (Input * len(units))()
        for n in range(0, len(units), 2):
            unit = int.from_bytes(units[n:n + 2], 'little')
            inputs[n] = Input(type=1, ki=KeyInput(wScan=unit, dwFlags=4))
            inputs[n + 1] = Input(type=1, ki=KeyInput(wScan=unit, dwFlags=6))
        # One batch; never retry a partial insertion, which would duplicate text.
        return self.user.SendInput(len(inputs), inputs, C.sizeof(Input)) == len(inputs)

    def close(self):
        self.stopping.set()
        if self.thread_id:
            self.user.PostThreadMessageW(self.thread_id, 0x12, 0, 0)
            self.thread.join(timeout=2)
        self.focus_thread.join(timeout=1)
