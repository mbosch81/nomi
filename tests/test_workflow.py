"""Session reuse, forced reanalysis, inspected samples and review safety."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication
from nomi.core import Settings, metadata_messages
from nomi.session import SessionResults, file_identity
from nomi.rename_review import review_plan

class SessionTests(unittest.TestCase):
    def test_identity_policy_and_eviction(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'a.txt';path.write_text('first')
            settings=Settings();cache=SessionResults(limit=1)
            cache.put(file_identity(path),settings,{'name':'A.txt'})
            self.assertIsNotNone(cache.get(path,replace(settings,analysis_hint='kurz')))
            self.assertIsNone(cache.get(path,replace(settings,video_frames=8)))
            path.write_text('other')
            self.assertIsNone(cache.get(path,settings))
            cache.put(file_identity(path),settings,{'name':'B.txt'})
            self.assertEqual(len(cache.entries),1)
            tiny=SessionResults(byte_limit=3);tiny.put(file_identity(path),settings,{'frames':[(0,'1234')]})
            self.assertFalse(tiny.entries)

    def test_cache_force_and_mutating_source(self):
        from nomi.app import Worker
        with TemporaryDirectory() as folder:
            path=Path(folder)/'a.txt';path.write_text('Dokument')
            settings=Settings(template='{titel}');cache=SessionResults()
            backend=Mock();backend.suggest.return_value={'titel':'Erster Titel'}
            for force in (False,False,True):
                worker=Worker(settings,[(0,path)],backend,cache=cache,force=force);worker.run()
            self.assertEqual(backend.suggest.call_count,2)
            changed=[]
            def suggest(*args):path.write_text('extern verändert');return {'titel':'Falsch'}
            backend.suggest.side_effect=suggest
            worker=Worker(settings,[(0,path)],backend,cache=cache,force=True)
            worker.result.connect(lambda *args:changed.append(args));worker.run()
            self.assertEqual(changed[0][1],'');self.assertIn('verändert',changed[0][2])
            self.assertIsNone(cache.get(path,settings))

    def test_review_rejects_source_changes_and_conflicts(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'a.txt';path.write_text('original');identity=file_identity(path)
            other=Path(folder)/'b.txt';other.write_text('other')
            rows=review_plan([(path,'b.txt',''),(other,'b.txt','')])
            self.assertTrue(rows[0]['problems']);self.assertTrue(rows[1]['problems'])
            path.write_text('changed')
            rows=review_plan([(path,'c.txt','')],{path:identity})
            self.assertIn('verändert',rows[0]['problems'][0])
            self.assertEqual(path.read_text(),'changed')

    def test_hint_is_separate_from_document_facts(self):
        messages=metadata_messages('Rechnung Beispiel', 'Ort hervorheben')
        self.assertIn('Ort hervorheben',messages[0]['content'])
        self.assertEqual(messages[1]['content'],'DOKUMENTINHALT:\nRechnung Beispiel')

class WorkflowUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        from nomi.app import Window
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'source.txt';self.source.write_text('Rechnung Beispiel')
        self.store=QSettings(str(self.root/'settings.ini'),QSettings.Format.IniFormat)
        self.store.setValue('engine','ollama');self.store.setValue('model','synthetic');self.store.setValue('template','{titel}')
        self.window=Window(store=self.store);self.window.show();self.app.processEvents()
    def tearDown(self):
        self.window.close();self.app.processEvents();self.temp.cleanup()
    def wait(self):
        deadline=time.monotonic()+5
        while self.window.busy() and time.monotonic()<deadline:self.app.processEvents();time.sleep(.01)
        self.app.processEvents();self.assertFalse(self.window.busy())
    def test_reimport_manual_edit_force_and_review(self):
        self.window.add([self.source])
        with patch('nomi.app.OllamaBackend.suggest',return_value={'titel':'Vorschlag'}) as backend:
            self.window.analyze();self.wait()
            self.window.table.item(0,2).setText('Mein_Name.txt')
            self.window.clear();self.window.add([self.source])
            self.assertEqual(self.window.table.item(0,2).text(),'Mein_Name.txt')
            self.window.analyze();self.wait();self.assertEqual(backend.call_count,1)
            with patch('nomi.app.QInputDialog.getText',return_value=('kurz benennen',True)):
                self.window.reanalyze();self.wait()
            self.assertEqual(backend.call_count,2)
            self.assertEqual(backend.call_args.args[1].analysis_hint,'kurz benennen')
            self.window.review_rename();self.assertTrue(self.source.exists())
            self.assertTrue(self.window.rename_review.confirm.isEnabled())
            self.window.rename_review.reject();self.assertTrue(self.source.exists())
            self.window.review_rename();self.window.rename_review.accept()
            target=self.root/'Vorschlag.txt';self.assertTrue(target.exists());self.assertFalse(self.source.exists())
            self.window.revert();self.assertTrue(self.source.exists())
            self.window.clear();self.window.add([self.source])
            self.assertEqual(self.window.table.item(0,2).text(),'Vorschlag.txt')
            self.source.write_text('extern geändert')
            self.window.clear();self.window.add([self.source])
            self.assertEqual(self.window.table.item(0,2).text(),'')

    def test_automatic_start_uses_selected_text_model_and_preserves_manual_path(self):
        from nomi.local_model import model_spec
        model=self.root/model_spec('mistral').filename;model.write_bytes(b'GGUFtest')
        class Engine:
            model=None
            backend=None
            def start(self,path,cancelled,progress):
                self.model=path;self.backend=Mock(supports_images=False);return self.backend
            def stop(self):self.model=None;self.backend=None
            def alive(self):return self.backend is not None
        self.window.local_engine=Engine()
        self.window.autoload.setChecked(False)
        self.window.engine.setCurrentIndex(self.window.engine.findData('llama'))
        self.window.auto_models.setChecked(True)
        self.window.text_model.setCurrentIndex(self.window.text_model.findData('mistral'))
        manual=self.window.gguf.text()
        self.window.autoload.setChecked(True)
        with patch('nomi.app.model_directory',return_value=self.root):
            self.window.auto_load();self.wait()
        self.assertEqual(self.window.local_engine.model,model)
        self.assertEqual(self.window.gguf.text(),manual)

    def test_review_does_not_include_later_inbox_import(self):
        self.window.add([self.source])
        self.window.table.item(0,2).setText('Approved.txt')
        self.window.review_rename()
        incoming=self.root/'incoming.txt';incoming.write_text('Later import')
        self.window.add([incoming])
        self.window.rename_review.accept()
        self.assertTrue((self.root/'Approved.txt').exists())
        self.assertTrue(incoming.exists())
        self.window.revert()
        self.assertTrue(self.source.exists())

    def test_exact_video_frames_are_selectable(self):
        from nomi.image_analysis import encode_image
        from PySide6.QtGui import QImage
        path=self.root/'sample.png'
        image=QImage(120,80,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.red);image.save(str(path))
        encoded=encode_image(path)
        frames=[(1.,encoded),(2.,encoded),(3.,encoded)]
        self.window.preview.set_analysis_frames(frames)
        self.assertEqual(self.window.preview.frame_layout.count(),3)
        self.window.preview.show_analysis_frame(2)
        self.assertIn('3/3',self.window.preview.note.text())
        self.assertFalse(self.window.preview._image.isNull())
        self.window.preview.set_analysis_frames([])
        self.assertTrue(self.window.preview.frame_bar.isHidden())
