"""Fetch a pinned upstream llama.cpp runtime for inclusion in the macOS app."""
from pathlib import Path
import hashlib
import platform
import shutil
import tarfile
import tempfile
from urllib.request import urlopen

VERSION = 'b11622'
DIGESTS = {
    'arm64': '69ce43d516c61e2836c11b7a0fa9e12f38d2a5e33d849ccb58e49394cd855413',
    'x64': '6678e8a16a7cf55c5c51d9fee100681f2a150fe11090dd521f3edb0e6f418a16',
}


def fetch() -> Path:
    root = Path(__file__).resolve().parent.parent
    arch = 'arm64' if platform.machine() == 'arm64' else 'x64'
    archive = root / 'work' / f'llama-{VERSION}-{arch}.tar.gz'
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != DIGESTS[arch]:
        with urlopen(f'https://github.com/ggml-org/llama.cpp/releases/download/{VERSION}/llama-{VERSION}-bin-macos-{arch}.tar.gz', timeout=60) as response:
            payload = response.read()
        if hashlib.sha256(payload).hexdigest() != DIGESTS[arch]:
            raise ValueError('llama.cpp runtime checksum mismatch')
        archive.write_bytes(payload)
    destination = root / 'nomi' / 'bin' / 'llama'
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nomi-runtime-') as folder:
        with tarfile.open(archive) as tar:
            tar.extractall(folder, filter='data')
        source = Path(folder) / f'llama-{VERSION}'
        for entry in source.iterdir():
            if entry.name == 'llama-server' or entry.name.endswith(('.dylib', '.metallib')) or entry.name.startswith('LICENSE'):
                target = destination / entry.name
                if target.is_symlink():
                    target.unlink()
                if entry.is_symlink():
                    target.unlink(missing_ok=True)
                    target.symlink_to(entry.readlink())
                else:
                    shutil.copy2(entry, target)
    return destination


if __name__ == '__main__':
    print(fetch())
