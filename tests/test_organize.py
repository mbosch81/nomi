from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest
from unittest.mock import patch
from nomi.core import Settings,undo,RenameError
from nomi.organize import destination_for,organize_batch,secure_move,validate_destination

@unittest.skipUnless(os.name == 'posix', 'Secure directory organization requires POSIX directory descriptors')
class OrganizeTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        self.target=self.root/'Archive';self.target.mkdir()
        self.source=self.root/'source.txt';self.source.write_text('unchanged content')
        self.settings=Settings(organize_enabled=True,organize_root=str(self.target))
    def tearDown(self):self.temp.cleanup()
    def test_plan_is_read_only_and_missing_date_is_explicit(self):
        dest=destination_for(self.source,'New.txt',{'datum':'','dokumenttyp':'Video'},self.settings)
        self.assertEqual(dest,self.target/'Ohne_Datum/Video/New.txt')
        self.assertFalse(dest.parent.exists())
        self.assertEqual(destination_for(self.source,'New.txt',None,replace(self.settings,folder_template='')),self.target/'New.txt')
        escaped=destination_for(self.source,'New.txt',{'datum':'2026-10-16','dokumenttyp':'../../outside'},self.settings)
        self.assertTrue(escaped.is_relative_to(self.target))
        self.assertNotIn('..',escaped.parts)
        for template in ('../{jahr}','/{jahr}','{jahr}/../../bad','{titel.__class__}','{jahr}//x'):
            with self.assertRaises(ValueError):destination_for(self.source,'New.txt',{},replace(self.settings,folder_template=template))
        with self.assertRaises(ValueError):destination_for(self.source,'New.txt',None,self.settings)
    def test_move_and_undo_create_only_needed_folders(self):
        dest=destination_for(self.source,'New.txt',{'datum':'2026-10-16','dokumenttyp':'Rechnung'},self.settings)
        records=organize_batch([(self.source,dest)],self.target)
        self.assertFalse(self.source.exists());self.assertEqual(dest.read_text(),'unchanged content')
        undo(records)
        self.assertEqual(self.source.read_text(),'unchanged content');self.assertFalse((self.target/'2026').exists())
    def test_existing_nonempty_folders_are_preserved(self):
        parent=self.target/'2026/Rechnung';parent.mkdir(parents=True)
        records=organize_batch([(self.source,parent/'New.txt')],self.target)
        (parent/'other.txt').write_text('foreign')
        undo(records);self.assertTrue(parent.exists());self.assertEqual((parent/'other.txt').read_text(),'foreign')
    def test_collision_and_symbolic_link_never_overwrite(self):
        dest=self.target/'existing.txt';dest.write_text('foreign')
        with self.assertRaises(ValueError):organize_batch([(self.source,dest)],self.target)
        self.assertEqual(dest.read_text(),'foreign');self.assertTrue(self.source.exists())
        external=self.root/'external';external.mkdir();(self.target/'link').symlink_to(external,target_is_directory=True)
        with self.assertRaises((ValueError,OSError)):organize_batch([(self.source,self.target/'link/New.txt')],self.target)
        self.assertFalse(list(external.iterdir()));self.assertTrue(self.source.exists())
        with self.assertRaises(ValueError):validate_destination(self.source,self.root/'outside.txt',self.target)
    def test_rollback_and_directory_cleanup_on_second_move_failure(self):
        second=self.root/'second.txt';second.write_text('second')
        one=self.target/'2026/A/one.txt';two=self.target/'2026/B/two.txt'
        def move(source,target):
            if source==second:raise OSError('synthetic failure')
            secure_move(source,target)
        with patch('nomi.organize.secure_move',side_effect=move):
            with self.assertRaises(RenameError) as result:organize_batch([(self.source,one),(second,two)],self.target)
        self.assertFalse(result.exception.records);self.assertTrue(self.source.exists());self.assertTrue(second.exists())
        self.assertFalse((self.target/'2026').exists())
    def test_late_destination_and_unlink_failure_preserve_source(self):
        dest=self.target/'late.txt'
        dest.write_text('foreign')
        with self.assertRaises(FileExistsError):secure_move(self.source,dest)
        dest.unlink()
        actual=os.unlink
        def unlink(name,*args,**kwargs):
            if name==self.source.name:raise PermissionError('synthetic source unlink failure')
            return actual(name,*args,**kwargs)
        with patch('nomi.organize.os.unlink',side_effect=unlink):
            with self.assertRaises(PermissionError):secure_move(self.source,dest)
        self.assertTrue(self.source.exists());self.assertFalse(dest.exists())
    def test_worker_reserves_names_across_source_folders_without_creating_targets(self):
        from nomi.app import Worker
        from unittest.mock import Mock
        second_dir=self.root/'Second';second_dir.mkdir()
        second=second_dir/'source.txt';second.write_text('second')
        settings=replace(self.settings,template='{titel}')
        backend=Mock();backend.suggest.return_value={'datum':'2026-10-16','dokumenttyp':'Rechnung','titel':'Same'}
        worker=Worker(settings,[(0,self.source),(1,second)],backend)
        results=[];worker.result.connect(lambda *args:results.append(args));worker.run()
        self.assertEqual([entry[1] for entry in results],['Same.txt','Same_2.txt'])
        self.assertFalse((self.target/'2026').exists())

    def test_cross_device_is_rejected_before_any_directory_creation(self):
        from types import SimpleNamespace
        dest=self.target/'new/Sub/file.txt'
        with patch('nomi.organize.os.fstat',return_value=SimpleNamespace(st_dev=self.source.stat().st_dev+1)):
            with self.assertRaisesRegex(ValueError,'Laufwerk'):validate_destination(self.source,dest,self.target)
        self.assertTrue(self.source.exists());self.assertFalse((self.target/'new').exists())

    def test_incomplete_rollback_records_remain_undoable(self):
        second=self.root/'second.txt';second.write_text('second')
        one=self.target/'A/one.txt';two=self.target/'B/two.txt'
        def move(source,target):
            if source in (second,one):raise OSError('synthetic failure')
            secure_move(source,target)
        with patch('nomi.organize.secure_move',side_effect=move):
            with self.assertRaises(RenameError) as result:organize_batch([(self.source,one),(second,two)],self.target)
        self.assertEqual(len(result.exception.records),1);self.assertTrue(one.exists())
        undo(result.exception.records)
        self.assertTrue(self.source.exists());self.assertFalse((self.target/'A').exists())

    def test_undo_refuses_modified_file_and_occupied_original(self):
        dest=self.target/'New.txt';records=organize_batch([(self.source,dest)],self.target)
        self.source.write_text('foreign')
        with self.assertRaises(ValueError):undo(records)
        self.assertEqual(self.source.read_text(),'foreign');self.assertTrue(dest.exists())
        self.source.unlink();dest.write_text('modified')
        with self.assertRaises(ValueError):undo(records)
        self.assertTrue(dest.exists())

