import hashlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from nomi.core import AnalysisCancelled
from nomi.local_model import download_default_model, check_model


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
