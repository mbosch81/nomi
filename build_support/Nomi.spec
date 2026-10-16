# Build on macOS with: .venv/bin/python -m PyInstaller build_support/Nomi.spec
from pathlib import Path
import tomllib
import platform
import runpy
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).parent
license_directory = runpy.run_path(str(root / 'build_support/collect_licenses.py'))['collect']()
app_version = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
metadata = copy_metadata('nomi-renamer')
# Always compile from tracked source, never reuse a developer's stale binary.
vision_helper = runpy.run_path(str(root / 'build_support' / 'build_vision.py'))['build']()
llama_directory = runpy.run_path(str(root / 'build_support' / 'fetch_llama.py'))['fetch']()
ffmpeg_directory = runpy.run_path(str(root / 'build_support' / 'build_ffmpeg.py'))['build']()
ffmpeg_binaries = [(str(ffmpeg_directory / name), 'nomi/bin/ffmpeg') for name in ('ffmpeg', 'ffprobe')]
ffmpeg_data = [(str(ffmpeg_directory / name), 'third_party/ffmpeg') for name in ('COPYING.LGPLv2.1', 'build.json', 'ffmpeg-9.0.2.tar.xz')]
llama_binaries = [(str(p), 'nomi/bin/llama') for p in llama_directory.iterdir()
                  if p.name == 'llama-server' or p.name.endswith('.dylib')]
a = Analysis(
    [str(root / 'build_support' / 'launcher.py')],
    pathex=[str(root)],
    binaries=[(str(vision_helper), 'nomi/bin')] + llama_binaries + ffmpeg_binaries,
    datas=[(str(root / 'LICENSE'), '.'), (str(root / 'README.md'), '.'),
           (str(root / 'CHANGELOG.md'), '.'), (str(root / 'docs'), 'docs')]
          + [(str(llama_directory / 'LICENSE'), 'third_party/llama.cpp')]
          + [(str(license_directory), 'third_party/python')] + ffmpeg_data + metadata + collect_data_files('pypdfium2_raw'),
    hiddenimports=['PIL.PdfImagePlugin', 'nomi.diagnostics'],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'tkinter'],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Nomi',
          console=False, target_arch=None, codesign_identity=None)
coll = COLLECT(exe, a.binaries, a.datas, name='Nomi')
app = BUNDLE(coll, name='Nomi.app', bundle_identifier='de.moreweb.nomi',
             info_plist={
                 'CFBundleName': 'Nomi',
                 'CFBundleDisplayName': 'Nomi',
                 'CFBundleShortVersionString': app_version,
                 'CFBundleVersion': app_version,
                 'NSHighResolutionCapable': True,
                 'NSLocalNetworkUsageDescription': 'Nomi verbindet sich mit deinem konfigurierten Ollama-Server im lokalen Netzwerk, um Dokumenttexte zu analysieren.',
                 'LSMinimumSystemVersion': '.'.join(platform.mac_ver()[0].split('.')[:2]),
             })
