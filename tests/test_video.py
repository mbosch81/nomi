"""Synthetic-only video sampling, safety and settings checks."""
import base64
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch
from nomi.core import AnalysisCancelled, Settings
from nomi.video import sample_frames, runtime_tool, run_tool, suggest_video

class VideoTests(unittest.TestCase):
    def test_invalid_frame_counts(self):
        for count in (0, 13, True, 1.5):
            with self.assertRaises(ValueError):
                with sample_frames(Path('unused'), count):pass

    def test_text_backend_rejected_before_reading(self):
        with patch('nomi.video.sample_frames') as extract:
            with self.assertRaisesRegex(ValueError, 'Vision'):
                suggest_video(object(), Path('unused'), Settings(), lambda:False)
            extract.assert_not_called()

    def test_process_cancel_and_timeout(self):
        import sys
        with self.assertRaises(AnalysisCancelled):
            run_tool([sys.executable, '-c', 'import time; time.sleep(10)'], lambda:True, time.monotonic()+5)
        with self.assertRaises(TimeoutError):
            run_tool([sys.executable, '-c', 'import time; time.sleep(10)'], lambda:False, time.monotonic()+.1)

    def test_actual_frames_preview_and_no_original_changes(self):
        try:tool=runtime_tool('ffmpeg')
        except ValueError:self.skipTest('Build bundled FFmpeg before running integration test')
        with TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.avi'
            subprocess.run([str(tool), '-v','error','-f','lavfi','-i','testsrc=size=320x240:rate=5','-t','2','-c:v','mjpeg',str(path)],check=True)
            original=path.read_bytes()
            with sample_frames(path, 3) as frames:
                self.assertEqual(len(frames),3)
                self.assertEqual(sorted(t for t,_ in frames),[t for t,_ in frames])
                for _,encoded in frames:self.assertTrue(base64.b64decode(encoded).startswith(b'\xff\xd8'))
            from nomi.preview import load_preview
            self.assertFalse(load_preview(path)['image'].isNull())
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaises(AnalysisCancelled):
                with sample_frames(path, 3, cancelled=lambda:True):pass

    def test_vision_payload(self):
        from nomi.llama_backend import LlamaBackend
        response={'choices':[{'message':{'content':'{"datum":"","absender":"","empfaenger":"","dokumenttyp":"Video","titel":"Bunter Test","kennung":""}'}}]}
        with patch('nomi.llama_backend.local_request',return_value=response) as request:
            result=LlamaBackend('http://127.0.0.1', 'synthetic', supports_images=True).suggest_images([(1.0,'YWJj')],Settings())
            self.assertEqual(result['titel'],'Bunter Test')
            content=request.call_args.args[3]['messages'][0]['content']
            self.assertEqual(content[-1]['image_url']['url'],'data:image/jpeg;base64,YWJj')
