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
from nomi.ocr import recognize_page, effective_backend, VisionBackend, selected_backend, run_ocr

HAS_RENDERER = importlib.util.find_spec('pypdfium2') is not None and importlib.util.find_spec('PIL') is not None
HAS_TESSERACT = shutil.which('tesseract') is not None
HAS_VISION = sys.platform == 'darwin' and (Path(__file__).resolve().parent.parent / 'nomi/bin/nomi-vision').is_file()


class OcrTests(unittest.TestCase):
    def test_missing_command_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, 'Tesseract fehlt'):
            recognize_page(Path('not-read.pdf'), 0, Settings(ocr_command='nomi-missing-binary', ocr_backend='tesseract'), lambda: False)

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
        self.png = self.root/'scan.png'
        self.jpg = self.root/'scan.jpg'
        image.save(self.png)
        image.save(self.jpg)
        image.close()

    @unittest.skipUnless(HAS_RENDERER and (HAS_VISION or HAS_TESSERACT), 'Install Tesseract and .[ocr]')
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
                recognize_page(self.pdf, 0, Settings(ocr_command=self.slow_command(), ocr_backend='tesseract'), event.is_set)
        for timer in timers: timer.join()
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0][0].poll())
        self.assertFalse(processes[0][1].parent.exists())

    def test_timeout_cleans_raster_and_process(self):
        with self.assertRaises(TimeoutError):
            recognize_page(self.pdf, 0, Settings(ocr_command=self.slow_command(), timeout=.15, ocr_backend='tesseract'), lambda: False)

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
        from nomi.ocr import recognize_page, effective_backend, VisionBackend, selected_backend, run_ocr
        def which(command):
            return '/opt/homebrew/bin/tesseract' if command == '/opt/homebrew/bin/tesseract' else None
        with patch('nomi.ocr.shutil.which', side_effect=which):
            with self.assertRaises(AnalysisCancelled):
                recognize_page(Path('unused.pdf'), 0, Settings(ocr_backend='tesseract'), lambda: True)

    def test_auto_backend_selection_and_explicit_choices(self):
        with patch('nomi.ocr.sys.platform', 'darwin'):
            self.assertEqual(effective_backend('auto'), 'vision')
        with patch('nomi.ocr.sys.platform', 'linux'):
            self.assertEqual(effective_backend('auto'), 'tesseract')
            with self.assertRaisesRegex(ValueError, 'nur unter macOS'):
                VisionBackend().command(Path('x.png'), Settings())
        with self.assertRaises(ValueError):
            effective_backend('unknown')
        self.assertEqual(effective_backend('tesseract'), 'tesseract')

    @unittest.skipUnless(HAS_VISION, 'Requires compiled Vision helper on macOS')
    def test_real_vision_never_looks_for_tesseract(self):
        with patch('nomi.ocr.shutil.which', side_effect=AssertionError('No external OCR program allowed')):
            result = extract_document(self.pdf, settings=Settings(ocr_enabled=True))
        self.assertIn('Beispiel', result.text)
        self.assertIn('14.10.2026', result.text)
        self.assertEqual(result.ocr_backend, 'Apple Vision')

    @unittest.skipUnless(HAS_VISION, 'Requires compiled Vision helper on macOS')
    def test_vision_language_validation(self):
        with self.assertRaisesRegex(ValueError, 'Sprache'):
            VisionBackend().command(Path('x.png'), Settings(ocr_language='--bad'))
        command = VisionBackend().command(Path('x.png'), Settings(ocr_language='deu+eng'))
        self.assertEqual(command[-1], 'de-DE+en-US')
        with self.assertRaisesRegex(ValueError, 'unterstützt'):
            recognize_page(self.pdf, 0, Settings(ocr_backend='vision', ocr_language='zz-ZZ'), lambda: False)

    def test_shared_runner_cancels_and_terminates_vision_style_command(self):
        stopped = threading.Event()
        actual_popen = subprocess.Popen
        processes = []
        timers = []
        def start(*args, **kwargs):
            process = actual_popen(*args, **kwargs)
            processes.append(process)
            timer = threading.Timer(.2, stopped.set)
            timers.append(timer)
            timer.start()
            return process
        with patch('nomi.ocr.subprocess.Popen', side_effect=start):
            with self.assertRaises(AnalysisCancelled):
                run_ocr([sys.executable, '-c', 'import time; time.sleep(30)'], 5, stopped.is_set, 'Apple Vision')
        for timer in timers: timer.join()
        self.assertIsNotNone(processes[0].poll())

    @unittest.skipUnless(HAS_RENDERER and (HAS_VISION or HAS_TESSERACT), 'Needs OCR backend')
    def test_real_png_jpeg_ocr_preserves_sources(self):
        for path in (self.png, self.jpg):
            with self.subTest(format=path.suffix):
                original = path.read_bytes()
                with self.assertRaisesRegex(ValueError, 'OCR'):
                    extract_document(path)
                result = extract_document(path, settings=Settings(ocr_enabled=True, ocr_language='eng'))
                self.assertIn('Beispiel', result.text)
                self.assertTrue(result.used_ocr)
                self.assertEqual(path.read_bytes(), original)

    def test_image_cancel_and_corruption_never_call_ocr_process(self):
        from nomi.ocr import recognize_image
        settings = Settings(ocr_enabled=True)
        self.png.write_bytes(b'not an image')
        with patch('nomi.ocr.selected_backend') as backend, patch('nomi.ocr.run_ocr') as run:
            with self.assertRaises(AnalysisCancelled):
                recognize_image(self.png, settings, lambda: True)
            with self.assertRaisesRegex(ValueError, 'beschädigt'):
                recognize_image(self.png, settings, lambda: False)
            run.assert_not_called()

    def test_image_normalization_applies_rotation_and_white_background(self):
        from PIL import Image
        from nomi.ocr import recognize_image
        image = Image.new('RGBA', (20, 30), (0, 0, 0, 0))
        exif = Image.Exif(); exif[274] = 6
        image.save(self.png, exif=exif)
        image.close()
        original = self.png.read_bytes()
        def inspect(command, timeout, cancelled, label):
            with Image.open(command[0]) as normalized:
                self.assertEqual(normalized.size, (30, 20))
                self.assertEqual(normalized.getpixel((0, 0)), (255, 255, 255))
            return 'Rechnung'
        with patch('nomi.ocr.selected_backend') as backend, patch('nomi.ocr.run_ocr', side_effect=inspect):
            backend.return_value.command.side_effect = lambda path, settings: [str(path)]
            self.assertEqual(recognize_image(self.png, Settings(), lambda: False), 'Rechnung')
        self.assertEqual(self.png.read_bytes(), original)
