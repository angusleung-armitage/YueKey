#!/usr/bin/env python3
"""Exercise setup, repair, installed runtime and uninstall on a disposable CI VM."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / 'VERSION').read_text().strip()


def main():
    if sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('Only run this integration test on a disposable Windows Actions runner.')
    import winreg
    from quick_hk.windows_setup import install, uninstall

    key = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\YueKey.Companion_is1'
    access = winreg.KEY_READ | winreg.KEY_WOW64_64KEY

    def installed():
        try:
            return winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, access)
        except FileNotFoundError:
            return None

    assert installed() is None, 'An existing YueKey installation must not be touched'
    data = Path(os.environ['LOCALAPPDATA']) / 'YueKey'
    rime = Path(os.environ['APPDATA']) / 'Rime'
    shortcut = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/YueKey/YueKey.lnk'
    startup = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Startup/YueKey.lnk'
    assert not any(path.exists() for path in (data, rime, shortcut, startup)), 'Expected a clean disposable profile'
    logs = ROOT / 'build/windows-installer'
    logs.mkdir(parents=True, exist_ok=True)
    setup = ROOT / f'dist/YueKey-{VERSION}-windows-x64-setup.exe'
    quiet = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-']
    with tempfile.TemporaryDirectory(prefix='YueKey installer ') as temporary:
        app = Path(temporary) / '粵鍵 user programs'
        for step in ('install', 'repair'):
            subprocess.run([str(setup), *quiet, '/TASKS=startup', f'/DIR={app}', f'/LOG={logs / (step + ".log")}'],
                           check=True, timeout=180)
            with installed() as registration:
                assert winreg.QueryValueEx(registration, 'DisplayVersion')[0] == VERSION
                assert Path(winreg.QueryValueEx(registration, 'InstallLocation')[0]) == app
            assert (app / 'YueKey.exe').is_file() and shortcut.is_file()
            assert startup.is_file()
            if step == 'install':
                # Check that repair and uninstall leave files created by the
                # user alone, including typing configuration and learning.
                (data / 'dictation/models').mkdir(parents=True)
                (data / 'dictation/models/keep.txt').write_bytes(b'model sentinel')
                rime.mkdir()
                (rime / 'default.custom.yaml').write_bytes(b'# existing preferences\npatch: {}\n')
                (rime / 'quick_hk.userdb').write_bytes(b'learning sentinel')
                install(rime, app / '_internal/windows-data')
                (app / 'user-notes.txt').write_bytes(b'user notes')

        report = logs / 'installed-runtime.json'
        subprocess.run([str(app / 'YueKey.exe'), '--self-test', str(report),
                        '--models', str(ROOT / 'build/speech-models')], check=True, timeout=600)
        result = json.loads(report.read_text(encoding='utf-8'))
        print(json.dumps(result, indent=2))
        assert result['ok']
        # Simulate a companion in use: setup must reject repair instead of
        # overwriting a running app or forcing it closed.
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        mutex = kernel.CreateMutexW(None, False, r'Local\YueKey.Companion')
        assert mutex
        try:
            blocked = subprocess.run([str(setup), *quiet, f'/DIR={app}',
                                      f'/LOG={logs / "running-app.log"}'], timeout=60)
            assert blocked.returncode != 0, 'Setup overwrote an application that was still running'
        finally:
            kernel.CloseHandle(mutex)

        subprocess.run([str(app / 'unins000.exe'), *quiet, f'/LOG={logs / "uninstall.log"}'],
                       check=True, timeout=180)
        assert not (app / 'YueKey.exe').exists()
        assert not shortcut.exists() and not startup.exists() and installed() is None
        assert (app / 'user-notes.txt').read_bytes() == b'user notes'
        assert (data / 'dictation/models/keep.txt').read_bytes() == b'model sentinel'
        assert (rime / 'quick_hk.userdb').read_bytes() == b'learning sentinel'
        assert (rime / 'yuekey-install.json').is_file()
        assert uninstall(rime) == []
        assert (rime / 'default.custom.yaml').read_bytes() == b'# existing preferences\npatch: {}\n'
        # The uninstaller removes its own executable asynchronously.
        deadline = time.monotonic() + 10
        while (app / 'unins000.exe').exists() and time.monotonic() < deadline:
            time.sleep(0.1)
    print('Setup, repair, running-app guard, installed CPU runtime and uninstall preservation passed.')


if __name__ == '__main__':
    main()
