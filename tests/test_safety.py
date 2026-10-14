from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from nomi.core import rename_batch, undo, move_no_replace, RenameError, make_name

class SafetyTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = self.root / 'a.txt'
        self.b = self.root / 'b.txt'
        self.a.write_text('alpha')
        self.b.write_text('beta')

    def test_duplicate_source_rejected_before_changes(self):
        with self.assertRaises(ValueError):
            rename_batch([(self.a, 'x.txt'), (self.a, 'y.txt')])
        self.assertEqual(self.a.read_text(), 'alpha')
        self.assertFalse((self.root / 'x.txt').exists())

    def test_atomic_destination_reservation(self):
        with self.assertRaises(FileExistsError):
            move_no_replace(self.a, self.b)
        self.assertEqual(self.a.read_text(), 'alpha')
        self.assertEqual(self.b.read_text(), 'beta')

    def test_rollback_after_second_move_fails(self):
        def move(source, target):
            if source == self.b:
                raise OSError('synthetic failure')
            move_no_replace(source, target)
        with patch('nomi.core.move_no_replace', side_effect=move):
            with self.assertRaises(RenameError) as error:
                rename_batch([(self.a, 'x.txt'), (self.b, 'y.txt')])
        self.assertEqual(error.exception.records, [])
        self.assertEqual(self.a.read_text(), 'alpha')
        self.assertTrue(self.b.exists())
        self.assertFalse((self.root / 'x.txt').exists())

    def test_incomplete_rollback_exposes_recoverable_history(self):
        def move(source, target):
            if source == self.b or target == self.a:
                raise OSError('synthetic failure')
            move_no_replace(source, target)
        with patch('nomi.core.move_no_replace', side_effect=move):
            with self.assertRaises(RenameError) as error:
                rename_batch([(self.a, 'x.txt'), (self.b, 'y.txt')])
        self.assertEqual(len(error.exception.records), 1)
        undo(error.exception.records)
        self.assertEqual(self.a.read_text(), 'alpha')

    def test_undo_refuses_occupied_original(self):
        records = rename_batch([(self.a, 'x.txt')])
        self.a.write_text('external')
        with self.assertRaises(ValueError):
            undo(records)
        self.assertEqual(self.a.read_text(), 'external')
        self.assertEqual(records[0].after.read_text(), 'alpha')

    def test_failed_undo_rolls_back(self):
        records = rename_batch([(self.a, 'x.txt'), (self.b, 'y.txt')])
        def move(source, target):
            if target == self.a:
                raise OSError('synthetic failure')
            move_no_replace(source, target)
        with patch('nomi.core.move_no_replace', side_effect=move):
            with self.assertRaises(RenameError) as error:
                undo(records)
        self.assertEqual(error.exception.records, records)
        self.assertFalse(self.a.exists())
        self.assertFalse(self.b.exists())
        undo(records)
        self.assertTrue(self.a.exists())
        self.assertTrue(self.b.exists())

    def test_invalid_calendar_date(self):
        with self.assertRaises(ValueError):
            make_name({'datum': '2026-02-30'}, self.a, '{datum}')

    def test_incomplete_undo_rollback_retains_only_pending_records(self):
        records = rename_batch([(self.a, 'x.txt'), (self.b, 'y.txt')])
        def move(source, target):
            if target == self.a or target.name == 'y.txt':
                raise OSError('synthetic failure')
            move_no_replace(source, target)
        with patch('nomi.core.move_no_replace', side_effect=move):
            with self.assertRaises(RenameError) as error:
                undo(records)
        self.assertEqual(error.exception.records, records[:1])
        self.assertEqual(self.b.read_text(), 'beta')
        undo(error.exception.records)
        self.assertEqual(self.a.read_text(), 'alpha')
