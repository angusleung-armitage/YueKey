"""Read caret geometry without retrieving the text being edited.

Used only on the UI Automation worker, after the existing target checks pass.
SPDX-License-Identifier: MIT
"""
import ctypes as C
from ctypes import wintypes as W

from .dictation_position import valid_rect


class GuiThreadInfo(C.Structure):
    _fields_ = [('cbSize', W.DWORD), ('flags', W.DWORD),
                ('hwndActive', W.HWND), ('hwndFocus', W.HWND),
                ('hwndCapture', W.HWND), ('hwndMenuOwner', W.HWND),
                ('hwndMoveSize', W.HWND), ('hwndCaret', W.HWND), ('rcCaret', W.RECT)]


def enable_dpi_awareness():
    # UIA rectangles are physical pixels. Set this before Tk creates any HWND.
    user = C.WinDLL('user32', use_last_error=True)
    user.SetProcessDpiAwarenessContext.argtypes = [C.c_void_p]
    user.SetProcessDpiAwarenessContext(C.c_void_p(-4))  # Per-monitor v2


class CaretReader:
    def __init__(self, user, module):
        self.user, self.module = user, module
        user.GetGUIThreadInfo.argtypes = [W.DWORD, C.POINTER(GuiThreadInfo)]
        user.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]
        user.GetAncestor.argtypes = [W.HWND, W.UINT]
        user.GetAncestor.restype = W.HWND
        user.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]

    def read(self, element, window):
        # Native Edit/RichEdit controls provide a caret even when the UIA text
        # provider returns no rectangle for its degenerate (empty) caret range.
        info = GuiThreadInfo(cbSize=C.sizeof(GuiThreadInfo))
        thread = self.user.GetWindowThreadProcessId(window, None)
        if (self.user.GetGUIThreadInfo(thread, C.byref(info)) and info.hwndCaret
                and self.user.GetAncestor(info.hwndCaret, 2) == window):
            point = W.POINT(info.rcCaret.left, info.rcCaret.top)
            if self.user.ClientToScreen(info.hwndCaret, C.byref(point)):
                rect = (point.x, point.y, info.rcCaret.right - info.rcCaret.left,
                        info.rcCaret.bottom - info.rcCaret.top)
                if valid_rect(rect):
                    return rect
        try:
            pattern = element.GetCurrentPattern(10024).QueryInterface(self.module.IUIAutomationTextPattern2)
            active, caret = pattern.GetCaretRange()
            if active and caret:
                values = caret.GetBoundingRectangles()
                rect = tuple(values[:4]) if values else None
                if valid_rect(rect):
                    return rect
        except Exception:
            pass  # Not every editable provider implements TextPattern2.
        try:
            bounds = element.CurrentBoundingRectangle
            rect = (bounds.left, bounds.top, bounds.right - bounds.left, bounds.bottom - bounds.top)
            if valid_rect(rect):
                return rect
        except Exception:
            pass
        bounds = W.RECT()
        if self.user.GetWindowRect(window, C.byref(bounds)):
            # Last fallback remains beside the active window, never screen centre.
            return (bounds.left + 16, bounds.bottom - 64, 0, 1)
        return None
