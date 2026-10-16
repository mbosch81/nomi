# Changelog

Notable changes to Nomi, listed from newest to oldest.

This history was reconstructed from Git commits and project documentation. Dates
identify the first commit declaring each version, rather than a separate public
release date. Features developed across several commits are grouped under the
version in which they were completed. Documentation-only updates do not change
the application version.

## [Unreleased]

## [0.11.0] - 2026-10-16

### Added

- Public release packages: a standalone Windows x64 single EXE and an Apple Silicon
  macOS app ZIP, without installers, plus MIT license and SHA-256 checksums.
- Verified pinned Windows CPU llama.cpp runtime and a source-built minimal LGPL
  FFmpeg runtime, embedded in the executable; no external runtime installation.
- A manually dispatched release pipeline that publishes only after both platform
  tests and packaged checks pass, including actual Qwen inference on Windows.
- Explicit diagnostics output for the windowed executable during CI smoke checks.

### Changed

- Windows helper processes no longer open console windows.
- Windows preview disables POSIX-only folder organization and explains that scan
  OCR is not bundled; optional existing Tesseract remains available.
- Platform-specific test fixtures and diagnostics now distinguish unsupported
  Windows features from verified portable rename, undo, preview, and inference.

### Fixed

- Detect rapid same-size rewrites of small documents in session reuse, including
  Windows filesystems that coalesce modification timestamps.

### Documentation

- Replaced the developer-focused README with a user-facing product overview,
  concrete use cases, examples, and the verified Mac test-download path.
- Added dedicated download, first-use, settings, and troubleshooting guides.
- Moved technical setup, architecture, testing, and build details into a contributor guide.
- Corrected outdated model-selection, image/video analysis, platform, and version claims.
- Added an accessible workflow illustration and included linked guides in future app bundles.

## [0.10.0] - 2026-10-16

### Added

- Configurable filename length, spaces or underscores, letter case, German umlaut
  transliteration, and Windows/NAS-compatible name protection.
- Editable presets for invoices, contracts, general documents, photos, and videos,
  with live synthetic filename examples.
- Optional organization into a chosen destination directory using folder templates
  such as `{jahr}/{dokumenttyp}` or `{jahr}/{monat}/{absender}`.
- Full source and destination paths in the confirmation dialog before moving files.
- Reversible folder creation: undo restores original names and locations and removes
  only directories created by the operation that are still empty and unchanged.
- Safety tests for collisions, symlinks, cross-device rejection, partial failures,
  recovery, and metadata retention for larger batches.

### Changed

- Conflict suffixes respect the configured filename length and destination directory,
  including collisions between files imported from different source directories.
- Analysis metadata remains available for every visible row, independently of the
  bounded thumbnail and session caches.

### Limitations

- Organization currently supports macOS/Linux and moves within the same filesystem.
  There is no automatic copy-and-delete fallback for other filesystems or drives.
- Missing dates use `Ohne_Datum`; other missing folder fields use `Unsortiert`.
  Dates are not inferred from the current year.

## [0.9.0] - 2026-10-16

### Added

- Automatic local model selection: Qwen or Mistral for documents and OCR text,
  SmolVLM2 for images and videos, with background loading and progress reporting.
- Separate naming templates for documents, images, and videos.
- Targeted reanalysis of checked files with an optional per-run naming instruction.
- Selectable previews of the exact video frames submitted to the model, with timestamps.
- Batch rename review showing original and proposed names, conflicts, missing
  metadata, unchanged files, and sources modified since analysis.
- Bounded session-only result reuse, preserving manual corrections when unchanged
  files are reimported; explicit reanalysis bypasses the cache.

### Changed

- Rename confirmation applies only to the reviewed selection, excluding files
  imported later by the watched inbox.
- Automatic startup loading uses the selected text model while preserving the
  configured manual GGUF path. Only one local model remains loaded at a time.

### Limitations

- Automatic model routing applies to llama.cpp. Ollama continues to use the
  configured server model.

## [0.8.1] - 2026-10-16

### Added

- Direct visual analysis of PNG and JPEG images, including scenes and objects
  without readable text.
- A dedicated Images settings category with automatic, explicit vision, and
  OCR-only modes.
- In-memory image preparation with orientation handling, a white background for
  transparency, bounded dimensions, and file-size limits.

### Changed

- Local vision models can analyze images without enabling OCR. Ollama vision can
  be selected explicitly with a compatible server model.
- Original image contents, metadata, and filename extensions remain unchanged.

## [0.8.0] - 2026-10-16

### Added

- Video import, sampled-frame analysis, a still-image preview, and existing rename
  and undo workflows for supported video files.
- Configurable sampling of 1–12 frames per video, defaulting to 5, with an extraction
  timeout and cancellation.
- SmolVLM2 2.2B and its vision projector in the verified local model download catalog.
- Bundled FFmpeg and ffprobe, built from pinned source without network protocols,
  GPL, or nonfree components; no separate end-user installation is required.
- FFmpeg source, build configuration, and LGPL license material in the application bundle.
- Settings navigation for General, AI, Video, OCR, and the watched inbox.

### Fixed

- Preview worker cleanup when closing the application during loading.
- Apple Vision initialization stalls through explicit CPU execution.

