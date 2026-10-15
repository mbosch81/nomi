"""Bounded read-only extraction of DOCX text; no macros or external resources."""
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from defusedxml.ElementTree import fromstring
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import ParseError

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def read_docx(path: Path, limit=16000, cancelled=lambda: False):
    from .core import AnalysisCancelled
    pieces = []
    length = 0
    try:
        with ZipFile(path) as archive:
            names = archive.namelist()
            if 'word/document.xml' not in names:
                raise ValueError('DOCX enthält keinen Dokumenttext.')
            parts = ['word/document.xml'] + sorted(n for n in names if
                n.startswith(('word/header', 'word/footer')) and n.endswith('.xml'))
            if len(parts) > 100 or sum(archive.getinfo(n).file_size for n in parts) > 16*1024*1024:
                raise ValueError('DOCX ist für die Textextraktion zu groß.')
            for name in parts:
                if cancelled():
                    raise AnalysisCancelled()
                info = archive.getinfo(name)
                if info.file_size > 8*1024*1024:
                    raise ValueError('DOCX-Textteil ist zu groß.')
                with archive.open(name) as handle:
                    raw = handle.read(8*1024*1024+1)
                if len(raw) > 8*1024*1024:
                    raise ValueError('DOCX-Textteil ist zu groß.')
                root = fromstring(raw)
                for paragraph in root.iter(W+'p'):
                    if cancelled():
                        raise AnalysisCancelled()
                    text = ''.join((node.text or '') if node.tag == W+'t' else
                                   '\t' if node.tag == W+'tab' else '\n' if node.tag == W+'br' else ''
                                   for node in paragraph.iter())
                    pieces.append(text)
                    length += len(text)+1
                    if length > limit:
                        return '\n'.join(pieces)[:limit], True
    except (BadZipFile, KeyError, ParseError, DefusedXmlException, RuntimeError, OSError):
        raise ValueError('DOCX kann nicht sicher gelesen werden oder ist beschädigt.') from None
    return '\n'.join(pieces)[:limit], False
