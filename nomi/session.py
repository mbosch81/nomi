from .i18n import tr
"""Bounded session-only results. No document data is written to disk."""
from collections import OrderedDict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path


def file_identity(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError(tr('Datei fehlt oder ist ein symbolischer Link.'))
    stat=path.stat()
    # NTFS may coalesce timestamps for rapid same-size rewrites. Small documents
    # get a bounded content fingerprint; large media retain the cheap stat check
    # so opening a table row never hashes gigabytes on the UI thread.
    digest = None
    if stat.st_size <= 1024 * 1024:
        with path.open('rb') as handle:
            digest = hashlib.sha256(handle.read(1024 * 1024 + 1)).hexdigest()
    return (str(path.absolute()),stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns,digest)


def policy_key(settings):
    values=asdict(settings)
    values.pop('analysis_hint', None)  # Explicit reanalysis replaces the latest suggestion.
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()


class SessionResults:
    def __init__(self, limit=64, byte_limit=32*1024*1024):
        self.limit,self.byte_limit=limit,byte_limit
        self.entries=OrderedDict()

    def get(self, path, settings):
        try:key=(file_identity(path),policy_key(settings))
        except (ValueError,OSError):return None
        result=self.entries.get(key)
        if result is not None:self.entries.move_to_end(key)
        return result

    def put(self, identity, settings, result):
        key=(identity,policy_key(settings))
        self.entries[key]=result
        self.entries.move_to_end(key)
        while self.entries and (len(self.entries)>self.limit or sum(sum(len(encoded) for _,encoded in entry.get('frames', [])) for entry in self.entries.values())>self.byte_limit):
            _, evicted = self.entries.popitem(last=False)
            evicted['frames'] = []  # Release samples also held by a table detail record.

    def edit(self, path, settings, name, status):
        entry=self.get(path, settings)
        if entry is not None:
            entry['name'],entry['status']=name,status

    def forget(self, path):
        location=str(Path(path).absolute())
        for key in list(self.entries):
            if key[0][0]==location:del self.entries[key]
