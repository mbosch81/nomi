"""Offline smoke check for the built application, using only temporary files."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys
import hashlib
import json
from PySide6.QtCore import QSettings, QTimer


def run_self_test(app) -> int:
    from PIL import Image, ImageDraw, ImageFont
    from .app import Window
    from .core import Settings, extract_document, make_name
    result = {}
    with TemporaryDirectory(prefix='nomi-self-test-') as folder:
        root = Path(folder).resolve()
        image = Image.new('RGB', (1400, 500), 'white')
        draw = ImageDraw.Draw(image)
        draw.text((60, 80), 'Rechnung Beispiel GmbH', fill='black', font=ImageFont.load_default(size=55))
        source = root / 'scan.pdf'
        image.save(source, 'PDF', resolution=150)
        image.save(root / 'scan.png')
        image.save(root / 'scan.jpg')
        image.close()
        from zipfile import ZipFile
        docx = root / 'preview.docx'
        with ZipFile(docx, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>DOCX Textvorschau Beispiel GmbH</w:t></w:r></w:p></w:body></w:document>')
        assert 'Beispiel' in extract_document(docx).text
        from .inbox import inbox_snapshot
        assert docx in inbox_snapshot(root, False)
        import subprocess
        from .video import runtime_tool, sample_frames
        video = root / 'synthetic.avi'
        subprocess.run([str(runtime_tool('ffmpeg')), '-v', 'error', '-f', 'lavfi',
                        '-i', 'testsrc=size=320x240:rate=5', '-t', '1', '-c:v', 'mjpeg', str(video)],
                       check=True, timeout=15)
        from .preview import load_preview
        assert not load_preview(video)['image'].isNull()
        with sample_frames(video, 3) as frames:assert len(frames) == 3

        (root / 'preview.txt').write_text('Lokale Textvorschau Beispiel GmbH', encoding='utf-8')
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        document = None
        if os.name != 'nt' or '--ocr-self-test' in sys.argv:
            document = extract_document(source, settings=Settings(ocr_enabled=True, ocr_language='deu+eng' if os.name == 'nt' else 'eng'))
            if not document.used_ocr or 'Beispiel' not in document.text:
                raise RuntimeError('OCR-Selbsttest fehlgeschlagen.')
            for image_source in (root / 'scan.png', root / 'scan.jpg'):
                original = image_source.read_bytes()
                recognized = extract_document(image_source, settings=Settings(ocr_enabled=True, ocr_language='deu+eng' if os.name == 'nt' else 'eng'))
                assert recognized.used_ocr and 'Beispiel' in recognized.text
                assert image_source.read_bytes() == original
        else:
            source = root / 'preview.txt'
            before = hashlib.sha256(source.read_bytes()).hexdigest()
        store = QSettings(str(root / 'settings.ini'), QSettings.Format.IniFormat)
        store.setValue('engine', 'ollama')
        window = Window(store=store)
        window.setWindowTitle('Nomi · Selbsttest mit temporärer Datei')
        window.add([source])
        window.table.item(0, 2).setText(make_name({'absender': 'Beispiel GmbH', 'dokumenttyp': 'Rechnung'}, source, Settings().template))

        preview_paths = [root / 'scan.pdf', root / 'scan.png', root / 'scan.jpg', root / 'preview.txt', docx]
        preview_index = [0]
        preview_ticks = [0]
        timer = QTimer()

        def check():
            preview_ticks[0] += 1
            if window.preview._active is not None and preview_ticks[0] < 500:
                return
            try:
                assert window.preview._active is None
                if preview_index[0] >= 3:
                    assert 'Textvorschau' in window.preview.text.toPlainText()
                else:
                    assert not window.preview._image.isNull()
                preview_index[0] += 1
                if preview_index[0] < len(preview_paths):
                    window.preview.show_path(preview_paths[preview_index[0]])
                    return
                timer.stop()
                window.review_rename()
                assert source.exists() and window.rename_review.confirm.isEnabled()
                window.rename_review.accept()
                target = root / ('Beispiel_GmbH_Rechnung' + source.suffix)
                assert target.exists() and not source.exists()
                window.revert()
                assert hashlib.sha256(source.read_bytes()).hexdigest() == before
                assert not target.exists()
                archive=root/'Sorted';archive.mkdir()
                window.organize_root.setText(str(archive))
                window.organize_enabled.setChecked(True)
                window.transliterate_umlauts.setChecked(True)
                window.name_case.setCurrentIndex(window.name_case.findData('lower'))
                metadata={'datum':'2026-10-16','absender':'Müller GmbH','dokumenttyp':'Rechnung'}
                settings=window.settings()
                window.table.item(0,2).setText(make_name(metadata,source,'{datum}_{absender}_{dokumenttyp}',settings))
                from .session import file_identity
                window.remember_analysis(0,dict(identity=file_identity(source),settings=settings,metadata=metadata,frames=[]))
                window.review_rename()
                assert window.rename_review.confirm.isEnabled() and source.exists()
                assert not (archive/'2026').exists()
                window.rename_review.accept()
                assert window.paths[0].parent==archive/'2026/rechnung'
                assert 'mueller' in window.paths[0].name and not source.exists()
                window.revert()
                assert hashlib.sha256(source.read_bytes()).hexdigest()==before
                assert archive.exists() and not (archive/'2026').exists()
                result.update(ok=True, organize=True, naming_rules=True, video_frames=True, docx=True, inbox_snapshot=True, preview=True, image_ocr=document is not None, ocr=document is not None, ocr_backend=document.ocr_backend if document else None, qt=True, rename=True, undo=True)
            except Exception as error:
                result.update(ok=False, error=type(error).__name__)
            timer.stop()
            window.close()

        window.preview.show_path(preview_paths[0])
        window.show()
        timer.timeout.connect(check)
        timer.start(20)
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
        root = Path(folder).resolve()
        source = root / 'scan.png'
        image = Image.new('RGB', (1400, 500), 'white')
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(['Rechnung Beispiel GmbH', 'Rechnungsdatum: 14.10.2026', 'Rechnungsnummer: TEST-42']):
            draw.text((60, 40 + index * 120), line, fill='black', font=ImageFont.load_default(size=50))
        image.save(source)
        image.close()
        if os.name == 'nt':
            source = root / 'invoice.txt'
            source.write_text('Rechnung Beispiel GmbH Rechnungsdatum: 14.10.2026 Rechnungsnummer: TEST-42', encoding='utf-8')
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        store = QSettings(str(root / 'settings.ini'), QSettings.Format.IniFormat)
        for key, value in {'engine': 'llama', 'llama_model': str(model), 'ocr_enabled': True, 'auto_models': False, 'image_analysis': 'ocr', 'image_template': '{datum}_{absender}_{dokumenttyp}'}.items():
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
                    if os.name != 'nt':assert 'OCR' in window.table.item(0, 3).text()
                    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
                    result['analysis_seconds'] = round(time.monotonic() - generation_started[0], 2)
                    window.rename()
                    assert not source.exists()
                    window.revert()
                    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
                    result.update(ok=True, autoload=True, local_inference=True, ocr=os.name != 'nt', rename=True, undo=True, ui_ticks=len(ticks))
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
