"""Optional local OCR. Raster images exist only in a temporary directory."""
from __future__ import annotations
import math
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import time
from .core import AnalysisCancelled, Settings


def recognize_page(path: Path, index: int, settings: Settings, cancelled) -> str:
    command = shutil.which(settings.ocr_command)
    if not command:
        raise ValueError('Tesseract fehlt. Bitte installieren oder den Programmpfad einstellen.')
    if not re.fullmatch(r'[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*', settings.ocr_language):
        raise ValueError('Ungültige OCR-Sprache, z.B. deu+eng verwenden.')
    try:
        import pypdfium2 as pdfium
        from PIL import Image  # noqa: F401; make the optional dependency error explicit
    except ImportError:
        raise ValueError('OCR-Zusatz fehlt. Bitte Nomi mit pip install -e ".[ocr]" installieren.')
    if cancelled():
        raise AnalysisCancelled()
    with TemporaryDirectory(prefix='nomi-ocr-') as folder:
        image_path = Path(folder) / 'page.png'
        with pdfium.PdfDocument(path) as document:
            page = document[index]
            try:
                width, height = page.get_size()
                scale = min(300 / 72, math.sqrt(12_000_000 / max(width * height, 1)))
                bitmap = page.render(scale=scale)
                try:
                    image = bitmap.to_pil()
                    try:
                        image.save(image_path)
                    finally:
                        image.close()
                finally:
                    bitmap.close()
            finally:
                page.close()
        if cancelled():
            raise AnalysisCancelled()
        # No shell; do not include stderr or document content in errors/logs.
        process = subprocess.Popen([command, str(image_path), 'stdout', '-l', settings.ocr_language],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        started = time.monotonic()
        try:
            while True:
                if cancelled():
                    raise AnalysisCancelled()
                if time.monotonic() - started >= settings.timeout:
                    raise TimeoutError('Zeitlimit der OCR-Seite erreicht.')
                try:
                    output, _ = process.communicate(timeout=.1)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if process.returncode:
                raise ValueError('Tesseract fehlgeschlagen. Sprachpakete und Scanqualität prüfen.')
            return output.decode('utf-8', errors='replace')
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()
