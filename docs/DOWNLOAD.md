# Download Nomi

[**Open the latest public release**](https://github.com/mbosch81/nomi/releases/latest)

Downloads are public; no GitHub account or installer is required.

| Computer | Package | Requirements |
| --- | --- | --- |
| Windows | `Nomi-<version>-windows-x64.exe` | Windows 10/11, x64 CPU |
| Apple Silicon Mac | `Nomi-<version>-macos-arm64.zip` | macOS 14.8 or newer |

The Windows EXE extracts runtime files into a temporary folder when launched.
The Mac ZIP contains Nomi.app. There are currently no Intel Mac, Windows ARM or
Linux binary packages. Python, llama.cpp and FFmpeg are included; Ollama is optional.

## Version 0.12.0

German and English interface languages are available on both platforms. Windows
now includes native scan OCR and safe local folder organization with undo. OCR
uses installed Windows recognition languages; organization requires a local drive
with hard-link support, such as NTFS. Windows network shares are not supported.
Older 0.11.0 Windows downloads do not contain these features.

The 0.12.0 Windows implementation was checked on Windows 11 Pro with the actual
single EXE: scanned PDF and PNG/JPEG OCR, destination-folder organization and undo,
and the German-to-English language switch after restarting. Automated package
checks also cover local Qwen inference and confirm that external runtime tools
are unnecessary. The Mac package is checked with native Apple Vision OCR.

The public 0.11.0 EXE was checked on Windows 11 Pro using synthetic documents:
import, preview, local model download/inference, cancellation/resume, confirmed
renaming, checksum-verified undo, settings, column resizing and shutdown. Windows
10 was not manually tested. Automated checks additionally exercise the packages.

## Models and storage

Models download separately: approximately 2.5 GB for Qwen, 4.4 GB for Mistral and
1.7 GB for SmolVLM2 with its projector. Keep extra space for the app, temporary
extraction and downloads. Local inference speed depends on CPU, memory and model.

## Signing and checksums

The Windows executable is unsigned. The Mac app is ad hoc signed, without Apple
Developer ID signing or notarization. Your operating system may display a warning.
Download only from this project's release page. Each release provides SHA256SUMS.txt,
LICENSE.txt and per-platform third-party notices archives.

Try copies of your files first. Nomi requires explicit confirmation before changes
and does not overwrite existing destinations.
