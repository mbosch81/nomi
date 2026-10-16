from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from nomi.core import Settings, AnalysisCancelled
from nomi.routing import LocalModelRouter, naming_template
from nomi.local_model import model_catalog

class RoutingTests(unittest.TestCase):
    def test_type_templates(self):
        settings=Settings(template='{datum}', image_template='{titel}', video_template='Video_{titel}')
        self.assertEqual(naming_template(settings,Path('a.pdf')),'{datum}')
        self.assertEqual(naming_template(settings,Path('a.PNG')),'{titel}')
        self.assertEqual(naming_template(settings,Path('a.mov')),'Video_{titel}')

    def test_switch_and_ocr_policy(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            for spec in model_catalog():
                (root/spec.filename).write_bytes(b'GGUF')
                if spec.projector:(root/spec.projector.filename).write_bytes(b'GGUF')
            engine=Mock();settings=Settings(text_model='mistral')
            router=LocalModelRouter(engine,settings,lambda:False,Mock())
            with patch('nomi.routing.model_directory',return_value=root), patch('nomi.routing.download_model_package') as download:
                router.backend_for(Path('a.txt'));router.backend_for(Path('a.jpg'));router.backend_for(Path('a.mp4'))
                self.assertIn('Mistral',engine.start.call_args_list[0].args[0].name)
                self.assertIn('Smol',engine.start.call_args_list[1].args[0].name)
                self.assertIn('projector',engine.start.call_args_list[2].kwargs)
                from dataclasses import replace
                router.settings=replace(settings,image_analysis='ocr');router.backend_for(Path('a.jpg'))
                self.assertNotIn('projector',engine.start.call_args.kwargs)
                download.assert_not_called()

    def test_missing_download_and_cancel(self):
        engine=Mock();router=LocalModelRouter(engine,Settings(),lambda:False,Mock())
        with TemporaryDirectory() as folder, patch('nomi.routing.model_directory',return_value=Path(folder)), patch('nomi.routing.download_model_package',return_value=(Path('vision.gguf'),Path('mmproj.gguf'))) as download:
            router.backend_for(Path('clip.mp4'))
            self.assertEqual(download.call_args.args[0],'smolvlm')
        router.cancelled=lambda:True
        with self.assertRaises(AnalysisCancelled):router.backend_for(Path('a.pdf'))
