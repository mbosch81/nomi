"""Real Qt event-loop checks using synthetic documents and an isolated settings file."""
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from PySide6.QtCore import QSettings, Qt, QMimeData, QUrl, QPoint, QPointF
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog
from nomi.app import Window, STYLE

class AppTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = QSettings(str(self.root / 'settings.ini'), QSettings.Format.IniFormat)
        self.patcher = patch('nomi.app.QSettings', return_value=self.store)
        self.patcher.start()
        self.window = Window()
        self.window.show()
        QTest.qWait(30)
        self.a = self.root / 'a.txt'
        self.a.write_text('Rechnung von Beispiel GmbH')
        self.b = self.root / 'b.csv'
        self.b.write_text('datum,betrag\n2026-10-14,42')

    def tearDown(self):
        self.wait_idle()
        self.window.close()
        self.app.processEvents()
        self.patcher.stop()
        self.temp.cleanup()

    def click(self, widget):
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def wait_idle(self):
        deadline = time.monotonic() + 5
        while self.window.busy() and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertFalse(self.window.busy())

    def test_import_edit_select_rename_undo(self):
        with patch.object(QFileDialog, 'getOpenFileNames', return_value=([str(self.a), str(self.b)], '')):
            self.click(self.window.files_button)
        self.assertEqual(len(self.window.paths), 2)
        self.click(self.window.none_button)
        self.assertEqual(self.window.selected(), [])
        self.click(self.window.all_button)
        self.window.table.item(0, 2).setText('Rechnung.txt')
        self.window.table.item(1, 2).setText('Tabelle.csv')
        self.assertTrue(self.a.exists())
        self.click(self.window.rename_button)
        self.assertFalse(self.a.exists())
        self.assertEqual((self.root / 'Rechnung.txt').read_text(), 'Rechnung von Beispiel GmbH')
        self.click(self.window.undo_button)
        self.assertTrue(self.a.exists())
        self.assertTrue(self.b.exists())
        self.click(self.window.clear_button)
        self.assertEqual(self.window.table.rowCount(), 0)
        self.assertTrue(self.a.exists())

    def test_folder_dialog_and_cancel_worker(self):
        nested = self.root / 'nested'
        nested.mkdir()
        (nested / 'c.md').write_text('Testnotiz')
        self.window.recursive.setChecked(True)
        with patch.object(QFileDialog, 'getExistingDirectory', return_value=str(self.root)):
            self.click(self.window.folder_button)
        self.assertEqual(len(self.window.paths), 3)
        self.window.model.setCurrentText('synthetic-model')
        calls = []
        def suggest(*args):
            calls.append(1)
            time.sleep(.15)
            return {'absender': 'Beispiel', 'dokumenttyp': 'Rechnung'}
        with patch('nomi.app.OllamaBackend.suggest', side_effect=suggest):
            self.click(self.window.analyze_button)
            QTest.qWait(40)
            self.assertFalse(self.window.rename_button.isEnabled())
            self.assertTrue(self.window.cancel_button.isEnabled())
            self.click(self.window.cancel_button)
            self.wait_idle()
        self.assertEqual(len(calls), 1)
        self.assertTrue(self.window.rename_button.isEnabled())
        self.assertIn('abgebrochen', self.window.status.text())
        self.assertTrue(self.a.exists())
        self.assertEqual(sum('abgebrochen' in self.window.table.item(r, 3).text() for r in range(3)), 2)

    def test_drag_drop_import(self):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.a))])
        enter = QDragEnterEvent(QPoint(20, 20), Qt.DropAction.CopyAction, mime,
                                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.window.dragEnterEvent(enter)
        self.assertTrue(enter.isAccepted())
        drop = QDropEvent(QPointF(20, 20), Qt.DropAction.CopyAction, mime,
                         Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.window.dropEvent(drop)
        self.assertTrue(drop.isAccepted())
        self.assertEqual(self.window.paths, [self.a])
        self.assertTrue(self.a.exists())

    def test_models_and_analysis(self):
        with patch('nomi.app.OllamaBackend.models', return_value=['synthetic-model']):
            self.click(self.window.connect_button)
            self.wait_idle()
        self.assertEqual(self.window.model.currentText(), 'synthetic-model')
        self.window.add([self.a])
        with patch('nomi.app.OllamaBackend.suggest', return_value={'datum': '2026-10-14', 'absender': 'Beispiel', 'dokumenttyp': 'Rechnung'}):
            self.click(self.window.analyze_button)
            self.wait_idle()
        self.assertEqual(self.window.table.item(0, 2).text(), '2026-10-14_Beispiel_Rechnung.txt')
        self.assertEqual(self.window.table.item(0, 3).text(), 'Bereit')
        self.assertTrue(self.a.exists())
