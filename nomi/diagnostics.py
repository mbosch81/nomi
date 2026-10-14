"""Offline smoke check for the built application, using only temporary files."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
from PySide6.QtCore import QSettings, QTimer


def run_self_test(app) -> int:
    from PIL import Image, ImageDraw, ImageFont
    from .app import Window
    from .core import Settings, extract_document, make_name
    result = {}
    with TemporaryDirectory(prefix='nomi-self-test-') as folder:
        root = Path(folder)
        image = Image.new('RGB', (1400, 500), 'white')
        draw = ImageDraw.Draw(image)
        draw.text((60, 80), 'Rechnung Beispiel GmbH', fill='black', font=ImageFont.load_default(size=55))
        source = root / 'scan.pdf'
        image.save(source, 'PDF', resolution=150)
        image.close()
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        document = extract_document(source, settings=Settings(ocr_enabled=True, ocr_language='eng'))
        if not document.used_ocr or 'Beispiel' not in document.text:
            raise RuntimeError('OCR-Selbsttest fehlgeschlagen.')
        store = QSettings(str(root / 'settings.ini'), QSettings.Format.IniFormat)
        store.setValue('engine', 'ollama')
        window = Window(store=store)
        window.setWindowTitle('Nomi · Selbsttest mit temporärer Datei')
        window.add([source])
        window.table.item(0, 2).setText(make_name({'absender': 'Beispiel GmbH', 'dokumenttyp': 'Rechnung'}, source, Settings().template))

        def check():
            try:
                window.rename()
                target = root / 'Beispiel_GmbH_Rechnung.pdf'
                assert target.exists() and not source.exists()
                window.revert()
                assert hashlib.sha256(source.read_bytes()).hexdigest() == before
                assert not target.exists()
                result.update(ok=True, ocr=True, ocr_backend=document.ocr_backend, qt=True, rename=True, undo=True)
            except Exception as error:
                result.update(ok=False, error=type(error).__name__)
            finally:
                window.close()

        window.show()
        QTimer.singleShot(0, check)
        app.exec()
    print(json.dumps(result), flush=True)
    return 0 if result.get('ok') else 1


def runtime_check() -> int:
    import subprocess
    from .llama_backend import runtime_path
    result = subprocess.run([str(runtime_path()), '--version'], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=20)
    print(json.dumps({'ok': result.returncode == 0, 'llama_cpp': True}), flush=True)
    return 0 if result.returncode == 0 else 1


def run_llama_self_test(app) -> int:
    """Opt-in integration check with an already downloaded GGUF; never downloads."""
    import time
    from PIL import Image, ImageDraw, ImageFont
    from .app import Window
    from .local_model import default_model_path, check_model
    model = default_model_path()
    check_model(model)
    result = {}
    with TemporaryDirectory(prefix='nomi-local-smoke-') as folder:
        root = Path(folder)
        source = root / 'scan.pdf'
        image = Image.new('RGB', (1400, 500), 'white')
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(['Rechnung Beispiel GmbH', 'Rechnungsdatum: 14.10.2026', 'Rechnungsnummer: TEST-42']):
            draw.text((60, 40 + index * 120), line, fill='black', font=ImageFont.load_default(size=50))
        image.save(source, 'PDF', resolution=150)
        image.close()
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        store = QSettings(str(root / 'settings.ini'), QSettings.Format.IniFormat)
        for key, value in {'engine': 'llama', 'llama_model': str(model), 'ocr_enabled': True}.items():
            store.setValue(key, value)
        started = time.monotonic()
        window = Window(store=store)
        window.setWindowTitle('Nomi · llama.cpp-Selbsttest mit temporärer Datei')
        window.error = lambda _: result.update(ok=False, error='Backend operation failed')
        phase = ['loading']
        ticks = []
        generation_started = [None]

        def advance():
            ticks.append(1)
            if time.monotonic() - started > 120:
                result.update(ok=False, error='Self-test timeout')
                window.cancel()
                window.local_engine.stop()
            if window.busy():
                return
            if result.get('error'):
                timer.stop();window.close();return
            if phase[0] == 'loading' and window._local_backend is not None:
                result['startup_seconds'] = round(time.monotonic() - started, 2)
                phase[0] = 'analysis'
                window.add([source])
                generation_started[0] = time.monotonic()
                window.analyze()
            elif phase[0] == 'analysis':
                try:
                    assert window.table.item(0, 2).text()
                    assert 'OCR' in window.table.item(0, 3).text()
                    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
                    result['analysis_seconds'] = round(time.monotonic() - generation_started[0], 2)
                    window.rename()
                    assert not source.exists()
                    window.revert()
                    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
                    result.update(ok=True, autoload=True, local_inference=True, ocr=True, rename=True, undo=True, ui_ticks=len(ticks))
                except Exception as error:
                    result.update(ok=False, error=type(error).__name__)
                timer.stop();window.close()

        timer = QTimer();timer.timeout.connect(advance);timer.start(20)
        window.show()
        app.exec()
        if window.local_engine.alive():
            window.local_engine.stop()
            result.update(ok=False, error='Process did not stop')
    print(json.dumps(result), flush=True)
    return 0 if result.get('ok') else 1
