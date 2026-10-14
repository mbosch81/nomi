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
                result.update(ok=True, ocr=True, qt=True, rename=True, undo=True)
            except Exception as error:
                result.update(ok=False, error=type(error).__name__)
            finally:
                window.close()

        window.show()
        QTimer.singleShot(0, check)
        app.exec()
    print(json.dumps(result), flush=True)
    return 0 if result.get('ok') else 1
