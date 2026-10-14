import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch
from nomi.core import AnalysisCancelled, Settings, extract_document
from nomi.ocr import recognize_page

HAS_RENDERER = importlib.util.find_spec('pypdfium2') is not None and importlib.util.find_spec('PIL') is not None
HAS_TESSERACT = shutil.which('tesseract') is not None


class OcrTests(unittest.TestCase):
    def test_missing_command_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, 'Tesseract fehlt'):
            recognize_page(Path('not-read.pdf'), 0, Settings(ocr_command='nomi-missing-binary'), lambda: False)

    @unittest.skipUnless(HAS_RENDERER, 'Install .[ocr] for rendering tests')
    def setUp(self):
        from PIL import Image, ImageDraw, ImageFont
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root/'scan.pdf'
        image = Image.new('RGB', (1400, 500), 'white')
        draw = ImageDraw.Draw(image)
        draw.text((60, 80), 'Rechnung Beispiel GmbH', fill='black', font=ImageFont.load_default(size=55))
        draw.text((60, 180), 'Datum: 14.10.2026', fill='black', font=ImageFont.load_default(size=55))
        image.save(self.pdf, 'PDF', resolution=150)
        image.close()

    @unittest.skipUnless(HAS_RENDERER and HAS_TESSERACT, 'Install Tesseract and .[ocr]')
    def test_real_image_pdf_ocr_preserves_original(self):
        original = self.pdf.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Kein Text'):
            extract_document(self.pdf)
        result = extract_document(self.pdf, settings=Settings(ocr_enabled=True, ocr_language='eng'))
        self.assertIn('Beispiel', result.text)
        self.assertIn('14.10.2026', result.text)
        self.assertTrue(result.used_ocr)
        self.assertFalse(result.truncated)
        self.assertEqual(self.pdf.read_bytes(), original)

    def slow_command(self):
        path = self.root/'slow-tesseract'
        path.write_text(f'#!{sys.executable}\nimport time\ntime.sleep(30)\n')
        path.chmod(0o700)
        return str(path)

    def test_cancellation_kills_process_and_cleans_raster(self):
        event = threading.Event()
        processes = []
        actual_popen = subprocess.Popen
        timers = []
        def start(*args, **kwargs):
            process = actual_popen(*args, **kwargs)
            processes.append((process, Path(args[0][1])))
            timer = threading.Timer(.2, event.set)
            timers.append(timer)
            timer.start()
            return process
        with patch('nomi.ocr.subprocess.Popen', side_effect=start):
            with self.assertRaises(AnalysisCancelled):
                recognize_page(self.pdf, 0, Settings(ocr_command=self.slow_command()), event.is_set)
        for timer in timers: timer.join()
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0][0].poll())
        self.assertFalse(processes[0][1].parent.exists())

    def test_timeout_cleans_raster_and_process(self):
        with self.assertRaises(TimeoutError):
            recognize_page(self.pdf, 0, Settings(ocr_command=self.slow_command(), timeout=.15), lambda: False)

    def test_mixed_document_ocr_only_for_scanned_page(self):
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=595, height=842)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 30 750 Td (Native text page with enough useful document content) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        writer.add_page(PdfReader(self.pdf).pages[0])
        mixed = self.root/'mixed.pdf';writer.write(mixed)
        with patch('nomi.ocr.recognize_page', return_value='Recognized second page') as recognize:
            result = extract_document(mixed, settings=Settings(ocr_enabled=True))
        self.assertEqual(recognize.call_args.args[1], 1)
        recognize.assert_called_once()
        self.assertIn('Native text page', result.text)
        self.assertIn('Recognized second page', result.text)
        self.assertTrue(result.used_ocr)

    def test_default_tesseract_resolves_homebrew_without_shell_path(self):
        from nomi.ocr import recognize_page
        def which(command):
            return '/opt/homebrew/bin/tesseract' if command == '/opt/homebrew/bin/tesseract' else None
        with patch('nomi.ocr.shutil.which', side_effect=which):
            with self.assertRaises(AnalysisCancelled):
                recognize_page(Path('unused.pdf'), 0, Settings(), lambda: True)
