# Development and application builds

[← Nomi](../README.md) · [User guide](START.md) · [Changelog](../CHANGELOG.md)

This page is for contributors and maintainers. To try the application, use the
[download instructions](DOWNLOAD.md); the packaged Mac app does not require a
Python setup on the user's computer.

## Run from source

Use Python 3.11–3.14. Python 3.15 is outside the supported range. On macOS, select
an installed compatible interpreter explicitly, for example:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -e '.[ocr]'
.venv/bin/python build_support/build_vision.py
.venv/bin/python build_support/fetch_llama.py
.venv/bin/python build_support/build_ffmpeg.py
.venv/bin/python -m nomi
```

The native OCR helper requires Apple's command-line development tools and Swift
at build time. FFmpeg is built from source using the local compiler and `make`.
Those tools are not required by users of the packaged application.

On Windows, automatic OCR uses Windows.Media.Ocr through the shipped PowerShell
helper. It uses OS language packs and requires no separate OCR program. Tesseract
remains optional on all supported platforms; Linux needs it for OCR.
The Windows preview bundles llama.cpp CPU x64 and the same minimal LGPL-only
FFmpeg build. Folder organization uses pinned directory descriptors on POSIX and native guarded
handles with non-replacing SetFileInformationByHandle moves on Windows. Windows
junctions/reparse points and network shares are rejected.
No Linux binary package is published.

## Build the Mac application

```sh
.venv/bin/python -m pip install -e '.[ocr,build]'
.venv/bin/python -m PyInstaller --noconfirm build_support/Nomi.spec
```

The result is `dist/Nomi.app`. The build includes Python, Qt, OCR dependencies,
Apple Vision's compiled helper, llama.cpp, FFmpeg/ffprobe, user documentation,
and third-party license material. Model weights remain separate from the bundle.
Generated binaries and model weights must not be committed to Git.

`build_support/Nomi.spec` takes the version from `pyproject.toml`. It builds for the
host architecture and sets the minimum macOS version from the build host's major
and minor version. A locally built package may therefore require a newer macOS
version than the CI artifact. Do not advertise a local macOS 27 build as compatible
with macOS 14. The workflow currently builds on `macos-14`; the checked October 16,
2026 job ran on macOS 14.8.9 ARM64.

The bundle is ad hoc signed. It is not Developer ID signed or Apple-notarized.
The macOS local-network usage declaration is included for configured LAN Ollama
connections. Public releases are published by the separate release workflow only when explicitly
dispatched with `publish` enabled and both platform jobs pass. No in-app updater is configured.

Archive with symlinks preserved:

```sh
ditto -c -k --sequesterRsrc --keepParent dist/Nomi.app dist/Nomi-macos.zip
codesign --verify --deep --strict dist/Nomi.app
```

## Tests and diagnostics

```sh
.venv/bin/python -m pip check
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen .venv/bin/python -m nomi --self-test
```

Tests use synthetic data. Platform-specific integration tests can be skipped when
an optional backend is unavailable; inspect the final result rather than relying
on a historical test count.

Packaged application checks:

```sh
QT_QPA_PLATFORM=offscreen dist/Nomi.app/Contents/MacOS/Nomi --runtime-check
QT_QPA_PLATFORM=offscreen dist/Nomi.app/Contents/MacOS/Nomi --self-test
# Opt-in: the default Qwen GGUF must already be downloaded.
QT_QPA_PLATFORM=offscreen dist/Nomi.app/Contents/MacOS/Nomi --llama-self-test
```

The offline smoke test covers OCR, previews, naming rules, reviewed renaming,
folder organization, and undo using temporary files and isolated preferences.
The opt-in llama check uses actual local inference and does not download weights.
CI uses synthetic model-server tests rather than multi-gigabyte model downloads.

[GitHub Actions](https://github.com/mbosch81/nomi/actions/workflows/tests.yml)
runs tests on Ubuntu with Python 3.11/3.14 and on macOS with Python 3.14. After
successful tests, a separate job builds the Mac bundle, exercises the packaged
runtime and offline test, and uploads the `Nomi-macos` artifact. Workflow behavior
is defined in [tests.yml](https://github.com/mbosch81/nomi/blob/main/.github/workflows/tests.yml).

## Runtime and model behavior

- llama.cpp is pinned to `b11622` and runs as an owned child process on loopback
  with an ephemeral API key. Local requests bypass system proxies. Closing Nomi
  or switching to Ollama stops the owned engine; there is no automatic cloud fallback.
- Qwen3 4B is the default document model, Mistral 7B Instruct v0.3 an alternative,
  and SmolVLM2 2.2B with its projector the vision model. Download revisions, sizes,
  and SHA-256 hashes are pinned in [local_model.py](https://github.com/mbosch81/nomi/blob/main/nomi/local_model.py).
- Automatic routing loads one model at a time. Own GGUF paths and projectors remain
  available through manual selection. Ollama uses the configured server model.
- The text model context is 8,192 tokens; vision uses 16,384. GPU offloading is
  requested where available. Model memory requirements exceed weight-file sizes.
- Apple Vision uses OCR revision 3, language correction, and explicit CPU execution.
  Tesseract remains optional. OCR does not rewrite input PDFs.
- Text analysis is limited to 16,000 characters and the first 20 PDF pages. Text
  previews have separate limits. Video sampling uses 1–12 JPEG frames, up to
  512 × 512 pixels. Direct vision images are prepared up to 1024 × 1024 pixels.

## Filesystem behavior

Renaming reserves a destination using a hard link before unlinking the source.
Conflicts never fall back to overwriting. Failed batches attempt rollback;
`RenameError.records` preserves remaining completed moves for recovery.

Folder organization is opt-in and stays on the same filesystem. Relative folder
schemas are validated, metadata cannot add path levels, and directory traversal
uses no-follow directory descriptors. Only newly created, still-empty directories
with matching identities are removed during cleanup. Undo refuses modified files
and occupied original names. Concurrent external changes and power loss are not
covered by a durable transaction journal. The history and caches are session-only.

## Architecture

| Module | Responsibility |
| --- | --- |
| `nomi/app.py` | Qt interface, background workers, and reviewed actions |
| `nomi/core.py` | Extraction, Ollama, metadata validation, rename and undo |
| `nomi/routing.py` | File-type templates and automatic local model routing |
| `nomi/naming.py` | Filename rules and presets |
| `nomi/organize.py` | Destination planning, secure moves, directory cleanup |
| `nomi/rename_review.py` | Read-only plan review and confirmation |
| `nomi/session.py` | Bounded session result reuse |
| `nomi/preview.py` | Asynchronous previews and inspected video samples |
| `nomi/local_model.py` | Model catalog, paths, verified downloads |
| `nomi/llama_backend.py` | Local process lifecycle and structured inference |
| `nomi/image_analysis.py`, `nomi/video.py` | Bounded visual input preparation |
| `nomi/ocr.py`, `native/VisionOCR.swift` | Cancellable OCR and native helper |
| `nomi/docx_reader.py`, `nomi/inbox.py` | Bounded DOCX extraction and watched import |

## Licenses and distribution

Nomi is [MIT licensed](../LICENSE). Dependencies and model weights have their own
licenses. The build includes the llama.cpp license and FFmpeg's LGPL notice,
complete matching source archive, and build recipe. FFmpeg 9.0.2 is built with
GPL, nonfree components, and network protocols disabled; it is invoked separately.
Keep that license/source material when redistributing the application.

Public releases contain the Windows single EXE, macOS ARM64 ZIP, MIT license,
and SHA-256 checksums. The Windows executable is unsigned; the Mac app is not
Developer ID signed/notarized. End users do not install Python or runtime tools.

## Build Windows and publish a release

Use native Windows x64, Python 3.14, and MSYS2 UCRT64 GCC/make at build time:

```powershell
python -m pip install -e '.[ocr,build]'
python -m PyInstaller --noconfirm build_support/Nomi-windows.spec
```

The result is `dist/Nomi.exe`. The one-file bootloader extracts bundled files to
a temporary directory at launch. Model weights live in `%LOCALAPPDATA%/Nomi/models`.
FFmpeg is built with a static MinGW runtime; llama.cpp uses the pinned upstream
CPU archive, verified against its SHA-256. Helper console windows are hidden.

The [release workflow](../.github/workflows/release.yml) builds both platforms,
runs the full suite (with documented platform-specific skips), and tests the actual
packages without external runtime tools on PATH. Windows additionally downloads
the pinned Qwen model and performs actual inference, rename and undo in the EXE.
The next version includes native Windows OCR and local-drive folder organization;
optional Tesseract remains configurable. Windows Server 2022 CI coverage
is complemented by a Windows 11 Pro (build 26200) desktop check of the public
0.11.0 EXE: synthetic TXT/Markdown/CSV folder import and preview, Qwen download
and inference, cancellation/resume, confirmation before rename, undo with original
paths and SHA-256 hashes, settings navigation, column resizing, and graceful exit.
Windows 10, image/video inference and external Ollama were not exercised in that
desktop check. The 0.11.0 Windows hint incorrectly said “Mac”; the next version uses
platform-neutral wording.

Dispatch **Release packages** with `publish=false` to validate without publication.
With `publish=true`, both checked assets are combined into a public release whose
tag is derived from `pyproject.toml` and points to the tested commit. Existing
release tags fail rather than being overwritten. Update the version, release notes,
changelog and download links together before dispatching. Never publish models,
production documents, local preferences, or credentials.

## Keeping documentation current

User-facing functionality belongs in the README, first-use guide, settings guide,
and FAQ. Technical details belong here. Keep the [English changelog](../CHANGELOG.md)
updated for application versions; documentation-only changes can be listed under
Unreleased without increasing the application version. Verify download links and
platform requirements against the actual artifact before making support claims.


## Interface translations

`nomi/locales/translations.json` is the central catalog. German source messages are
stable keys; the English locale supplies translations, and German falls back to
its source keys. New English platform errors have German entries. Add another
locale with a native display name and a `messages` mapping; the settings selector
discovers it automatically. `nomi.i18n.tr()` translates only application messages,
never user paths, document text or AI metadata. Keep all template field identifiers
and format placeholders intact. Language is stored separately from analysis
settings and takes effect on restart. Qt's matching translation catalog localizes
standard dialog buttons. Tests cover labels, persisted preferences and placeholders.

## Windows organization safety

The Windows path guard opens every ancestor with OPEN_REPARSE_POINT and denies
FILE_SHARE_DELETE. This rejects junctions and pins directories during each move.
A source handle denies write/delete sharing. An atomic hard link reserves the
destination without replacing an existing entry; the source link is then removed
by handle using SetFileInformationByHandle. There is no copy or overwrite fallback. Undo
uses the same primitive; cleanup deletes only matching empty created directories
by handle. Native Windows tests exercise collision, junction, parent replacement,
rollback, restoration and empty-folder cleanup. Unsupported filesystems fail
without weakening these checks.
