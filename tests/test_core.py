import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from nomi.core import Settings, OllamaBackend, collect, extract, make_name, rename_batch, undo, validate_name

class CoreTests(unittest.TestCase):
    def test_document_pipeline(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / 'scan.txt'
            source.write_text('Rechnung Beispiel GmbH', encoding='utf-8')
            self.assertIn('Beispiel', extract(source))
            name = make_name({'datum': '2026-10-14', 'absender': 'Beispiel GmbH', 'dokumenttyp': 'Rechnung', 'titel': ''}, source, Settings().template)
            self.assertEqual(name, '2026-10-14_Beispiel_GmbH_Rechnung.txt')
            history = rename_batch([(source, name)])
            self.assertFalse(source.exists())
            self.assertEqual(history[0].after.read_text(), 'Rechnung Beispiel GmbH')
            undo(history)
            self.assertTrue(source.exists())

    def test_batch_conflict_does_not_change_anything(self):
        with TemporaryDirectory() as folder:
            a, b, existing = [Path(folder)/n for n in ('a.txt', 'b.txt', 'existing.txt')]
            for p in (a, b, existing):
                p.write_text(p.name)
            with self.assertRaises(ValueError):
                rename_batch([(a, 'new.txt'), (b, 'existing.txt')])
            self.assertTrue(a.exists())
            self.assertEqual(existing.read_text(), 'existing.txt')
            self.assertFalse((Path(folder)/'new.txt').exists())
            with self.assertRaises(ValueError):
                rename_batch([(a, 'same.txt'), (b, 'same.txt')])

    def test_undo_protects_modified_file(self):
        with TemporaryDirectory() as folder:
            source = Path(folder)/'a.txt'
            source.write_text('a')
            records = rename_batch([(source, 'b.txt')])
            records[0].after.write_text('changed')
            with self.assertRaises(ValueError):
                undo(records)
            self.assertFalse(source.exists())

    def test_paths_and_extensions_rejected(self):
        for name in ('../escape.txt', 'bad/name.txt', 'new.pdf', 'CON.txt', 'bad?.txt', '.hidden.txt'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_name(Path('a.txt'), name)

    def test_collect_recursive_dedup_and_symlinks(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            a = root/'a.txt'
            a.write_text('a')
            sub = root/'nested'
            sub.mkdir()
            (sub/'b.md').write_text('b')
            (root/'link.txt').symlink_to(a)
            self.assertEqual(len(collect([root, a], False)), 1)
            self.assertEqual(len(collect([root], True)), 2)

    def test_pdf_extraction(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        with TemporaryDirectory() as folder:
            path = Path(folder)/'test.pdf'
            writer = PdfWriter()
            page = writer.add_blank_page(width=300, height=300)
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
            page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(b'BT /F1 12 Tf 20 250 Td (Rechnung Beispiel GmbH) Tj ET')
            page[NameObject('/Contents')] = writer._add_object(stream)
            writer.write(path)
            self.assertIn('Rechnung Beispiel GmbH', extract(path))

    def test_ollama_contract(self):
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"models":[{"name":"test-model"}]}')
            def do_POST(self):
                captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'message': {'content': json.dumps({'datum': '', 'absender': 'Beispiel', 'dokumenttyp': 'Rechnung', 'titel': ''})}}).encode())
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            settings = Settings(url=f'http://127.0.0.1:{server.server_port}', model='test-model')
            backend = OllamaBackend()
            self.assertEqual(backend.models(settings), ['test-model'])
            self.assertEqual(backend.suggest('Document', settings)['absender'], 'Beispiel')
            self.assertFalse(captured[0]['stream'])
            self.assertEqual(captured[0]['format']['type'], 'object')
        finally:
            server.shutdown(); server.server_close(); thread.join()

if __name__ == '__main__':
    unittest.main()
