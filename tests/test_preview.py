import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool
from nomi.preview import PreviewPanel, load_preview


class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.panel = PreviewPanel()
        self.panel.resize(480, 600)
        self.panel.show()

    def tearDown(self):
        QThreadPool.globalInstance().waitForDone(5000)
        self.app.processEvents()
        self.panel.close()
        self.temp.cleanup()

    def wait_ready(self):
        deadline = time.monotonic() + 5
        while (self.panel._active or self.panel._pending) and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIsNone(self.panel._active)
        self.app.processEvents()

    def test_pdf_page_navigation_and_original_preserved(self):
        from pypdf import PdfWriter
        path = self.root/'pages.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=400)
        writer.add_blank_page(width=400, height=300)
        writer.write(path)
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        self.panel.show_path(path);self.wait_ready()
        self.assertEqual(self.panel.counter.text(), 'Seite 1 / 2')
        self.assertFalse(self.panel._image.isNull())
        self.assertFalse(self.panel.previous.isEnabled())
        self.assertTrue(self.panel.next.isEnabled())
        self.panel.name.setText('Rechnung.pdf')
        self.panel.turn(1);self.wait_ready()
        self.assertEqual(self.panel.name.text(), 'Rechnung.pdf')
        self.assertEqual(self.panel.counter.text(), 'Seite 2 / 2')
        self.assertFalse(self.panel.next.isEnabled())
        self.panel.turn(-1);self.wait_ready()
        self.assertEqual(self.panel.page, 0)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)

    def test_text_is_plain_bounded_and_supports_windows_encoding(self):
        path = self.root/'letter.md'
        path.write_bytes('<script>ä</script>'.encode('cp1252'))
        self.panel.show_path(path);self.wait_ready()
        self.assertEqual(self.panel.text.toPlainText(), '<script>ä</script>')
        path.write_bytes(b'x'*(256*1024+10))
        result = load_preview(path)
        self.assertTrue(result['truncated'])
        self.assertEqual(len(result['text']), 256*1024)

    def test_image_preview_and_damage(self):
        from PySide6.QtGui import QImage
        path = self.root/'image.png'
        image = QImage(40, 60, QImage.Format.Format_RGB32)
        image.fill(0xffffffff);self.assertTrue(image.save(str(path)))
        self.panel.show_path(path);self.wait_ready()
        self.assertFalse(self.panel._image.isNull())
        self.panel.zoom.setCurrentIndex(1)
        self.app.processEvents()
        self.assertFalse(self.panel.scroll.widgetResizable())
        self.panel.zoom.setCurrentIndex(0)
        self.app.processEvents()
        self.assertTrue(self.panel.scroll.widgetResizable())
        path.write_bytes(b'broken')
        self.panel.show_path(path);self.wait_ready()
        self.assertIn('beschädigt', self.panel.message.text())
        self.assertIs(self.panel.stack.currentWidget(), self.panel.message)

    def test_encrypted_pdf_has_inline_error(self):
        from pypdf import PdfWriter
        path = self.root/'encrypted.pdf'
        writer = PdfWriter();writer.add_blank_page(width=300, height=400)
        writer.encrypt('secret-for-synthetic-test');writer.write(path)
        self.panel.show_path(path);self.wait_ready()
        self.assertIn('passwortgeschützt', self.panel.message.text())

    def test_rapid_switch_and_clear_ignore_old_worker_results(self):
        began, release = threading.Event(), threading.Event()
        path = self.root/'first.txt';path.write_text('first')
        other = self.root/'second.txt';other.write_text('second')
        actual = load_preview
        def slow(source, page):
            if source == path:
                began.set();release.wait(3)
            return actual(source, page)
        with patch('nomi.preview.load_preview', side_effect=slow):
            self.panel.show_path(path)
            self.assertTrue(began.wait(2))
            self.panel.show_path(other)
            release.set();self.wait_ready()
        self.assertEqual(self.panel.text.toPlainText(), 'second')
        self.panel.show_path(other);self.panel.show_path(None);self.wait_ready()
        self.assertIsNone(self.panel.path)
        self.assertEqual(self.panel.text.toPlainText(), '')
        self.assertIs(self.panel.stack.currentWidget(), self.panel.message)
