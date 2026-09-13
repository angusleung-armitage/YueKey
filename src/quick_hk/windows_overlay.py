"""Small non-activating dictation badge. SPDX-License-Identifier: MIT."""
import ctypes as C
from ctypes import wintypes as W

from .dictation_position import indicator_position, valid_rect


class MonitorInfo(C.Structure):
    _fields_ = [('cbSize', W.DWORD), ('rcMonitor', W.RECT), ('rcWork', W.RECT), ('dwFlags', W.DWORD)]


class DictationBadge:
    def __init__(self, root, user):
        import tkinter as tk
        self.user = user
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.canvas = tk.Canvas(self.window, width=56, height=38, bg='#173f3a',
                                highlightthickness=0, takefocus=False)
        self.canvas.pack(fill='both', expand=True)
        self.window.update_idletasks()
        self.hwnd = user.GetParent(self.window.winfo_id()) or self.window.winfo_id()
        # Non-activating and click-through, including an accidental mouse click.
        get_long = user.GetWindowLongPtrW if C.sizeof(C.c_void_p) == 8 else user.GetWindowLongW
        set_long = user.SetWindowLongPtrW if C.sizeof(C.c_void_p) == 8 else user.SetWindowLongW
        get_long.argtypes, get_long.restype = [W.HWND, C.c_int], C.c_ssize_t
        set_long.argtypes, set_long.restype = [W.HWND, C.c_int, C.c_ssize_t], C.c_ssize_t
        set_long(self.hwnd, -20, get_long(self.hwnd, -20) | 0x08000000 | 0x80 | 0x20)
        user.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT]
        user.MonitorFromRect.argtypes = [C.POINTER(W.RECT), W.DWORD]
        user.MonitorFromRect.restype = W.HMONITOR
        user.GetMonitorInfoW.argtypes = [W.HMONITOR, C.POINTER(MonitorInfo)]
        user.GetDpiForWindow.argtypes, user.GetDpiForWindow.restype = [W.HWND], W.UINT

    def show(self, target, state='recording', level=0.0):
        if target is None or not valid_rect(target.anchor):
            self.hide()
            return
        x, y, w, h = target.anchor
        self.window.title('粵鍵 · 收音 Listening' if state == 'recording' else '粵鍵 · 辨識 Recognizing')
        anchor = W.RECT(round(x), round(y), round(x + w), round(y + h))
        monitor = self.user.MonitorFromRect(C.byref(anchor), 2)
        info = MonitorInfo(cbSize=C.sizeof(MonitorInfo))
        if not self.user.GetMonitorInfoW(monitor, C.byref(info)):
            self.hide()
            return
        scale = max(1.0, self.user.GetDpiForWindow(target.window) / 96)
        width, height, gap = round(56 * scale), round(38 * scale), round(8 * scale)
        area = (info.rcWork.left, info.rcWork.top, info.rcWork.right - info.rcWork.left,
                info.rcWork.bottom - info.rcWork.top)
        px, py = indicator_position(target.anchor, area, width, height, gap)
        self.canvas.delete('all')
        color = '#78e0c2' if state == 'recording' else '#ffffff'
        self.canvas.create_oval(17, 7, 27, 22, fill=color, outline=color)
        self.canvas.create_arc(12, 12, 32, 28, start=180, extent=180,
                               style='arc', outline=color, width=2)
        self.canvas.create_line(22, 27, 22, 31, fill=color, width=2)
        self.canvas.create_line(17, 31, 27, 31, fill=color, width=2)
        if state == 'recording':
            for index in range(3):
                high = 4 + max(0, min(1, level)) * (10 + index * 4)
                self.canvas.create_line(39 + index * 4, 27, 39 + index * 4, 27 - high,
                                        fill=color, width=2)
        else:
            for index in range(3):
                self.canvas.create_oval(36 + index * 5, 19, 38 + index * 5, 21, fill=color, outline=color)
        self.canvas.scale('all', 0, 0, scale, scale)
        # Physical coordinates also work on monitors left of the primary one;
        # Tk's negative geometry offsets would mean distance from the right edge.
        self.user.SetWindowPos(self.hwnd, W.HWND(-1), px, py, width, height, 0x10 | 0x40)

    def hide(self):
        self.user.ShowWindow(self.hwnd, 0)
