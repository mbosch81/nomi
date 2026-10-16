from __future__ import annotations
from .i18n import tr
import sys
from pathlib import Path
from dataclasses import asdict, replace
from PySide6.QtCore import Qt, QThread, Signal, QSettings, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QCheckBox, QLineEdit, QComboBox, QSpinBox, QProgressBar, QMessageBox, QDialog, QDialogButtonBox, QGroupBox, QFormLayout, QSplitter, QScrollArea, QListWidget, QStackedWidget, QInputDialog)
from .preview import PreviewPanel
from .model_manager import ModelManager
from .inbox import InboxWatcher
from .llama_backend import LocalEngine
from .local_model import default_model_path, download_model_package, model_catalog, model_directory
from .core import Settings, OllamaBackend, collect, make_name, rename_batch, undo, validate_template, RenameError, extract_document, AnalysisCancelled, available_name, validate_name, VIDEO_FORMATS, IMAGE_FORMATS

class Worker(QThread):
    result = Signal(int, str, str)
    models_ready = Signal(list)
    problem = Signal(str)
    progress = Signal(str)
    details = Signal(int, object)
    def __init__(self, settings, items=None, backend=None, router=None, cache=None, force=False):
        super().__init__()
        self.settings, self.items = settings, items
        self.cancelled = False
        self.backend = backend
        self.router = router
        self.cache, self.force = cache, force
    def requestInterruption(self):
        self.cancelled = True
        super().requestInterruption()

    def reserve_name(self,path,name,metadata,reserved):
        directory=path.parent
        if self.settings.organize_enabled:
            from .organize import destination_for
            directory=destination_for(path,name,metadata,self.settings).parent
        return available_name(path,name,reserved.setdefault(directory,set()),self.settings,
                              directory if self.settings.organize_enabled else None)

    def run(self):
        backend = self.backend if self.backend is not None else OllamaBackend()
        if self.items is None:
            try:
                self.models_ready.emit(backend.models(self.settings))
            except Exception as error:
                self.problem.emit(str(error))
            return
        reserved = {}
        for row, path in self.items:
            if self.isInterruptionRequested():
                break
            try:
                from .session import file_identity
                identity = file_identity(path)
                cached = self.cache.get(path, self.settings) if self.cache is not None and not self.force else None
                if cached is not None:
                    name = self.reserve_name(path,cached['name'],cached.get('metadata'),reserved)
                    detail = dict(cached, name=name)
                    self.cache.put(identity, self.settings, detail)
                    self.details.emit(row, detail)
                    self.result.emit(row, name, cached['status'] + tr(' · Aus Sitzung übernommen'))
                    continue
                frames = []
                if self.router:backend = self.router.backend_for(path)
                is_video = path.suffix.lower() in VIDEO_FORMATS
                is_visual_image = path.suffix.lower() in IMAGE_FORMATS and (self.settings.image_analysis == 'vision' or
                    (self.settings.image_analysis == 'auto' and self.settings.engine == 'llama' and getattr(backend, 'supports_images', False)))
                if is_visual_image:
                    from .image_analysis import suggest_image
                    from .core import Extraction
                    metadata = suggest_image(backend, path, self.settings, self.isInterruptionRequested)
                    document = Extraction('')
                elif is_video:
                    from .video import suggest_video
                    from .core import Extraction
                    metadata = suggest_video(backend, path, self.settings, self.isInterruptionRequested, frames.extend)
                    document = Extraction('')
                else:
                    document = extract_document(path, settings=self.settings, cancelled=self.isInterruptionRequested)
                    if self.isInterruptionRequested():break
                    metadata = backend.suggest(document.text, self.settings)
                if self.isInterruptionRequested():break
                from .routing import naming_template
                proposed = make_name(metadata, path, naming_template(self.settings, path), self.settings)
                name = self.reserve_name(path,proposed,metadata,reserved)
                if name == path.name:
                    status = tr('Unverändert')
                elif path.with_name(name).exists():
                    status = tr('Namenskonflikt — bitte bearbeiten')
                else:
                    status = tr('Bereit')
                if name != proposed:
                    status += tr(' · Konflikt durch Nummernzusatz vermieden')
                for warning in metadata.get('_warnings', []):
                    status += ' · ' + warning
                if is_video:
                    status += f"{tr(' · Video-Stichprobe (')}{self.settings.video_frames} Frames)"
                if is_visual_image:status += tr(' · Bildinhalt (Vision)')
                if document.used_ocr:
                    status += ' · OCR' + (f' ({document.ocr_backend})' if document.ocr_backend else '')
                if document.truncated:
                    status += tr(' · Textausschnitt, bitte prüfen')
                if file_identity(path) != identity:
                    raise ValueError(tr('Datei wurde während der Analyse verändert. Bitte erneut analysieren.'))
                from string import Formatter
                missing = [field for _,field,_,_ in Formatter().parse(naming_template(self.settings,path)) if field and not metadata.get(field)]
                detail = dict(name=name, status=status, frames=frames, identity=identity, settings=self.settings, missing_fields=missing, metadata={key:metadata.get(key,'') for key in ('datum','absender','empfaenger','dokumenttyp','titel','kennung')})
                if self.cache is not None:self.cache.put(identity, self.settings, detail)
                self.details.emit(row, detail)
                self.result.emit(row, name, status)
            except AnalysisCancelled:
                break
            except Exception as error:
                self.result.emit(row, '', tr('Fehler: ') + str(error))

class EngineWorker(QThread):
    progress = Signal(str)
    ready = Signal(object, str)
    problem = Signal(str)

    def __init__(self, engine, settings, download=False):
        super().__init__()
        self.engine, self.settings, self.download = engine, settings, download
        self.items = None
        self.cancelled = False

    def requestInterruption(self):
        self.cancelled = True
        super().requestInterruption()

    def run(self):
        try:
            if self.download:
                path, projector = download_model_package('qwen' if self.download is True else self.download,
                    cancelled=self.isInterruptionRequested, progress=self.progress.emit)
            else:
                path = Path(self.settings.llama_model)
                projector = Path(self.settings.llama_projector) if self.settings.llama_projector else None
            options = {'projector': projector} if projector else {}
            backend = self.engine.start(path, self.isInterruptionRequested, self.progress.emit, **options)
            if self.isInterruptionRequested():
                raise AnalysisCancelled()
            self.ready.emit(backend, str(path))
        except AnalysisCancelled:
            self.cancelled = True
        except Exception as error:
            self.engine.stop()
            if not self.isInterruptionRequested():
                self.problem.emit(str(error))
        finally:
            if self.cancelled:
                self.engine.stop()

