#!/usr/bin/env python3
"""Check the installed Weasel server on disposable Windows CI, without typing into apps.

The pinned Weasel 0.17.4 named-pipe protocol carries test-session keys and the
same preedit response consumed by its TSF client. Candidate geometry comes from
the server's actual window. See upstream include/WeaselIPC.h and PipeChannel.h.
"""
import ctypes as C
from ctypes import wintypes as W
from dataclasses import replace
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time


class Client:
    def __init__(self, client_type='tsf'):
        self.kernel = k = C.WinDLL('kernel32', use_last_error=True)
        k.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, C.c_void_p, W.DWORD, W.DWORD, W.HANDLE]
        k.CreateFileW.restype = W.HANDLE
        k.CloseHandle.argtypes = [W.HANDLE]
        k.SetNamedPipeHandleState.argtypes = [W.HANDLE, C.POINTER(W.DWORD), C.c_void_p, C.c_void_p]
        k.GetNamedPipeServerProcessId.argtypes = [W.HANDLE, C.POINTER(W.DWORD)]
        k.PeekNamedPipe.argtypes = [W.HANDLE, C.c_void_p, W.DWORD, C.c_void_p, C.POINTER(W.DWORD), C.c_void_p]
        for name in ('ReadFile', 'WriteFile'):
            getattr(k, name).argtypes = [W.HANDLE, C.c_void_p, W.DWORD, C.POINTER(W.DWORD), C.c_void_p]
        advapi = C.WinDLL('advapi32', use_last_error=True)
        advapi.GetUserNameW.argtypes = [W.LPWSTR, C.POINTER(W.DWORD)]
        name, length = C.create_unicode_buffer(256), W.DWORD(256)
        assert advapi.GetUserNameW(name, C.byref(length))
        pipe = '\\\\.\\pipe\\' + name.value + '\\WeaselNamedPipe'
        self.session = 0
        deadline = time.monotonic() + 15
        while True:
            self.handle = k.CreateFileW(pipe, 0xC0000000, 0, None, 3, 0, None)
            if self.handle != W.HANDLE(-1).value:
                break
            if time.monotonic() >= deadline:
                raise C.WinError(C.get_last_error())
            time.sleep(.1)
        mode = W.DWORD(2)  # PIPE_READMODE_MESSAGE
        assert k.SetNamedPipeHandleState(self.handle, C.byref(mode), None, None)
        pid = W.DWORD()
        assert k.GetNamedPipeServerProcessId(self.handle, C.byref(pid))
        self.pid = pid.value
        self.session, response = self.send(2, body=(
            f'action=session\nsession.client_app=yuekey-ci.exe\nsession.client_type={client_type}\n.\n'))
        assert self.session and response.get('status.schema_id') == 'quick_hk', response
        assert response.get('config.inline_preedit') == '1', response
        self.send(6)  # FocusIn
        self.send(8, (22 << 24) | (160 << 12) | 180)  # Input position

    def send(self, command, value=0, body=''):
        request = struct.pack('<III', 0x8000 + command, value, self.session)
        if body:
            request = (request + body.encode('utf-16-le') + b'\0\0').ljust(65536, b'\0')
        count = W.DWORD()
        assert self.kernel.WriteFile(self.handle, request, len(request), C.byref(count), None)
        assert count.value == len(request)
        available = W.DWORD()
        deadline = time.monotonic() + 15
        while True:
            assert self.kernel.PeekNamedPipe(self.handle, None, 0, None, C.byref(available), None)
            if available.value:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('Weasel did not answer the isolated test session')
            time.sleep(.02)
        buffer = C.create_string_buffer(65536)
        assert self.kernel.ReadFile(self.handle, buffer, len(buffer), C.byref(count), None)
        assert count.value >= 4
        result = struct.unpack_from('<I', buffer.raw)[0]
        text = buffer.raw[4:count.value].decode('utf-16-le').split('\0', 1)[0]
        response = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
        return result, response

    def key(self, value):
        return self.send(4, ord(value) if isinstance(value, str) else value)[1]

    def close(self):
        try:
            if self.session:
                self.send(3)
        finally:
            self.kernel.CloseHandle(self.handle)


def candidate_window(pid):
    user = C.WinDLL('user32', use_last_error=True)
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    user.EnumWindows.argtypes = [callback_type, W.LPARAM]
    user.IsWindowVisible.argtypes = [W.HWND]
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    found = []

    @callback_type
    def visit(hwnd, _):
        owner, rect = W.DWORD(), W.RECT()
        user.GetWindowThreadProcessId(hwnd, C.byref(owner))
        if owner.value == pid and user.IsWindowVisible(hwnd) and user.GetWindowRect(hwnd, C.byref(rect)):
            width, height = rect.right - rect.left, rect.bottom - rect.top
            if width > 50 and height > 30:
                found.append((width * height, hwnd, width, height))
        return True

    deadline = time.monotonic() + 5
    while not found and time.monotonic() < deadline:
        user.EnumWindows(visit, 0)
        time.sleep(.05)
    assert found, 'The installed Weasel server did not show its candidate window'
    return max(found)[1:]


def exercise(engine, directory: Path, output: Path):
    if sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Only run on the disposable Windows installer-test runner')
    from quick_hk.settings import load_settings
    from quick_hk.windows_setup import apply_settings
    from quick_hk.windows_weasel import deploy
    from quick_hk.windows_visual import capture_window
    original = load_settings()
    result = []
    try:
        for horizontal in (True, False, True):
            settings = replace(original, horizontal=horizontal, page_size=9,
                               show_candidates=True, prediction=True)
            apply_settings(directory, settings)
            deploy(engine, directory)
            subprocess.Popen([str(engine.root / 'WeaselServer.exe')], cwd=engine.root,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
            client = Client()
            try:
                client.key('h')
                typed = client.key('i')
                assert typed.get('ctx.preedit') == '我', typed
                predicted = client.key('1')
                assert predicted.get('commit') == '我', predicted
                assert predicted.get('status.composing') == '1', predicted
                assert predicted.get('ctx.preedit') == '同', predicted
                cancelled = client.key(0xff1b)
                assert not cancelled.get('commit') and cancelled.get('status.composing') == '0', cancelled
                client.key('h'); client.key('i'); client.key('1')
                accepted = client.key('1')
                assert accepted.get('commit') == '同', accepted
                assert accepted.get('status.composing') == '0', accepted
                client.key('h'); client.key('i'); client.key('1')
                new_code = client.key('v')
                assert not new_code.get('commit'), new_code
                client.key(0xff1b)
            finally:
                client.close()
            # TSF hosts the candidate UI inside the client process. The IME
            # session uses the same WeaselUI renderer inside WeaselServer,
            # allowing geometry checks without injecting keys into an app.
            client = Client('ime')
            try:
                client.key('h'); client.key('i')
                hwnd, width, height = candidate_window(client.pid)
                assert (width > height) == horizontal, (horizontal, width, height)
                capture_window(hwnd, output / f'candidates-{len(result)}.png', expected_pid=client.pid)
                client.key(0xff1b)
                result.append(dict(horizontal=horizontal, width=width, height=height,
                                   preview=predicted['ctx.preedit']))
            finally:
                client.close()
    finally:
        apply_settings(directory, original)
        deploy(engine, directory)
    (output / 'candidate-ui.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS installed Weasel: horizontal/vertical candidates, inline prediction preview, confirm and cancel', flush=True)
