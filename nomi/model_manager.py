"""Local model inventory; removal goes to the OS trash, never permanent delete."""
from pathlib import Path
from PySide6.QtCore import QFile
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                              QTableWidgetItem, QPushButton, QMessageBox, QHeaderView)
from .local_model import model_directory


def installed_models(extra=None):
    folder = model_directory()
    paths = set(p for p in folder.glob('*.gguf') if p.is_file() and not p.is_symlink())
    if extra:
        path = Path(extra).expanduser().absolute()
        if path.is_file() and not path.is_symlink():
            paths.add(path)
    return sorted(paths)


def trash_model(path: Path, active=None):
    path = path.absolute()
    if path.is_symlink() or path.parent.resolve() != model_directory().resolve() or path.suffix.lower() != '.gguf':
        raise ValueError('Nur Modelle im Nomi-Modellordner können entfernt werden.')
    if active and path.resolve() == Path(active).resolve():
        raise ValueError('Das geladene Modell muss zuerst entladen werden.')
    success = QFile.moveToTrash(str(path))
    if not success:
        raise ValueError('Modell konnte nicht in den Papierkorb verschoben werden. Datei bleibt erhalten.')


class ModelManager(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle('Nomi · Modelle verwalten')
        self.resize(850, 380)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['Modell', 'Speicherbedarf', 'Status'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        actions = QHBoxLayout()
        self.use = QPushButton('Auswahl laden')
        self.unload = QPushButton('Modell entladen')
        self.remove = QPushButton('In Papierkorb verschieben')
        self.refresh_button = QPushButton('Aktualisieren')
        self.close_button = QPushButton('Schließen')
        for button in (self.use, self.unload, self.remove, self.refresh_button, self.close_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.refresh_button.clicked.connect(self.refresh)
        self.use.clicked.connect(self.load_selected)
        self.unload.clicked.connect(self.unload_model)
        self.remove.clicked.connect(self.remove_selected)
        self.close_button.clicked.connect(self.close)
        self.table.itemSelectionChanged.connect(self.update_actions)
        self.paths = []

    def refresh(self):
        current = self.selected()
        self.paths = installed_models(self.window.gguf.text())
        self.table.setRowCount(len(self.paths))
        active = self.window.local_engine.model
        for row, path in enumerate(self.paths):
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            status = 'Geladen' if active and path == Path(active) else 'Installiert'
            if path.parent.resolve() != model_directory().resolve():
                status += ' · externer Speicherort'
            for col, value in enumerate((path.name, f'{size/1_000_000_000:.2f} GB', status)):
                item = QTableWidgetItem(value);item.setToolTip(str(path))
                self.table.setItem(row, col, item)
        if self.paths:
            self.table.selectRow(self.paths.index(current) if current in self.paths else 0)
        self.update_actions()

    def selected(self):
        row = self.table.currentRow()
        return self.paths[row] if 0 <= row < len(self.paths) else None

    def update_actions(self):
        busy = self.window.busy()
        path = self.selected()
        active = self.window.local_engine.model
        self.use.setEnabled(not busy and path is not None)
        self.unload.setEnabled(not busy and active is not None)
        self.remove.setEnabled(not busy and path is not None and path != active and
                               path.parent.resolve() == model_directory().resolve())

    def load_selected(self):
        path = self.selected()
        if path and not self.window.busy():
            self.window.engine.setCurrentIndex(self.window.engine.findData('llama'))
            self.window.gguf.setText(str(path))
            if not self.window.busy():
                self.window.start_local_model()
            self.update_actions()

    def unload_model(self):
        if self.window.busy():return
        self.window.local_engine.stop()
        self.window._local_backend = None
        self.window.refresh_analysis_enabled()
        self.window.status.setText('Lokales Modell entladen.')
        self.refresh()

    def remove_selected(self):
        path = self.selected()
        if not path or self.window.busy():return
        answer = QMessageBox.question(self, 'Modell entfernen', f'{path.name} in den Papierkorb verschieben?')
        if answer != QMessageBox.StandardButton.Yes:return
        try:
            trash_model(path, self.window.local_engine.model)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, 'Modell entfernen', str(error))
        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
