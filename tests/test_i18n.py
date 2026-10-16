import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from nomi.i18n import tr, set_language, languages

class LanguageTests(unittest.TestCase):
    def tearDown(self):set_language('de')

    def test_catalog_and_template_fields(self):
        from string import Formatter
        catalog=json.loads((Path(__file__).parents[1]/'nomi/locales/translations.json').read_text())
        self.assertEqual(set(languages()), {'de','en'})
        for locale in catalog.values():
            for source,translated in locale['messages'].items():
                self.assertEqual([x[1] for x in Formatter().parse(source) if x[1]],
                                 [x[1] for x in Formatter().parse(translated) if x[1]])
        set_language('en');self.assertEqual(tr('Rückgängig'),'Undo')
        self.assertEqual(tr('private user data'),'private user data')
        set_language('unknown');self.assertEqual(tr('Rückgängig'),'Rückgängig')

    def test_english_startup_and_language_preference(self):
        from nomi.app import Window
        app=QApplication.instance() or QApplication([])
        with TemporaryDirectory() as folder:
            store=QSettings(str(Path(folder)/'settings.ini'),QSettings.Format.IniFormat)
            store.setValue('language','en');store.setValue('engine','ollama')
            window=Window(store=store)
            try:
                self.assertEqual(window.analyze_button.text(),'Analyze selected')
                self.assertEqual(window.settings_navigation.item(0).text(),'General')
                self.assertEqual(window.table.horizontalHeaderItem(1).text(),'Original name')
                self.assertEqual(window.preview.name.placeholderText(),'Edit proposed name')
                self.assertIn('Invoices',[window.preset.itemText(i) for i in range(window.preset.count())])
                window.language.setCurrentIndex(window.language.findData('de'))
                self.assertEqual(store.value('language'),'de')
                self.assertEqual(window.analyze_button.text(),'Analyze selected') # stable until restart
                self.assertNotIn('Mac',window.privacy_note.text())
            finally:window.close();app.processEvents()
