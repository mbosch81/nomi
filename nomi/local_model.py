"""A pinned data-only model download; no runtime executable is downloaded here."""
from __future__ import annotations
from .i18n import tr
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label: str
    filename: str
    url: str
    sha256: str
    size: int
    projector: ModelSpec | None = None


def model_catalog() -> tuple[ModelSpec, ...]:
    return (
        ModelSpec('qwen', tr('Qwen3 4B · Standard · 2,5 GB'), MODEL_FILENAME,
                  MODEL_URL, MODEL_SHA256, MODEL_BYTES),
        ModelSpec('mistral', tr('Mistral 7B Instruct v0.3 · 4,4 GB'),
                  'Mistral-7B-Instruct-v0.3-Q4_K_M.gguf',
                  'https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/resolve/'
                  '61fd4167fff3ab01ee1cfe0da183fa27a944db48/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf',
                  '1270d22c0fbb3d092fb725d4d96c457b7b687a5f5a715abe1e818da303e562b6',
                  4372812000),
        ModelSpec('smolvlm', tr('SmolVLM2 2.2B · Bilder/Video · 1,7 GB'),
                  'SmolVLM2-2.2B-Instruct-Q4_K_M.gguf',
                  'https://huggingface.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF/resolve/'
                  '1bc3c9f74ceafd4c8d4411cc9cf188bba3798f91/SmolVLM2-2.2B-Instruct-Q4_K_M.gguf',
                  '0cf76814555b8665149075b74ab6b5c1d428ea1d3d01c1918c12012e8d7c9f58', 1112602656,
                  ModelSpec('smolvlm-projector', tr('SmolVLM2 Vision-Projektor'),
                            'mmproj-SmolVLM2-2.2B-Instruct-Q8_0.gguf',
                            'https://huggingface.co/ggml-org/SmolVLM2-2.2B-Instruct-GGUF/resolve/'
                            '1bc3c9f74ceafd4c8d4411cc9cf188bba3798f91/mmproj-SmolVLM2-2.2B-Instruct-Q8_0.gguf',
                            'ae07ea1facd07dd3230c4483b63e8cda96c6944ad2481f33d531f79e892dd024', 592523200)),
    )


def model_spec(key: str) -> ModelSpec:
    for model in model_catalog():
        if model.key == key:
            return model
        if model.projector and model.projector.key == key:
            return model.projector
    raise ValueError(tr('Unbekanntes Download-Modell.'))


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
        raise ValueError(tr('Bitte eine vorhandene GGUF-Modelldatei auswählen.'))
    with path.open('rb') as handle:
        if handle.read(4) != b'GGUF':
            raise ValueError(tr('Die Datei ist kein gültiges GGUF-Modell.'))


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
    return download_model('qwen', destination, cancelled, progress)


def download_model(key: str, destination: Path | None = None, cancelled=lambda: False,
                   progress=lambda message: None) -> Path:
    model = model_spec(key)
    destination = destination if destination is not None else model_directory() / model.filename
    if destination.exists():
        progress(f"{tr('Vorhandenes Modell wird geprüft · ')}{model.label}")
        if destination.stat().st_size != model.size or file_digest(destination, cancelled) != model.sha256:
            raise ValueError(tr('Die vorhandene Modelldatei stimmt nicht mit dem gewählten Download-Modell überein; sie wird nicht überschrieben.'))
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
            with urlopen(model.url, timeout=30) as response:
                while block := response.read(1024 * 1024):
                    if cancelled():
                        raise AnalysisCancelled()
                    received += len(block)
                    if received > model.size:
                        raise ValueError(tr('Unerwartete Größe der Modelldatei.'))
                    handle.write(block)
                    digest.update(block)
                    percent = min(100, received * 100 // model.size)
                    if percent != last_percent:
                        progress(f'{tr(model.label)}{tr(" herunterladen: ")}{percent} %' )
                        last_percent = percent
            handle.flush()
            os.fsync(handle.fileno())
        if cancelled():
            raise AnalysisCancelled()
        if received != model.size or digest.hexdigest() != model.sha256:
            raise ValueError(tr('Prüfsumme der Modelldatei stimmt nicht. Download wurde verworfen.'))
        # Reserve atomically without overwriting a model another app downloaded.
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if file_digest(destination, cancelled) != model.sha256:
                raise ValueError(tr('Modelldatei wurde zwischenzeitlich belegt; nichts überschrieben.'))
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def download_model_package(key, cancelled=lambda: False, progress=lambda message: None):
    model = model_spec(key)
    path = download_model(key, cancelled=cancelled, progress=progress)
    projector = download_model(model.projector.key, cancelled=cancelled, progress=progress) if model.projector else None
    return path, projector
