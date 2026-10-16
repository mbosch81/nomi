"""Central UI catalogs. Source keys are stable German messages, never file data.

Add a locale to translations.json; keep template field names unchanged. Language
is applied at startup so in-flight workers and review plans retain one language.
"""
import json
from pathlib import Path

_catalog = json.loads((Path(__file__).parent / 'locales/translations.json').read_text(encoding='utf-8'))
_language = 'de'


def languages():
    return {key: value['name'] for key, value in _catalog.items()}


def set_language(language):
    global _language
    _language = language if language in _catalog else 'de'


def tr(source):
    return _catalog.get(_language, {}).get('messages', {}).get(source, source)


def install_qt_translation(app, language):
    from PySide6.QtCore import QTranslator, QLibraryInfo
    translator = QTranslator(app)
    translator.load('qtbase_' + language, QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    app.installTranslator(translator)
    app._nomi_translator = translator
