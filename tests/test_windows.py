"""Windows state and deployment contracts; safe to run on any platform."""
import json
from pathlib import Path
import os
import sys
from dataclasses import replace
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import yaml
from quick_hk.windows_setup import FILES, install, uninstall, apply_settings, learning_lock, reset_learning
from quick_hk.settings import Settings, load_settings, save_settings, settings_path
from quick_hk.windows_devices import microphones, resolve_microphone
from quick_hk.windows_state import DoubleControl, Request, Target, editable
from quick_hk.rime_config import DeploymentError
from quick_hk.dictation_worker import WindowsRecording


class WindowsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        env = patch.dict(os.environ, {'QUICK_HK_CONFIG': str(Path(temporary.name) / 'settings.toml')})
        env.start()
        self.addCleanup(env.stop)

    def payload(self, source):
        for name in (*FILES, 'yuekey-predict/4f.tsv'):
            (source / name).parent.mkdir(parents=True, exist_ok=True)
            (source / name).write_text(name, encoding='utf-8')

    def test_settings_upgrade_keeps_original_backup_and_rejects_user_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'source', Path(tmp) / 'user'
            target.mkdir()
            self.payload(source)
            original = b'# Before YueKey\npatch: {}\n'
            (target / 'default.custom.yaml').write_bytes(original)
            backup = install(target, source)
            # Simulate the v0.3 manifest and payload (no predictions or settings).
            marker = target / 'yuekey-install.json'
            record = json.loads(marker.read_text())
            old_names = {'quick_hk.schema.yaml', 'quick_hk.dict.yaml', 'lua/quick_hk.lua', 'default.custom.yaml'}
            for name in list(record['files']):
                if name not in old_names:
                    del record['files'][name]
                    (target / name).unlink()
            marker.write_text(json.dumps(record), encoding='utf-8')
            preferences = Settings(horizontal=False, page_size=5, font_size=24, learning=False,
                prediction=False, show_candidates=False, ascii_punctuation=True, theme='dark',
                switch_key='Control_L', dictation_enabled=True, dictation_microphone='test',
                dictation_punctuation=False)
            self.assertEqual(install(target, source, preferences), backup)
            save_settings(preferences)
            self.assertEqual(load_settings(), preferences)
            patch_values = yaml.safe_load((target / 'quick_hk.windows.custom.yaml').read_text(encoding='utf-8'))['patch']
            for key, expected in {'menu/page_size': 5, 'style/font_point': 24,
                    'style/horizontal': False, 'style/color_scheme': 'yuekey_dark',
                    'translator/enable_user_dict': False, 'switches/@1/reset': 0,
                    'switches/@2/reset': 1, 'quick_hk/show_candidates': False,
                    'quick_hk/dictation_key': 'Control_R'}.items():
                self.assertEqual(patch_values[key], expected, key)
            apply_settings(target, replace(preferences, prediction=True))
            (target / 'lua/quick_hk.lua').write_text('user edit', encoding='utf-8')
            before = marker.read_bytes()
            with self.assertRaisesRegex(ValueError, 'Preserving'):
                install(target, source)
            self.assertEqual(marker.read_bytes(), before)
            self.assertIn('lua/quick_hk.lua', uninstall(target))
            self.assertEqual((target / 'default.custom.yaml').read_bytes(), original)
            self.assertEqual((target / 'lua/quick_hk.lua').read_text(), 'user edit')

    def test_microphone_selection_survives_reordering_and_fails_if_missing(self):
        devices = [dict(name='Mic A', hostapi=0, max_input_channels=1),
                   dict(name='Speakers', hostapi=0, max_input_channels=0),
                   dict(name='Mic B', hostapi=0, max_input_channels=1)]
        sd = SimpleNamespace(query_devices=lambda: devices,
                             query_hostapis=lambda: [{'name': 'Windows WASAPI'}])
        choices = microphones(sd)
        self.assertEqual(len(choices), 3)
        value = choices[1][0]
        self.assertEqual(resolve_microphone(value, sd), 0)
        devices.reverse()
        self.assertEqual(resolve_microphone(value, sd), 2)
        devices.pop()
        with self.assertRaisesRegex(ValueError, 'missing'):
            resolve_microphone(value, sd)
        self.assertIsNone(resolve_microphone('default', sd))

    @unittest.skipUnless(sys.platform == 'win32', 'Requires actual Windows file locking')
    def test_learning_reset_refuses_live_database_and_preserves_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            database = target / 'quick_hk.userdb'
            database.mkdir()
            (database / 'data.ldb').write_bytes(b'learned words')
            with learning_lock(database):
                with self.assertRaises(OSError):
                    reset_learning(target)
                self.assertEqual((database / 'data.ldb').read_bytes(), b'learned words')
            backup = reset_learning(target)
            self.assertEqual([path.name for path in database.iterdir()], ['LOCK'])
            self.assertEqual((backup / 'data.ldb').read_bytes(), b'learned words')

    def test_windows_settings_location_uses_localappdata(self):
        with patch('quick_hk.settings.sys.platform', 'win32'), patch.dict(os.environ, {'LOCALAPPDATA': 'local-data'}):
            os.environ.pop('QUICK_HK_CONFIG')
            self.assertEqual(settings_path(), Path('local-data/YueKey/settings.toml'))

    def test_double_control_requires_two_short_complete_taps(self):
        gesture = DoubleControl()
        self.assertFalse(gesture.feed(0xA2, True, 1))
        self.assertFalse(gesture.feed(0xA2, False, 1.1))
        self.assertFalse(gesture.feed(0xA2, True, 1.2))
        self.assertTrue(gesture.feed(0xA2, False, 1.3))
        self.assertFalse(gesture.feed(0xA2, False, 1.35))

    def test_chords_repeats_holds_and_slow_taps_do_not_toggle(self):
        sequences = [
            [(0xA2, True, 0), (65, True, .1), (0xA2, False, .2)],
            [(0xA2, True, 0), (0xA2, True, .1), (0xA2, True, .2), (0xA2, False, .3)],
            [(0xA2, True, 0), (0xA2, False, .6)],
            [(0xA2, True, 0), (0xA2, False, .1), (0xA2, True, .8), (0xA2, False, .9)],
        ]
        for events in sequences:
            gesture = DoubleControl()
            self.assertFalse(any(gesture.feed(*event) for event in events))

    def test_right_control_is_independent(self):
        gesture = DoubleControl(0xA3)
        for key in [0xA2, 0xA3]:
            toggled = [gesture.feed(key, down, timestamp) for down, timestamp in
                       [(True, 1), (False, 1.1), (True, 1.2), (False, 1.3)]]
            self.assertEqual(any(toggled), key == 0xA3)

    def test_commit_requires_unchanged_field_and_activity_once(self):
        target = Target(10, 20, (1, 2), 5)
        request = Request('id', target)
        self.assertFalse(request.consume('id', target))
        request.state = 'finishing'
        for wrong in [None, Target(11, 20, (1, 2), 5), Target(10, 20, (1, 3), 5), Target(10, 20, (1, 2), 6)]:
            self.assertFalse(request.consume('id', wrong))
        self.assertFalse(request.consume('old', target))
        self.assertTrue(request.consume('id', target))
        self.assertFalse(request.consume('id', target))

    def test_password_and_unknown_controls_fail_closed(self):
        valid = dict(control_type=50004, password=False, focused=True, enabled=True)
        self.assertTrue(editable(**valid))
        for key, value in [('password', True), ('password', None), ('focused', None), ('enabled', False), ('control_type', 50000)]:
            self.assertFalse(editable(**{**valid, key: value}))

    def test_install_remove_restores_exact_config_and_preserves_learning(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'source', Path(tmp) / 'user'
            target.mkdir()
            self.payload(source)
            original = b'# user comment\npatch:\n  menu/page_size: 7\n'
            (target / 'default.custom.yaml').write_bytes(original)
            (target / 'quick_hk.userdb').write_bytes(b'learned')
            install(target, source)
            config = yaml.safe_load((target / 'default.custom.yaml').read_text(encoding='utf-8'))
            self.assertEqual(config['patch']['schema_list/+'], [{'schema': 'quick_hk'}])
            original_backup = json.loads((target / 'yuekey-install.json').read_text())['backup']
            self.assertEqual(str(install(target, source)), original_backup)
            self.assertEqual(uninstall(target), [])
            self.assertEqual((target / 'default.custom.yaml').read_bytes(), original)
            self.assertEqual((target / 'quick_hk.userdb').read_bytes(), b'learned')
            self.assertFalse((target / 'quick_hk.schema.yaml').exists())

    def test_existing_schema_list_and_later_edits_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'source', Path(tmp) / 'user'
            target.mkdir()
            self.payload(source)
            config = target / 'default.custom.yaml'
            config.write_text('patch:\n  schema_list:\n    - schema: other\n', encoding='utf-8')
            install(target, source)
            self.assertEqual(yaml.safe_load(config.read_text())['patch']['schema_list'],
                             [{'schema': 'other'}, {'schema': 'quick_hk'}])
            config.write_text('user edited this', encoding='utf-8')
            self.assertIn('default.custom.yaml', uninstall(target))
            self.assertEqual(config.read_text(), 'user edited this')

    def test_ambiguous_or_duplicate_config_fails_without_changes(self):
        configurations = [
            'patch:\n  menu/page_size: 5\n  menu/page_size: 7\n',
            'patch:\n  schema_list: []\n  schema_list/+: []\n',
            'patch:\n  schema_list/@0: {schema: other}\n',
            'patch:\n  schema_list: [invalid]\n',
        ]
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            config = target / 'default.custom.yaml'
            for original in configurations:
                with self.subTest(original=original):
                    config.write_text(original, encoding='utf-8')
                    with self.assertRaises(DeploymentError):
                        install(target, target / 'nonexistent-source')
                    self.assertEqual(config.read_text(encoding='utf-8'), original)
                    self.assertEqual(list(target.iterdir()), [config])

    def test_missing_backup_does_not_partially_remove_typing(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, target = Path(temporary) / 'source', Path(temporary) / 'user'
            target.mkdir()
            self.payload(source)
            (target / 'default.custom.yaml').write_text('patch: {}', encoding='utf-8')
            backup = install(target, source)
            (backup / 'default.custom.yaml').unlink()
            with self.assertRaises(FileNotFoundError):
                uninstall(target)
            for name in (*FILES, 'default.custom.yaml', 'yuekey-install.json'):
                self.assertTrue((target / name).is_file(), name)

    def test_invalid_late_manifest_entry_does_not_remove_typing(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, target = Path(temporary) / 'source', Path(temporary) / 'user'
            target.mkdir()
            self.payload(source)
            install(target, source)
            marker = target / 'yuekey-install.json'
            manifest = json.loads(marker.read_text())
            manifest['files']['unmanaged'] = {'existed': False, 'installed': 'invalid'}
            marker.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaises(ValueError):
                uninstall(target)
            self.assertTrue(marker.is_file())
            for name in FILES:
                self.assertTrue((target / name).is_file(), name)

    def test_device_shutdown_errors_release_decoder_and_do_not_escape_to_ui(self):
        for failure in ('abort', 'close'):
            with self.subTest(failure=failure):
                stopped, reading = threading.Event(), threading.Event()

                class Stream:
                    closed = False

                    def start(self):
                        pass

                    def read(self, _):
                        reading.set()
                        if not stopped.wait(2):
                            raise RuntimeError('Test capture did not stop')
                        raise RuntimeError('Device disconnected')

                    def abort(self):
                        stopped.set()
                        if failure == 'abort':
                            raise RuntimeError('Abort failed')

                    def close(self):
                        self.closed = True
                        if failure == 'close':
                            raise RuntimeError('Close failed')

                stream = Stream()
                recognizer = SimpleNamespace(vad=SimpleNamespace(reset=lambda: None))
                events = []
                with patch.dict('sys.modules', {'sounddevice': SimpleNamespace(RawInputStream=lambda **_: stream)}):
                    recording = WindowsRecording(recognizer, {'id': 'request'}, events.append)
                    self.assertTrue(reading.wait(1))
                    recording.stop()
                    recording.reader.join(3)
                    recording.thread.join(3)
                self.assertTrue(stream.closed)
                self.assertFalse(recording.reader.is_alive())
                self.assertFalse(recording.thread.is_alive())
                self.assertTrue(any(event['event'] == 'error' for event in events))
                self.assertFalse(any(event['event'] == 'result' for event in events))


if __name__ == '__main__':
    unittest.main()
