import hashlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from nomi.core import AnalysisCancelled
from nomi.local_model import download_default_model, download_model, model_spec, check_model
from dataclasses import replace


class ModelDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'model.gguf'
        self.payload = b'GGUFsynthetic-model'
        self.patches = [patch('nomi.local_model.MODEL_BYTES', len(self.payload)),
                        patch('nomi.local_model.MODEL_SHA256', hashlib.sha256(self.payload).hexdigest()),
                        patch('nomi.local_model.urlopen', return_value=io.BytesIO(self.payload))]
        for item in self.patches:
            item.start();self.addCleanup(item.stop)

    def test_verified_download_is_reused_without_network(self):
        self.assertEqual(download_default_model(self.path), self.path)
        check_model(self.path)
        with patch('nomi.local_model.urlopen', side_effect=AssertionError('No repeated download')):
            self.assertEqual(download_default_model(self.path), self.path)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_bad_checksum_and_cancel_leave_no_partial_files(self):
        with patch('nomi.local_model.MODEL_SHA256', '0'*64):
            with self.assertRaisesRegex(ValueError, 'Prüfsumme'):
                download_default_model(self.path)
        self.assertEqual(list(self.path.parent.iterdir()), [])
        with self.assertRaises(AnalysisCancelled):
            download_default_model(self.path, cancelled=lambda: True)
        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_cancel_during_download_cleans_partial(self):
        cancelled = [False]
        with self.assertRaises(AnalysisCancelled):
            download_default_model(self.path, cancelled=lambda: cancelled[0], progress=lambda _: cancelled.__setitem__(0, True))
        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_existing_different_model_is_never_overwritten(self):
        self.path.write_bytes(b'GGUFdifferent')
        with self.assertRaises(ValueError):
            download_default_model(self.path)
        self.assertEqual(self.path.read_bytes(), b'GGUFdifferent')

    def test_mistral_download_uses_its_own_url_and_checksum(self):
        model = replace(model_spec('mistral'), size=len(self.payload),
                        sha256=hashlib.sha256(self.payload).hexdigest())
        with patch('nomi.local_model.model_spec', return_value=model), \
             patch('nomi.local_model.urlopen', return_value=io.BytesIO(self.payload)) as fetch:
            self.assertEqual(download_model('mistral', self.path), self.path)
            fetch.assert_called_once_with(model.url, timeout=30)
        self.assertEqual(self.path.read_bytes(), self.payload)

    def test_unknown_model_is_rejected_before_network(self):
        with self.assertRaisesRegex(ValueError, 'Unbekanntes'):
            download_model('unknown', self.path)
        self.assertFalse(self.path.exists())

    def test_network_timeout_cleans_partial_file(self):
        with patch('nomi.local_model.urlopen', side_effect=TimeoutError('network timeout')):
            with self.assertRaises(TimeoutError):
                download_model('mistral', self.path)
        self.assertEqual(list(self.path.parent.iterdir()), [])
