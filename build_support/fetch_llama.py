"""Fetch a pinned upstream llama.cpp runtime for inclusion in the macOS app."""
from pathlib import Path
import hashlib
import platform
import shutil
import tarfile
import tempfile
import zipfile
from urllib.request import urlopen

VERSION = 'b11622'
DIGESTS = {
    'arm64': '69ce43d516c61e2836c11b7a0fa9e12f38d2a5e33d849ccb58e49394cd855413',
    'win-x64': '344b8c2204e3a3b921164d449b3e4c2bdd166eb41d1ceb8ecc0ca0fb99657a52',
    'x64': '6678e8a16a7cf55c5c51d9fee100681f2a150fe11090dd521f3edb0e6f418a16',
}


def fetch() -> Path:
    root = Path(__file__).resolve().parent.parent
    arch = 'arm64' if platform.machine() == 'arm64' else 'x64'
    windows = platform.system() == 'Windows'
    if windows and platform.machine().lower() not in {'amd64', 'x86_64'}:
        raise ValueError('Windows runtime build currently requires x64')
    digest = DIGESTS['win-x64' if windows else arch]
    filename = f'llama-{VERSION}-bin-win-cpu-x64.zip' if windows else f'llama-{VERSION}-bin-macos-{arch}.tar.gz'
    archive = root / 'work' / filename
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
        with urlopen(f'https://github.com/ggml-org/llama.cpp/releases/download/{VERSION}/{filename}', timeout=60) as response:
            payload = response.read()
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError('llama.cpp runtime checksum mismatch')
        archive.write_bytes(payload)
    destination = root / 'nomi' / 'bin' / 'llama'
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nomi-runtime-') as folder:
        if windows:
            with zipfile.ZipFile(archive) as handle:
                # Only flat executable/library/license entries; no archive paths escape.
                for entry in handle.infolist():
                    name = Path(entry.filename).name
                    if name == 'llama-server.exe' or name.endswith('.dll') or name.startswith('LICENSE'):
                        (Path(folder) / name).write_bytes(handle.read(entry))
            source = Path(folder)
        else:
            with tarfile.open(archive) as tar:
                tar.extractall(folder, filter='data')
            source = Path(folder) / f'llama-{VERSION}'
        for entry in source.iterdir():
            if entry.name in {'llama-server', 'llama-server.exe'} or entry.name.endswith(('.dll', '.dylib', '.metallib')) or entry.name.startswith('LICENSE'):
                target = destination / entry.name
                if target.is_symlink():
                    target.unlink()
                if entry.is_symlink():
                    target.unlink(missing_ok=True)
                    target.symlink_to(entry.readlink())
                else:
                    shutil.copy2(entry, target)
    if not (destination / 'LICENSE').exists():
        with urlopen(f'https://raw.githubusercontent.com/ggml-org/llama.cpp/{VERSION}/LICENSE', timeout=30) as response:
            license_data = response.read()
        if b'MIT License' not in license_data:
            raise ValueError('Missing upstream license')
        (destination / 'LICENSE').write_bytes(license_data)
    return destination


if __name__ == '__main__':
    print(fetch())
