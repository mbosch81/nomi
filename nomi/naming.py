"""Deterministic filename rules and editable template presets."""
import re
import unicodedata
from pathlib import Path
from .core import RESERVED, validate_name

PRESETS = {
    'Rechnungen': ('document', '{datum}_{absender}_Rechnung_{kennung}'),
    'Verträge': ('document', '{datum}_{absender}_Vertrag_{titel}'),
    'Dokumente allgemein': ('document', '{datum}_{absender}_{dokumenttyp}'),
    'Fotos': ('image', '{titel}'),
    'Videos': ('video', 'Video_{titel}'),
}
EXAMPLE = dict(datum='2026-10-16',absender='Müller & Söhne',empfaenger='Max Muster',
               dokumenttyp='Rechnung',titel='Reparatur Fahrrad',kennung='R-42')


def format_name(value, source, settings):
    separator=settings.name_separator
    if separator not in ('_', ' '):raise ValueError('Trennzeichen muss Leerzeichen oder Unterstrich sein.')
    if settings.name_case not in ('preserve','lower','upper'):raise ValueError('Ungültige Schreibweise.')
    if not 40 <= settings.max_name_length <= 240:raise ValueError('Namenslänge muss zwischen 40 und 240 liegen.')
    value=unicodedata.normalize('NFC',value)
    value=''.join(c for c in value if unicodedata.category(c) not in ('Cc','Cf'))
    value=re.sub(r'[<>:"/\\|?*]',separator,value)
    value=re.sub(r'[\s_]+',separator,value).strip(' ._')
    if settings.transliterate_umlauts:
        for old,new in (('ä','ae'),('ö','oe'),('ü','ue'),('Ä','Ae'),('Ö','Oe'),('Ü','Ue'),('ß','ss'),('ẞ','SS')):
            value=value.replace(old,new)
    if settings.name_case=='lower':value=value.lower()
    elif settings.name_case=='upper':value=value.upper()
    if settings.windows_compatible and value.split('.')[0].upper() in RESERVED:
        prefix='DATEI' if settings.name_case=='upper' else 'datei' if settings.name_case=='lower' else 'Datei'
        value=prefix+separator+value
    suffix=Path(source).suffix
    limit=settings.max_name_length-len(suffix.encode('utf-8'))
    while len(value)>limit or len(value.encode('utf-8'))>limit:value=value[:-1]
    value=value.rstrip(' ._')
    name=value+suffix
    validate_name(Path(source),name)
    return name
