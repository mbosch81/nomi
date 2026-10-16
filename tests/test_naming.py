from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from nomi.core import Settings,make_name,available_name
from nomi.naming import EXAMPLE,PRESETS

class NamingTests(unittest.TestCase):
    def test_rules_preserve_extension(self):
        settings=Settings(name_case='lower',name_separator=' ',transliterate_umlauts=True)
        self.assertEqual(make_name({'titel':'Grüße_Ärger für Müller'},Path('a.JPG'),'{titel}',settings),'gruesse aerger fuer mueller.JPG')
    def test_reserved_and_unsafe(self):
        self.assertEqual(make_name({'titel':'CON'},Path('a.txt'),'{titel}',Settings()),'Datei_CON.txt')
        name=make_name({'titel':'../A/B\\C:*?\u202e'},Path('a.txt'),'{titel}',Settings())
        self.assertNotIn('/',name);self.assertNotIn('\\',name);self.assertNotIn('\u202e',name)
    def test_multibyte_limit_including_conflicts(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'a.txt';path.write_text('source')
            settings=Settings(max_name_length=40)
            name=make_name({'titel':'ä'*100},path,'{titel}',settings)
            self.assertLessEqual(len(name.encode()),40)
            path.with_name(name).write_text('other')
            second=available_name(path,name,set(),settings)
            self.assertNotEqual(name,second);self.assertLessEqual(len(second.encode()),40)
    def test_presets_are_valid_editable_templates(self):
        for _,template in PRESETS.values():
            self.assertTrue(make_name(EXAMPLE,Path('a.pdf'),template,Settings()).endswith('.pdf'))
    def test_live_example_and_preset_target(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings
        from nomi.app import Window
        app=QApplication.instance() or QApplication([])
        with TemporaryDirectory() as folder:
            store=QSettings(str(Path(folder)/'prefs.ini'),QSettings.Format.IniFormat);store.setValue('engine','ollama')
            window=Window(store=store)
            before=window.template.text();window.preset.setCurrentText('Fotos');window.apply_naming_preset()
            self.assertEqual(window.template.text(),before);self.assertEqual(window.image_template.text(),'{titel}')
            window.transliterate_umlauts.setChecked(True);window.name_case.setCurrentIndex(window.name_case.findData('lower'))
            self.assertIn('mueller',window.naming_example.text())
            window.template.setText('{ungueltig}');self.assertIn('prüfen',window.naming_example.text())
            window.close();app.processEvents()
