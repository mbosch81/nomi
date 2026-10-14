from __future__ import annotations
import sys
from pathlib import Path
from dataclasses import asdict
from PySide6.QtCore import Qt, QThread, Signal, QSettings, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QCheckBox, QLineEdit, QComboBox, QSpinBox, QProgressBar, QMessageBox, QDialog, QDialogButtonBox, QGroupBox, QFormLayout)
from .llama_backend import LocalEngine
from .local_model import default_model_path, download_model, model_catalog, model_directory
from .core import Settings, OllamaBackend, collect, make_name, rename_batch, undo, validate_template, RenameError, extract_document, AnalysisCancelled, available_name, validate_name

class Worker(QThread):
    result = Signal(int, str, str)
    models_ready = Signal(list)
    problem = Signal(str)
    def __init__(self, settings, items=None, backend=None):
        super().__init__()
        self.settings, self.items = settings, items
        self.cancelled = False
        self.backend = backend
    def requestInterruption(self):
        self.cancelled = True
        super().requestInterruption()

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
                document = extract_document(path, settings=self.settings, cancelled=self.isInterruptionRequested)
                if self.isInterruptionRequested():
                    break
                metadata = backend.suggest(document.text, self.settings)
                proposed = make_name(metadata, path, self.settings.template)
                name = available_name(path, proposed, reserved.setdefault(path.parent, set()))
                if name == path.name:
                    status = 'Unverändert'
                elif path.with_name(name).exists():
                    status = 'Namenskonflikt — bitte bearbeiten'
                else:
                    status = 'Bereit'
                if name != proposed:
                    status += ' · Konflikt durch Nummernzusatz vermieden'
                for warning in metadata.get('_warnings', []):
                    status += ' · ' + warning
                if document.used_ocr:
                    status += ' · OCR' + (f' ({document.ocr_backend})' if document.ocr_backend else '')
                if document.truncated:
                    status += ' · Textausschnitt, bitte prüfen'
                self.result.emit(row, name, status)
            except AnalysisCancelled:
                break
            except Exception as error:
                self.result.emit(row, '', 'Fehler: ' + str(error))

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
            path = (download_model('qwen' if self.download is True else self.download, cancelled=self.isInterruptionRequested, progress=self.progress.emit)
                    if self.download else Path(self.settings.llama_model))
            backend = self.engine.start(path, self.isInterruptionRequested, self.progress.emit)
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
        self.setWindowTitle('Nomi · Jede Datei verdient einen Namen')
        self.resize(1100, 720)
        self.setAcceptDrops(True)
        self.paths = []
        self.worker = None
        self.history = []
        self.local_engine = LocalEngine()
        self._local_backend = None
        self._close_pending = False
        self.store = store if store is not None else QSettings('Nomi', 'Nomi')
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
        self.settings_button.setToolTip('Einstellungen öffnen (⌘, auf macOS)')
        self.settings_button.setAccessibleName('Einstellungen öffnen')
        self.settings_button.clicked.connect(self.show_settings)
        header.addWidget(self.settings_button)
        layout.addLayout(header)
        layout.addWidget(QLabel('Jede Datei verdient einen Namen.'))
        self.drop_hint = QLabel('Dateien oder Ordner hierher ziehen · PDF, TXT, Markdown und CSV')
        self.drop_hint.setStyleSheet('border: 2px dashed #55618a; border-radius: 12px; padding: 22px; color: #bec8e5;')
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.drop_hint)
        import_row = QHBoxLayout()
        self.files_button = QPushButton('Dateien hinzufügen')
        self.folder_button = QPushButton('Ordner auswählen')
        self.recursive = QCheckBox('Unterordner einbeziehen')
        self.clear_button = QPushButton('Liste leeren')
        for widget in (self.files_button, self.folder_button, self.recursive, self.clear_button):
            import_row.addWidget(widget)
        import_row.addStretch()
        layout.addLayout(import_row)
        self.settings_dialog = QDialog(self)
        self.settings_dialog.setWindowTitle('Nomi · Einstellungen')
        self.settings_dialog.resize(760, 650)
        settings_layout = QVBoxLayout(self.settings_dialog)
        settings_layout.setContentsMargins(24, 24, 24, 24)
        settings_layout.setSpacing(16)
        backend_group = QGroupBox('Analyse und Modelle')
        backend_row = QFormLayout(backend_group)
        settings_layout.addWidget(backend_group)
        settings_menu = self.menuBar().addMenu('Einstellungen')
        self.settings_action = QAction('Einstellungen …', self)
        self.settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        self.settings_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(self.settings_action)
        self.engine = QComboBox()
        self.engine.addItem('Lokal · llama.cpp', 'llama')
        self.engine.addItem('Ollama · Server', 'ollama')
        selected_engine = str(self.store.value('engine', 'llama'))
        self.engine.setCurrentIndex(max(0, self.engine.findData(selected_engine)))
        backend_row.addRow('Backend', self.engine)
        self.url = QLineEdit(str(self.store.value('url', 'http://localhost:11434')))
        self.url.setPlaceholderText('http://server:port')
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.setMinimumWidth(160)
        self.model.setCurrentText(str(self.store.value('model', '')))
        self.model.setPlaceholderText('Modellname')
        self.connect_button = QPushButton('Modelle laden')
        self.timeout = QSpinBox()
        self.timeout.setRange(10, 600)
        self.timeout.setValue(int(self.store.value('timeout', 120)))
        self.timeout.setSuffix(' s')
        self.url_label = QLabel('Ollama-Adresse')
        self.model_label = QLabel('Ollama-Modell')
        backend_row.addRow(self.url_label, self.url)
        model_row = QHBoxLayout()
        model_row.addWidget(self.model)
        model_row.addWidget(self.connect_button)
        backend_row.addRow(self.model_label, model_row)
        backend_row.addRow('Zeitlimit pro Anfrage', self.timeout)
        self.local_group = QGroupBox('Lokales GGUF-Modell')
        local_row = QVBoxLayout(self.local_group)
        settings_layout.addWidget(self.local_group)
        self.gguf = QLineEdit(str(self.store.value('llama_model', str(default_model_path()))))
        self.gguf.setPlaceholderText('GGUF-Modell auswählen')
        self.gguf_button = QPushButton('GGUF wählen')
        self.download_choice = QComboBox()
        self.download_choice.setAccessibleName('Download-Modell')
        for model in model_catalog():
            self.download_choice.addItem(model.label, model.key)
        for index, model in enumerate(model_catalog()):
            if Path(self.gguf.text()).name == model.filename:
                self.download_choice.setCurrentIndex(index)
                break
        self.download_button = QPushButton('Ausgewähltes Modell herunterladen / laden')
        self.local_load_button = QPushButton('Modell laden')
        self.autoload = QCheckBox('Beim Start laden')
        self.autoload.setChecked(str(self.store.value('llama_autoload', 'true')).lower() in {'true', '1'})
        local_row.addWidget(QLabel('Verfügbare Modelle (Q4_K_M)'))
        local_row.addWidget(self.download_choice)
        path_row = QHBoxLayout()
        path_row.addWidget(self.gguf, 1)
        path_row.addWidget(self.gguf_button)
        local_row.addLayout(path_row)
        model_actions = QHBoxLayout()
        model_actions.addWidget(self.download_button)
        model_actions.addWidget(self.local_load_button)
        local_row.addLayout(model_actions)
        local_row.addWidget(self.autoload)
        schema_group = QGroupBox('Dateinamen')
        schema_row = QFormLayout(schema_group)
        settings_layout.addWidget(schema_group)
        self.template = QLineEdit(str(self.store.value('template', '{datum}_{absender}_{dokumenttyp}')))
        self.template.setToolTip('Verfügbare Felder: {datum}, {absender}, {dokumenttyp}, {titel}, {empfaenger}, {kennung}')
        schema_row.addRow('Namensschema', self.template)
        schema_hint = QLabel('{datum}, {absender}, {dokumenttyp}, {titel}, {empfaenger}, {kennung}')
        schema_hint.setWordWrap(True)
        schema_row.addRow(schema_hint)
        ocr_group = QGroupBox('Texterkennung')
        ocr_row = QFormLayout(ocr_group)
        settings_layout.addWidget(ocr_group)
        self.ocr_enabled = QCheckBox('OCR für gescannte PDF-Seiten')
        self.ocr_enabled.setChecked(str(self.store.value('ocr_enabled', 'false')).lower() in {'true', '1'})
        self.ocr_backend = QComboBox()
        self.ocr_backend.addItem('Automatisch', 'auto')
        self.ocr_backend.addItem('Apple Vision (macOS)', 'vision')
        self.ocr_backend.addItem('Tesseract', 'tesseract')
        index = self.ocr_backend.findData(str(self.store.value('ocr_backend', 'auto')))
        self.ocr_backend.setCurrentIndex(max(0, index))
        self.ocr_language = QLineEdit(str(self.store.value('ocr_language', 'deu+eng')))
        self.ocr_language.setMaximumWidth(110)
        self.ocr_language.setToolTip('OCR-Sprachen, z.B. deu+eng (Deutsch und Englisch)')
        self.ocr_command = QLineEdit(str(self.store.value('ocr_command', 'tesseract')))
        self.ocr_command.setToolTip('Tesseract-Programmname oder vollständiger Programmpfad')
        self.ocr_command_label = QLabel('Tesseract')
        ocr_row.addRow(self.ocr_enabled)
        ocr_row.addRow('OCR-Backend', self.ocr_backend)
        ocr_row.addRow('Sprachen', self.ocr_language)
        ocr_row.addRow(self.ocr_command_label, self.ocr_command)
        settings_layout.addWidget(QLabel('Änderungen werden direkt übernommen und beim Schließen gespeichert.'))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText('Schließen')
        buttons.rejected.connect(self.settings_dialog.close)
        settings_layout.addWidget(buttons)
        self.settings_dialog.finished.connect(lambda _: self.settings())
        self.ocr_backend.currentIndexChanged.connect(self.update_ocr_controls)
        self.update_ocr_controls()
        self.privacy_note = QLabel('Die Analyse sendet bis zu 16.000 Zeichen je Datei an die eingestellte Adresse. PDFs: maximal 20 Seiten.\nEin vorgeschalteter Router kann Inhalte an Cloud-Anbieter weiterleiten. Umbenennung erfolgt erst nach deinem Klick.')
        self.privacy_note.setWordWrap(True)
        self.privacy_note.setStyleSheet('color: #aeb9d2; font-size: 11px;')
        layout.addWidget(self.privacy_note)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Verwenden', 'Originalname', 'Neuer Name · editierbar', 'Status'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for col in (1, 2, 3):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self.changed)
        layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        self.all_button = QPushButton('Alle auswählen')
        self.none_button = QPushButton('Alle abwählen')
        self.analyze_button = QPushButton('Auswahl analysieren')
        self.cancel_button = QPushButton('Abbrechen')
        self.cancel_button.setEnabled(False)
        self.rename_button = QPushButton('Auswahl umbenennen')
        self.rename_button.setStyleSheet('background: #6677dd; color: white; font-weight: 600;')
        self.undo_button = QPushButton('Rückgängig')
        self.undo_button.setEnabled(False)
        for widget in (self.all_button, self.none_button, self.analyze_button, self.cancel_button, self.rename_button, self.undo_button):
            actions.addWidget(widget)
        layout.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QLabel('Bereit · Einstellungen werden automatisch gespeichert.')
        layout.addWidget(self.status)
        self.files_button.clicked.connect(self.choose_files)
        self.folder_button.clicked.connect(self.choose_folder)
        self.clear_button.clicked.connect(self.clear)
        self.connect_button.clicked.connect(self.load_models)
        self.analyze_button.clicked.connect(self.analyze)
        self.cancel_button.clicked.connect(self.cancel)
        self.rename_button.clicked.connect(self.rename)
        self.undo_button.clicked.connect(self.revert)
        self.all_button.clicked.connect(lambda: self.select_all(True))
        self.none_button.clicked.connect(lambda: self.select_all(False))
        self.busy_widgets = [self.files_button, self.folder_button, self.recursive, self.clear_button, self.url, self.model, self.connect_button, self.timeout, self.template, self.all_button, self.none_button, self.analyze_button, self.rename_button, self.undo_button, self.ocr_enabled, self.ocr_language, self.ocr_command, self.ocr_backend, self.engine, self.gguf, self.gguf_button, self.download_button, self.local_load_button, self.autoload, self.download_choice]

        self.engine.currentIndexChanged.connect(self.engine_changed)
        self.gguf.textChanged.connect(self.model_path_changed)
        self.gguf_button.clicked.connect(self.choose_gguf)
        self.download_button.clicked.connect(lambda: self.start_local_model(download=self.download_choice.currentData()))
        self.download_choice.currentIndexChanged.connect(self.download_model_changed)
        self.local_load_button.clicked.connect(lambda: self.start_local_model())
        self.update_engine_controls()
        QTimer.singleShot(0, self.auto_load)

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
        for widget in (self.gguf, self.gguf_button, self.download_button, self.local_load_button, self.autoload):
            widget.setVisible(local)
        self.privacy_note.setText(
            'Analyse vollständig auf diesem Mac über llama.cpp. Bis zu 16.000 Zeichen je Datei, PDFs maximal 20 Seiten. '
            'Beim erstmaligen Modelldownload wird Hugging Face kontaktiert. Umbenennung erst nach deinem Klick.'
            if local else 'Die Analyse sendet bis zu 16.000 Zeichen je Datei an die eingestellte Ollama-Adresse. PDFs: maximal 20 Seiten. '
            'Ein vorgeschalteter Router kann Inhalte an Cloud-Anbieter weiterleiten. Umbenennung erst nach deinem Klick.')
        self.refresh_analysis_enabled()

    def refresh_analysis_enabled(self):
        ready = self.engine.currentData() != 'llama' or (self._local_backend is not None and self.local_engine.alive())
        self.analyze_button.setEnabled(not self.busy() and ready)

    def engine_changed(self):
        if self.engine.currentData() != 'llama':
            self.local_engine.stop()
            self._local_backend = None
            self.status.setText('Ollama · Modell wählen oder Modelle laden.')
        self.update_engine_controls()
        if self.engine.currentData() == 'llama':
            QTimer.singleShot(0, self.auto_load)

    def model_path_changed(self):
        if self.local_engine.model != Path(self.gguf.text()).expanduser().absolute():
            self._local_backend = None
            if self.engine.currentData() == 'llama':
                self.status.setText('Modellauswahl geändert · Modell laden anklicken.')
        self.refresh_analysis_enabled()

    def choose_gguf(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Lokales Modell auswählen', '', 'GGUF-Modelle (*.gguf)')
        if path:
            self.gguf.setText(path)

    def auto_load(self):
        if self.busy() or self.engine.currentData() != 'llama':
            return
        if not self.autoload.isChecked():
            self.status.setText('Lokales Modell noch nicht geladen · Modell laden anklicken.')
        elif Path(self.gguf.text()).expanduser().is_file():
            self.start_local_model()
        else:
            self.status.setText('Lokales Modell fehlt · GGUF auswählen oder ein angebotenes Modell herunterladen.')

    def start_local_model(self, download=False):
        if self.busy():
            return
        self._local_backend = None
        self.progress.setRange(0, 0)
        self.status.setText('Lokales Modell wird vorbereitet …')
        worker = EngineWorker(self.local_engine, self.settings(), download)
        worker.progress.connect(self.status.setText)
        worker.ready.connect(self.local_model_ready)
        self.start(worker)

    def local_model_ready(self, backend, path):
        self.gguf.setText(path)
        self._local_backend = backend
        self.store.setValue('llama_model', path)
        self.status.setText('Lokales Modell bereit · ' + Path(path).name)

    def update_ocr_controls(self):
        from .ocr import effective_backend
        show_command = effective_backend(self.ocr_backend.currentData()) == 'tesseract'
        self.ocr_command.setVisible(show_command)
        self.ocr_command_label.setVisible(show_command)

    def settings(self):
        settings = Settings(url=self.url.text().strip(), model=self.model.currentText().strip(),
                            template=self.template.text().strip(), timeout=self.timeout.value(),
                            ocr_enabled=self.ocr_enabled.isChecked(), ocr_language=self.ocr_language.text().strip(),
                            ocr_command=self.ocr_command.text().strip(), ocr_backend=self.ocr_backend.currentData(),
                            engine=self.engine.currentData(), llama_model=self.gguf.text().strip(),
                            llama_autoload=self.autoload.isChecked())
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
        self.cancel_button.setEnabled(value)
        self.refresh_analysis_enabled()

    def dragEnterEvent(self, event):
        if not self.busy() and event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not self.busy():
            self.add([Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()])
            event.acceptProposedAction()

    def choose_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Dateien hinzufügen', '', 'Dokumente (*.pdf *.txt *.md *.csv)')
        self.add([Path(f) for f in files])

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Ordner auswählen')
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
            for col, text in ((1, path.name), (2, ''), (3, 'Noch nicht analysiert')):
                item = QTableWidgetItem(text)
                if col != 2:
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setToolTip(str(path))
                self.table.setItem(row, col, item)
        self.table.blockSignals(False)
        self.status.setText(f'{len(self.paths)} Dateien · Keine Dateien wurden verändert.')

    def clear(self):
        self.paths.clear()
        self.table.setRowCount(0)
        self.status.setText('Liste geleert. Die Dateien bleiben erhalten.')

    def select_all(self, selected):
        for row in range(len(self.paths)):
            self.table.item(row, 0).setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)

    def selected(self):
        return [(row, path) for row, path in enumerate(self.paths) if self.table.item(row, 0).checkState() == Qt.CheckState.Checked]

    def changed(self, item):
        if item.column() == 2:
            self.table.item(item.row(), 3).setText('Manuell bearbeitet — wird beim Umbenennen geprüft')
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
                target = validate_name(path, name)
                key = str(target).casefold()
                targets.setdefault(key, []).append(row)
                if target != path and (target.exists() or target.is_symlink()):
                    self.table.item(row, 3).setText('Namenskonflikt — Ziel existiert')
                elif self.table.item(row, 3).text().startswith('Namenskonflikt'):
                    self.table.item(row, 3).setText('Vorschlag prüfen')
            except ValueError as error:
                self.table.item(row, 3).setText('Ungültiger Name: ' + str(error))
        for rows in targets.values():
            if len(rows) > 1:
                for row in rows:
                    self.table.item(row, 3).setText('Namenskonflikt — mehrfach ausgewählter Zielname')

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
        self.status.setText('Verbindung zu Ollama wird geprüft …')
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
        self.status.setText(f'{len(names)} Modelle gefunden.' if names else 'Verbindung erfolgreich, aber keine Modelle gefunden.')

    def analyze(self):
        items = self.selected()
        if not items:
            self.error('Bitte mindestens eine Datei auswählen.')
            return
        settings = self.settings()
        try:
            validate_template(settings.template)
            if settings.engine == 'llama' and (self._local_backend is None or not self.local_engine.alive()):
                raise ValueError('Bitte zuerst das lokale Modell laden.')
            if settings.engine == 'ollama' and not settings.model:
                raise ValueError('Bitte zuerst ein Modell auswählen oder eingeben.')
        except ValueError as error:
            self.error(str(error))
            return
        self.progress.setRange(0, len(items))
        self.progress.setValue(0)
        for row, _ in items:
            self.table.item(row, 3).setText('Wartet auf Analyse …')
        self.status.setText('Analysiert ausgewählte Dateien nacheinander …')
        worker = Worker(settings, items, self._local_backend if settings.engine == 'llama' else None)
        worker.result.connect(self.result)
        self.start(worker)

    def result(self, row, name, status):
        self.table.blockSignals(True)
        self.table.item(row, 2).setText(name)
        self.table.item(row, 3).setText(status)
        self.table.item(row, 3).setToolTip(status)
        self.table.blockSignals(False)
        self.check_conflicts()
        self.progress.setValue(self.progress.value() + 1)

    def cancel(self):
        if self.worker:
            self.worker.requestInterruption()
            self.status.setText('Abbruch vorgemerkt — Download/Laden wird beendet; eine laufende KI-Anfrage endet spätestens nach dem Timeout.')
            self.cancel_button.setEnabled(False)

    def finished(self):
        interrupted = self.worker.cancelled
        if self.worker.items is not None:
            for row, _ in self.worker.items:
                if self.table.item(row, 3).text() == 'Wartet auf Analyse …':
                    self.table.item(row, 3).setText('Nicht analysiert · abgebrochen')
            self.status.setText('Analyse abgebrochen.' if interrupted else 'Analyse beendet · Vorschläge prüfen und gewünschte Dateien umbenennen.')
        if isinstance(self.worker, EngineWorker) and interrupted:
            self.local_engine.stop()
            self._local_backend = None
            self.status.setText('Lokales Laden abgebrochen.')
        self.set_busy(False)
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
        self.worker.deleteLater()
        self.worker = None
        self.refresh_analysis_enabled()
        if self._close_pending:
            QTimer.singleShot(0, self.close)

    def rename(self):
        selected = self.selected()
        if not selected:
            self.error('Bitte mindestens eine Datei auswählen.')
            return
        items = [(path, self.table.item(row, 2).text()) for row, path in selected]
        if any(not name for _, name in items):
            self.error('Für jede ausgewählte Datei muss ein neuer Name vorliegen. Dateien ohne Vorschlag bitte abwählen.')
            return
        failure = None
        try:
            records = rename_batch(items)
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
            self.table.item(row, 3).setText('Umbenannt' if path in mapping else 'Unverändert')
        self.undo_button.setEnabled(bool(self.history))
        self.status.setText(('Aktion fehlgeschlagen · ' + failure) if failure else f'{len(records)} Dateien umbenannt · Rückgängig ist in dieser Sitzung möglich.')

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
        mapping = {r.after: r.before for r in records}
        for row, path in enumerate(self.paths):
            if path in mapping:
                self.paths[row] = mapping[path]
                self.table.item(row, 1).setText(mapping[path].name)
                self.table.item(row, 1).setToolTip(str(mapping[path]))
                self.table.item(row, 3).setText('Umbenennung rückgängig gemacht')
        self.undo_button.setEnabled(bool(self.history))
        self.status.setText(('Rückgängig unvollständig · ' + failure) if failure else f'{len(records)} Umbenennungen rückgängig gemacht.')

    def error(self, message):
        self.status.setText('Aktion fehlgeschlagen.')
        QMessageBox.warning(self, 'Nomi', message)

    def closeEvent(self, event):
        if self.busy():
            self.cancel()
            if isinstance(self.worker, EngineWorker):
                self._close_pending = True
                event.ignore()
                return
            QMessageBox.information(self, 'Analyse läuft', 'Bitte warte, bis die laufende Anfrage beendet ist. Danach lässt sich Nomi schließen.')
            event.ignore()
        else:
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