class Window(QMainWindow):
    def __init__(self, store=None):
        super().__init__()

        self.resize(1380, 820)
        self.setAcceptDrops(True)
        self.paths = []
        self.worker = None
        self.history = []
        from .session import SessionResults
        self.session_results = SessionResults()
        self.analysis_details = {}
        self.analysis_identities = {}
        self.local_engine = LocalEngine()
        self._local_backend = None
        self._close_pending = False
        self.store = store if store is not None else QSettings('Nomi', 'Nomi')
        from .i18n import set_language, languages, install_qt_translation
        language = str(self.store.value('language', 'de'))
        set_language(language)
        install_qt_translation(QApplication.instance(), language)
        self.setWindowTitle(tr('Nomi · Jede Datei verdient einen Namen'))
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        title = QLabel('Nomi')
        title.setStyleSheet('font-size: 34px; font-weight: 700; color: #a6b5ff;')
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        self.settings_button = QPushButton('⚙')
        self.settings_button.setFixedSize(42, 42)
        self.settings_button.setStyleSheet('font-size: 25px; padding: 0;')
        self.settings_button.setToolTip(tr('Einstellungen öffnen (⌘, auf macOS)'))
        self.settings_button.setAccessibleName(tr('Einstellungen öffnen'))
        self.settings_button.clicked.connect(self.show_settings)
        header.addWidget(self.settings_button)
        layout.addLayout(header)
        layout.addWidget(QLabel(tr('Jede Datei verdient einen Namen.')))
        self.drop_hint = QLabel(tr('Dateien oder Ordner hierher ziehen · PDF, DOCX, Bilder, Videos, TXT, Markdown und CSV'))
        self.drop_hint.setStyleSheet('border: 2px dashed #55618a; border-radius: 12px; padding: 22px; color: #bec8e5;')
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.drop_hint)
        import_row = QHBoxLayout()
        self.files_button = QPushButton(tr('Dateien hinzufügen'))
        self.folder_button = QPushButton(tr('Ordner auswählen'))
        self.recursive = QCheckBox(tr('Unterordner einbeziehen'))
        self.clear_button = QPushButton(tr('Liste leeren'))
        for widget in (self.files_button, self.folder_button, self.recursive, self.clear_button):
            import_row.addWidget(widget)
        import_row.addStretch()
        layout.addLayout(import_row)
        self.settings_dialog = QDialog(self)
        self.settings_dialog.setWindowTitle(tr('Nomi · Einstellungen'))
        self.settings_dialog.resize(760, 650)
        settings_outer = QVBoxLayout(self.settings_dialog)
        settings_body = QHBoxLayout()
        self.settings_navigation = QListWidget()
        self.settings_navigation.setAccessibleName(tr('Einstellungsbereiche'))
        self.settings_navigation.setFixedWidth(170)
        self.settings_stack = QStackedWidget()
        settings_body.addWidget(self.settings_navigation)
        settings_body.addWidget(self.settings_stack, 1)
        settings_outer.addLayout(settings_body, 1)
        def category(title):
            self.settings_navigation.addItem(title)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QWidget()
            section = QVBoxLayout(content)
            section.setContentsMargins(16, 12, 16, 12)
            section.setSpacing(16)
            scroll.setWidget(content)
            self.settings_stack.addWidget(scroll)
            return section
        general_layout = category(tr('Allgemein'))
        language_form = QFormLayout()
        self.language = QComboBox()
        for code, label in languages().items():
            self.language.addItem(label, code)
        self.language.setCurrentIndex(max(0, self.language.findData(language)))
        self.language.currentIndexChanged.connect(lambda: self.store.setValue('language', self.language.currentData()))
        language_form.addRow(tr('Sprache'), self.language)
        general_layout.addLayout(language_form)
        general_layout.addWidget(QLabel(tr('Sprache nach Neustart von Nomi aktiv.')))
        ai_layout = category(tr('KI'))
        video_layout = category('Video')
        image_layout = category(tr('Bilder'))
        ocr_layout = category(tr('Texterkennung'))
        inbox_page = category(tr('Eingangsordner'))
        organize_page = category(tr('Einsortieren'))
        self.settings_navigation.currentRowChanged.connect(self.settings_stack.setCurrentIndex)
        self.settings_navigation.setCurrentRow(0)
        backend_group = QGroupBox(tr('Analyse und Modelle'))
        backend_row = QFormLayout(backend_group)
        ai_layout.addWidget(backend_group)
        settings_menu = self.menuBar().addMenu(tr('Einstellungen'))
        self.settings_action = QAction(tr('Einstellungen …'), self)
        self.settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        self.settings_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(self.settings_action)
        self.engine = QComboBox()
        self.engine.addItem(tr('Lokal · llama.cpp'), 'llama')
        self.engine.addItem(tr('Ollama · Server'), 'ollama')
        selected_engine = str(self.store.value('engine', 'llama'))
        self.engine.setCurrentIndex(max(0, self.engine.findData(selected_engine)))
        backend_row.addRow('Backend', self.engine)
        self.url = QLineEdit(str(self.store.value('url', 'http://localhost:11434')))
        self.url.setPlaceholderText('http://server:port')
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.setMinimumWidth(160)
        self.model.setCurrentText(str(self.store.value('model', '')))
        self.model.setPlaceholderText(tr('Modellname'))
        self.connect_button = QPushButton(tr('Modelle laden'))
        self.timeout = QSpinBox()
        self.timeout.setRange(10, 600)
        self.timeout.setValue(int(self.store.value('timeout', 120)))
        self.timeout.setSuffix(' s')
        self.url_label = QLabel(tr('Ollama-Adresse'))
        self.model_label = QLabel(tr('Ollama-Modell'))
        backend_row.addRow(self.url_label, self.url)
        model_row = QHBoxLayout()
        model_row.addWidget(self.model)
        model_row.addWidget(self.connect_button)
        backend_row.addRow(self.model_label, model_row)
        backend_row.addRow(tr('Zeitlimit pro Anfrage'), self.timeout)
        self.local_group = QGroupBox(tr('Lokales GGUF-Modell'))
        local_row = QVBoxLayout(self.local_group)
        ai_layout.addWidget(self.local_group)
        self.auto_models = QCheckBox(tr('Modell passend zur Datei automatisch wählen'))
        self.auto_models.setChecked(str(self.store.value('auto_models', 'true')).lower() in {'true', '1'})
        local_row.addWidget(self.auto_models)
        self.text_model = QComboBox()
        for spec in model_catalog():
            if not spec.projector:self.text_model.addItem(tr(spec.label), spec.key)
        self.text_model.setCurrentIndex(max(0, self.text_model.findData(str(self.store.value('text_model', 'qwen')))))
        local_row.addWidget(QLabel(tr('Dokumentmodell für automatische Auswahl')))
        local_row.addWidget(self.text_model)
        routing_hint = QLabel(tr('Dokumente: Qwen oder Mistral · Bilder/Videos: SmolVLM2. Fehlende Modelle werden beim Analysieren heruntergeladen. Es bleibt jeweils nur ein Modell geladen. Für eigene GGUFs automatische Auswahl ausschalten.'))
        routing_hint.setWordWrap(True)
        local_row.addWidget(routing_hint)
        self.gguf = QLineEdit(str(self.store.value('llama_model', str(default_model_path()))))
        self.gguf.setPlaceholderText(tr('GGUF-Modell auswählen'))
        self.gguf_button = QPushButton(tr('GGUF wählen'))
        self.download_choice = QComboBox()
        self.download_choice.setAccessibleName(tr('Download-Modell'))
        for model in model_catalog():
            self.download_choice.addItem(tr(model.label), model.key)
        self.download_choice.setCurrentIndex(-1)
        for index, model in enumerate(model_catalog()):
            if Path(self.gguf.text()).name == model.filename:
                self.download_choice.setCurrentIndex(index)
                break
        self.download_button = QPushButton(tr('Ausgewähltes Modell herunterladen / laden'))
        self.download_button.setEnabled(self.download_choice.currentIndex() >= 0)
        self.local_load_button = QPushButton(tr('Modell laden'))
        self.autoload = QCheckBox(tr('Beim Start laden'))
        self.autoload.setChecked(str(self.store.value('llama_autoload', 'true')).lower() in {'true', '1'})
        local_row.addWidget(QLabel(tr('Verfügbare Modelle (Q4_K_M)')))
        local_row.addWidget(self.download_choice)
        path_row = QHBoxLayout()
        path_row.addWidget(self.gguf, 1)
        path_row.addWidget(self.gguf_button)
        local_row.addLayout(path_row)
        model_actions = QHBoxLayout()
        model_actions.addWidget(self.download_button)
        model_actions.addWidget(self.local_load_button)
        local_row.addLayout(model_actions)
        self.projector = QLineEdit(str(self.store.value('llama_projector', '')))
        self.projector.setPlaceholderText(tr('Optionaler Vision-Projektor (mmproj.gguf)'))
        self.projector_button = QPushButton(tr('Projektor wählen'))
        projector_row = QHBoxLayout()
        projector_row.addWidget(self.projector, 1)
        projector_row.addWidget(self.projector_button)
        local_row.addLayout(projector_row)
        local_row.addWidget(self.autoload)
        self.manage_models = QPushButton(tr('Installierte Modelle verwalten …'))
        self.manage_models.clicked.connect(lambda: self.model_manager.open_manager())
        local_row.addWidget(self.manage_models)
        schema_group = QGroupBox(tr('Dateinamen'))
        schema_row = QFormLayout(schema_group)
        general_layout.addWidget(schema_group)
        self.template = QLineEdit(str(self.store.value('template', '{datum}_{absender}_{dokumenttyp}')))
        self.template.setToolTip(tr('Verfügbare Felder: {datum}, {absender}, {dokumenttyp}, {titel}, {empfaenger}, {kennung}'))
        schema_row.addRow(tr('Dokumente'), self.template)
        self.image_template = QLineEdit(str(self.store.value('image_template', '{titel}')))
        self.video_template = QLineEdit(str(self.store.value('video_template', 'Video_{titel}')))
        schema_row.addRow(tr('Bilder'), self.image_template)
        schema_row.addRow('Videos', self.video_template)
        from .naming import PRESETS
        self.preset = QComboBox()

        for key in PRESETS:self.preset.addItem(tr(key),key)
        self.apply_preset = QPushButton(tr('Vorlage übernehmen'))
        presets_row = QHBoxLayout()
        presets_row.addWidget(self.preset,1);presets_row.addWidget(self.apply_preset)
        schema_row.addRow(tr('Vorlagen'),presets_row)
        self.name_separator = QComboBox()
        self.name_separator.addItem(tr('Unterstriche'),'_');self.name_separator.addItem(tr('Leerzeichen'),' ')
        self.name_separator.setCurrentIndex(max(0,self.name_separator.findData(str(self.store.value('name_separator','_')))))
        self.name_case = QComboBox()
        for label,value in [(tr('Beibehalten'),'preserve'),(tr('kleinschreibung'),'lower'),(tr('GROSSSCHREIBUNG'),'upper')]:self.name_case.addItem(label,value)
        self.name_case.setCurrentIndex(max(0,self.name_case.findData(str(self.store.value('name_case','preserve')))))
        self.max_name_length = QSpinBox();self.max_name_length.setRange(40,240)
        self.max_name_length.setValue(int(self.store.value('max_name_length',180)))
        self.max_name_length.setToolTip(tr('Gesamter Dateiname einschließlich Endung; zusätzlich wird die UTF-8-Bytelänge begrenzt.'))
        self.transliterate_umlauts = QCheckBox(tr('Umlaute ersetzen (ä → ae, ß → ss)'))
        self.transliterate_umlauts.setChecked(str(self.store.value('transliterate_umlauts','false')).lower() in ('true','1'))
        self.windows_compatible = QCheckBox(tr('Windows-/NAS-kompatible Namen absichern'))
        self.windows_compatible.setChecked(str(self.store.value('windows_compatible','true')).lower() in ('true','1'))
        schema_row.addRow(tr('Trennzeichen'),self.name_separator)
        schema_row.addRow(tr('Schreibweise'),self.name_case)
        schema_row.addRow(tr('Maximale Namenslänge'),self.max_name_length)
        schema_row.addRow(self.transliterate_umlauts);schema_row.addRow(self.windows_compatible)
        self.naming_example = QLabel()
        self.naming_example.setWordWrap(True);self.naming_example.setTextFormat(Qt.TextFormat.PlainText)
        schema_row.addRow(tr('Beispiel (synthetisch)'),self.naming_example)
        schema_hint = QLabel('{datum}, {absender}, {dokumenttyp}, {titel}, {empfaenger}, {kennung}')
        schema_hint.setWordWrap(True)
        schema_row.addRow(schema_hint)
        ocr_group = QGroupBox(tr('Texterkennung'))
        ocr_row = QFormLayout(ocr_group)
        ocr_layout.addWidget(ocr_group)
        self.ocr_enabled = QCheckBox(tr('OCR für PDF- und Bildscans'))
        self.ocr_enabled.setChecked(str(self.store.value('ocr_enabled', 'false')).lower() in {'true', '1'})
        self.ocr_backend = QComboBox()
        self.ocr_backend.addItem(tr('Automatisch'), 'auto')
        self.ocr_backend.addItem('Apple Vision (macOS)', 'vision')
        self.ocr_backend.addItem('Windows OCR', 'windows')
        self.ocr_backend.addItem('Tesseract', 'tesseract')
        index = self.ocr_backend.findData(str(self.store.value('ocr_backend', 'auto')))
        self.ocr_backend.setCurrentIndex(max(0, index))
        self.ocr_language = QLineEdit(str(self.store.value('ocr_language', 'deu+eng')))
        self.ocr_language.setMaximumWidth(110)
        self.ocr_language.setToolTip(tr('OCR-Sprachen, z.B. deu+eng (Deutsch und Englisch)'))
        self.ocr_command = QLineEdit(str(self.store.value('ocr_command', 'tesseract')))
        self.ocr_command.setToolTip(tr('Tesseract-Programmname oder vollständiger Programmpfad'))
        self.ocr_command_label = QLabel('Tesseract')
        ocr_row.addRow(self.ocr_enabled)
        ocr_row.addRow('OCR-Backend', self.ocr_backend)
        ocr_row.addRow(tr('Sprachen'), self.ocr_language)
        ocr_row.addRow(self.ocr_command_label, self.ocr_command)
        notice = QLabel(tr('Apple Vision auf macOS, Windows OCR auf Windows: keine separate OCR-Installation nötig. Verfügbare Sprachen hängen vom Betriebssystem ab. Tesseract bleibt optional.'))
        notice.setWordWrap(True)
        ocr_row.addRow(notice)
        inbox_group = QGroupBox(tr('Überwachter Eingangsordner'))
        inbox_layout = QVBoxLayout(inbox_group)
        self.inbox_enabled = QCheckBox(tr('Eingangsordner überwachen'))
        self.inbox_enabled.setChecked(str(self.store.value('inbox_enabled', 'false')).lower() in {'true', '1'})
        self.inbox_folder = QLineEdit(str(self.store.value('inbox_folder', '')))
        self.inbox_folder.setPlaceholderText(tr('Ordner für neue Dokumente'))
        self.inbox_choose = QPushButton(tr('Ordner wählen'))
        inbox_path = QHBoxLayout();inbox_path.addWidget(self.inbox_folder);inbox_path.addWidget(self.inbox_choose)
        self.inbox_recursive = QCheckBox(tr('Unterordner überwachen'))
        self.inbox_recursive.setChecked(str(self.store.value('inbox_recursive', 'false')).lower() in {'true', '1'})
        inbox_layout.addWidget(self.inbox_enabled)
        inbox_layout.addLayout(inbox_path)
        inbox_layout.addWidget(self.inbox_recursive)
        self.inbox_status = QLabel(tr('Nur Import · keine automatische Analyse oder Umbenennung'))
        self.inbox_status.setWordWrap(True)
        inbox_layout.addWidget(self.inbox_status)
        inbox_page.addWidget(inbox_group)
        video_group = QGroupBox(tr('Videoanalyse'))
        video_form = QFormLayout(video_group)
        self.video_frames = QSpinBox()
        self.video_frames.setRange(1, 12)
        self.video_frames.setValue(int(self.store.value('video_frames', 5)))
        self.video_timeout = QSpinBox()
        self.video_timeout.setRange(10, 300)
        self.video_timeout.setSuffix(' s')
        self.video_timeout.setValue(int(self.store.value('video_timeout', 60)))
        video_form.addRow(tr('Einzelbilder pro Video'), self.video_frames)
        video_form.addRow(tr('Zeitlimit für Frame-Extraktion'), self.video_timeout)
        video_hint = QLabel(tr('Verteilte Einzelbilder werden mit einem Vision-Modell ausgewertet. '
                            'Ton wird nicht analysiert. Mehr Frames benötigen mehr Zeit und Arbeitsspeicher. '
                            'FFmpeg ist in der App enthalten; eine separate Installation ist nicht nötig.'))
        video_hint.setWordWrap(True)
        video_form.addRow(video_hint)
        video_layout.addWidget(video_group)
        image_group = QGroupBox(tr('Bildanalyse'))
        image_form = QFormLayout(image_group)
        self.image_analysis = QComboBox()
        for label, value in [(tr('Automatisch (lokal Vision, sonst OCR)'), 'auto'),
                             (tr('Bildinhalt mit Vision-Modell'), 'vision'), (tr('Nur Text erkennen (OCR)'), 'ocr')]:
            self.image_analysis.addItem(label, value)
        self.image_analysis.setCurrentIndex(max(0, self.image_analysis.findData(str(self.store.value('image_analysis', 'auto')))))
        image_form.addRow(QLabel(tr('Auswertung für PNG und JPEG')))
        image_form.addRow(self.image_analysis)
        image_hint = QLabel(tr('Vision erkennt Motive, Objekte und Szenen auch ohne Text. Dafür SmolVLM2 oder ein anderes Vision-Modell laden. '
                            'Für Ollama die Vision-Auswertung ausdrücklich auswählen und ein bildfähiges Modell verwenden. '
                            'Für Dokument-Scans bleibt „Nur Text erkennen (OCR)“ verfügbar. '
                            'Für beschreibende Namen {titel} im Namensschema verwenden. Originalbilder bleiben unverändert.'))
        image_hint.setWordWrap(True)
        image_form.addRow(image_hint)
        image_layout.addWidget(image_group)
        organize_group=QGroupBox(tr('Optional nach Analyse einsortieren'))
        organize_form=QFormLayout(organize_group)
        self.organize_enabled=QCheckBox(tr('Beim Umbenennen in Zielordner einsortieren'))
        self.organize_enabled.setChecked(str(self.store.value('organize_enabled','false')).lower() in ('true','1'))
        self.organize_root=QLineEdit(str(self.store.value('organize_root','')))
        self.organize_choose=QPushButton(tr('Zielordner wählen'))
        root_row=QHBoxLayout();root_row.addWidget(self.organize_root,1);root_row.addWidget(self.organize_choose)
        self.folder_template=QLineEdit(str(self.store.value('folder_template','{jahr}/{dokumenttyp}')))
        self.folder_template.setPlaceholderText(tr('Leer = direkt im Zielordner'))
        self.organize_example=QLabel();self.organize_example.setWordWrap(True)
        self.organize_example.setTextFormat(Qt.TextFormat.PlainText)
        organize_form.addRow(self.organize_enabled)
        organize_form.addRow(tr('Zielordner'),root_row)
        organize_form.addRow(tr('Unterordner-Schema'),self.folder_template)
        organize_form.addRow(tr('Beispiel'),self.organize_example)
        organize_hint=QLabel(tr('Felder: {jahr}, {monat}, {datum}, {dokumenttyp}, {absender}, {titel}, {empfaenger}, {kennung}. '
                            'Fehlendes Datum → Ohne_Datum; andere fehlende Felder → Unsortiert. '
                            'Ziel und Quelle müssen auf demselben Laufwerk liegen. Ordner entstehen erst nach Bestätigung. '
                            'Rückgängig stellt die ursprünglichen Speicherorte wieder her. Symbolische Links werden nicht verwendet.'))
        organize_hint.setWordWrap(True);organize_form.addRow(organize_hint)
        organize_page.addWidget(organize_group)
        for section in (general_layout, ai_layout, video_layout, image_layout, ocr_layout, inbox_page, organize_page):
            section.addStretch()
        settings_outer.addWidget(QLabel(tr('Änderungen werden direkt übernommen und beim Schließen gespeichert.')))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(tr('Schließen'))
        buttons.rejected.connect(self.settings_dialog.close)
        settings_outer.addWidget(buttons)
        self.settings_dialog.finished.connect(lambda _: self.settings())
        self.ocr_backend.currentIndexChanged.connect(self.update_ocr_controls)
        self.update_ocr_controls()
        self.privacy_note = QLabel(tr('Die Analyse sendet bis zu 16.000 Zeichen je Datei an die eingestellte Adresse. PDFs: maximal 20 Seiten.\nEin vorgeschalteter Router kann Inhalte an Cloud-Anbieter weiterleiten. Umbenennung erfolgt erst nach deinem Klick.'))
        self.privacy_note.setWordWrap(True)
        self.privacy_note.setStyleSheet('color: #aeb9d2; font-size: 11px;')
        layout.addWidget(self.privacy_note)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr('Verwenden'), tr('Originalname'), tr('Neuer Name · editierbar'), 'Status'])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(40)
        widths = self.store.value('table_column_widths', [100, 260, 300, 220])
        if not isinstance(widths, (list, tuple)) or len(widths) != 4:
            widths = [100, 260, 300, 220]
        for column, width in enumerate(widths):
            try:
                width = max(40, min(3000, int(width)))
            except (ValueError, TypeError):
                width = [100, 260, 300, 220][column]
            header.resizeSection(column, width)
        header.setToolTip(tr('Spaltengrenzen ziehen · Doppelklick passt die Breite an den Inhalt an'))
        header.sectionResized.connect(lambda *_: self.store.setValue(
            'table_column_widths', [header.sectionSize(column) for column in range(4)]))
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self.changed)
        self.preview = PreviewPanel()
        self.preview.name_edited.connect(self.edit_preview_name)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.preview)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setSizes([820, 500])
        layout.addWidget(self.splitter, 1)
        self.table.currentCellChanged.connect(lambda *_: self.update_preview())
        actions = QHBoxLayout()
        self.all_button = QPushButton(tr('Alle auswählen'))
        self.none_button = QPushButton(tr('Alle abwählen'))
        self.analyze_button = QPushButton(tr('Auswahl analysieren'))
        self.reanalyze_button = QPushButton(tr('Erneut analysieren …'))
        self.reanalyze_button.setToolTip(tr('Markierte Dateien erneut analysieren · optional mit Hinweis'))
        self.cancel_button = QPushButton(tr('Abbrechen'))
        self.cancel_button.setEnabled(False)
        self.rename_button = QPushButton(tr('Auswahl umbenennen'))
        self.rename_button.setStyleSheet('background: #6677dd; color: white; font-weight: 600;')
        self.undo_button = QPushButton(tr('Rückgängig'))
        self.undo_button.setEnabled(False)
        for widget in (self.all_button, self.none_button, self.analyze_button, self.reanalyze_button, self.cancel_button, self.rename_button, self.undo_button):
            actions.addWidget(widget)
        layout.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QLabel(tr('Bereit · Einstellungen werden automatisch gespeichert.'))
        layout.addWidget(self.status)
        self.files_button.clicked.connect(self.choose_files)
        self.folder_button.clicked.connect(self.choose_folder)
        self.clear_button.clicked.connect(self.clear)
        self.connect_button.clicked.connect(self.load_models)
        self.analyze_button.clicked.connect(lambda: self.analyze())
        self.reanalyze_button.clicked.connect(self.reanalyze)
        self.cancel_button.clicked.connect(self.cancel)
        self.rename_button.clicked.connect(self.review_rename)
        self.undo_button.clicked.connect(self.revert)
        self.all_button.clicked.connect(lambda: self.select_all(True))
        self.none_button.clicked.connect(lambda: self.select_all(False))
        self.busy_widgets = [self.files_button, self.folder_button, self.recursive, self.clear_button, self.url, self.model, self.connect_button, self.timeout, self.template, self.all_button, self.none_button, self.analyze_button, self.reanalyze_button, self.rename_button, self.undo_button, self.ocr_enabled, self.ocr_language, self.ocr_command, self.ocr_backend, self.engine, self.gguf, self.gguf_button, self.download_button, self.local_load_button, self.autoload, self.download_choice, self.inbox_enabled, self.inbox_folder, self.inbox_choose, self.inbox_recursive, self.projector, self.projector_button, self.video_frames, self.video_timeout, self.image_analysis, self.auto_models, self.text_model, self.image_template, self.video_template, self.preset, self.apply_preset, self.name_separator, self.name_case, self.max_name_length, self.transliterate_umlauts, self.windows_compatible, self.organize_enabled, self.organize_root, self.organize_choose, self.folder_template]

        self.auto_models.toggled.connect(self.refresh_analysis_enabled)
        self.apply_preset.clicked.connect(self.apply_naming_preset)
        for widget in (self.template,self.image_template,self.video_template):widget.textChanged.connect(self.update_naming_example)
        for widget in (self.name_separator,self.name_case):widget.currentIndexChanged.connect(self.update_naming_example)
        self.max_name_length.valueChanged.connect(self.update_naming_example)
        self.transliterate_umlauts.toggled.connect(self.update_naming_example)
        self.windows_compatible.toggled.connect(self.update_naming_example)
        self.organize_choose.clicked.connect(self.choose_organize_root)
        self.organize_enabled.toggled.connect(self.update_naming_example)
        self.organize_enabled.toggled.connect(self.check_conflicts)
        self.organize_root.textChanged.connect(self.update_naming_example)
        self.folder_template.textChanged.connect(self.update_naming_example)
        self.update_naming_example()
        self.engine.currentIndexChanged.connect(self.engine_changed)
        self.gguf.textChanged.connect(self.model_path_changed)
        self.projector.textChanged.connect(self.projector_path_changed)
        self.projector_button.clicked.connect(self.choose_projector)
        self.gguf_button.clicked.connect(self.choose_gguf)
        self.download_button.clicked.connect(lambda: self.start_local_model(download=self.download_choice.currentData()))
        self.download_choice.currentIndexChanged.connect(self.download_model_changed)
        self.local_load_button.clicked.connect(lambda: self.start_local_model())
        for model in model_catalog():
            if model.projector and Path(self.gguf.text()).name == model.filename and not self.projector.text():
                self.projector.setText(str(Path(self.gguf.text()).parent / model.projector.filename))
        self.update_engine_controls()
        self.model_manager = ModelManager(self)
        self.inbox = InboxWatcher(self.busy, self)
        self.inbox.files_ready.connect(self.add)
        self.inbox.message.connect(self.inbox_status.setText)
        self.inbox_enabled.toggled.connect(self.configure_inbox)
        self.inbox_recursive.toggled.connect(self.configure_inbox)
        self.inbox_folder.editingFinished.connect(self.configure_inbox)
        self.inbox_choose.clicked.connect(self.choose_inbox)
        self.configure_inbox()
        QTimer.singleShot(0, self.auto_load)

    def choose_inbox(self):
        folder = QFileDialog.getExistingDirectory(self, tr('Eingangsordner wählen'))
        if folder:
            self.inbox_folder.setText(folder)
            self.configure_inbox()

    def configure_inbox(self):
        enabled = self.inbox_enabled.isChecked()
        folder = self.inbox_folder.text().strip()
        recursive = self.inbox_recursive.isChecked()
        for key, value in (('inbox_enabled', enabled), ('inbox_folder', folder), ('inbox_recursive', recursive)):
            self.store.setValue(key, value)
        self.inbox.configure(folder if enabled else '', recursive)

    def download_model_changed(self):
        selected = self.download_choice.currentData()
        for model in model_catalog():
            if model.key == selected:
                self.gguf.setText(str(model_directory() / model.filename))
                break

    def show_settings(self):
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def update_engine_controls(self):
        local = self.engine.currentData() == 'llama'
        self.url_label.setVisible(not local)
        self.model_label.setVisible(not local)
        self.local_group.setVisible(local)
        for widget in (self.url, self.model, self.connect_button):
            widget.setVisible(not local)
        for widget in (self.gguf, self.gguf_button, self.download_button, self.local_load_button, self.autoload, self.projector, self.projector_button):
            widget.setVisible(local)
        self.privacy_note.setText(
            tr('Analyse vollständig auf diesem Gerät über llama.cpp. Bis zu 16.000 Zeichen je Datei, PDFs maximal 20 Seiten. '
            'Bei Videos werden Einzelbilder lokal ausgewertet. Beim erstmaligen Modelldownload wird Hugging Face kontaktiert. Umbenennung erst nach deinem Klick.')
            if local else tr('Die Analyse sendet bis zu 16.000 Zeichen je Datei an die eingestellte Ollama-Adresse. PDFs: maximal 20 Seiten. '
            'Bilder und Video-Einzelbilder werden ebenfalls an das Backend gesendet. Ein vorgeschalteter Router kann Inhalte an Cloud-Anbieter weiterleiten. Umbenennung erst nach deinem Klick.'))
        self.refresh_analysis_enabled()

    def refresh_analysis_enabled(self):
        ready = self.engine.currentData() != 'llama' or self.auto_models.isChecked() or (self._local_backend is not None and self.local_engine.alive() and self.local_engine.model == Path(self.gguf.text()).expanduser().absolute())
        self.analyze_button.setEnabled(not self.busy() and ready)
        self.reanalyze_button.setEnabled(not self.busy() and ready)

    def engine_changed(self):
        if self.engine.currentData() != 'llama':
            self.local_engine.stop()
            self._local_backend = None
            self.status.setText(tr('Ollama · Modell wählen oder Modelle laden.'))
        self.update_engine_controls()
        if self.engine.currentData() == 'llama':
            QTimer.singleShot(0, self.auto_load)

    def model_path_changed(self):
        index = next((i for i, model in enumerate(model_catalog())
                      if Path(self.gguf.text()).name == model.filename), -1)
        self.download_choice.blockSignals(True)
        self.download_choice.setCurrentIndex(index)
        self.download_choice.blockSignals(False)
        self.download_button.setEnabled(not self.busy() and index >= 0)
        if index >= 0:
            model = model_catalog()[index]
            self.projector.setText(str(Path(self.gguf.text()).parent / model.projector.filename) if model.projector else '')
        if self.local_engine.model != Path(self.gguf.text()).expanduser().absolute():
            self._local_backend = None
            if self.engine.currentData() == 'llama':
                self.status.setText(tr('Modellauswahl geändert · Modell laden anklicken.'))
        self.refresh_analysis_enabled()

    def projector_path_changed(self):
        current = Path(self.projector.text()).expanduser().absolute() if self.projector.text() else None
        if current != getattr(self.local_engine, 'projector', None):
            self._local_backend = None
            self.refresh_analysis_enabled()

    def choose_projector(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Vision-Projektor auswählen'), '', tr('GGUF-Projektor (*.gguf)'))
        if path:self.projector.setText(path)

    def choose_gguf(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Lokales Modell auswählen'), '', tr('GGUF-Modelle (*.gguf)'))
        if path:
            self.gguf.setText(path)

    def auto_load(self):
        if self.busy() or self.engine.currentData() != 'llama':
            return
        if not self.autoload.isChecked():
            self.status.setText(tr('Lokales Modell noch nicht geladen · Modell laden anklicken.'))
        elif self.auto_models.isChecked():
            from .local_model import model_spec
            path = model_directory() / model_spec(self.text_model.currentData()).filename
            if not path.is_file():
                self.status.setText(tr('Automatische Modellwahl bereit · fehlende Modelle werden beim Analysieren geladen.'))
                return
            self._local_backend = None
            self.progress.setRange(0, 0)
            worker = EngineWorker(self.local_engine, replace(self.settings(), llama_model=str(path), llama_projector=''))
            worker.progress.connect(self.status.setText)
            worker.ready.connect(self.automatic_model_ready)
            self.start(worker)
        elif Path(self.gguf.text()).expanduser().is_file():
            self.start_local_model()
        else:
            self.status.setText(tr('Lokales Modell fehlt · GGUF auswählen oder ein angebotenes Modell herunterladen.'))

    def automatic_model_ready(self, backend, path):
        self._local_backend = backend
        self.status.setText(tr('Automatische Modellwahl · bereit mit ') + Path(path).name)
        self.model_manager.refresh()

    def start_local_model(self, download=False):
        if self.busy():
            return
        self._local_backend = None
        self.progress.setRange(0, 0)
        self.status.setText(tr('Lokales Modell wird vorbereitet …'))
        worker = EngineWorker(self.local_engine, self.settings(), download)
        worker.progress.connect(self.status.setText)
        worker.ready.connect(self.local_model_ready)
        self.start(worker)

    def local_model_ready(self, backend, path):
        self.gguf.setText(path)
        self.projector.setText(str(getattr(self.local_engine, 'projector', '') or ''))
        self._local_backend = backend
        self.store.setValue('llama_model', path)
        self.store.setValue('llama_projector', self.projector.text())
        self.status.setText(tr('Lokales Modell bereit · ') + Path(path).name)
        self.model_manager.refresh()

    def update_ocr_controls(self):
        from .ocr import effective_backend
        show_command = effective_backend(self.ocr_backend.currentData()) == 'tesseract'
        self.ocr_command.setVisible(show_command)
        self.ocr_command_label.setVisible(show_command)

    def choose_organize_root(self):
        folder=QFileDialog.getExistingDirectory(self,tr('Zielordner für Einsortieren wählen'))
        if folder:self.organize_root.setText(folder)

    def apply_naming_preset(self):
        from .naming import PRESETS
        kind,template=PRESETS[self.preset.currentData()]
        {'document':self.template,'image':self.image_template,'video':self.video_template}[kind].setText(template)

    def update_naming_example(self):
        from .naming import EXAMPLE
        from .routing import naming_template
        try:
            settings=self.settings()
            examples=[label+': '+make_name(EXAMPLE,path,naming_template(settings,path),settings)
                      for label,path in [(tr('Dokument'),Path('beispiel.pdf')),(tr('Bild'),Path('beispiel.jpg')),('Video',Path('beispiel.mp4'))]]
            self.naming_example.setText('\n'.join(examples))
        except ValueError as error:self.naming_example.setText(tr('Vorlage prüfen: ')+str(error))
        try:
            from .organize import destination_for
            sample=replace(settings,organize_enabled=True,organize_root=settings.organize_root or tr('/Zielordner'))
            self.organize_example.setText(str(destination_for(Path('beispiel.pdf'),make_name(EXAMPLE,Path('beispiel.pdf'),settings.template,settings),EXAMPLE,sample)))
        except ValueError as error:self.organize_example.setText(tr('Schema prüfen: ')+str(error))

    def settings(self):
        settings = Settings(url=self.url.text().strip(), model=self.model.currentText().strip(),
                            template=self.template.text().strip(), timeout=self.timeout.value(),
                            ocr_enabled=self.ocr_enabled.isChecked(), ocr_language=self.ocr_language.text().strip(),
                            ocr_command=self.ocr_command.text().strip(), ocr_backend=self.ocr_backend.currentData(),
                            engine=self.engine.currentData(), llama_model=self.gguf.text().strip(),
                            llama_autoload=self.autoload.isChecked(), llama_projector=self.projector.text().strip(),
                            video_frames=self.video_frames.value(), video_timeout=self.video_timeout.value(),
                            image_analysis=self.image_analysis.currentData(), auto_models=self.auto_models.isChecked(),
                            text_model=self.text_model.currentData(), image_template=self.image_template.text().strip(),
                            video_template=self.video_template.text().strip(),
                            name_separator=self.name_separator.currentData(),name_case=self.name_case.currentData(),
                            max_name_length=self.max_name_length.value(),transliterate_umlauts=self.transliterate_umlauts.isChecked(),
                            windows_compatible=self.windows_compatible.isChecked(), organize_enabled=self.organize_enabled.isChecked(),
                            organize_root=self.organize_root.text().strip(),folder_template=self.folder_template.text().strip())
        for key, value in asdict(settings).items():
            self.store.setValue(key, value)
        return settings

    def busy(self):
        return self.worker is not None

    def set_busy(self, value):
        for widget in self.busy_widgets:
            widget.setEnabled(not value)
        self.undo_button.setEnabled(not value and bool(self.history))
        self.table.setEnabled(not value)
        self.preview.name.setEnabled(not value and self.preview.path is not None)
        self.cancel_button.setEnabled(value)
        self.refresh_analysis_enabled()
        self.model_manager.update_actions()
        self.download_button.setEnabled(not value and bool(self.download_choice.currentData()))

    def dragEnterEvent(self, event):
        if not self.busy() and event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not self.busy():
            self.add([Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()])
            event.acceptProposedAction()

    def choose_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, tr('Dateien hinzufügen'), '', tr('Dokumente (*.pdf *.docx *.png *.jpg *.jpeg *.txt *.md *.csv *.mp4 *.mov *.mkv *.webm *.avi *.m4v *.ts)'))
        self.add([Path(f) for f in files])

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr('Ordner auswählen'))
        if folder:
            self.add([Path(folder)])

    def add(self, incoming):
        try:
            files = collect(incoming, self.recursive.isChecked())
        except OSError as error:
            self.error(str(error))
            return
        self.table.blockSignals(True)
        for path in files:
            if path in self.paths:
                continue
            row = len(self.paths)
            self.paths.append(path)
            self.table.insertRow(row)
            check = QTableWidgetItem('')
            check.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(row, 0, check)
            cached = self.session_results.get(path, self.settings())
            if cached:self.remember_analysis(row, cached)
            for col, text in ((1, path.name), (2, cached['name'] if cached else ''),
                              (3, tr('Aus Sitzung übernommen · Vorschlag prüfen') if cached else tr('Noch nicht analysiert'))):
                item = QTableWidgetItem(text)
                if col != 2:
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setToolTip(str(path))
                self.table.setItem(row, col, item)
        self.table.blockSignals(False)
        if self.paths and self.table.currentRow() < 0:
            self.table.setCurrentCell(0, 1)
        self.check_conflicts()
        self.status.setText(f"{len(self.paths)}{tr(' Dateien · Keine Dateien wurden verändert.')}")

    def edit_preview_name(self, name):
        row = self.table.currentRow()
        if not self.busy() and 0 <= row < len(self.paths):
            self.table.item(row, 2).setText(name)

    def update_preview(self):
        row = self.table.currentRow()
        self.preview.show_path(self.paths[row] if 0 <= row < len(self.paths) else None)
        if 0 <= row < len(self.paths):
            detail = self.analysis_details.get(self.paths[row], {})
            self.preview.set_analysis_frames(detail.get('frames', []))
            self.preview.name.setText(self.table.item(row, 2).text())
            self.preview.name.setEnabled(not self.busy())

    def clear(self):
        self.preview.show_path(None)
        self.paths.clear()
        self.analysis_details.clear()
        self.analysis_identities.clear()
        self.table.setRowCount(0)
        self.status.setText(tr('Liste geleert. Die Dateien bleiben erhalten.'))

    def select_all(self, selected):
        for row in range(len(self.paths)):
            self.table.item(row, 0).setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)

    def selected(self):
        return [(row, path) for row, path in enumerate(self.paths) if self.table.item(row, 0).checkState() == Qt.CheckState.Checked]

    def changed(self, item):
        if item.column() == 2:
            if item.row() == self.table.currentRow():
                self.preview.name.setText(item.text())
            self.table.item(item.row(), 3).setText(tr('Manuell bearbeitet — wird beim Umbenennen geprüft'))
            path = self.paths[item.row()]
            detail = self.analysis_details.get(path)
            if detail:
                self.session_results.edit(path, detail['settings'], item.text(), tr('Manuell bearbeitet'))
        if item.column() in (0, 2):
            self.check_conflicts()

    def check_conflicts(self):
        selected = self.selected()
        targets = {}
        for row, path in selected:
            name = self.table.item(row, 2).text()
            if not name:
                continue
            try:
                settings=self.settings()
                from .organize import destination_for
                target = destination_for(path,name,self.analysis_details.get(path,{}).get('metadata'),settings)
                key = str(target).casefold()
                targets.setdefault(key, []).append(row)
                if target != path and (target.exists() or target.is_symlink()):
                    self.table.item(row, 3).setText(tr('Namenskonflikt — Ziel existiert'))
                elif self.table.item(row, 3).text().startswith(tr('Namenskonflikt')):
                    self.table.item(row, 3).setText(tr('Vorschlag prüfen'))
            except ValueError as error:
                self.table.item(row, 3).setText(tr('Ungültiger Name: ') + str(error))
        for rows in targets.values():
            if len(rows) > 1:
                for row in rows:
                    self.table.item(row, 3).setText(tr('Namenskonflikt — mehrfach ausgewählter Zielname'))

    def start(self, worker):
        if self.busy():
            worker.deleteLater()
            return
        self.worker = worker
        worker.problem.connect(self.error)
        worker.finished.connect(self.finished)
        self.set_busy(True)
        worker.start()

    def load_models(self):
        self.progress.setRange(0, 0)
        self.status.setText(tr('Verbindung zu Ollama wird geprüft …'))
        worker = Worker(self.settings())
        worker.models_ready.connect(self.models_loaded)
        self.start(worker)

    def models_loaded(self, names):
        current = self.model.currentText()
        self.model.clear()
        self.model.addItems(names)
        if current:
            self.model.setCurrentText(current)
        elif names:
            self.model.setCurrentIndex(0)
        self.status.setText(f"{len(names)}{tr(' Modelle gefunden.')}" if names else tr('Verbindung erfolgreich, aber keine Modelle gefunden.'))

    def reanalyze(self):
        if self.busy():return
        if not self.selected():
            self.error(tr('Bitte mindestens eine Datei auswählen.'))
            return
        hint, accepted = QInputDialog.getText(self, tr('Erneut analysieren'),
            tr('Optionaler Hinweis für die markierten Dateien (z. B. kürzer benennen, Ort hervorheben):'))
        if accepted:self.analyze(force=True, hint=hint[:500])

    def analyze(self, force=False, hint=''):
        items = self.selected()
        if not items:
            self.error(tr('Bitte mindestens eine Datei auswählen.'))
            return
        settings = replace(self.settings(), analysis_hint=hint)
        try:
            for template in (settings.template, settings.image_template, settings.video_template):
                validate_template(template or settings.template)
            if settings.engine == 'llama' and not settings.auto_models and (self._local_backend is None or not self.local_engine.alive()):
                raise ValueError(tr('Bitte zuerst das lokale Modell laden.'))
            if settings.engine == 'ollama' and not settings.model:
                raise ValueError(tr('Bitte zuerst ein Modell auswählen oder eingeben.'))
        except ValueError as error:
            self.error(str(error))
            return
        self.progress.setRange(0, len(items))
        self.progress.setValue(0)
        for row, _ in items:
            self.table.item(row, 3).setText(tr('Wartet auf Analyse …'))
        self.status.setText(tr('Analysiert ausgewählte Dateien nacheinander …'))
        from .routing import LocalModelRouter
        router = LocalModelRouter(self.local_engine, settings, lambda: self.worker.isInterruptionRequested(), self.status.setText) if settings.engine == 'llama' and settings.auto_models else None
        worker = Worker(settings, items, self._local_backend if settings.engine == 'llama' else None, router, self.session_results, force)
        worker.details.connect(self.remember_analysis)
        if router:router.progress = worker.progress.emit
        worker.progress.connect(self.status.setText)
        worker.result.connect(self.result)
        self.start(worker)

    def remember_analysis(self, row, detail):
        path = self.paths[row]
        self.analysis_identities[path] = detail['identity']
        self.analysis_details.pop(path, None)
        self.analysis_details[path] = detail
        # Keep metadata for every visible row; only thumbnail payloads are bounded.
        while sum(bool(entry.get('frames')) for entry in self.analysis_details.values())>64 or sum(sum(len(encoded) for _,encoded in entry.get('frames', [])) for entry in self.analysis_details.values())>32*1024*1024:
            for entry in self.analysis_details.values():
                if entry.get('frames'):
                    entry['frames']=[]
                    break
        if row == self.table.currentRow():self.preview.set_analysis_frames(detail.get('frames', []))

    def result(self, row, name, status):
        if not name:
            self.analysis_details.pop(self.paths[row], None)
            if row == self.table.currentRow():self.preview.show_path(self.paths[row])
        self.table.blockSignals(True)
        self.table.item(row, 2).setText(name)
        self.table.item(row, 3).setText(status)
        self.table.item(row, 3).setToolTip(status)
        self.table.blockSignals(False)
        if row == self.table.currentRow():
            self.preview.name.setText(name)
        self.check_conflicts()
        self.progress.setValue(self.progress.value() + 1)

    def cancel(self):
        if self.worker:
            self.worker.requestInterruption()
            self.status.setText(tr('Abbruch vorgemerkt — Download/Laden wird beendet; eine laufende KI-Anfrage endet spätestens nach dem Timeout.'))
            self.cancel_button.setEnabled(False)

    def finished(self):
        interrupted = self.worker.cancelled
        if getattr(self.worker, 'router', None):
            self._local_backend = self.local_engine.backend
        if self.worker.items is not None:
            for row, _ in self.worker.items:
                if self.table.item(row, 3).text() == tr('Wartet auf Analyse …'):
                    self.table.item(row, 3).setText(tr('Nicht analysiert · abgebrochen'))
            self.status.setText(tr('Analyse abgebrochen.') if interrupted else tr('Analyse beendet · Vorschläge prüfen und gewünschte Dateien umbenennen.'))
        if isinstance(self.worker, EngineWorker) and interrupted:
            self.local_engine.stop()
            self._local_backend = None
            self.status.setText(tr('Lokales Laden abgebrochen.'))
        self.set_busy(False)
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
        self.worker.deleteLater()
        self.worker = None
        self.refresh_analysis_enabled()
        self.model_manager.refresh()
        if self._close_pending:
            QTimer.singleShot(0, self.close)

    def review_rename(self):
        if self.busy():return
        from .rename_review import review_plan, RenameReview
        items=[]
        for row,path in self.selected():
            status=self.table.item(row,3).text()
            missing=self.analysis_details.get(path,{}).get('missing_fields',[])
            if missing:status += tr(' · Fehlende Angaben: ')+', '.join(missing)
            items.append((path,self.table.item(row,2).text(),status))
        if not items:
            self.error(tr('Bitte mindestens eine Datei auswählen.'))
            return
        operation_settings=self.settings()
        metadata={path:detail.get('metadata') for path,detail in self.analysis_details.items()}
        rows=review_plan(items,self.analysis_identities,operation_settings,metadata)
        destinations={row['path']:row['target'] for row in rows}
        self.rename_review = RenameReview(rows,self)
        approved=tuple((row,path,self.table.item(row,2).text()) for row,path in self.selected())
        self.rename_review.accepted.connect(lambda: self.rename(approved,destinations,operation_settings))
        self.rename_review.open()

    def rename(self, approved=None, destinations=None, operation_settings=None):
        if self.busy():return
        if approved is not None:
            if any(row >= len(self.paths) or self.paths[row] != path or self.table.item(row,2).text() != name for row,path,name in approved):
                self.error(tr('Die geprüfte Auswahl hat sich verändert. Bitte erneut prüfen.'))
                return
            selected=[(row,path) for row,path,name in approved]
        else:
            selected = self.selected()
        if not selected:
            self.error(tr('Bitte mindestens eine Datei auswählen.'))
            return
        items = [(path, self.table.item(row, 2).text()) for row, path in selected]
        if any(not name for _, name in items):
            self.error(tr('Für jede ausgewählte Datei muss ein neuer Name vorliegen. Dateien ohne Vorschlag bitte abwählen.'))
            return
        from .rename_review import review_plan
        operation_settings=operation_settings or self.settings()
        metadata={path:detail.get('metadata') for path,detail in self.analysis_details.items()}
        rows=review_plan([(path,name,'') for path,name in items],self.analysis_identities,operation_settings,metadata,destinations)
        problems=[problem for row in rows for problem in row['problems']]
        if problems:
            self.error('; '.join(dict.fromkeys(problems)))
            return
        failure = None
        try:
            if operation_settings.organize_enabled:
                from .organize import organize_batch
                records=organize_batch([(row['path'],row['target']) for row in rows],Path(operation_settings.organize_root).expanduser())
            else:records = rename_batch(items)
        except RenameError as error:
            failure = str(error)
            records = error.records
            self.error(str(error))
        except Exception as error:
            self.error(str(error))
            return
        if records:
            self.history.append(records)
        mapping = {r.before: r.after for r in records}
        for row, path in selected:
            self.paths[row] = mapping.get(path, path)
            self.table.item(row, 1).setText(self.paths[row].name)
            self.table.item(row, 1).setToolTip(str(self.paths[row]))
            self.table.item(row, 3).setText((tr('Einsortiert und umbenannt') if operation_settings.organize_enabled else tr('Umbenannt')) if path in mapping else tr('Unverändert'))
        for record in records:self.remap_analysis(record.before, record.after)
        self.update_preview()
        self.undo_button.setEnabled(bool(self.history))
        self.status.setText((tr('Aktion fehlgeschlagen · ') + failure) if failure else f"{len(records)}{tr(' Dateien umbenannt · Rückgängig ist in dieser Sitzung möglich.')}")

    def remap_analysis(self, before, after):
        from .session import file_identity
        detail = self.analysis_details.pop(before, None)
        self.analysis_identities.pop(before, None)
        self.session_results.forget(before)
        if detail:
            try:
                identity = file_identity(after)
                detail = dict(detail, identity=identity)
                self.analysis_details[after] = detail
                self.analysis_identities[after] = identity
                self.session_results.put(identity, detail['settings'], detail)
            except (ValueError, OSError):pass

    def revert(self):
        if not self.history:
            return
        records = self.history[-1]
        failure = None
        try:
            undo(records)
        except RenameError as error:
            failure = str(error)
            self.error(str(error))
            remaining = error.records
            self.history[-1] = remaining
            records = [r for r in records if r not in remaining]
            if not remaining:
                self.history.pop()
        except Exception as error:
            self.error(str(error))
            return
        else:
            self.history.pop()
        for record in records:self.remap_analysis(record.after, record.before)
        mapping = {r.after: r.before for r in records}
        for row, path in enumerate(self.paths):
            if path in mapping:
                self.paths[row] = mapping[path]
                self.table.item(row, 1).setText(mapping[path].name)
                self.table.item(row, 1).setToolTip(str(mapping[path]))
                self.table.item(row, 3).setText(tr('Umbenennung rückgängig gemacht'))
        self.update_preview()
        self.undo_button.setEnabled(bool(self.history))
        self.status.setText((tr('Rückgängig unvollständig · ') + failure) if failure else f"{len(records)}{tr(' Umbenennungen rückgängig gemacht.')}")

    def error(self, message):
        self.status.setText(tr('Aktion fehlgeschlagen.'))
        QMessageBox.warning(self, 'Nomi', message)

    def closeEvent(self, event):
        if self.busy():
            self.cancel()
            if isinstance(self.worker, EngineWorker):
                self._close_pending = True
                event.ignore()
                return
            QMessageBox.information(self, tr('Analyse läuft'), tr('Bitte warte, bis die laufende Anfrage beendet ist. Danach lässt sich Nomi schließen.'))
            event.ignore()
        else:
            self.inbox.configure(None)
            self.preview.shutdown()
            self.model_manager.close()
            self.settings_dialog.close()
            self.local_engine.stop()
            self.settings()
            event.accept()

