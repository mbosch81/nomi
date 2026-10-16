"""Managed llama.cpp subprocess; binds only loopback and uses an ephemeral key."""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
from .core import Settings, AnalysisCancelled, metadata_messages, metadata_schema, parse_metadata
from .local_model import check_model


def runtime_path() -> Path:
    bundled = Path(__file__).resolve().parent / 'bin' / 'llama' / 'llama-server'
    if bundled.is_file():
        return bundled
    installed = shutil.which('llama-server')
    if installed:
        return Path(installed)
    raise ValueError('llama.cpp-Runtime fehlt. Bitte das vollständige Nomi-App-Bundle verwenden oder build_support/fetch_llama.py ausführen.')


def local_request(url: str, key: str, route: str, payload=None, timeout=5):
    request = Request(url + route, data=None if payload is None else json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    # Local document requests must never traverse a configured system HTTP proxy.
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        error.close()
        raise


class LlamaBackend:
    def __init__(self, url: str, key: str, supports_images=False):
        self.supports_images = supports_images
        self.url = url
        self._key = key

    def suggest(self, text: str, settings: Settings) -> dict:
        result = local_request(self.url, self._key, '/v1/chat/completions', {
            'model': 'nomi-local', 'stream': False, 'temperature': 0, 'max_tokens': 600,
            'messages': metadata_messages(text),
            'chat_template_kwargs': {'enable_thinking': False},
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'document_metadata', 'strict': True, 'schema': metadata_schema()}},
        }, timeout=settings.timeout)
        choice = result['choices'][0]
        if choice.get('finish_reason') == 'length':
            raise ValueError('Lokale KI-Antwort wurde abgeschnitten. Bitte erneut versuchen oder kürzeren Text verwenden.')
        return parse_metadata(choice['message']['content'], text)


    def suggest_images(self, frames, settings, *, prompt=None):
        from .video import VIDEO_PROMPT
        if not self.supports_images:
            raise ValueError('Das geladene Modell unterstützt keine Bilder.')
        content = [{'type': 'text', 'text': prompt or VIDEO_PROMPT}]
        for timestamp, encoded in frames:
            content.extend([{'type': 'text', 'text': f'Sample {timestamp:.2f}'},
                            {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,'+encoded}}])
        result = local_request(self.url, self._key, '/v1/chat/completions', {
            'model': 'nomi-local', 'stream': False, 'temperature': 0, 'max_tokens': 600,
            'messages': [{'role': 'user', 'content': content}],
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'video_metadata', 'strict': True, 'schema': metadata_schema()}},
        }, timeout=settings.timeout)
        choice = result['choices'][0]
        if choice.get('finish_reason') == 'length':
            raise ValueError('Vision-Antwort wurde abgeschnitten. Weniger Frames versuchen.')
        return parse_metadata(choice['message']['content'], '')


class LocalEngine:
    def __init__(self):
        self._process = None
        self._lock = threading.RLock()
        self.model = None
        self.projector = None
        self._model_identity = None
        self.backend = None

    def start(self, model: Path, cancelled=lambda: False, progress=lambda message: None,
              executable: Path | None = None, startup_timeout=120, projector: Path | None = None) -> LlamaBackend:
        with self._lock:
            model = model.expanduser().absolute()
            check_model(model)
            stat = model.stat()
            fingerprint = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
            if projector:
                projector = projector.expanduser().absolute()
                check_model(projector)
                project_stat = projector.stat()
                fingerprint += (str(projector), project_stat.st_ino, project_stat.st_size, project_stat.st_mtime_ns)
            if self._model_identity == fingerprint and self._process is not None and self._process.poll() is None and self.model == model and self.backend:
                return self.backend
            self.stop()
            if cancelled():
                raise AnalysisCancelled()
            executable = executable if executable is not None else runtime_path()
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0))
                port = reservation.getsockname()[1]
            key = secrets.token_urlsafe(32)
            environment = {name: value for name, value in os.environ.items()
                           if not name.startswith('LLAMA_') and name not in {'HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN'}}
            environment['LLAMA_API_KEY'] = key
            args = [str(executable), '--model', str(model), '--host', '127.0.0.1', '--port', str(port),
                    '--alias', 'nomi-local', '--ctx-size', '16384' if projector else '8192', '--parallel', '1',
                    '--n-gpu-layers', '99', '--no-webui', '--no-agent', '--log-disable',
                    '--chat-template-kwargs', '{"enable_thinking":false}', '--reasoning', 'off']
            if projector:
                args += ['--mmproj', str(projector)]
            progress('Lokales Modell wird geladen …')
            self._process = subprocess.Popen(args, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                              stdin=subprocess.DEVNULL)
            url = f'http://127.0.0.1:{port}'
            started = time.monotonic()
            try:
                while time.monotonic() - started < startup_timeout:
                    if cancelled():
                        raise AnalysisCancelled()
                    if self._process.poll() is not None:
                        raise ValueError('llama.cpp konnte das Modell nicht laden. GGUF-Datei, Arbeitsspeicher und Runtime prüfen.')
                    try:
                        ready = local_request(url, key, '/health', timeout=.5)
                        if ready.get('status') == 'ok':
                            # Authenticated model endpoint confirms inference is ready.
                            local_request(url, key, '/v1/models', timeout=1)
                            self.model = model
                            self._model_identity = fingerprint
                            self.projector = projector
                            self.backend = LlamaBackend(url, key, supports_images=projector is not None)
                            progress('Lokales Modell bereit · ' + model.name)
                            return self.backend
                    except (OSError, ValueError):
                        pass
                    time.sleep(.1)
                raise TimeoutError('Zeitlimit beim Laden des lokalen Modells erreicht.')
            except BaseException:
                self.stop()
                raise

    def stop(self):
        with self._lock:
            process, self._process = self._process, None
            self.backend = None
            self.model = None
            self.projector = None
            self._model_identity = None
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=2)

    def alive(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None
