"""Real Qt event-loop checks using synthetic documents and an isolated settings file."""
import time
import threading
import importlib.util
import shutil
import unittest
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
        self.store.setValue('engine', 'ollama')
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

    def wait_idle(self, timeout=5):
        deadline = time.monotonic() + timeout
        while self.window.busy() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)  # Release the GIL while the worker imports/runs PDF libraries.
        self.assertFalse(self.window.busy())

    def test_settings_menu_moves_controls_and_persists_changes(self):
        self.assertFalse(self.window.settings_dialog.isVisible())
        for widget in (self.window.engine, self.window.url, self.window.model,
                       self.window.template, self.window.ocr_enabled, self.window.timeout):
            self.assertTrue(self.window.settings_dialog.isAncestorOf(widget))
            self.assertFalse(widget.isVisible())
        self.assertTrue(self.window.table.isVisible())
        self.assertTrue(self.window.settings_button.isVisible())
        self.click(self.window.settings_button)
        self.assertTrue(self.window.settings_dialog.isVisible())
        self.assertTrue(self.window.template.isVisible())
        self.window.template.setText('{absender}_{titel}')
        self.window.timeout.setValue(90)
        self.window.settings_dialog.close()
        self.app.processEvents()
        self.assertEqual(self.store.value('template'), '{absender}_{titel}')
        self.assertEqual(int(self.store.value('timeout')), 90)
        self.window.settings_action.trigger()
        self.app.processEvents()
        self.assertEqual(self.window.template.text(), '{absender}_{titel}')
        self.window.set_busy(True)
        self.assertFalse(self.window.template.isEnabled())
        self.window.set_busy(False)
        self.assertTrue(self.window.template.isEnabled())

    def test_model_catalog_selects_mistral_download_and_locks_while_busy(self):
        self.window.autoload.setChecked(False)
        self.window.engine.setCurrentIndex(self.window.engine.findData('llama'))
        self.window.show_settings()
        self.window.download_choice.setCurrentIndex(self.window.download_choice.findData('mistral'))
        self.assertIn('Mistral-7B-Instruct-v0.3-Q4_K_M.gguf', self.window.gguf.text())
        with patch.object(self.window, 'start_local_model') as start:
            self.click(self.window.download_button)
            start.assert_called_once_with(download='mistral')
        self.window.set_busy(True)
        self.assertFalse(self.window.download_choice.isEnabled())
        self.window.set_busy(False)
        self.window.download_choice.setCurrentIndex(self.window.download_choice.findData('qwen'))
        self.assertIn('Qwen3-4B-Q4_K_M.gguf', self.window.gguf.text())

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
        started = threading.Event()
        release = threading.Event()
        def suggest(*args):
            calls.append(1)
            started.set()
            release.wait(3)
            return {'absender': 'Beispiel', 'dokumenttyp': 'Rechnung'}
        with patch('nomi.app.OllamaBackend.suggest', side_effect=suggest):
            self.click(self.window.analyze_button)
            deadline = time.monotonic() + 3
            while not started.is_set() and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
            self.assertTrue(started.is_set())
            self.assertFalse(self.window.rename_button.isEnabled())
            self.assertTrue(self.window.cancel_button.isEnabled())
            self.click(self.window.cancel_button)
            release.set()
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

    def test_batch_suggestions_are_unique_and_manual_conflicts_visible(self):
        second = self.root/'second.txt'
        second.write_text('Rechnung Test AG')
        self.window.add([self.a, second])
        self.window.model.setCurrentText('synthetic-model')
        with patch('nomi.app.OllamaBackend.suggest', return_value={'absender': 'Test AG', 'dokumenttyp': 'Rechnung'}):
            self.click(self.window.analyze_button)
            self.wait_idle()
        names = [self.window.table.item(r, 2).text() for r in range(2)]
        self.assertEqual(names, ['Test_AG_Rechnung.txt', 'Test_AG_Rechnung_2.txt'])
        self.window.table.item(1, 2).setText(names[0])
        self.assertTrue(all('Namenskonflikt' in self.window.table.item(r, 3).text() for r in range(2)))
        with patch.object(self.window, 'error') as error:
            self.click(self.window.rename_button)
            error.assert_called_once()
        self.assertTrue(self.a.exists())
        self.assertTrue(second.exists())
        self.window.table.item(1, 0).setCheckState(Qt.CheckState.Unchecked)
        self.assertNotIn('Namenskonflikt', self.window.table.item(0, 3).text())

    def test_ocr_settings_are_persisted_and_passed_to_worker(self):
        self.window.ocr_enabled.setChecked(True)
        self.window.ocr_language.setText('eng')
        self.window.ocr_command.setText('/custom/tesseract')
        settings = self.window.settings()
        self.assertTrue(settings.ocr_enabled)
        self.assertEqual(settings.ocr_language, 'eng')
        self.assertEqual(settings.ocr_command, '/custom/tesseract')
        self.assertTrue(self.store.value('ocr_enabled'))
        self.window.add([self.a])
        self.window.model.setCurrentText('synthetic-model')
        from nomi.core import Extraction
        with patch('nomi.app.extract_document', return_value=Extraction('Synthetic OCR', True, True)) as extract_document:
            with patch('nomi.app.OllamaBackend.suggest', return_value={'dokumenttyp': 'Rechnung'}):
                self.click(self.window.analyze_button)
                self.wait_idle()
        from dataclasses import replace
        self.assertEqual(extract_document.call_args.kwargs['settings'], replace(settings, model='synthetic-model'))
        self.assertIn('OCR', self.window.table.item(0, 3).text())
        self.assertIn('Textausschnitt', self.window.table.item(0, 3).text())

    @unittest.skipUnless((shutil.which('tesseract') or (Path(__file__).resolve().parent.parent / 'nomi/bin/nomi-vision').is_file()) and importlib.util.find_spec('pypdfium2') and importlib.util.find_spec('PIL'), 'Install Tesseract and .[ocr]')
    def test_real_ocr_in_ui_worker(self):
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new('RGB', (1400, 500), 'white')
        draw = ImageDraw.Draw(image)
        draw.text((60, 80), 'Rechnung Beispiel GmbH', fill='black', font=ImageFont.load_default(size=55))
        source = self.root/'scan.pdf'
        image.save(source, 'PDF', resolution=150)
        image.close()
        original = source.read_bytes()
        self.window.add([source])
        self.window.ocr_enabled.setChecked(True)
        self.window.ocr_language.setText('eng')
        self.window.model.setCurrentText('synthetic-model')
        with patch('nomi.app.OllamaBackend.suggest', return_value={'dokumenttyp': 'Rechnung'}) as suggest:
            self.click(self.window.analyze_button)
            self.wait_idle(timeout=45)  # Native framework cold-start can exceed five seconds.
        self.assertIn('Beispiel', suggest.call_args.args[0])
        self.assertIn('OCR', self.window.table.item(0, 3).text())
        self.assertEqual(self.window.table.item(0, 2).text(), 'Rechnung.pdf')
        self.assertEqual(source.read_bytes(), original)

    def test_ocr_backend_controls_and_settings(self):
        from nomi.ocr import effective_backend
        self.assertEqual(self.window.ocr_backend.currentData(), 'auto')
        self.assertEqual(self.window.ocr_command.isHidden(), effective_backend('auto') != 'tesseract')
        self.window.ocr_backend.setCurrentIndex(self.window.ocr_backend.findData('tesseract'))
        self.assertFalse(self.window.ocr_command.isHidden())
        self.assertEqual(self.window.settings().ocr_backend, 'tesseract')
        self.window.ocr_backend.setCurrentIndex(self.window.ocr_backend.findData('vision'))
        self.assertTrue(self.window.ocr_command.isHidden())
        self.assertEqual(self.window.settings().ocr_backend, 'vision')

    def test_missing_local_model_keeps_analysis_disabled(self):
        self.window.autoload.setChecked(False)
        self.window.engine.setCurrentIndex(self.window.engine.findData('llama'))
        self.window.gguf.setText(str(self.root/'missing.gguf'))
        self.app.processEvents()
        self.assertFalse(self.window.busy())
        self.assertFalse(self.window.analyze_button.isEnabled())
        self.assertFalse(self.window.gguf.isHidden())
        self.assertTrue(self.window.url.isHidden())
        self.assertEqual(self.window.settings().engine, 'llama')

    def test_local_auto_load_runs_in_background_and_routes_analysis(self):
        from PySide6.QtCore import QTimer
        self.window.close()
        model=self.root/'test.gguf';model.write_bytes(b'GGUFtest')
        self.store.setValue('engine','llama');self.store.setValue('llama_model',str(model))
        began=threading.Event();release=threading.Event()
        class Backend:
            def suggest(self,text,settings):
                return {'absender':'Beispiel GmbH','dokumenttyp':'Rechnung'}
        class Engine:
            model=None
            running=False
            def start(self,path,cancelled,progress):
                began.set()
                while not release.wait(.01):
                    if cancelled():
                        from nomi.core import AnalysisCancelled
                        raise AnalysisCancelled()
                self.model=path;self.running=True;return Backend()
            def alive(self):return self.running
            def stop(self):self.running=False;self.model=None
        engine=Engine()
        with patch('nomi.app.LocalEngine',return_value=engine):
            self.window=Window()
        self.window.show()
        deadline=time.monotonic()+3
        while not began.is_set() and time.monotonic()<deadline:
            self.app.processEvents();time.sleep(.01)
        self.assertTrue(began.is_set())
        ticks=[];timer=QTimer();timer.timeout.connect(lambda:ticks.append(1));timer.start(10)
        try:
            deadline=time.monotonic()+3
            while len(ticks)<3 and time.monotonic()<deadline:
                self.app.processEvents();time.sleep(.01)
            self.assertGreater(len(ticks),2)
            self.assertFalse(self.window.analyze_button.isEnabled())
        finally:
            timer.stop()
            release.set()
            self.wait_idle()
        self.assertTrue(self.window.analyze_button.isEnabled())
        self.window.add([self.a]);self.click(self.window.analyze_button);self.wait_idle()
        self.assertEqual(self.window.table.item(0,2).text(),'Beispiel_GmbH_Rechnung.txt')
        self.window.close()
        self.assertFalse(engine.running)

    def test_close_during_local_start_cancels_without_blocking(self):
        from nomi.core import AnalysisCancelled
        self.window.close()
        model=self.root/'test.gguf';model.write_bytes(b'GGUFtest')
        self.store.setValue('engine','llama');self.store.setValue('llama_model',str(model))
        began=threading.Event()
        class Engine:
            model=None
            def start(self,path,cancelled,progress):
                began.set()
                while not cancelled():time.sleep(.01)
                raise AnalysisCancelled()
            def alive(self):return False
            def stop(self):pass
        with patch('nomi.app.LocalEngine',return_value=Engine()):self.window=Window()
        self.window.show()
        deadline=time.monotonic()+3
        while not began.is_set() and time.monotonic()<deadline:self.app.processEvents();time.sleep(.01)
        self.assertTrue(began.is_set())
        self.window.close();self.wait_idle();self.app.processEvents()
        self.assertFalse(self.window.isVisible())
