from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from nomi.core import normalize_date, make_name, available_name, extract_document, Settings, grounded_date


class QualityTests(TestCase):
    def test_dates_normalize_without_guessing(self):
        for value in ('3.10.2026', '03.10.2026', '2026-10-3', '2026-10-03'):
            self.assertEqual(normalize_date(value), '2026-10-03')
        for value in ('', 'Unbekannt', 'tt.mm.jjjj', 'YYYY-MM-DD'):
            self.assertEqual(normalize_date(value), '')
        for value in ('2026', '10/03/2026', '31.02.2026', '2026-13-01', '2026-00-00'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_date(value)

    def test_unknown_fields_and_optional_identifiers(self):
        name = make_name({'datum': 'Unbekannt', 'titel': 'Unbekannter Titel',
                          'absender': 'Test AG', 'dokumenttyp': 'Rechnung',
                          'empfaenger': 'Beispiel GmbH', 'kennung': 'TEST-42'},
                         Path('scan.pdf'), '{datum}_{absender}_{empfaenger}_{titel}_{kennung}')
        self.assertEqual(name, 'Test_AG_Beispiel_GmbH_TEST-42.pdf')

    def test_existing_and_batch_collisions_get_visible_suffixes(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'a.pdf'
            source.touch()
            (root/'Rechnung.pdf').touch()
            (root/'Rechnung_2.pdf').symlink_to(root/'missing.pdf')
            reserved = set()
            self.assertEqual(available_name(source, 'Rechnung.pdf', reserved), 'Rechnung_3.pdf')
            self.assertEqual(available_name(source, 'Rechnung.pdf', reserved), 'Rechnung_4.pdf')
            self.assertEqual(available_name(source, source.name, reserved), source.name)
            self.assertEqual({p.name for p in root.iterdir()}, {'a.pdf', 'Rechnung.pdf', 'Rechnung_2.pdf'})

    def test_extraction_reports_limits(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'a.txt'
            path.write_text('abcdefghijk')
            result = extract_document(path, limit=5)
            self.assertEqual(result.text, 'abcde')
            self.assertTrue(result.truncated)
            self.assertFalse(result.used_ocr)

    def test_document_date_requires_evidence_and_excludes_contract_start(self):
        self.assertEqual(grounded_date('03.10.2026', 'Rechnungsdatum: 3.10.2026')[0], '2026-10-03')
        self.assertEqual(grounded_date('2026-10-03', 'Mannheim, 3. Oktober 2026')[0], '2026-10-03')
        self.assertEqual(grounded_date('2026-10-03', 'Berufserfahrung seit 10/2026')[0], '')
        self.assertEqual(grounded_date('2026-11-01', 'Das Mietverhältnis beginnt am 01.11.2026')[0], '')
        self.assertEqual(grounded_date('2026-11-01', 'Monatliche Zahlung ab 01.11.2026 Betrag')[0], '')
        self.assertEqual(grounded_date('2026-11-01', 'Abrechnungszeitraum umfasst den 01.11.2026')[0], '')
        self.assertEqual(grounded_date('2026-11-01', 'Beginn: 01.11.2026. Rechnungsdatum: 01.11.2026')[0], '2026-11-01')
        self.assertEqual(grounded_date('August 2026', 'Stand: August 2026')[0], '')

    def test_backend_does_not_forward_unproven_dates_to_filename(self):
        import json
        from nomi.core import OllamaBackend
        backend = OllamaBackend()
        response = {'message': {'content': json.dumps({'datum': '2020-02-01', 'absender': 'Beispiel', 'dokumenttyp': 'Lebenslauf'})}}
        with patch.object(backend, 'request', return_value=response):
            metadata = backend.suggest('Lebenslauf: Berufserfahrung seit 02/2020', Settings(model='test'))
        self.assertEqual(metadata['datum'], '')
        self.assertTrue(metadata['_warnings'])
        self.assertEqual(make_name(metadata, Path('scan.pdf'), Settings().template), 'Beispiel_Lebenslauf.pdf')
