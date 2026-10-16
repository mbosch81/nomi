from .i18n import tr
"""Review the complete selected rename plan; the actual move rechecks atomically."""
from collections import Counter
from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QDialogButtonBox
from PySide6.QtGui import QColor
from .core import validate_name
from .session import file_identity


def review_plan(items, identities=None, settings=None, metadata=None, approved_targets=None):
    rows=[]
    identities=identities or {}
    for path, name, status in items:
        problems=[]
        target=None
        try:
            current=file_identity(path)
            if path in identities and current != identities[path]:problems.append('Quelle seit Analyse verändert · erneut analysieren')
            target=validate_name(path,name)
            if settings and len(name.encode('utf-8'))>settings.max_name_length:
                raise ValueError(tr('Name überschreitet die eingestellte maximale Länge.'))
            if settings and settings.organize_enabled:
                from .organize import destination_for,validate_destination
                target=destination_for(path,name,(metadata or {}).get(path),settings)
                validate_destination(path,target,Path(settings.organize_root).expanduser())
            if approved_targets is not None and target!=approved_targets.get(path):raise ValueError(tr('Geprüfter Zielpfad hat sich verändert.'))
            if target != path and (target.exists() or target.is_symlink()):problems.append(tr('Ziel existiert bereits'))
        except (ValueError,OSError) as error:problems.append(str(error))
        rows.append(dict(path=path,name=name,target=target,problems=problems,status=status))
    counts=Counter(str(row['target']).casefold() for row in rows if row['target'])
    for row in rows:
        if row['target'] and counts[str(row['target']).casefold()]>1:row['problems'].append(tr('Ziel mehrfach vergeben'))
    return rows


class RenameReview(QDialog):
    def __init__(self, rows, parent=None):
        super().__init__(parent)
        moving=any(row['target'] and row['target'].parent!=row['path'].parent for row in rows)
        self.setWindowTitle(tr('Umbenennen und Einsortieren prüfen') if moving else tr('Umbenennungen prüfen'))
        self.resize(850,480)
        self.setModal(True)
        layout=QVBoxLayout(self)
        errors=sum(bool(row['problems']) for row in rows)
        unchanged=sum(row['target']==row['path'] for row in rows)
        layout.addWidget(QLabel(f"{len(rows)}{tr(' Dateien · ')}{unchanged}{tr(' unverändert · ')}{errors}{tr(' mit Problemen')}"))
        self.list=QListWidget()
        for row in rows:
            state=tr('STOPP: ')+ '; '.join(row['problems']) if row['problems'] else (tr('Unverändert') if row['target']==row['path'] else tr('Bitte prüfen'))
            self.list.addItem(f"{row['path'] if moving else row['path'].name}\n→ {(row['target'] if moving else row['name']) or tr('(Ziel fehlt)')}\n{state} · {row['status']}")
            item=self.list.item(self.list.count()-1)
            item.setToolTip(str(row['path'].parent))
            if row['problems']:item.setForeground(QColor('#ff8d8d'))
            elif tr('Fehlende Angaben') in row['status']:item.setForeground(QColor('#ffd479'))
        layout.addWidget(self.list)
        note=QLabel(tr('Erst „Jetzt ausführen“ verändert Dateinamen oder Speicherorte. Bestehende Dateien werden nicht überschrieben. Fehlende oder unsichere Angaben im Vorschlag bitte vorab bearbeiten.'))
        note.setWordWrap(True);layout.addWidget(note)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.confirm=buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.confirm.setText(tr('Jetzt ausführen') if moving else tr('Jetzt umbenennen'));self.confirm.setEnabled(bool(rows) and not errors)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr('Zurück'))
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
