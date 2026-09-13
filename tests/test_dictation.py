"""Dictation ownership, settings and model setup without live audio or input."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quick_hk.dictation_setup import download, digest
from quick_hk.dictation_state import Session, Target
from quick_hk.dictation_worker import Recognizer, join_chunks
from quick_hk.settings import Settings, SettingsError
from quick_hk.deployment import _schema_custom
import yaml


class DictationTests(unittest.TestCase):
    def test_bundled_setup_is_offline_and_rejects_corrupt_models(self):
        from quick_hk import dictation_setup as setup
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'yuekey-speech').touch()
            (root / 'model').write_bytes(b'verified')
            with patch.object(setup, 'BUNDLED_RUNTIME', root), patch.object(setup, 'BUNDLED_MODELS', root), \
                    patch.object(setup, 'model_hashes', return_value={'model': digest(root / 'model')}), \
                    patch.object(setup.os, 'geteuid', return_value=1000), \
                    patch.object(setup.subprocess, 'run') as execute, \
                    patch.object(setup, 'prepare_models') as download_models:
                self.assertTrue(setup.status(verify=True)['ready'])
                setup.setup()
                self.assertEqual(execute.call_args.args[0], [str(root / 'yuekey-speech'), '--models', str(root), '--check'])
                download_models.assert_not_called()
                (root / 'model').write_bytes(b'corrupt')
                self.assertFalse(setup.status(verify=True)['ready'])
                with self.assertRaisesRegex(RuntimeError, 'Reinstall'):
                    setup.setup()
                self.assertEqual(execute.call_count, 1)

    def test_result_requires_same_request_field_and_finishing_state(self):
        target = Target('/field/1', 8, 42)
        session = Session('request', target)
        self.assertFalse(session.consume('request', target))
        session.state = 'finishing'
        for wrong in [Target('/field/2', 8, 42), Target('/field/1', 9, 42), Target('/field/1', 8, 43)]:
            self.assertFalse(session.consume('request', wrong))
        self.assertFalse(session.consume('previous-request', target))
        self.assertTrue(session.consume('request', target))
        self.assertFalse(session.consume('request', target))

    def test_cancelled_session_cannot_commit(self):
        session = Session('x', Target('/field', 1, 1), 'finishing', consumed=True)
        self.assertFalse(session.consume('x', session.target))

    def test_control_conflict_and_frontend_scoping(self):
        settings = Settings(dictation_enabled=True, switch_key='Control_L')
        self.assertEqual(settings.effective_dictation_key, 'Control_R')
        ibus = yaml.safe_load(_schema_custom(settings, 'ibus'))['patch']
        fcitx = yaml.safe_load(_schema_custom(settings, 'fcitx5'))['patch']
        self.assertEqual(ibus['engine/processors/@before 0'], 'quick_hk_dictation')
        self.assertNotIn('engine/processors/@before 0', fcitx)
        self.assertFalse(fcitx['quick_hk/dictation_enabled'])
        self.assertFalse(Settings().dictation_enabled)

    def test_invalid_preferences(self):
        for values in [{'dictation_enabled': 1}, {'dictation_punctuation': 'true'},
                       {'dictation_key': 'Shift_L'}, {'dictation_microphone': 'bad\nnode'}]:
            with self.assertRaises(SettingsError):
                Settings(**values)

    def test_punctuation_does_not_rewrite_words(self):
        r = object.__new__(Recognizer)
        class Converter:
            def convert(self, text): return text
        class Punctuation:
            def add_punctuation(self, text): return '我不知道。'
        r.traditional, r.punctuation = Converter(), Punctuation()
        self.assertEqual(r.finish(['我唔知'], True), '我唔知')
        r.punctuation.add_punctuation = lambda _: '我唔知。'
        self.assertEqual(r.finish(['我唔知'], True), '我唔知。')
        self.assertEqual(r.finish(['我唔知'], False), '我唔知')
        self.assertEqual(join_chunks(['hello', 'world', '我哋', '去食飯']), 'hello world我哋去食飯')

    def test_download_hash_failure_never_replaces_working_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model'
            path.write_bytes(b'original')
            response = io.BytesIO(b'wrong')
            response.status = 200
            with patch('urllib.request.urlopen', return_value=response):
                with self.assertRaises(RuntimeError):
                    download('https://example.invalid/model', path, '0' * 64)
            self.assertEqual(path.read_bytes(), b'original')
            self.assertFalse(path.with_name('model.part').exists())

    def test_verified_download_is_reused_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model'
            path.write_bytes(b'verified')
            with patch('urllib.request.urlopen') as network:
                download('https://example.invalid/model', path, digest(path))
                network.assert_not_called()

    def test_server_ignoring_range_restarts_partial_download(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model'
            path.with_name('model.part').write_bytes(b'old partial')
            fixture = Path(directory) / 'fixture'
            fixture.write_bytes(b'complete')
            response = io.BytesIO(b'complete')
            response.status = 200
            with patch('urllib.request.urlopen', return_value=response):
                download('https://example.invalid/model', path, digest(fixture))
            self.assertEqual(path.read_bytes(), b'complete')
