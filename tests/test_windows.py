"""Windows state and deployment contracts; safe to run on any platform."""
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import yaml
from quick_hk.windows_setup import FILES, install, uninstall
from quick_hk.windows_state import DoubleControl, Request, Target, editable
from quick_hk.rime_config import DeploymentError
from quick_hk.dictation_worker import WindowsRecording


class WindowsTests(unittest.TestCase):
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
            for name in FILES:
                (source / name).parent.mkdir(parents=True, exist_ok=True)
                (source / name).write_text(name, encoding='utf-8')
            original = b'# user comment\npatch:\n  menu/page_size: 7\n'
            (target / 'default.custom.yaml').write_bytes(original)
            (target / 'quick_hk.userdb').write_bytes(b'learned')
            install(target, source)
            config = yaml.safe_load((target / 'default.custom.yaml').read_text(encoding='utf-8'))
            self.assertEqual(config['patch']['schema_list/+'], [{'schema': 'quick_hk'}])
            with self.assertRaises(ValueError):
                install(target, source)
            self.assertEqual(uninstall(target), [])
            self.assertEqual((target / 'default.custom.yaml').read_bytes(), original)
            self.assertEqual((target / 'quick_hk.userdb').read_bytes(), b'learned')
            self.assertFalse((target / 'quick_hk.schema.yaml').exists())

    def test_existing_schema_list_and_later_edits_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'source', Path(tmp) / 'user'
            target.mkdir()
            for name in FILES:
                (source / name).parent.mkdir(parents=True, exist_ok=True)
                (source / name).write_text(name, encoding='utf-8')
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
            for name in FILES:
                (source / name).parent.mkdir(parents=True, exist_ok=True)
                (source / name).write_text(name, encoding='utf-8')
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
            for name in FILES:
                (source / name).parent.mkdir(parents=True, exist_ok=True)
                (source / name).write_text(name, encoding='utf-8')
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
