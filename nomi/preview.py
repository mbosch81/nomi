from .i18n import tr
"""Read-only local previews, loaded in a separate worker without OCR or network."""
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Qt, QSize
from PySide6.QtGui import QImage, QImageReader, QPixmap, QIcon
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QPlainTextEdit, QScrollArea, QStackedWidget, QComboBox, QLineEdit)


def load_preview(path: Path, page: int = 0, cancelled=lambda:False) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(tr('Datei nicht mehr vorhanden oder symbolischer Link.'))
    suffix = path.suffix.lower()
    from .core import VIDEO_FORMATS
    if suffix in VIDEO_FORMATS:
        import base64
        from .video import sample_frames
        with sample_frames(path, 1, timeout=15, cancelled=cancelled) as frames:
            image = QImage.fromData(base64.b64decode(frames[0][1]), 'JPEG')
        if image.isNull():raise ValueError(tr('Video-Vorschau kann nicht angezeigt werden.'))
        return {'image': image, 'page': 0, 'pages': 1, 'video': True}
    if suffix == '.pdf':
        from PySide6.QtPdf import QPdfDocument
        if path.stat().st_size > 200 * 1024 * 1024:
            raise ValueError(tr('PDF ist für die Vorschau zu groß (maximal 200 MB).'))
        document = QPdfDocument(None)
        try:
            error = document.load(str(path))
            if error != QPdfDocument.Error.None_:
                raise ValueError(tr('PDF kann nicht angezeigt werden (beschädigt oder passwortgeschützt).'))
            count = document.pageCount()
            if count < 1:
                raise ValueError(tr('PDF enthält keine darstellbaren Seiten.'))
            page = max(0, min(page, count - 1))
            size = document.pagePointSize(page)
            scale = min(1600 / max(size.width(), 1), 2000 / max(size.height(), 1))
            image = document.render(page, QSize(max(1, int(size.width() * scale)),
                                               max(1, int(size.height() * scale))))
            if image.isNull():
                raise ValueError(tr('PDF-Seite kann nicht angezeigt werden.'))
            return {'image': image, 'page': page, 'pages': count}
        finally:
            document.close()
    if suffix in {'.png', '.jpg', '.jpeg'}:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        size = reader.size()
        if not size.isValid() or size.width() * size.height() > 48_000_000:
            raise ValueError(tr('Bild ist beschädigt oder zu groß (maximal 48 Megapixel).'))
        reader.setScaledSize(size.scaled(1600, 2000, Qt.AspectRatioMode.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            raise ValueError(tr('Bild kann nicht angezeigt werden.'))
        return {'image': image, 'page': 0, 'pages': 1}
    if suffix == '.docx':
        from .docx_reader import read_docx
        text, truncated = read_docx(path, 256*1024)
        return {'text': text, 'truncated': truncated, 'page': 0, 'pages': 1, 'docx': True}
    if suffix not in {'.txt', '.md', '.csv'}:
        raise ValueError(tr('Für diesen Dateityp gibt es keine Vorschau.'))
    limit = 256 * 1024
    with path.open('rb') as handle:
        raw = handle.read(limit + 1)
    truncated = len(raw) > limit
    raw = raw[:limit]
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp1252', errors='replace')
    return {'text': text, 'truncated': truncated, 'page': 0, 'pages': 1}


class PreviewSignals(QObject):
    ready = Signal(int, object, str)


class PreviewTask(QRunnable):
    def __init__(self, request, path, page):
        super().__init__()
        self.request, self.path, self.page = request, path, page
        self.signals = PreviewSignals()
        from threading import Event
        self.cancelled = Event()

    def run(self):
        try:
            data = load_preview(self.path, self.page, self.cancelled.is_set)
            error = ''
        except Exception as failure:
            message = str(failure) if isinstance(failure, ValueError) else tr('Datei kann nicht angezeigt werden.')
            data, error = None, message
        if not self.cancelled.is_set():
            try:self.signals.ready.emit(self.request, data, error)
            except RuntimeError:pass  # The owning window may have closed during loading.


class PreviewPanel(QWidget):
    name_edited = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sample_frames = []
        self.path = None
        self.page = 0
        self.pages = 0
        self._request = 0
        self._active = None
        self._pending = None
        self._image = QImage()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        self.title = QLabel(tr('Dokumentvorschau'))
        self.title.setWordWrap(True)
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.title)
        self.name = QLineEdit()
        self.name.setAccessibleName(tr('Namensvorschlag bearbeiten'))
        self.name.setPlaceholderText(tr('Namensvorschlag bearbeiten'))
        self.name.setEnabled(False)
        self.name.textEdited.connect(self.name_edited)
        layout.addWidget(self.name)
        navigation = QHBoxLayout()
        self.previous = QPushButton(tr('‹ Zurück'))
        self.next = QPushButton(tr('Weiter ›'))
        self.counter = QLabel('')
        navigation.addWidget(self.previous)
        navigation.addWidget(self.counter, 1, Qt.AlignmentFlag.AlignCenter)
        navigation.addWidget(self.next)
        layout.addLayout(navigation)
        self.zoom = QComboBox()
        self.zoom.addItems([tr('Einpassen'), '100 %', '150 %'])
        self.zoom.setAccessibleName(tr('Vorschau-Zoom'))
        self.zoom.currentIndexChanged.connect(self._fit_image)
        layout.addWidget(self.zoom)
        self.frame_bar = QScrollArea()
        self.frame_bar.setWidgetResizable(True)
        self.frame_bar.setFixedHeight(120)
        self.frame_widget = QWidget()
        self.frame_layout = QHBoxLayout(self.frame_widget)
        self.frame_bar.setWidget(self.frame_widget)
        self.frame_bar.hide()
        layout.addWidget(self.frame_bar)
        self.stack = QStackedWidget()
        self.message = QLabel(tr('Datei in der Liste auswählen.'))
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.message)
        self.image = QLabel()
        self.image.setStyleSheet('background: white;')
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumSize(1, 1)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.image)
        self.stack.addWidget(self.scroll)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.stack.addWidget(self.text)
        layout.addWidget(self.stack, 1)
        self.note = QLabel(tr('Vorschau lokal · Originaldatei bleibt unverändert'))
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.previous.clicked.connect(lambda: self.turn(-1))
        self.next.clicked.connect(lambda: self.turn(1))
        self._navigation()

    def _navigation(self):
        self.previous.setEnabled(self._active is None and self.page > 0)
        self.next.setEnabled(self._active is None and self.page + 1 < self.pages)
        self.counter.setText(f"{tr('Seite ')}{self.page + 1} / {self.pages}" if self.pages else '')

    def show_path(self, path, page=0):
        self.set_analysis_frames([])
        self._request += 1
        old_path = self.path
        self.path = Path(path) if path else None
        self.page, self.pages = page, 0
        self._image = QImage()
        self.image.clear()
        self.text.clear()
        if self.path != old_path:
            self.name.clear()
        self.name.setEnabled(self.path is not None)
        self.title.setText(self.path.name if self.path else tr('Dokumentvorschau'))
        self.title.setToolTip(str(self.path) if self.path else '')
        self.note.setText(tr('Vorschau lokal · Originaldatei bleibt unverändert'))
        self.message.setText(tr('Vorschau wird geladen …') if self.path else tr('Datei in der Liste auswählen.'))
        self.stack.setCurrentWidget(self.message)
        self._pending = (self._request, self.path, page) if self.path else None
        self._start_pending()
        self._navigation()

    def _start_pending(self):
        if self._active is not None or self._pending is None:
            return
        request, path, page = self._pending
        self._pending = None
        task = PreviewTask(request, path, page)
        task.signals.ready.connect(self._loaded)
        self._active = task
        QThreadPool.globalInstance().start(task)

    def _loaded(self, request, data, error):
        self._active = None
        if request == self._request:
            if error:
                self.message.setText(error)
                self.stack.setCurrentWidget(self.message)
            else:
                self.page, self.pages = data['page'], data['pages']
                if data.get('video'):self.note.setText(tr('Video-Stichprobe · einzelnes Vorschaubild · ohne Ton'))
                if 'text' in data:
                    self.text.setPlainText(data['text'])
                    self.stack.setCurrentWidget(self.text)
                    if data.get('docx'):
                        self.note.setText(tr('DOCX-Textvorschau · ohne Seitenlayout und eingebettete Bilder'))
                    if data.get('truncated'):
                        self.note.setText(tr('Textvorschau auf 256 KiB begrenzt · Original unverändert'))
                else:
                    self._image = data['image']
                    self.stack.setCurrentWidget(self.scroll)
                    self._fit_image()
                    if data.get('video') and self._sample_frames:self.show_analysis_frame(0)
        self._start_pending()
        self._navigation()

    def set_analysis_frames(self, frames):
        import base64
        self._sample_frames = frames
        while self.frame_layout.count():
            item=self.frame_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        self.frame_bar.setVisible(bool(frames))
        for index,(timestamp,encoded) in enumerate(frames):
            image=QImage.fromData(base64.b64decode(encoded),'JPEG')
            button=QPushButton(f'{int(timestamp)//60:02d}:{timestamp%60:05.2f}')
            button.setIcon(QIcon(QPixmap.fromImage(image)))
            button.setIconSize(QSize(96,64))
            button.setToolTip(f"{tr('Ausgewerteter Frame ')}{index + 1} · {timestamp:.2f}{tr(' Sekunden')}")
            button.clicked.connect(lambda checked=False,i=index:self.show_analysis_frame(i))
            self.frame_layout.addWidget(button)
        if frames:self.show_analysis_frame(0)

    def show_analysis_frame(self, index):
        import base64
        if not 0<=index<len(self._sample_frames):return
        timestamp,encoded=self._sample_frames[index]
        self._image=QImage.fromData(base64.b64decode(encoded),'JPEG')
        self.stack.setCurrentWidget(self.scroll)
        self._fit_image()
        self.note.setText(f"{tr('Ausgewertete Stichprobe · Frame ')}{index + 1}/{len(self._sample_frames)} · {timestamp:.2f}{tr(' s · ohne Ton')}")

    def shutdown(self):
        self._request += 1
        self._pending = None
        if self._active is not None:self._active.cancelled.set()

    def turn(self, step):
        if self.path and self._active is None and 0 <= self.page + step < self.pages:
            self.show_path(self.path, self.page + step)

    def _fit_image(self):
        if self._image.isNull():
            return
        pixmap = QPixmap.fromImage(self._image)
        fit = self.zoom.currentIndex() == 0
        self.scroll.setWidgetResizable(fit)
        if fit:
            size = self.scroll.viewport().size() - QSize(12, 12)
            if size.width() > 0 and size.height() > 0:
                pixmap = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
        else:
            scale = 1.5 if self.zoom.currentIndex() == 2 else 1
            pixmap = pixmap.scaled(pixmap.size() * scale, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self.image.resize(pixmap.size())
        self.image.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_image()
