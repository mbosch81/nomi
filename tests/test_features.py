from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import time
import unittest
from unittest.mock import patch
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication
from nomi.core import Settings, extract_document, AnalysisCancelled
from nomi.docx_reader import read_docx
from nomi.inbox import InboxWatcher, inbox_snapshot
from nomi.model_manager import installed_models, trash_model


def make_docx(path, content='Rechnung Beispiel GmbH'):
    with ZipFile(path, 'w') as z:
        z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+content+'</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Tabelle 42 EUR</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        z.writestr('word/header1.xml', '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Kopfzeile</w:t></w:r></w:p></w:hdr>')


class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_docx_extracts_paragraphs_tables_headers_and_preserves_source(self):
        path=self.root/'letter.docx';make_docx(path)
        original=path.read_bytes()
        data=extract_document(path, settings=Settings())
        for value in ('Beispiel', '42 EUR', 'Kopfzeile'):self.assertIn(value,data.text)
        self.assertFalse(data.used_ocr)
        self.assertEqual(path.read_bytes(),original)
        text,truncated=read_docx(path,8)
        self.assertEqual(len(text),8);self.assertTrue(truncated)
        from nomi.preview import load_preview
        self.assertIn('Beispiel',load_preview(path)['text'])

    def test_docx_rejects_entities_damage_and_cancellation(self):
        path=self.root/'bad.docx'
        with ZipFile(path,'w') as z:
            z.writestr('word/document.xml','<!DOCTYPE x [<!ENTITY a "secret">]><x>&a;</x>')
        with self.assertRaisesRegex(ValueError,'sicher'):read_docx(path)
        path.write_bytes(b'not a zip')
        with self.assertRaises(ValueError):read_docx(path)
        make_docx(path)
        with self.assertRaises(AnalysisCancelled):read_docx(path,cancelled=lambda:True)

    def test_docx_rejects_oversize_xml(self):
        path=self.root/'big.docx'
        with ZipFile(path,'w') as z:z.writestr('word/document.xml',b'x'*(8*1024*1024+1))
        with self.assertRaisesRegex(ValueError,'groß'):read_docx(path)

    def test_snapshot_recursion_and_temporary_files(self):
        (self.root/'good.docx').write_bytes(b'test')
        (self.root/'~$lock.docx').write_bytes(b'test')
        (self.root/'.hidden.txt').write_bytes(b'test')
        sub=self.root/'sub';sub.mkdir();(sub/'scan.txt').write_bytes(b'test')
        (self.root/'link').symlink_to(sub,target_is_directory=True)
        self.assertEqual(len(inbox_snapshot(self.root,False)),1)
        self.assertEqual(len(inbox_snapshot(self.root,True)),2)

    def wait_scan(self, watcher):
        deadline=time.monotonic()+3
        while watcher._active and time.monotonic()<deadline:
            self.app.processEvents();time.sleep(.01)
        self.assertIsNone(watcher._active)

    def test_inbox_waits_for_stability_and_does_not_reimport_rename(self):
        path=self.root/'new.txt';path.write_text('first')
        watcher=InboxWatcher();received=[]
        watcher.files_ready.connect(received.extend)
        watcher.configure(self.root);watcher.timer.stop();self.wait_scan(watcher)
        self.assertEqual(received,[])
        path.write_text('copy still in progress')
        watcher.poll();self.wait_scan(watcher);self.assertEqual(received,[])
        watcher.poll();self.wait_scan(watcher);self.assertEqual(received,[path])
        target=path.with_name('renamed.txt');path.rename(target)
        watcher.poll();self.wait_scan(watcher);watcher.poll();self.wait_scan(watcher)
        self.assertEqual(received,[path])
        watcher.configure(None)

    def test_inbox_pauses_while_busy_and_disabled_result_is_ignored(self):
        blocked=[True]
        watcher=InboxWatcher(lambda:blocked[0]);received=[]
        watcher.files_ready.connect(received.extend)
        watcher.configure(self.root);watcher.timer.stop()
        self.assertIsNone(watcher._active)
        blocked[0]=False
        watcher.poll();watcher.configure(None);self.wait_scan(watcher)
        self.assertEqual(received,[])
        QThreadPool.globalInstance().waitForDone(3000)

    def test_model_inventory_and_safe_trash_boundaries(self):
        model=self.root/'model.gguf';model.write_bytes(b'GGUFtest')
        external=self.root/'outside';external.mkdir();other=external/'other.gguf';other.write_bytes(b'GGUF')
        (self.root/'link.gguf').symlink_to(other)
        with patch('nomi.model_manager.model_directory',return_value=self.root):
            self.assertEqual(installed_models(),[model])
            with self.assertRaises(ValueError):trash_model(model,active=model)
            with self.assertRaises(ValueError):trash_model(other)
            with self.assertRaises(ValueError):trash_model(self.root/'link.gguf')
            with patch('nomi.model_manager.QFile.moveToTrash',return_value=False):
                with self.assertRaises(ValueError):trash_model(model)
            self.assertTrue(model.exists())
            with patch('nomi.model_manager.QFile.moveToTrash',return_value=True) as move:
                trash_model(model);move.assert_called_once_with(str(model))
