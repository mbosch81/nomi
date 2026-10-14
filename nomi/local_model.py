"""A pinned data-only model download; no runtime executable is downloaded here."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
from urllib.request import urlopen
from .core import AnalysisCancelled

MODEL_FILENAME = 'Qwen3-4B-Q4_K_M.gguf'
MODEL_REVISION = 'bc640142c66e1fdd12af0bd68f40445458f3869b'
MODEL_URL = f'https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/{MODEL_REVISION}/{MODEL_FILENAME}'
MODEL_SHA256 = '7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5'
MODEL_BYTES = 2497280256


def model_directory() -> Path:
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'Nomi' / 'models'
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'Nomi' / 'models'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'nomi' / 'models'


def default_model_path() -> Path:
    return model_directory() / MODEL_FILENAME


def check_model(path: Path):
    if path.suffix.lower() != '.gguf' or not path.is_file():
        raise ValueError('Bitte eine vorhandene GGUF-Modelldatei auswählen.')
    with path.open('rb') as handle:
        if handle.read(4) != b'GGUF':
            raise ValueError('Die Datei ist kein gültiges GGUF-Modell.')


def file_digest(path: Path, cancelled=lambda: False) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        while block := handle.read(4 * 1024 * 1024):
            if cancelled():
                raise AnalysisCancelled()
            digest.update(block)
    return digest.hexdigest()


def download_default_model(destination: Path | None = None, cancelled=lambda: False,
                           progress=lambda message: None) -> Path:
    destination = destination if destination is not None else default_model_path()
    if destination.exists():
        progress('Vorhandenes Standardmodell wird geprüft …')
        if destination.stat().st_size != MODEL_BYTES or file_digest(destination, cancelled) != MODEL_SHA256:
            raise ValueError('Die vorhandene Modelldatei stimmt nicht mit dem Standardmodell überein; sie wird nicht überschrieben.')
        return destination
    if cancelled():
        raise AnalysisCancelled()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=destination.parent, prefix='.nomi-model-', suffix='.partial', delete=False) as handle:
            temporary = Path(handle.name)
            digest = hashlib.sha256()
            received = 0
            last_percent = -1
            with urlopen(MODEL_URL, timeout=30) as response:
                while block := response.read(1024 * 1024):
                    if cancelled():
                        raise AnalysisCancelled()
                    received += len(block)
                    if received > MODEL_BYTES:
                        raise ValueError('Unerwartete Größe der Modelldatei.')
                    handle.write(block)
                    digest.update(block)
                    percent = min(100, received * 100 // MODEL_BYTES)
                    if percent != last_percent:
                        progress(f'Standardmodell herunterladen: {percent} %')
                        last_percent = percent
            handle.flush()
            os.fsync(handle.fileno())
        if cancelled():
            raise AnalysisCancelled()
        if received != MODEL_BYTES or digest.hexdigest() != MODEL_SHA256:
            raise ValueError('Prüfsumme der Modelldatei stimmt nicht. Download wurde verworfen.')
        # Reserve atomically without overwriting a model another app downloaded.
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if file_digest(destination, cancelled) != MODEL_SHA256:
                raise ValueError('Modelldatei wurde zwischenzeitlich belegt; nichts überschrieben.')
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
