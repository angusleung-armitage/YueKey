#!/usr/bin/env python3
"""Exercise the Windows schema in Weasel's actual librime DLL, without installing an IME."""
import ctypes as C
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from quick_hk.windows_weasel import fetch_installer, installer_path


class Traits(C.Structure):
    _fields_ = [('data_size', C.c_int)] + [(name, C.c_char_p) for name in (
        'shared_data_dir', 'user_data_dir', 'distribution_name', 'distribution_code_name',
        'distribution_version', 'app_name')] + [
        ('modules', C.POINTER(C.c_char_p)), ('min_log_level', C.c_int),
        ('log_dir', C.c_char_p), ('prebuilt_data_dir', C.c_char_p), ('staging_dir', C.c_char_p)]


class Commit(C.Structure):
    _fields_ = [('data_size', C.c_int), ('text', C.c_char_p)]


class Composition(C.Structure):
    _fields_ = [(name, C.c_int) for name in ('length', 'cursor_pos', 'sel_start', 'sel_end')] + [('preedit', C.c_char_p)]


class Candidate(C.Structure):
    _fields_ = [('text', C.c_char_p), ('comment', C.c_char_p), ('reserved', C.c_void_p)]


class Menu(C.Structure):
    _fields_ = [(name, C.c_int) for name in ('page_size', 'page_no', 'is_last_page', 'highlighted_candidate_index', 'num_candidates')] + [
        ('candidates', C.POINTER(Candidate)), ('select_keys', C.c_char_p)]


class Context(C.Structure):
    _fields_ = [('data_size', C.c_int), ('composition', Composition), ('menu', Menu),
                ('commit_text_preview', C.c_char_p), ('select_labels', C.POINTER(C.c_char_p))]


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


