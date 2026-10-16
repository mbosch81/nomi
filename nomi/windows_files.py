from .i18n import tr
"""Windows directory guards and atomic, non-replacing moves by file handle.

Directory handles deny delete sharing, pinning every ancestor against renames and
junction substitution until the operation finishes. No copy/delete fallback.
"""
from contextlib import contextmanager
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import os
import stat


def api():
    k = C.WinDLL('kernel32', use_last_error=True)
    k.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, W.LPVOID, W.DWORD, W.DWORD, W.HANDLE]
    k.CreateFileW.restype = W.HANDLE
    k.CloseHandle.argtypes = [W.HANDLE]
    k.SetFileInformationByHandle.argtypes = [W.HANDLE, C.c_int, W.LPVOID, W.DWORD]
    k.SetFileInformationByHandle.restype = W.BOOL
    return k


@contextmanager
def handle(path, *, directory=False, delete=False):
    k = api()
    access = 0x81 | (0x10000 if delete else 0)  # READ_ATTRIBUTES, DELETE
    h = k.CreateFileW(str(path), access, 3 if directory else 1, None, 3,
                      0x00200000 | (0x02000000 if directory else 0), None)
    if h == W.HANDLE(-1).value:
        raise C.WinError(C.get_last_error())
    try:
        st = os.lstat(path)
        if st.st_file_attributes & 0x400:
            raise ValueError(tr('Symbolic links and junctions are not allowed.'))
        if directory != stat.S_ISDIR(st.st_mode):
            raise ValueError(tr('Unexpected file type.'))
        yield h
    finally:
        k.CloseHandle(h)


@contextmanager
def directory_guard(path, create=False, created=None):
    """Local drive paths only; unsupported shares fail closed."""
    from contextlib import ExitStack
    path = Path(path).absolute()
    if '..' in path.parts or not path.drive or path.drive.startswith('\\\\'):
        raise ValueError(tr('Use a local drive without parent path segments.'))
    with ExitStack() as stack:
        current = Path(path.anchor)
        stack.enter_context(handle(current, directory=True))
        for part in path.parts[1:]:
            current /= part
            if create:
                try:
                    current.mkdir()
                except FileExistsError:
                    pass
                else:
                    st = current.stat()
                    if created is not None:
                        created.append((current, (st.st_dev, st.st_ino)))
            stack.enter_context(handle(current, directory=True))
        yield path


def validate_destination(source, target, root):
    from .core import validate_name
    source, target, root = (Path(p).absolute() for p in (source, target, root))
    target.relative_to(root)
    validate_name(source, target.name)
    with directory_guard(root), directory_guard(source.parent):
        with handle(source):
            if source.stat().st_dev != root.stat().st_dev:
                raise ValueError(tr('Source and destination must be on the same drive.'))
        parent = target.parent
        while True:
            try:
                with directory_guard(parent):
                    if parent.stat().st_dev != root.stat().st_dev:
                        raise ValueError(tr('Destination is on another drive.'))
                    if parent == target.parent and source != target and any(p.name.casefold() == target.name.casefold() for p in parent.iterdir()):
                        raise ValueError(tr('Destination already exists.'))
                break
            except FileNotFoundError:
                if parent == root:
                    raise
                parent = parent.parent


def secure_move(source, target):
    source, target = Path(source).absolute(), Path(target).absolute()
    with directory_guard(source.parent), directory_guard(target.parent), handle(source, delete=True) as h:
        if source.stat().st_dev != target.parent.stat().st_dev:
            raise ValueError(tr('Source and destination must be on the same drive.'))
        class RenameInfo(C.Structure):
            _fields_ = [('replace', W.DWORD), ('root', W.HANDLE), ('length', W.DWORD), ('name', W.WCHAR * 1)]
        name = str(target).encode('utf-16-le')
        offset = RenameInfo.name.offset
        buffer = C.create_string_buffer(max(C.sizeof(RenameInfo), offset + len(name)))
        info = C.cast(buffer, C.POINTER(RenameInfo)).contents
        info.replace = 0
        info.root = None
        info.length = len(name)
        C.memmove(C.addressof(buffer) + offset, name, len(name))
        if not api().SetFileInformationByHandle(h, 3, buffer, len(buffer)):
            raise C.WinError(C.get_last_error())


def cleanup_created(directories):
    for path, expected in sorted(set(directories), key=lambda item: len(item[0].parts), reverse=True):
        try:
            with directory_guard(path.parent), handle(path, directory=True, delete=True) as h:
                st = path.stat()
                if (st.st_dev, st.st_ino) != expected:
                    continue
                delete = W.BOOL(True)
                if not api().SetFileInformationByHandle(h, 4, C.byref(delete), C.sizeof(delete)):
                    raise C.WinError(C.get_last_error())
        except (OSError, ValueError):
            pass  # Keep nonempty or replaced directories.


def organize_batch(items, root):
    from .core import identity, RenameRecord, RenameError
    from .organize import secure_move as move
    root = Path(root).absolute()
    created, records, plan = [], [], []
    sources, targets = set(), set()
    with directory_guard(root):
        for source, target in items:
            source, target = Path(source).absolute(), Path(target).absolute()
            validate_destination(source, target, root)
            if source in sources or str(target).casefold() in targets:
                raise ValueError(tr('Duplicate source or destination.'))
            sources.add(source); targets.add(str(target).casefold())
            if source != target:
                plan.append((source, target, identity(source)))
        try:
            for source, target, expected in plan:
                with directory_guard(source.parent), directory_guard(target.parent, True, created):
                    validate_destination(source, target, root)
                    if identity(source) != expected:
                        raise ValueError(tr('Source changed before the operation.'))
                    move(source, target)
                    records.append(RenameRecord(source, target, expected, organized=True))
        except Exception as cause:
            remaining = []
            for record in reversed(records):
                try: move(record.after, record.before)
                except Exception: remaining.append(record)
            cleanup_created(created)
            for record in remaining: record.created_dirs = tuple(created)
            raise RenameError(cause, list(reversed(remaining))) from cause
    for record in records: record.created_dirs = tuple(created)
    return records
