"""Explicit same-filesystem organization; no copying, overwriting or symlink traversal."""
import os
from pathlib import Path
import stat
from string import Formatter
from dataclasses import replace
from .core import FIELDS, RenameRecord, RenameError, identity, validate_name, normalize_date
from .naming import format_name

FOLDER_FIELDS=set(FIELDS)|{'jahr','monat'}


def destination_for(source, name, metadata, settings):
    source=Path(source).absolute()
    validate_name(source,name)
    if not settings.organize_enabled:return source.with_name(name)
    if not settings.organize_root.strip():raise ValueError('Bitte einen vorhandenen Zielordner auswählen.')
    root=Path(settings.organize_root).expanduser().absolute()
    template=settings.folder_template
    if not template:return root/name
    if metadata is None:raise ValueError('Zum Einsortieren bitte zuerst analysieren.')
    if template.startswith('/') or '\\' in template:raise ValueError('Ordnerschema muss ein relativer Pfad sein.')
    parts=template.split('/')
    if len(parts)>8 or any(part.strip() in ('','.','..') for part in parts):raise ValueError('Ungültige Ordnerstruktur (maximal 8 Ebenen).')
    values={field:str(metadata.get(field,'') or '') for field in FIELDS}
    try:date=normalize_date(values['datum'])
    except ValueError:date=''
    values.update(jahr=date[:4] if date else 'Ohne_Datum',monat=date[5:7] if date else 'Ohne_Datum')
    folder_settings=replace(settings,max_name_length=min(80,settings.max_name_length))
    # Sanitize values before substitution, so metadata cannot introduce path levels.
    for key,value in values.items():
        if not value:value='Unsortiert'
        values[key]=format_name(value,Path('folder.txt'),folder_settings)[:-4]
    folders=[]
    for part in parts:
        try:
            parsed=list(Formatter().parse(part))
            if any(field is not None and (field not in FOLDER_FIELDS or spec or conversion) for _,field,spec,conversion in parsed):raise ValueError()
            rendered=part.format(**values)
        except (KeyError,ValueError,IndexError):raise ValueError('Ungültige Felder im Ordnerschema.')
        folders.append(format_name(rendered,Path('folder.txt'),folder_settings)[:-4])
    return root.joinpath(*folders,name)


def open_directory(path, create=False, created=None):
    """Walk from the filesystem root with O_NOFOLLOW, holding directory descriptors."""
    path=Path(path).absolute()
    if '..' in path.parts:raise ValueError('Übergeordnete Pfadsegmente sind nicht erlaubt.')
    if os.name!='posix':raise ValueError('Sicheres Einsortieren ist derzeit für macOS/Linux verfügbar.')
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    fd=os.open(path.anchor,flags)
    current=Path(path.anchor)
    try:
        for part in path.parts[1:]:
            current=current/part
            try:new=os.open(part,flags,dir_fd=fd)
            except FileNotFoundError:
                if not create:raise
                try:os.mkdir(part,dir_fd=fd)
                except FileExistsError:pass
                else:
                    st=os.stat(part,dir_fd=fd,follow_symlinks=False)
                    if created is not None:created.append((current,(st.st_dev,st.st_ino)))
                new=os.open(part,flags,dir_fd=fd)
            os.close(fd);fd=new
        return fd
    except BaseException:
        os.close(fd)
        raise


def validate_destination(source,target,root):
    source,target,root=map(lambda p:Path(p).absolute(),(source,target,root))
    target.relative_to(root)
    if '..' in target.parts:raise ValueError('Ungültiger Zielpfad.')
    root_fd=open_directory(root)
    try:device=os.fstat(root_fd).st_dev
    finally:os.close(root_fd)
    if source.is_symlink() or not source.is_file():raise ValueError('Quelldatei fehlt oder ist ein symbolischer Link.')
    if source.stat().st_dev!=device:raise ValueError('Ziel muss auf demselben Laufwerk wie die Quelle liegen.')
    source_fd=open_directory(source.parent);os.close(source_fd)
    parent=target.parent
    while True:
        try:fd=open_directory(parent);break
        except FileNotFoundError:
            if parent==root:raise
            parent=parent.parent
    try:
        if os.fstat(fd).st_dev!=device:raise ValueError('Ziel liegt auf einem anderen Laufwerk.')
        if parent==target.parent and source!=target:
            if any(name.casefold()==target.name.casefold() for name in os.listdir(fd)):
                raise ValueError('Ziel existiert bereits.')
    finally:os.close(fd)
    validate_name(source,target.name)