@unittest.skipUnless(os.name == 'posix', 'Folder organization is unavailable in Windows preview')
class OrganizeUITests(unittest.TestCase):
    def test_all_metadata_survives_large_batch(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings
        from nomi.app import Window
        from nomi.session import file_identity
        app=QApplication.instance() or QApplication([])
        with TemporaryDirectory() as folder:
            root=Path(folder).resolve();archive=root/'Archive';archive.mkdir()
            paths=[]
            for i in range(70):
                path=root/f'{i}.txt';path.write_text('synthetic');paths.append(path)
            store=QSettings(str(root/'settings.ini'),QSettings.Format.IniFormat);store.setValue('engine','ollama')
            window=Window(store=store);window.add(paths)
            for row,path in enumerate(window.paths):
                window.table.item(row,2).setText(f'New-{row}.txt')
                window.remember_analysis(row,dict(identity=file_identity(path),settings=window.settings(),metadata={'datum':'2026-10-16','dokumenttyp':'Rechnung'},frames=[]))
            window.organize_root.setText(str(archive));window.organize_enabled.setChecked(True)
            window.review_rename()
            self.assertEqual(window.rename_review.list.count(),70)
            self.assertTrue(window.rename_review.confirm.isEnabled())
            window.rename_review.reject();window.close();app.processEvents()

    def test_review_shows_destination_and_restores_paths(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings
        from nomi.app import Window
        from nomi.session import file_identity
        app=QApplication.instance() or QApplication([])
        with TemporaryDirectory() as folder:
            root=Path(folder).resolve();source=root/'source.txt';source.write_text('synthetic')
            target=root/'Archive';target.mkdir()
            store=QSettings(str(root/'settings.ini'),QSettings.Format.IniFormat);store.setValue('engine','ollama')
            window=Window(store=store);window.add([source]);window.table.item(0,2).setText('New.txt')
            window.remember_analysis(0,dict(identity=file_identity(source),settings=window.settings(),metadata={'datum':'2026-10-16','dokumenttyp':'Rechnung'},frames=[]))
            window.organize_root.setText(str(target));window.organize_enabled.setChecked(True)
            window.review_rename()
            self.assertTrue(source.exists());self.assertFalse((target/'2026').exists())
            self.assertIn(str(target/'2026/Rechnung/New.txt'),window.rename_review.list.item(0).text())
            self.assertTrue(window.rename_review.confirm.isEnabled())
            window.rename_review.accept();self.assertFalse(source.exists())
            self.assertEqual(window.paths[0],target/'2026/Rechnung/New.txt')
            window.revert();self.assertTrue(source.exists());self.assertEqual(window.paths[0],source)
            window.close();app.processEvents()
