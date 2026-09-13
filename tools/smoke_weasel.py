#!/usr/bin/env python3
"""Exercise the Windows schema in Weasel's actual librime DLL, without installing an IME."""
import ctypes as C
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://github.com/rime/weasel/releases/download/0.17.4/weasel-0.17.4.0-installer.exe'
SHA256 = 'cf509534a8f5f8af9c98ed7cbb8f135439f145a8cbe7e50ede42bb5b5ab45c29'


class Traits(C.Structure):
    _fields_ = [('data_size', C.c_int)] + [(name, C.c_char_p) for name in (
        'shared_data_dir', 'user_data_dir', 'distribution_name', 'distribution_code_name',
        'distribution_version', 'app_name')] + [
        ('modules', C.POINTER(C.c_char_p)), ('min_log_level', C.c_int),
        ('log_dir', C.c_char_p), ('prebuilt_data_dir', C.c_char_p), ('staging_dir', C.c_char_p)]


class Commit(C.Structure):
    _fields_ = [('data_size', C.c_int), ('text', C.c_char_p)]


# The versioned C API's stable prefix, through select_schema. Unused slots retain
# their pointer width; sizeof is checked before any optional field is accessed.
class Api(C.Structure):
    _fields_ = [('data_size', C.c_int)] + [(name, C.c_void_p) for name in (
        'setup', 'set_notification_handler', 'initialize', 'finalize', 'start_maintenance',
        'is_maintenance_mode', 'join_maintenance_thread', 'deployer_initialize', 'prebuild',
        'deploy', 'deploy_schema', 'deploy_config_file', 'sync_user_data', 'create_session',
        'find_session', 'destroy_session', 'cleanup_stale_sessions', 'cleanup_all_sessions',
        'process_key', 'commit_composition', 'clear_composition', 'get_commit', 'free_commit',
        'get_context', 'free_context', 'get_status', 'free_status', 'set_option', 'get_option',
        'set_property', 'get_property', 'get_schema_list', 'free_schema_list', 'get_current_schema',
        'select_schema')]


def exercise(library: Path):
    handles = []
    if sys.platform == 'win32':
        handles.append(os.add_dll_directory(str(library.parent)))
    dll = C.CDLL(str(library), mode=C.RTLD_GLOBAL)
    if sys.platform == 'linux':
        plugins = list(Path('/usr/lib').glob('*/rime-plugins/librime-lua.so'))
        assert plugins, 'Install the Lua module for the Linux comparison test'
        handles.append(C.CDLL(str(plugins[0]), mode=C.RTLD_GLOBAL))
    dll.rime_get_api.restype = C.POINTER(Api)
    api = dll.rime_get_api().contents
    assert api.data_size >= C.sizeof(Api) - C.sizeof(C.c_int)

    def call(name, result, arguments, *values):
        return C.CFUNCTYPE(result, *arguments)(getattr(api, name))(*values)

    with tempfile.TemporaryDirectory(prefix='yuekey-weasel-') as temp:
        user, shared = Path(temp) / 'user', Path(temp) / 'shared'
        shutil.copytree(ROOT / 'build/windows-data', user)
        shared.mkdir()
        (shared / 'default.yaml').write_text("config_version: '1'\nschema_list:\n  - schema: quick_hk\n", encoding='utf-8')
        traits = Traits(data_size=C.sizeof(Traits) - C.sizeof(C.c_int),
                        shared_data_dir=str(shared).encode(), user_data_dir=str(user).encode(),
                        app_name=b'rime.yuekey_test', log_dir=str(user).encode(), min_log_level=2)
        modules = (C.c_char_p * 3)(b'default', b'lua', None)
        traits.modules = modules
        call('setup', None, [C.POINTER(Traits)], C.byref(traits))
        call('initialize', None, [C.POINTER(Traits)], C.byref(traits))
        try:
            call('start_maintenance', C.c_int, [C.c_int], 1)
            call('join_maintenance_thread', None, [])
            session = call('create_session', C.c_size_t, [])
            assert session and call('select_schema', C.c_int, [C.c_size_t, C.c_char_p], session, b'quick_hk')
            for keys, expected in [('hi1', '我'), ('zb1', '，'), ('zd1', '。'), ('hio', '我'), ('zz ', '')]:
                committed = ''
                for key in keys:
                    call('process_key', C.c_int, [C.c_size_t, C.c_int, C.c_int], session, ord(key), 0)
                    commit = Commit(data_size=C.sizeof(Commit) - C.sizeof(C.c_int))
                    if call('get_commit', C.c_int, [C.c_size_t, C.POINTER(Commit)], session, C.byref(commit)):
                        committed += commit.text.decode()
                        call('free_commit', C.c_int, [C.POINTER(Commit)], C.byref(commit))
                assert committed == expected, (keys, committed, expected)
                call('clear_composition', None, [C.c_size_t], session)
            call('destroy_session', C.c_int, [C.c_size_t], session)
        finally:
            call('finalize', None, [])
    print('PASS actual Weasel Rime runtime: hi1, zb1, zd1, Lua schema loading')


def main():
    if len(sys.argv) == 2:
        exercise(Path(sys.argv[1]))
        return
    installer = ROOT / 'build/weasel-installer.exe'
    urllib.request.urlretrieve(URL, installer)
    assert hashlib.sha256(installer.read_bytes()).hexdigest() == SHA256
    extracted = ROOT / 'build/weasel-runtime'
    subprocess.run(['7z', 'x', str(installer), f'-o{extracted}', '-y'], check=True, stdout=subprocess.DEVNULL)
    for file in extracted.rglob('rime.dll'):
        data = file.read_bytes()
        pe = int.from_bytes(data[0x3c:0x40], 'little')
        machine = 0x8664 if C.sizeof(C.c_void_p) == 8 else 0x14c
        if int.from_bytes(data[pe + 4:pe + 6], 'little') == machine:
            exercise(file)
            return
    raise RuntimeError('No rime.dll matches this Python architecture; Weasel uses a 32-bit server')


if __name__ == '__main__':
    main()
