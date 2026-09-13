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
    from quick_hk.windows_setup import uninstall
    from quick_hk.windows_arch import package_architecture
    from quick_hk.windows_weasel import detect, verify_installer, INSTALLER_NAME
    import hashlib

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
    assert detect() is None, 'Do not modify an existing Weasel installation in this test'
    # Seed real user preferences before either installer runs.
    rime.mkdir()
    original = b'# existing preferences\npatch: {}\n'
    (rime / 'default.custom.yaml').write_bytes(original)
    learned = rime / 'quick_hk.userdb' / 'keep.txt'
    learned.parent.mkdir()
    learned.write_bytes(b'learning sentinel')
    logs = ROOT / 'build/windows-installer'
    logs.mkdir(parents=True, exist_ok=True)
    architecture = package_architecture()
    setup = ROOT / f'dist/YueKey-{VERSION}-windows-{architecture}-setup.exe'
    quiet = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-']
    with tempfile.TemporaryDirectory(prefix='YueKey installer ') as temporary:
        app = Path(temporary) / '粵鍵 user programs'
        for step in ('install', 'repair'):
            process = subprocess.run([str(setup), *quiet, '/TASKS=startup', f'/DIR={app}', f'/LOG={logs / (step + ".log")}'],
                                     timeout=600)
            report = data / 'setup-report.json'
            if report.is_file():
                (logs / f'{step}-typing.json').write_bytes(report.read_bytes())
                print(report.read_text(encoding='utf-8'), flush=True)
            process.check_returncode()
            result = json.loads(report.read_text(encoding='utf-8'))
            assert result['ok'] and Path(result['user_directory']) == rime
            assert result['input_profile'].startswith('0404:'), 'Fresh setup should register Traditional Chinese'
            engine = detect()
            assert engine and engine.version == '0.17.4.0'
            verify_installer(app / '_internal/prerequisites' / INSTALLER_NAME)
            assert (rime / 'build/quick_hk.table.bin').is_file(), 'Typing was not automatically deployed'
            backup = Path(json.loads((rime / 'yuekey-install.json').read_text())['backup'])
            assert (backup / 'default.custom.yaml').read_bytes() == original
            assert learned.read_bytes() == b'learning sentinel'
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
                (app / 'user-notes.txt').write_bytes(b'user notes')
                engine_hash = hashlib.sha256((engine.root / 'WeaselServer.exe').read_bytes()).hexdigest()
                first_backup = backup
            else:
                assert backup == first_backup, 'Repair replaced the original preference backup'
                assert hashlib.sha256((engine.root / 'WeaselServer.exe').read_bytes()).hexdigest() == engine_hash
                assert 'Reusing existing Weasel installation' in (logs / 'repair.log').read_text(encoding='utf-8-sig')

        if architecture == 'arm64':
            # The Windows 11 hosted image can show an OS first-login account
            # prompt. Dismiss only that known prompt on this disposable CI VM;
            # it otherwise keeps our isolated test field from gaining focus.
            import ctypes
            from ctypes import wintypes as W
            user = ctypes.WinDLL('user32', use_last_error=True)
            user.FindWindowW.argtypes = [W.LPCWSTR, W.LPCWSTR]
            user.FindWindowW.restype = W.HWND
            user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
            user.PostMessageW.restype = W.BOOL
            prompt = user.FindWindowW(None, 'Microsoft account')
            if prompt:
                assert user.PostMessageW(prompt, 0x0010, 0, 0), 'Could not dismiss runner first-login prompt'
                deadline = time.monotonic() + 10
                while user.FindWindowW(None, 'Microsoft account') and time.monotonic() < deadline:
                    time.sleep(0.1)
                assert not user.FindWindowW(None, 'Microsoft account'), 'Runner first-login prompt stayed open'
                print('Dismissed first-login account prompt on the disposable Windows ARM runner.')

        from smoke_weasel_ui import exercise as exercise_candidates
        exercise_candidates(engine, rime, logs)

        report = logs / 'installed-runtime.json'
        process = subprocess.run([str(app / 'YueKey.exe'), '--self-test', str(report),
                                  '--models', str(ROOT / 'build/speech-models')], timeout=600)
        result = json.loads(report.read_text(encoding='utf-8'))
        print(json.dumps(result, indent=2))
        process.check_returncode()
        assert result['ok']
        assert result['architecture'] == architecture
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
        assert learned.read_bytes() == b'learning sentinel'
        assert detect() == engine, 'Removing YueKey must retain the shared Weasel installation'
        assert (rime / 'yuekey-install.json').is_file()
        assert uninstall(rime) == []
        assert (rime / 'default.custom.yaml').read_bytes() == original
        # The uninstaller removes its own executable asynchronously.
        deadline = time.monotonic() + 10
        while (app / 'unins000.exe').exists() and time.monotonic() < deadline:
            time.sleep(0.1)
    print('Setup, repair, running-app guard, installed CPU runtime and uninstall preservation passed.')


if __name__ == '__main__':
    main()