def secure_move(source,target):
    """Reserve the destination atomically, then unlink the verified source."""
    source,target=Path(source),Path(target)
    source_fd=open_directory(source.parent)
    try:
        target_fd=open_directory(target.parent)
        try:
            before=os.stat(source.name,dir_fd=source_fd,follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode):raise ValueError('Quelle ist keine reguläre Datei.')
            expected=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
            os.link(source.name,target.name,src_dir_fd=source_fd,dst_dir_fd=target_fd,follow_symlinks=False)
            try:
                linked=os.stat(target.name,dir_fd=target_fd,follow_symlinks=False)
                current=os.stat(source.name,dir_fd=source_fd,follow_symlinks=False)
                if any((st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)!=expected for st in (linked,current)):
                    raise ValueError('Quelle wurde während der Aktion verändert.')
                os.unlink(source.name,dir_fd=source_fd)
            except BaseException:
                # Only remove the link created by this operation, never a replacement.
                current=os.stat(target.name,dir_fd=target_fd,follow_symlinks=False)
                if (current.st_dev,current.st_ino)==(before.st_dev,before.st_ino):os.unlink(target.name,dir_fd=target_fd)
                raise
        finally:os.close(target_fd)
    finally:os.close(source_fd)


def cleanup_created(directories):
    for path,expected in sorted(set(directories),key=lambda item:len(item[0].parts),reverse=True):
        try:
            fd=open_directory(path.parent)
            try:
                st=os.stat(path.name,dir_fd=fd,follow_symlinks=False)
                if stat.S_ISDIR(st.st_mode) and (st.st_dev,st.st_ino)==expected:os.rmdir(path.name,dir_fd=fd)
            finally:os.close(fd)
        except (OSError,ValueError):pass  # Keep nonempty, replaced or inaccessible directories.


def organize_batch(items,root):
    root=Path(root).absolute()
    root_fd=open_directory(root)
    try:
        st=os.fstat(root_fd);root_identity=(st.st_dev,st.st_ino)
    finally:os.close(root_fd)
    sources=set();targets=set();plan=[]
    for source,target in items:
        source,target=Path(source).absolute(),Path(target).absolute()
        if source in sources:raise ValueError('Quelle mehrfach ausgewählt.')
        sources.add(source)
        validate_destination(source,target,root)
        key=str(target).casefold()
        if key in targets:raise ValueError('Ziel mehrfach vergeben.')
        targets.add(key)
        if source!=target:plan.append((source,target,identity(source)))
    created=[];records=[]
    try:
        for source,target,expected in plan:
            root_fd=open_directory(root)
            try:
                st=os.fstat(root_fd)
                if (st.st_dev,st.st_ino)!=root_identity:raise ValueError('Zielordner wurde ausgetauscht.')
            finally:os.close(root_fd)
            fd=open_directory(target.parent,True,created);os.close(fd)
            validate_destination(source,target,root)
            if identity(source)!=expected:raise ValueError('Quelle wurde vor der Aktion verändert.')
            secure_move(source,target)
            records.append(RenameRecord(source,target,expected,organized=True))
    except Exception as cause:
        remaining=[]
        for record in reversed(records):
            try:secure_move(record.after,record.before)
            except Exception:remaining.append(record)
        cleanup_created(created)
        for record in remaining:record.created_dirs=tuple(created)
        raise RenameError(cause,list(reversed(remaining))) from cause
    for record in records:record.created_dirs=tuple(created)
    return records
