"""Platform path checks without starting external runtimes."""
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from nomi.llama_backend import runtime_path
from nomi.video import runtime_tool

class PortableRuntimeTests(unittest.TestCase):
    def test_windows_helpers_use_executable_suffix(self):
        with patch('nomi.llama_backend.os', SimpleNamespace(name='nt')), patch('nomi.video.os', SimpleNamespace(name='nt')), patch.object(Path, 'is_file', return_value=True):
            self.assertEqual(runtime_path().name, 'llama-server.exe')
            self.assertEqual(runtime_tool('ffmpeg').name, 'ffmpeg.exe')
            self.assertEqual(runtime_tool('ffprobe').name, 'ffprobe.exe')

    def test_posix_helpers_keep_native_names(self):
        with patch('nomi.llama_backend.os', SimpleNamespace(name='posix')), patch('nomi.video.os', SimpleNamespace(name='posix')), patch.object(Path, 'is_file', return_value=True):
            self.assertEqual(runtime_path().name, 'llama-server')
            self.assertEqual(runtime_tool('ffmpeg').name, 'ffmpeg')
