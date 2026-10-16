"""Native Windows safety checks; exercised by Windows CI, no mocked filesystem."""
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from nomi.core import undo, RenameError
from nomi.organize import organize_batch, secure_move

@unittest.skipUnless(os.name=='nt','Native Windows handles')
class WindowsFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name)
        self.archive=self.root/'archive';self.archive.mkdir()
        self.source=self.root/'source.txt';self.source.write_text('synthetic data')
    def tearDown(self):self.temp.cleanup()
    def test_move_undo_and_directory_cleanup(self):
        target=self.archive/'2026/Invoices/renamed.txt'
        records=organize_batch([(self.source,target)],self.archive)
        self.assertFalse(self.source.exists());self.assertEqual(target.read_text(),'synthetic data')
        undo(records);self.assertEqual(self.source.read_text(),'synthetic data')
        self.assertFalse((self.archive/'2026').exists())
    def test_late_collision_and_junction_are_rejected(self):
        target=self.archive/'foreign.txt';target.write_text('foreign')
        try:
            secure_move(self.source,target)
        except OSError:
            pass
        else:
            self.fail(f'Collision accepted: source_exists={self.source.exists()}, target_content={target.read_text()}')
        self.assertEqual(target.read_text(),'foreign');self.assertTrue(self.source.exists())
        outside=self.root/'outside';outside.mkdir();junction=self.archive/'junction'
        subprocess.run(['cmd','/c','mklink','/J',str(junction),str(outside)],check=True,capture_output=True)
        try:
            with self.assertRaises((ValueError,OSError)):organize_batch([(self.source,junction/'bad.txt')],self.archive)
            self.assertFalse(list(outside.iterdir()))
        finally:junction.rmdir()
    def test_directory_guard_blocks_replacement(self):
        from nomi.windows_files import directory_guard
        with directory_guard(self.archive):
            with self.assertRaises(OSError):self.archive.rename(self.root/'replaced')
    def test_partial_failure_rolls_back(self):
        second=self.root/'second.txt';second.write_text('second')
        def move(source,target):
            if source==second:raise OSError('synthetic failure')
            secure_move(source,target)
        with patch('nomi.organize.secure_move',side_effect=move):
            with self.assertRaises(RenameError) as error:organize_batch([(self.source,self.archive/'A/one.txt'),(second,self.archive/'B/two.txt')],self.archive)
        self.assertFalse(error.exception.records)
        self.assertTrue(self.source.exists());self.assertTrue(second.exists())
        self.assertFalse(list(self.archive.iterdir()))
