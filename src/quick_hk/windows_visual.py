"""Capture only YueKey's own window for disposable-runner visual diagnostics.

SPDX-License-Identifier: MIT
"""
import ctypes as C
from ctypes import wintypes as W
import os
import struct
import zlib


def capture_window(hwnd, destination):
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Visual diagnostics are restricted to disposable CI runners')
    user = C.WinDLL('user32', use_last_error=True)
    gdi = C.WinDLL('gdi32', use_last_error=True)
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.GetWindowDC.argtypes = [W.HWND]
    user.GetWindowDC.restype = W.HDC
    user.ReleaseDC.argtypes = [W.HWND, W.HDC]
    user.PrintWindow.argtypes = [W.HWND, W.HDC, W.UINT]
    gdi.CreateCompatibleDC.argtypes = [W.HDC]
    gdi.CreateCompatibleDC.restype = W.HDC
    gdi.CreateCompatibleBitmap.argtypes = [W.HDC, C.c_int, C.c_int]
    gdi.CreateCompatibleBitmap.restype = W.HBITMAP
    gdi.SelectObject.argtypes = [W.HDC, W.HANDLE]
    gdi.SelectObject.restype = W.HANDLE
    gdi.DeleteObject.argtypes = [W.HANDLE]
    gdi.DeleteDC.argtypes = [W.HDC]
    gdi.GetDIBits.argtypes = [W.HDC, W.HBITMAP, W.UINT, W.UINT, C.c_void_p, C.c_void_p, W.UINT]
    process = W.DWORD()
    user.GetWindowThreadProcessId(hwnd, C.byref(process))
    assert process.value == os.getpid(), 'Refusing to capture another application'
    rect = W.RECT()
    assert user.GetWindowRect(hwnd, C.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    dc = user.GetWindowDC(hwnd)
    memory = bitmap = previous = None
    try:
        assert dc
        memory = gdi.CreateCompatibleDC(dc)
        bitmap = gdi.CreateCompatibleBitmap(dc, width, height)
        assert memory and bitmap
        previous = gdi.SelectObject(memory, bitmap)
        assert previous
        assert user.PrintWindow(hwnd, memory, 0), 'Could not render YueKey window'
        gdi.SelectObject(memory, previous)
        previous = None
        header = C.create_string_buffer(struct.pack('<IiiHHIIiiII', 40, width, -height,
                                                    1, 32, 0, 0, 0, 0, 0, 0))
        pixels = C.create_string_buffer(width * height * 4)
        assert gdi.GetDIBits(memory, bitmap, 0, height, pixels, header, 0) == height
        raw = pixels.raw
        rgb = bytearray(width * height * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = raw[2::4], raw[1::4], raw[0::4]
        stride = width * 3
        scanlines = b''.join(b'\0' + rgb[start:start + stride] for start in range(0, len(rgb), stride))

        def chunk(kind, value):
            return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value))

        destination.write_bytes(b'\x89PNG\r\n\x1a\n' +
                                chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
                                chunk(b'IDAT', zlib.compress(scanlines)) + chunk(b'IEND', b''))
    finally:
        if previous:
            gdi.SelectObject(memory, previous)
        if bitmap:
            gdi.DeleteObject(bitmap)
        if memory:
            gdi.DeleteDC(memory)
        if dc:
            user.ReleaseDC(hwnd, dc)
