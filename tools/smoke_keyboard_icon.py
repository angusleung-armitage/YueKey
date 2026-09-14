"""Check actual Windows profile resources and reversible machine registration.

Only the disposable installer-test runner may execute these checks.
SPDX-License-Identifier: MIT
"""
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import zlib


def guard():
    if sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Only run on the disposable Windows installer-test runner')


def registrations():
    guard()
    import winreg as R
    from quick_hk.windows_keyboard import profile_keys
    result = {}
    for view in (R.KEY_WOW64_32KEY, R.KEY_WOW64_64KEY):
        for key in profile_keys():
            try:
                handle = R.OpenKey(R.HKEY_LOCAL_MACHINE, key, 0, R.KEY_READ | view)
            except FileNotFoundError:
                continue
            with handle:
                values = {}
                for name in ('IconFile', 'IconIndex'):
                    try:
                        values[name] = R.QueryValueEx(handle, name)
                    except FileNotFoundError:
                        values[name] = None
                result[(view, key)] = values
    return result


def backups():
    guard()
    import winreg as R
    from quick_hk.windows_keyboard import STATE_KEY
    result = {}
    for view, key in registrations():
        language = key.split('0x0000')[1][:4]
        side = 0 if view == R.KEY_WOW64_32KEY else 1
        with R.OpenKey(R.HKEY_LOCAL_MACHINE, rf'{STATE_KEY}\Backup\{side}\{language}',
                       0, R.KEY_READ | R.KEY_WOW64_32KEY) as handle:
            assert R.QueryValueEx(handle, 'Format')[0] == 1
            result[(view, key)] = {}
            for name, type_name in (('IconFile', 'FileKind'), ('IconIndex', 'IndexKind')):
                kind = R.QueryValueEx(handle, type_name)[0]
                result[(view, key)][name] = (R.QueryValueEx(handle, name)[0], kind) if kind else None
    return result


def icon_pixels(path, size):
    """Ask Windows to extract resource index 0 and render it on a white surface."""
    shell, user, gdi = C.WinDLL('shell32'), C.WinDLL('user32'), C.WinDLL('gdi32')
    shell.SHDefExtractIconW.argtypes = [W.LPCWSTR, C.c_int, W.UINT,
                                      C.POINTER(W.HICON), C.POINTER(W.HICON), W.UINT]
    shell.SHDefExtractIconW.restype = C.c_long
    user.DestroyIcon.argtypes = [W.HICON]
    user.DrawIconEx.argtypes = [W.HDC, C.c_int, C.c_int, W.HICON, C.c_int, C.c_int,
                               W.UINT, W.HBRUSH, W.UINT]
    gdi.CreateCompatibleDC.argtypes = [W.HDC]
    gdi.CreateCompatibleDC.restype = W.HDC
    gdi.CreateDIBSection.argtypes = [W.HDC, C.c_void_p, W.UINT, C.POINTER(C.c_void_p), W.HANDLE, W.DWORD]
    gdi.CreateDIBSection.restype = W.HBITMAP
    gdi.SelectObject.argtypes = [W.HDC, W.HANDLE]
    gdi.SelectObject.restype = W.HANDLE
    gdi.DeleteObject.argtypes = [W.HANDLE]
    gdi.DeleteDC.argtypes = [W.HDC]
    icon = W.HICON()
    dc = bitmap = previous = None
    try:
        assert shell.SHDefExtractIconW(str(path), 0, 0, C.byref(icon), None, size) == 0 and icon.value
        dc = gdi.CreateCompatibleDC(None)
        bits = C.c_void_p()
        header = C.create_string_buffer(struct.pack('<IiiHHIIiiII', 40, size, -size, 1, 32, 0, 0, 0, 0, 0, 0))
        bitmap = gdi.CreateDIBSection(dc, header, 0, C.byref(bits), None, 0)
        assert dc and bitmap and bits.value
        previous = gdi.SelectObject(dc, bitmap)
        C.memset(bits, 255, size * size * 4)
        assert user.DrawIconEx(dc, 0, 0, icon, size, size, 0, None, 3)
        assert gdi.GdiFlush()
        return C.string_at(bits, size * size * 4)
    finally:
        if previous:
            gdi.SelectObject(dc, previous)
        if bitmap:
            gdi.DeleteObject(bitmap)
        if dc:
            gdi.DeleteDC(dc)
        if icon.value:
            user.DestroyIcon(icon)


