# Build on macOS with: .venv/bin/python -m PyInstaller build_support/Nomi.spec
from pathlib import Path
from importlib.metadata import version
import platform
import runpy
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).parent
metadata = copy_metadata('nomi-renamer')
# Always compile from tracked source, never reuse a developer's stale binary.
vision_helper = runpy.run_path(str(root / 'build_support' / 'build_vision.py'))['build']()
llama_directory = runpy.run_path(str(root / 'build_support' / 'fetch_llama.py'))['fetch']()
llama_binaries = [(str(p), 'nomi/bin/llama') for p in llama_directory.iterdir()
                  if p.name == 'llama-server' or p.name.endswith('.dylib')]
a = Analysis(
    [str(root / 'build_support' / 'launcher.py')],
    pathex=[str(root)],
    binaries=[(str(vision_helper), 'nomi/bin')] + llama_binaries,
    datas=[(str(root / 'LICENSE'), '.'), (str(root / 'README.md'), '.')]
          + [(str(llama_directory / 'LICENSE'), 'third_party/llama.cpp')]
          + metadata + collect_data_files('pypdfium2_raw'),
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
                 'CFBundleShortVersionString': version('nomi-renamer'),
                 'CFBundleVersion': version('nomi-renamer'),
                 'NSHighResolutionCapable': True,
                 'NSLocalNetworkUsageDescription': 'Nomi verbindet sich mit deinem konfigurierten Ollama-Server im lokalen Netzwerk, um Dokumenttexte zu analysieren.',
                 'LSMinimumSystemVersion': '.'.join(platform.mac_ver()[0].split('.')[:2]),
             })
