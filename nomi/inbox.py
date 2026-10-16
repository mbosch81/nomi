from .i18n import tr
"""Polling inbox monitor: only imports stable files, never analyses or renames."""
import os
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal
from .core import SUPPORTED


def inbox_snapshot(folder: Path, recursive: bool):
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError(tr('Eingangsordner ist nicht erreichbar oder ein symbolischer Link.'))
    result = {}
    for directory, dirs, files in os.walk(folder, followlinks=False, onerror=lambda error: (_ for _ in ()).throw(error)):
        dirs[:] = [d for d in dirs if not d.startswith('.') and not (Path(directory)/d).is_symlink()] if recursive else []
        for name in files:
            path = Path(directory)/name
            if name.startswith(('.', '~$')) or path.suffix.lower() not in SUPPORTED or path.is_symlink():
                continue
            try:
                stat = path.stat()
                if path.is_file() and stat.st_size:
                    result[path] = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
            except FileNotFoundError:
                continue  # A producer can atomically replace a file while scanning.
            if len(result) > 5000:
                raise ValueError(tr('Eingangsordner enthält mehr als 5.000 unterstützte Dateien.'))
    return result


class ScanSignals(QObject):
    done = Signal(int, object, str)


class ScanTask(QRunnable):
    def __init__(self, generation, path, recursive):
        super().__init__()
        self.generation, self.path, self.recursive = generation, path, recursive
        self.signals = ScanSignals()

    def run(self):
        try:
            self.signals.done.emit(self.generation, inbox_snapshot(self.path, self.recursive), '')
        except Exception:
            self.signals.done.emit(self.generation, {}, tr('Eingangsordner nicht lesbar oder zu groß (maximal 5.000 Dateien).'))


class InboxWatcher(QObject):
    files_ready = Signal(list)
    message = Signal(str)

    def __init__(self, blocked=lambda: False, parent=None):
        super().__init__(parent)
        self.blocked = blocked
        self.folder = None
        self.recursive = False
        self._generation = 0
        self._active = None
        self._previous = {}
        self._seen = set()
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.poll)

    def configure(self, path, recursive=False):
        self._generation += 1
        self.folder = Path(path).expanduser().absolute() if path else None
        self.recursive = recursive
        self._previous.clear();self._seen.clear()
        if self.folder:
            self.timer.start()
            self.message.emit(tr('Eingangsordner aktiv · neue stabile Dateien werden nur zur Liste hinzugefügt.'))
            self.poll()
        else:
            self.timer.stop()
            self.message.emit(tr('Eingangsordner nicht überwacht.'))

    def poll(self):
        if not self.folder or self._active is not None or self.blocked():
            return
        task = ScanTask(self._generation, self.folder, self.recursive)
        task.signals.done.connect(self._received)
        self._active = task
        QThreadPool.globalInstance().start(task)

    def _received(self, generation, snapshot, error):
        self._active = None
        if generation != self._generation or not self.folder or self.blocked():
            return
        if error:
            self._previous.clear()
            self.message.emit(error)
            return
        ready = [path for path, identity in snapshot.items()
                 if self._previous.get(path) == identity and identity not in self._seen]
        self._previous = snapshot
        self._seen.update(snapshot[path] for path in ready)
        if ready:
            self.files_ready.emit(sorted(ready))
        self.message.emit(f"{tr('Eingangsordner aktiv · ')}{len(snapshot)}{tr(' Dateien geprüft · nur Import, keine automatische Analyse.')}")