def verify_visuals(output):
    guard()
    import winreg as R
    from quick_hk.windows_keyboard import assets, ready
    _, metadata = assets()
    assert ready(metadata['resource_sha256']), 'Shared keyboard icon registration is incomplete'
    paths = set()
    for values in registrations().values():
        assert values['IconIndex'] == (0, R.REG_DWORD)
        assert values['IconFile'][1] == R.REG_SZ
        paths.add(values['IconFile'][0])
    assert len(paths) == 1
    resource = Path(paths.pop())
    expected = Path(__file__).resolve().parents[1] / 'desktop/icons/yuekey-keyboard.ico'
    for size in (16, 20, 24, 32, 40, 48):
        raw = icon_pixels(resource, size)
        assert raw == icon_pixels(expected, size), f'Wrong keyboard glyph at {size}px'
        rgb = bytearray(size * size * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = raw[2::4], raw[1::4], raw[0::4]
        assert min(rgb) < 32 and max(rgb) == 255, 'The keyboard icon rendered blank'
        scanlines = b''.join(b'\0' + rgb[start:start + size * 3]
                             for start in range(0, len(rgb), size * 3))

        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

        (output / f'keyboard-identifier-{size}.png').write_bytes(
            b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(scanlines)) + chunk(b'IEND', b''))
    (output / 'keyboard-identifier.json').write_text(json.dumps(dict(
        glyph='中', resource=str(resource), mode_icons=['港', 'A'], sizes=[16, 20, 24, 32, 40, 48]),
        ensure_ascii=False, indent=2), encoding='utf-8')


def verify_restore(output, original):
    guard()
    import winreg as R
    from quick_hk.windows_keyboard import assets, STATE_KEY, ready
    from quick_hk.windows_weasel import registry_value
    installer, metadata = assets()
    resource = Path(registry_value(R.HKEY_LOCAL_MACHINE, STATE_KEY, 'IconFile'))
    uninstaller = resource.parent / 'unins000.exe'
    quiet = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-']

    def run(path, label):
        subprocess.run([str(path), *quiet, f'/LOG={output / (label + ".log")}'],
                       check=True, timeout=120)
        if path == uninstaller:
            deadline = time.monotonic() + 10
            while path.exists() and time.monotonic() < deadline:
                time.sleep(.1)
            assert not path.exists(), 'The old icon uninstaller did not finish its cleanup'

    run(uninstaller, 'keyboard-uninstall')
    assert registrations() == original, 'Original keyboard icons were not restored exactly'
    keys = list(original)
    assert len(keys) >= 2
    # Exercise a previous customization with an expandable path and absent index.
    view, key = keys[0]
    with R.OpenKey(R.HKEY_LOCAL_MACHINE, key, 0, R.KEY_WRITE | view) as handle:
        R.SetValueEx(handle, 'IconFile', 0, R.REG_EXPAND_SZ, r'%SystemRoot%\System32\imageres.dll')
        if original[keys[0]]['IconIndex'] is not None:
            R.DeleteValue(handle, 'IconIndex')
    customized = registrations()
    run(installer, 'keyboard-custom-install')
    assert ready(metadata['resource_sha256'])
    saved = backups()
    assert saved == customized
    run(installer, 'keyboard-custom-repair')
    assert backups() == saved, 'Repair replaced the first backup'
    run(uninstaller, 'keyboard-custom-uninstall')
    assert registrations() == customized, 'Restore changed value types or recreated a missing index'
    run(installer, 'keyboard-preserve-install')
    with R.OpenKey(R.HKEY_LOCAL_MACHINE, key, 0, R.KEY_WRITE | view) as handle:
        R.SetValueEx(handle, 'IconFile', 0, R.REG_SZ, r'C:\User-custom-icon.dll')
        R.SetValueEx(handle, 'IconIndex', 0, R.REG_DWORD, 7)
    changed = registrations()[(view, key)]
    run(uninstaller, 'keyboard-preserve-uninstall')
    restored = registrations()
    assert restored[(view, key)] == changed, 'Uninstall overwrote a later customization'
    for item in restored:
        if item != (view, key):
            # CTF can expose a shared registry key through both views.
            assert restored[item] in (customized[item], changed)
    print('PASS keyboard identifier: native resource sizes, repair, exact restore and preservation', flush=True)
