"""Compile the local Vision helper for development and the macOS bundle."""
from pathlib import Path
import platform
import subprocess
import sys


def build() -> Path:
    if sys.platform != 'darwin':
        raise RuntimeError('Apple Vision kann nur unter macOS gebaut werden.')
    root = Path(__file__).resolve().parent.parent
    destination = root / 'nomi' / 'bin' / 'nomi-vision'
    destination.parent.mkdir(exist_ok=True)
    subprocess.run(['xcrun', 'swiftc', '-O', '-target',
                    f'{platform.machine()}-apple-macos14.0',
                    str(root / 'native' / 'VisionOCR.swift'), '-o', str(destination)], check=True)
    return destination


if __name__ == '__main__':
    print(build())
