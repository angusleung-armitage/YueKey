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
        self.window.attributes('-transparentcolor', '#010203')
        self.canvas = tk.Canvas(self.window, width=36, height=28, bg='#010203',
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
        width, height, gap = round(36 * scale), round(28 * scale), round(6 * scale)
        area = (info.rcWork.left, info.rcWork.top, info.rcWork.right - info.rcWork.left,
                info.rcWork.bottom - info.rcWork.top)
        px, py = indicator_position(target.anchor, area, width, height, gap)
        self._draw(state, level, scale)
        # Physical coordinates also work on monitors left of the primary one.
        self.user.SetWindowPos(self.hwnd, W.HWND(-1), px, py, width, height, 0x10 | 0x40)

    def _draw(self, state, level, scale):
        self.canvas.delete('all')
        green = '#16a34a'
        self.canvas.create_oval(0, 0, 28, 28, fill=green, outline='')
        self.canvas.create_rectangle(14, 0, 22, 28, fill=green, outline='')
        self.canvas.create_oval(8, 0, 36, 28, fill=green, outline='')
        if state == 'recording':
            # Original line microphone, matching the GNOME symbolic drawing.
            self.canvas.create_line(15.4, 9.5, 15.4, 6.9, 18, 6.9, 20.6, 6.9, 20.6, 9.5,
                                    20.6, 13.3, 20.6, 15.9, 18, 15.9, 15.4, 15.9, 15.4, 13.3,
                                    15.4, 9.5, smooth=True, fill='white', width=1.35)
            self.canvas.create_line(13.1, 12.9, 13.1, 14, 13.1, 18.9, 18, 18.9,
                                    22.9, 18.9, 22.9, 14, 22.9, 12.9,
                                    smooth=True, fill='white', width=1.35)
            self.canvas.create_line(18, 18.9, 18, 21.1, fill='white', width=1.35)
            self.canvas.create_line(15.4, 21.1, 20.6, 21.1, fill='white', width=1.35)
            if level > 0:
                high = max(0, min(1, level)) * 5
                self.canvas.create_line(18, 14, 18, 14 - high, fill='#bbf7d0', width=2)
        else:
            for index in range(3):
                self.canvas.create_oval(11 + index * 5.5, 12.5, 14 + index * 5.5, 15.5,
                                        fill='white', outline='')
        self.canvas.scale('all', 0, 0, scale, scale)
        for item in self.canvas.find_all():
            if self.canvas.type(item) == 'line':
                self.canvas.itemconfigure(item, width=float(self.canvas.itemcget(item, 'width')) * scale)

    def hide(self):
        self.user.ShowWindow(self.hwnd, 0)
