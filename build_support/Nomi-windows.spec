# Native Windows x64 one-file build; runtime tools unpack beside the app modules.
from pathlib import Path
import runpy
from PyInstaller.utils.hooks import collect_data_files, copy_metadata
root = Path(SPECPATH).parent
license_directory = runpy.run_path(str(root / 'build_support/collect_licenses.py'))['collect']()
llama = runpy.run_path(str(root / 'build_support/fetch_llama.py'))['fetch']()
ffmpeg = runpy.run_path(str(root / 'build_support/build_ffmpeg.py'))['build']()
binaries = [(str(p), 'nomi/bin/llama') for p in llama.iterdir() if p.suffix in {'.exe', '.dll'}]
binaries += [(str(ffmpeg / (name + '.exe')), 'nomi/bin/ffmpeg') for name in ('ffmpeg', 'ffprobe')]
data = [(str(root / name), '.') for name in ('LICENSE', 'README.md', 'CHANGELOG.md')]
data += [(str(root / 'docs'), 'docs'), (str(llama / 'LICENSE'), 'third_party/llama.cpp')]
data += [(str(ffmpeg / name), 'third_party/ffmpeg') for name in ('COPYING.LGPLv2.1', 'build.json', 'ffmpeg-9.0.2.tar.xz')]
a = Analysis([str(root / 'build_support/launcher.py')], pathex=[str(root)], binaries=binaries,
             datas=data + [(str(license_directory), 'third_party/python')] + copy_metadata('nomi-renamer') + collect_data_files('pypdfium2_raw'),
             hiddenimports=['PIL.PdfImagePlugin', 'nomi.diagnostics'],
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'tkinter'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Nomi', console=False, upx=False)
