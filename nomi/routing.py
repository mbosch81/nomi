from .i18n import tr
"""File-type policies and lazy local model switching in the analysis worker."""
from pathlib import Path
from .core import VIDEO_FORMATS, IMAGE_FORMATS, AnalysisCancelled
from .local_model import model_spec, model_directory, download_model_package


def media_kind(path):
    suffix = Path(path).suffix.lower()
    return 'video' if suffix in VIDEO_FORMATS else 'image' if suffix in IMAGE_FORMATS else 'document'


def naming_template(settings, path):
    kind = media_kind(path)
    return (settings.image_template if kind == 'image' else settings.video_template if kind == 'video' else settings.template) or settings.template


class LocalModelRouter:
    def __init__(self, engine, settings, cancelled, progress):
        self.engine, self.settings = engine, settings
        self.cancelled, self.progress = cancelled, progress

    def backend_for(self, path):
        kind = media_kind(path)
        vision = kind == 'video' or (kind == 'image' and self.settings.image_analysis != 'ocr')
        key = 'smolvlm' if vision else self.settings.text_model
        spec = model_spec(key)
        folder = model_directory()
        model = folder / spec.filename
        projector = folder / spec.projector.filename if spec.projector else None
        if self.cancelled():raise AnalysisCancelled()
        if not model.is_file() or (projector and not projector.is_file()):
            self.progress(tr('Modell für ') + (tr('Bilder/Video') if vision else tr('Dokumente')) + tr(' wird heruntergeladen …'))
            model, projector = download_model_package(key, self.cancelled, self.progress)
        self.progress(tr('Modellwahl · ') + spec.label)
        options = {'projector': projector} if projector else {}
        return self.engine.start(model, self.cancelled, self.progress, **options)
