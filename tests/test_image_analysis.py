"""Synthetic scene images; no private files or model download."""
import base64
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from nomi.core import AnalysisCancelled, Settings
from nomi.image_analysis import encode_image, suggest_image, IMAGE_PROMPT

class ImageAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.path=Path(self.temp.name)/'scene.png'
        image=QImage(1800,1200,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
        self.assertTrue(image.save(str(self.path)))
    def tearDown(self):self.temp.cleanup()

    def test_bounded_jpeg_white_background_and_original_unchanged(self):
        before=self.path.read_bytes()
        image=QImage.fromData(base64.b64decode(encode_image(self.path)),'JPEG')
        self.assertLessEqual(max(image.width(),image.height()),1024)
        self.assertGreater(image.pixelColor(0,0).red(),245)
        self.assertEqual(self.path.read_bytes(),before)

    def test_cancel_corrupt_and_symlink(self):
        with self.assertRaises(AnalysisCancelled):encode_image(self.path, lambda:True)
        link=self.path.with_name('link.png');link.symlink_to(self.path)
        with self.assertRaises(ValueError):encode_image(link)
        self.path.write_bytes(b'broken')
        with self.assertRaises(ValueError):encode_image(self.path)

    def test_vision_prompt_and_capability(self):
        backend=Mock(supports_images=True)
        backend.suggest_images.return_value={'titel':'Haus'}
        self.assertEqual(suggest_image(backend,self.path,Settings())['titel'],'Haus')
        self.assertEqual(backend.suggest_images.call_args.kwargs['prompt'],IMAGE_PROMPT)
        with self.assertRaisesRegex(ValueError,'Vision'):
            suggest_image(Mock(supports_images=False),self.path,Settings())

    def test_worker_vision_without_ocr_and_text_backend_keeps_ocr(self):
        from nomi.app import Worker
        from unittest.mock import patch
        backend=Mock(supports_images=True)
        backend.suggest_images.return_value={'dokumenttyp':'Bild','titel':'Haus'}
        worker=Worker(Settings(engine='llama',template='{titel}'),[(0,self.path)],backend)
        results=[];worker.result.connect(lambda *args:results.append(args))
        with patch('nomi.app.extract_document') as ocr:
            worker.run();ocr.assert_not_called()
        self.assertEqual(results[0][1],'Haus.png')
        self.assertIn('Bildinhalt (Vision)',results[0][2])
        worker=Worker(Settings(engine='llama',image_analysis='ocr'),[(0,self.path)],backend)
        from nomi.core import Extraction
        with patch('nomi.app.extract_document',return_value=Extraction('Dokumenttext')) as ocr:
            worker.run();ocr.assert_called_once()
        backend.suggest.assert_called_once()
