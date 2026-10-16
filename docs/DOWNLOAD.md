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

## Published version and upcoming features

Version 0.11.0 is the current public release. Its Windows preview supports document
analysis and visual image/video analysis but does not bundle scan OCR or folder
organization. The next version adds native Windows OCR, safe local folder
organization and English/German interface selection. These changes are not part
of the existing 0.11.0 downloads. See the release notes for verified behavior.

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