STYLE = '''
QWidget { background: #171c2b; color: #e8edf9; font-size: 13px; }
QLineEdit, QComboBox, QSpinBox { background: #222b40; border: 1px solid #46516c; border-radius: 6px; padding: 7px; }
QPushButton { background: #2d3852; border: 1px solid #455372; border-radius: 6px; padding: 9px 12px; }
QPushButton:hover { background: #3e4c70; }
QPushButton:disabled { color: #78829a; background: #22283a; }
QTableWidget { background: #1d2436; alternate-background-color: #232c40; gridline-color: #35415a; border: 1px solid #35415a; }
QHeaderView::section { background: #2b3550; padding: 10px; border: none; }
QProgressBar { border: 1px solid #35415a; border-radius: 5px; text-align: center; }
QProgressBar::chunk { background: #6677dd; }
'''

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    if '--runtime-check' in sys.argv:
        from .diagnostics import runtime_check
        sys.exit(runtime_check())
    if '--llama-self-test' in sys.argv:
        from .diagnostics import run_llama_self_test
        sys.exit(run_llama_self_test(app))
    if '--self-test' in sys.argv:
        from .diagnostics import run_self_test
        sys.exit(run_self_test(app))
    window = Window()
    app.aboutToQuit.connect(window.local_engine.stop)
    window.show()
    sys.exit(app.exec())