### Limitations

- Video analysis uses visual samples only; audio and complete narrative analysis
  are not supported.

## [0.7.1] - 2026-10-16

### Added

- User-resizable table columns, double-click sizing to content, and persisted column widths.

## [0.7.0] - 2026-10-15

### Added

- Local model management showing installed GGUF files, sizes, and load state,
  with load, unload, and move-to-trash actions.
- An optional watched inbox with recursive scanning, file-stability checks, and
  duplicate-import protection; importing does not automatically analyze or rename files.
- DOCX import, bounded text extraction, analysis, and a text-only preview without
  requiring Microsoft Word.

### Fixed

- Native model manager stability on macOS by replacing its table with a list.
- Synchronization between model selection, the configured path, and downloaded model metadata.
- Application bundle version metadata now comes from `pyproject.toml`.

## [0.6.0] - 2026-10-15

### Added

- Background document previews alongside the file table.
- PDF page navigation and zoom, image previews, and bounded text previews.
- A preview-side filename editor synchronized with the table.
- Protection against stale preview results during rapid file selection changes.

## [0.5.0] - 2026-10-15

### Added

- PNG, JPG, and JPEG document scan import and OCR in the analysis worker.
- Image orientation correction, transparency handling, and bounded image preparation.
- Image OCR coverage in packaged offline and local-model integration checks.

## [0.4.3] - 2026-10-14

### Added

- Mistral 7B Instruct v0.3 as an alternative to the default Qwen model, with pinned
  download revision, size validation, and SHA-256 verification.

## [0.4.2] - 2026-10-14

### Added

- An accessible gear button in the main window for opening settings.

## [0.4.1] - 2026-10-14

### Changed

- Configuration controls moved out of the main window into a dedicated settings
  dialog, accessible through the native menu and preferences shortcut.

## [0.4.0] - 2026-10-14

### Added

- A bundled llama.cpp runtime with a managed local server and Qwen3 4B as the default model.
- Verified GGUF downloads, model loading at startup, and background loading with cancellation.
- Loopback-only server access using an ephemeral session key, local proxy bypass,
  and managed process shutdown without an automatic cloud fallback.

### Fixed

- UI responsiveness tests now tolerate macOS timer scheduling variation.

## [0.3.0] - 2026-10-14

### Added

- Bundled Apple Vision OCR as the default macOS OCR backend, without a separate
  Tesseract installation.
- OCR backend selection and language validation, while retaining optional Tesseract support.

## [0.2.1] - 2026-10-14

### Added

- A macOS application bundle build, an offline application smoke check, and CI.
- A macOS local-network usage declaration for configured Ollama connections.

## [0.2.0] - 2026-10-14

### Added

- Optional Tesseract OCR for scanned PDF pages, including OCR settings,
  cancellation, timeout handling, and cleanup.
- More conservative document naming with date grounding and visible quality warnings.
- Additional OCR, naming-quality, and UI worker tests.

## [0.1.0] - 2026-10-14

### Added

- Initial Python/PySide6 desktop application with configurable Ollama analysis.
- File and folder import through drag-and-drop or dialogs, with optional subdirectories.
- Support for text PDFs, TXT, Markdown, and CSV.
- Checkable file rows, editable naming suggestions, configurable naming templates,
  background analysis, and cancellation.
- Explicit batch renaming with no-overwrite checks, best-effort rollback, and session undo.
- MIT licensing, project documentation, and synthetic core, HTTP, and Qt tests.

[Unreleased]: https://github.com/mbosch81/nomi/compare/v0.11.0...HEAD
[0.11.0]: https://github.com/mbosch81/nomi/releases/tag/v0.11.0
[0.10.0]: https://github.com/mbosch81/nomi/compare/e11420b...f98fe82
[0.9.0]: https://github.com/mbosch81/nomi/compare/91aa37c...e11420b
[0.8.1]: https://github.com/mbosch81/nomi/compare/1b8dd6c...91aa37c
[0.8.0]: https://github.com/mbosch81/nomi/compare/3c5b1cb...1b8dd6c
[0.7.1]: https://github.com/mbosch81/nomi/compare/86d798b...3c5b1cb
[0.7.0]: https://github.com/mbosch81/nomi/compare/8db7301...86d798b
[0.6.0]: https://github.com/mbosch81/nomi/compare/d6753ce...8db7301
[0.5.0]: https://github.com/mbosch81/nomi/compare/04c83d1...d6753ce
[0.4.3]: https://github.com/mbosch81/nomi/compare/cb2ad34...04c83d1
[0.4.2]: https://github.com/mbosch81/nomi/compare/4f9b0c3...cb2ad34
[0.4.1]: https://github.com/mbosch81/nomi/compare/56cc577...4f9b0c3
[0.4.0]: https://github.com/mbosch81/nomi/compare/756e70d...56cc577
[0.3.0]: https://github.com/mbosch81/nomi/compare/a06ce39...756e70d
[0.2.1]: https://github.com/mbosch81/nomi/compare/4923119...a06ce39
[0.2.0]: https://github.com/mbosch81/nomi/compare/65f7aad...4923119
[0.1.0]: https://github.com/mbosch81/nomi/commit/65f7aad
