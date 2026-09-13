"""Install the official Windows IME and deploy YueKey for the current user.

Weasel is an unmodified, separately licensed prerequisite. Only its own
installer is elevated; profile writes and deployment stay in the user's session.
SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

VERSION = '0.17.4'
INSTALLER_NAME = 'weasel-0.17.4.0-installer.exe'
INSTALLER_URL = f'https://github.com/rime/weasel/releases/download/{VERSION}/{INSTALLER_NAME}'
INSTALLER_SHA256 = 'cf509534a8f5f8af9c98ed7cbb8f135439f145a8cbe7e50ede42bb5b5ab45c29'
WEASEL_KEY = r'Software\Rime\Weasel'
UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\Weasel'
TIP_CLSID = '{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}'
TIP_PROFILE = '{3D02CAB6-2B8E-4781-BA20-1C9267529467}'


@dataclass(frozen=True)
class Installation:
    root: Path
    version: str


def registry_value(hive, key, name):
    import winreg
    # Upstream's NSIS installer writes its machine keys in the 32-bit view.
    # Check both views so the native ARM64/x64 app also sees those entries.
    for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
        try:
            with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view) as handle:
                return winreg.QueryValueEx(handle, name)[0]
        except FileNotFoundError:
            continue
    return None


def detect() -> Installation | None:
    import winreg
    root = registry_value(winreg.HKEY_LOCAL_MACHINE, WEASEL_KEY, 'WeaselRoot')
    if not root:
        return None
    root = Path(root)
    if not root.is_absolute() or not all((root / name).is_file() for name in
            ('WeaselServer.exe', 'WeaselDeployer.exe', 'WeaselSetup.exe', 'rime.dll')):
        raise RuntimeError('小狼毫安裝不完整，請先修復。\nThe existing Weasel installation needs repair.')
    version = registry_value(winreg.HKEY_LOCAL_MACHINE, UNINSTALL_KEY, 'DisplayVersion') or ''
    if not re.fullmatch(r'\d+(?:\.\d+){2,3}', version) or tuple(map(int, version.split('.'))) < (0, 17, 4):
        raise RuntimeError('請先更新現有的小狼毫至 0.17.4 或更新版本。\n'
                           'Update your existing Weasel to 0.17.4 or newer, then retry. '
                           'YueKey will not silently replace an older installation.')
    return Installation(root, version)


def installer_path() -> Path:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2] / 'build'))
    return base / 'prerequisites' / INSTALLER_NAME


def verify_installer(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError('找不到內置安裝程式，請重新安裝粵鍵。\n'
                           'The bundled typing installer is missing. Reinstall YueKey.')
    with path.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    if checksum != INSTALLER_SHA256:
        raise RuntimeError('小狼毫安裝檔驗證失敗，請重新下載粵鍵。\n'
                           'Weasel installer checksum mismatch. Download YueKey again.')


def fetch_installer(path: Path) -> None:
    from .speech_assets import download
    path.parent.mkdir(parents=True, exist_ok=True)
    download(INSTALLER_URL, path, INSTALLER_SHA256)
    verify_installer(path)


def _run_installer(path: Path) -> None:
    import ctypes as C
    from ctypes import wintypes as W

    class ShellExecuteInfo(C.Structure):
        _fields_ = [('cbSize', W.DWORD), ('fMask', W.ULONG), ('hwnd', W.HWND),
                    ('lpVerb', W.LPCWSTR), ('lpFile', W.LPCWSTR), ('lpParameters', W.LPCWSTR),
                    ('lpDirectory', W.LPCWSTR), ('nShow', C.c_int), ('hInstApp', W.HINSTANCE),
                    ('lpIDList', C.c_void_p), ('lpClass', W.LPCWSTR), ('hkeyClass', W.HKEY),
                    ('dwHotKey', W.DWORD), ('hIcon', W.HANDLE), ('hProcess', W.HANDLE)]

    shell = C.WinDLL('shell32', use_last_error=True)
    kernel = C.WinDLL('kernel32', use_last_error=True)
    ole = C.OleDLL('ole32')
    shell.ShellExecuteExW.argtypes = [C.POINTER(ShellExecuteInfo)]
    shell.ShellExecuteExW.restype = W.BOOL
    kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    kernel.WaitForSingleObject.restype = W.DWORD
    kernel.GetExitCodeProcess.argtypes = [W.HANDLE, C.POINTER(W.DWORD)]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    ole.CoInitializeEx(None, 2)
    info = ShellExecuteInfo(cbSize=C.sizeof(ShellExecuteInfo), fMask=0x140,
                            lpVerb='runas', lpFile=str(path), lpParameters='/S /T',
                            lpDirectory=str(path.parent), nShow=1)
    try:
        if not shell.ShellExecuteExW(C.byref(info)):
            if C.get_last_error() == 1223:
                raise RuntimeError('已取消安裝；可按「設定速成」再試。\n'
                                   'Installation was cancelled. Choose Set up typing to try again.')
            raise C.WinError(C.get_last_error())
        if not info.hProcess:
            raise RuntimeError('Windows did not return a handle for the typing installer.')
        if kernel.WaitForSingleObject(info.hProcess, 600000) != 0:
            raise RuntimeError('小狼毫安裝仍未完成，請完成後再試。\n'
                               'Finish the Weasel installer, then try again.')
        code = W.DWORD()
        if not kernel.GetExitCodeProcess(info.hProcess, C.byref(code)):
            raise C.WinError(C.get_last_error())
        if code.value != 0:
            raise RuntimeError(f'Weasel setup returned {code.value}. Run YueKey setup again.')
    finally:
        if info.hProcess:
            kernel.CloseHandle(info.hProcess)
        ole.CoUninitialize()


def ensure_engine(progress=lambda message: None) -> Installation:
    existing = detect()
    if existing:
        return existing
    path = installer_path()
    verify_installer(path)
    progress('正在安裝輸入法，請允許 Windows 管理員提示。\n'
             'Installing typing support. Approve the Windows administrator prompt.')
    _run_installer(path)
    installed = detect()
    if installed is None:
        raise RuntimeError('小狼毫未完成安裝，請再試一次。\nWeasel installation did not complete. Try again.')
    return installed


def enable_current_user() -> str:
    """Enable the installed TIP for this user, including after over-the-shoulder UAC."""
    import ctypes as C
    from ctypes import wintypes as W
    import winreg
    language = None
    for lang in ('0404', '0804'):
        key = rf'SOFTWARE\Microsoft\CTF\TIP\{TIP_CLSID}\LanguageProfile\0x0000{lang}\{TIP_PROFILE}'
        for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key, 0, winreg.KEY_READ | view):
                    language = lang
                    break
            except FileNotFoundError:
                pass
        if language:
            break
    if language is None:
        raise RuntimeError('Windows 尚未註冊小狼毫，請重新執行安裝程式。\n'
                           'Weasel is not registered with Windows. Run setup again.')
    library = C.WinDLL(str(Path(os.environ['SystemRoot']) / 'System32/input.dll'))
    library.InstallLayoutOrTip.argtypes = [W.LPCWSTR, W.DWORD]
    library.InstallLayoutOrTip.restype = W.BOOL
    profile = f'{language}:{TIP_CLSID}{TIP_PROFILE}'
    if not library.InstallLayoutOrTip(profile, 0):  # do not replace the default keyboard
        raise RuntimeError('未能啟用輸入法，請在 Windows 輸入設定加入小狼毫。\n'
                           'Windows could not enable Weasel. Add it in Windows input settings.')
    return profile


def deploy(engine: Installation, destination: Path, *, require_yuekey=True) -> None:
    completed = subprocess.run([str(engine.root / 'WeaselDeployer.exe'), '/deploy'],
                               cwd=engine.root, timeout=180, creationflags=0x08000000)
    if completed.returncode != 0:
        raise RuntimeError('小狼毫正忙碌，請稍後再按「套用」。\n'
                           'Weasel could not deploy the profile. Wait for other deployment to finish, then retry.')
    if not require_yuekey:
        return
    # Upstream's deployer can return zero even when compilation fails.
    for name in ('quick_hk.schema.yaml', 'quick_hk.table.bin', 'quick_hk.prism.bin'):
        path = destination / 'build' / name
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError('速成尚未完成部署，請按「設定速成」再試。\n'
                               f'Typing deployment is incomplete ({name}). Choose Set up typing to retry.')


def configure_typing(settings=None, progress=lambda message: None, *, install_missing=True) -> dict:
    from .windows_setup import install, rime_directory
    engine = ensure_engine(progress) if install_missing else detect()
    if engine is None:
        raise RuntimeError('The bundled Weasel prerequisite did not finish. Run YueKey setup again.')
    destination = rime_directory().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    progress('正在備份及設定速成… · Preparing your typing profile…')
    backup = install(destination, settings=settings)
    profile = enable_current_user()
    deploy(engine, destination)
    subprocess.Popen([str(engine.root / 'WeaselServer.exe')], cwd=engine.root,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
    return dict(ok=True, engine_version=engine.version, engine_root=str(engine.root),
                user_directory=str(destination), backup=str(backup), input_profile=profile)
