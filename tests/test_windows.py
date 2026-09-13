"""Windows state and deployment contracts; safe to run on any platform."""
import json
from pathlib import Path
import tempfile
import unittest

import yaml
from quick_hk.windows_setup import FILES, install, uninstall
from quick_hk.windows_state import DoubleControl, Request, Target, editable


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


if __name__ == '__main__':
    unittest.main()
