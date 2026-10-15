"""Optional local OCR. Raster images exist only in a temporary directory."""
from __future__ import annotations
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Protocol
from tempfile import TemporaryDirectory
import time
from .core import AnalysisCancelled, Settings


class OcrBackend(Protocol):
    label: str

    def command(self, image: Path, settings: Settings) -> list[str]: ...


def effective_backend(name: str) -> str:
    if name == 'auto':
        return 'vision' if sys.platform == 'darwin' else 'tesseract'
    if name not in {'vision', 'tesseract'}:
        raise ValueError('Unbekanntes OCR-Backend.')
    return name


class VisionBackend:
    label = 'Apple Vision'

    def command(self, image: Path, settings: Settings) -> list[str]:
        if sys.platform != 'darwin':
            raise ValueError('Apple Vision ist nur unter macOS verfügbar.')
        helper = Path(__file__).resolve().parent / 'bin' / 'nomi-vision'
        if not helper.is_file():
            raise ValueError('Apple-Vision-Helfer fehlt. Bitte das vollständige Nomi-App-Bundle verwenden oder build_support/build_vision.py ausführen.')
        mapping = {'deu': 'de-DE', 'eng': 'en-US', 'fra': 'fr-FR', 'spa': 'es-ES', 'ita': 'it-IT'}
        languages = [mapping.get(part, part) for part in settings.ocr_language.split('+')]
        if not languages or any(not re.fullmatch(r'[a-z]{2}-[A-Z]{2}', part) for part in languages):
            raise ValueError('Ungültige Vision-Sprache, z.B. deu+eng oder de-DE+en-US verwenden.')
        return [str(helper), str(image), '+'.join(languages)]


class TesseractBackend:
    label = 'Tesseract'

    def command(self, image: Path, settings: Settings) -> list[str]:
        command = shutil.which(settings.ocr_command)
        if not command and settings.ocr_command == 'tesseract':
            # Finder does not necessarily inherit the shell's Homebrew PATH.
            for candidate in ('/opt/homebrew/bin/tesseract', '/usr/local/bin/tesseract'):
                command = shutil.which(candidate)
                if command:
                    break
        if not command:
            raise ValueError('Tesseract fehlt. Bitte installieren oder den Programmpfad einstellen.')
        if not re.fullmatch(r'[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*', settings.ocr_language):
            raise ValueError('Ungültige OCR-Sprache, z.B. deu+eng verwenden.')
        return [command, str(image), 'stdout', '-l', settings.ocr_language]


def selected_backend(settings: Settings) -> OcrBackend:
    return VisionBackend() if effective_backend(settings.ocr_backend) == 'vision' else TesseractBackend()


def run_ocr(command: list[str], timeout: float, cancelled, label: str) -> str:
    if cancelled():
        raise AnalysisCancelled()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    started = time.monotonic()
    try:
        while True:
            if cancelled():
                raise AnalysisCancelled()
            if time.monotonic() - started >= timeout:
                raise TimeoutError('Zeitlimit der OCR-Seite erreicht.')
            try:
                output, _ = process.communicate(timeout=.1)
                break
            except subprocess.TimeoutExpired:
                continue
        if process.returncode:
            if label == 'Apple Vision' and process.returncode == 3:
                raise ValueError('Apple Vision unterstützt die eingestellte Sprache nicht.')
            raise ValueError(f'{label} fehlgeschlagen. Sprache und Scanqualität prüfen.')
        return output.decode('utf-8', errors='replace')
    finally:
        if process.poll() is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        process.communicate()


def recognize_page(path: Path, index: int, settings: Settings, cancelled) -> str:
    backend = selected_backend(settings)
    # Validate availability and settings before doing expensive PDF rendering.
    backend.command(Path('page.png'), settings)
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
        # No shell; stderr and document content are never logged.
        return run_ocr(backend.command(image_path, settings), settings.timeout, cancelled, backend.label)


def recognize_image(path: Path, settings: Settings, cancelled) -> str:
    """Normalize a scan copy for OCR; never write to the imported image."""
    backend = selected_backend(settings)
    backend.command(Path('scan.png'), settings)
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError:
        raise ValueError('OCR-Zusatz fehlt. Bitte Nomi mit pip install -e ".[ocr]" installieren.')
    if cancelled():
        raise AnalysisCancelled()
    with TemporaryDirectory(prefix='nomi-image-ocr-') as folder:
        image_path = Path(folder) / 'scan.png'
        try:
            with Image.open(path) as source:
                if source.format not in {'PNG', 'JPEG'}:
                    raise ValueError('Nur PNG- und JPEG-Bilddateien werden unterstützt.')
                if source.width * source.height > 48_000_000:
                    raise ValueError('Bild ist zu groß (maximal 48 Megapixel).')
                with ImageOps.exif_transpose(source) as oriented:
                    scale = min(1, math.sqrt(12_000_000 / max(oriented.width * oriented.height, 1)))
                    oriented.thumbnail((max(1, int(oriented.width * scale)), max(1, int(oriented.height * scale))))
                    with oriented.convert('RGBA') as rgba, Image.new('RGB', rgba.size, 'white') as normalized:
                        normalized.paste(rgba, mask=rgba.getchannel('A'))
                        normalized.save(image_path)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ValueError('Bilddatei kann nicht sicher gelesen werden oder ist beschädigt.') from None
        if cancelled():
            raise AnalysisCancelled()
        return run_ocr(backend.command(image_path, settings), settings.timeout, cancelled, backend.label)
