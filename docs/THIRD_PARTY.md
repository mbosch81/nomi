# Third-party notices and rebuilding

Nomi itself uses the [MIT license](../LICENSE). This does not replace any third-party
license. Release packages include the installed Python packages' shipped notices,
package versions and upstream links in `third_party/python`, plus the Qt LGPLv3
and GPLv3 license texts in `docs/licenses`. The matching per-platform notices ZIP
in each release makes these notices accessible without launching the app.

| Component | License / source |
| --- | --- |
| Python | [PSF license and source](https://www.python.org/downloads/source/) |
| PySide6 / Shiboken6 / Qt | LGPLv3; [Qt source archives](https://download.qt.io/archive/qt/), [Qt for Python sources](https://download.qt.io/official_releases/QtForPython/pyside6/) |
| llama.cpp | MIT; [pinned b11622 source](https://github.com/ggml-org/llama.cpp/tree/b11622) |
| FFmpeg | LGPLv2.1 or later, GPL/nonfree disabled; matching complete source archive and build recipe included in `third_party/ffmpeg` |
| PDFium / pypdfium2 | BSD/Apache and component notices, included from the installed distribution |
| Pillow / pypdf / fonttools / defusedxml | Their respective notices included from the installed distributions |
| PyInstaller | GPL with bootloader exception; [source and exception](https://github.com/pyinstaller/pyinstaller) |

Qt/PySide are used as shared libraries. Nomi does not prohibit modifying them or
reverse engineering for debugging such modifications. The public source and
[build instructions](DEVELOPMENT.md) allow rebuilding the app with modified shared
libraries, including the Windows one-file package. Neither platform uses a
publisher signature or integrity restriction requiring a private signing key to
run such a rebuilt package. Preserve applicable notices when redistributing.

Build tools are required only for rebuilding. Users of the released app do not
need to install Python, Qt, a compiler, llama.cpp, or FFmpeg. Unmodified upstream
source archives and the exact installed versions are identified in each platform's
`packages.json`; the native build scripts and pinned runtime hashes are in the
public repository. Models are downloaded separately and retain their own licenses:
[Qwen3](https://huggingface.co/Qwen/Qwen3-4B-GGUF),
[Mistral](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3),
[SmolVLM2](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct).