def exercise(library: Path, preferences=False):
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
        if preferences:
            custom = user / 'quick_hk.windows.custom.yaml'
            text = custom.read_text(encoding='utf-8')
            for old, new in [('menu/page_size: 9', 'menu/page_size: 5'),
                             ('translator/enable_user_dict: true', 'translator/enable_user_dict: false'),
                             ('quick_hk/show_candidates: true', 'quick_hk/show_candidates: false'),
                             ('switches/@1/reset: 1', 'switches/@1/reset: 0'),
                             ('switches/@2/reset: 0', 'switches/@2/reset: 1'),
                             ('Shift_L: commit_code', 'Shift_L: noop'),
                             ('Shift_R: noop', 'Shift_R: commit_code')]:
                assert old in text, old
                text = text.replace(old, new)
            custom.write_text(text, encoding='utf-8')
        shared.mkdir()
        (shared / 'default.yaml').write_text("config_version: '1'\nschema_list:\n  - schema: luna_pinyin\n", encoding='utf-8')
        (user / 'user.yaml').write_text('var:\n  previously_selected_schema: luna_pinyin\n', encoding='utf-8')
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
            def assert_default(current):
                schema = C.create_string_buffer(128)
                assert current and call('get_current_schema', C.c_int,
                                        [C.c_size_t, C.c_void_p, C.c_size_t], current, schema, len(schema))
                assert schema.value == b'quick_hk', schema.value

            assert_default(session)
            def snapshot(current=session, *, require_prediction_menu=False):
                context = Context(data_size=C.sizeof(Context) - C.sizeof(C.c_int))
                assert call('get_context', C.c_int, [C.c_size_t, C.POINTER(Context)], current, C.byref(context))
                values = [context.menu.candidates[n].text.decode() for n in range(context.menu.num_candidates)]
                if require_prediction_menu:
                    assert values and context.commit_text_preview
                    assert context.commit_text_preview.decode() == values[context.menu.highlighted_candidate_index]
                    # A zero-length composition is valid for continuations;
                    # Keep its text out of the client preedit until selection.
                    assert context.composition.length == 0
                    assert not context.composition.preedit
                if values:
                    assert context.menu.page_size == (5 if preferences else 9), context.menu.page_size
                call('free_context', C.c_int, [C.POINTER(Context)], C.byref(context))
                return values

            def key(value, modifiers=0, current=session):
                call('process_key', C.c_int, [C.c_size_t, C.c_int, C.c_int], current,
                     ord(value) if isinstance(value, str) else value, modifiers)
                commit = Commit(data_size=C.sizeof(Commit) - C.sizeof(C.c_int))
                text = ''
                if call('get_commit', C.c_int, [C.c_size_t, C.POINTER(Commit)], current, C.byref(commit)):
                    text = commit.text.decode()
                    call('free_commit', C.c_int, [C.POINTER(Commit)], C.byref(commit))
                return text
            if preferences:
                def option(name):
                    return bool(call('get_option', C.c_int, [C.c_size_t, C.c_char_p], session, name.encode()))
                assert not option('prediction') and option('ascii_punct')
                key('h'); key('i')
                assert not snapshot(), 'Hidden candidates appeared before Space'
                assert key(' ') == ''
                assert snapshot()[0] == '我', snapshot()
                assert key('1') == '我' and not snapshot()
                assert not (user / 'quick_hk.userdb').exists(), 'Disabled learning opened a user database'
                key(0xffe1); key(0xffe1, 1 << 30)
                assert not option('ascii_mode'), 'Disabled Left Shift changed language'
                key(0xffe2); key(0xffe2, 1 << 30)
                assert option('ascii_mode'), 'Configured Right Shift did not change language'
                key(0xffe2); key(0xffe2, 1 << 30)
                assert not option('ascii_mode')
                assert not call('process_key', C.c_int, [C.c_size_t, C.c_int, C.c_int],
                                session, ord(','), 0), 'English punctuation was not passed to the application'
                call('destroy_session', C.c_int, [C.c_size_t], session)
                print('PASS actual Rime preferences: page size, hidden candidates, learning/prediction off, language key, English punctuation')
                return
            for keys, expected in [('hi1', '我'), ('zb1', '，'), ('zd1', '。'),
                                   ('zf1', '‧'), ('zk1', '︰'), ('zt1', '﹖'), ('zu1', '﹗'),
                                   ('hio', '我'), ('zz ', '')]:
                committed = ''
                for letter in keys:
                    call('process_key', C.c_int, [C.c_size_t, C.c_int, C.c_int], session, ord(letter), 0)
                    commit = Commit(data_size=C.sizeof(Commit) - C.sizeof(C.c_int))
                    if call('get_commit', C.c_int, [C.c_size_t, C.POINTER(Commit)], session, C.byref(commit)):
                        committed += commit.text.decode()
                        call('free_commit', C.c_int, [C.POINTER(Commit)], C.byref(commit))
                assert committed == expected, (keys, committed, expected)
                call('clear_composition', None, [C.c_size_t], session)
            for letters, modifiers in (('HI', 0), ('HI', 2), ('HI', 1), ('hi', 3)):
                for letter in letters:
                    assert not key(letter, modifiers)
                assert snapshot()[0] == '我', (letters, modifiers, snapshot())
                assert key('1', modifiers & 2) == '我'
                call('clear_composition', None, [C.c_size_t], session)
            key('o'); key('f')
            assert key(str(snapshot().index('你') + 1)) == '你'
            assert '好' in snapshot(require_prediction_menu=True), ('Missing portable continuations', snapshot())
            second = call('create_session', C.c_size_t, [])
            assert_default(second)
            assert not snapshot(second), 'Predictions leaked into a second input context'
            assert key(str(snapshot().index('好') + 1)) == '好'
            assert not snapshot(), 'Prediction chaining did not stop at one continuation'
            key('o'); key('f'); key(str(snapshot().index('你') + 1))
            assert '好' in snapshot()
            key(0xff1b)
            assert not snapshot(), 'Escape resurrected predictions'
            key('o'); key('f'); key(str(snapshot().index('你') + 1))
            assert '好' in snapshot()
            assert key('z') == '' and key('b') == '' and key('1') == '，'
            assert not snapshot(), 'Punctuation produced predictions'
            call('set_option', None, [C.c_size_t, C.c_char_p, C.c_int], session, b'prediction', 0)
            key('o'); key('f'); key(str(snapshot().index('你') + 1))
            assert not snapshot(), 'Disabled predictions were shown'
            call('destroy_session', C.c_int, [C.c_size_t], second)
            call('destroy_session', C.c_int, [C.c_size_t], session)
        finally:
            call('finalize', None, [])
    print('PASS actual Rime runtime: hi1, zb1, zd1, continuations, reset, cancellation, settings and session isolation')
    subprocess.run([sys.executable, str(Path(__file__).resolve()), str(library), '--preferences'], check=True)


def main():
    if len(sys.argv) in (2, 3):
        exercise(Path(sys.argv[1]), len(sys.argv) == 3 and sys.argv[2] == '--preferences')
        return
    installer = installer_path()
    fetch_installer(installer)
    extracted = ROOT / 'build/weasel-runtime'
    shutil.rmtree(extracted, ignore_errors=True)
    # NSIS stores both architectures as rime.dll. Preserve duplicates instead of
    # letting the second payload overwrite the first during archive extraction.
    subprocess.run(['7z', 'x', str(installer), f'-o{extracted}', '-aou', '-y'], check=True, stdout=subprocess.DEVNULL)
    for file in extracted.rglob('rime*.dll'):
        data = file.read_bytes()
        pe = int.from_bytes(data[0x3c:0x40], 'little')
        machine = 0x8664 if C.sizeof(C.c_void_p) == 8 else 0x14c
        if int.from_bytes(data[pe + 4:pe + 6], 'little') == machine:
            exercise(file)
            return
    raise RuntimeError('No rime.dll matches this Python architecture')


if __name__ == '__main__':
    main()
