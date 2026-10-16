# Settings

Open settings using the gear button or the application menu. Settings are saved
locally. Close the settings dialog to return to your files.

## General

**Language**: German or English, applied after restarting
Nomi. This controls interface text, not document contents, model output or OCR
languages. Naming templates retain their existing field identifiers:

| Field | Meaning |
| --- | --- |
| `{datum}` | Document date |
| `{absender}` | Sender |
| `{empfaenger}` | Recipient |
| `{dokumenttyp}` | Document type |
| `{titel}` | Descriptive title |
| `{kennung}` | Reference or document number |

Example: `{datum}_{absender}_{dokumenttyp}`. Separate templates are available for
documents, images and videos. Presets are editable. Choose spaces or underscores,
letter case, maximum length and optional German umlaut replacement. Windows/NAS
compatibility removes reserved names and unsafe characters.

## AI

Choose local llama.cpp or an existing Ollama server. Local runtime tools are
included; model weights are downloaded separately and verified before use.
Automatic selection uses Qwen or Mistral for documents and SmolVLM2 for images and
videos. Custom GGUF models require turning off automatic selection. Image-capable
GGUF models may also require a matching projector file.

Load at startup uses an existing model. Missing models download when analysis
starts or when you explicitly choose download. Manage installed models to load,
unload or move an unused Nomi-managed model to the operating system's Trash.
External model files are not deleted.

For Ollama, enter the server's HTTP(S) address, refresh its model list and choose
a model. Use a vision-capable model for visual analysis. The timeout bounds each
request. A remote server or upstream cloud router receives the selected content.

## Video and images

Video frame count ranges from 1 to 12. More frames improve coverage but require
more time and memory. A separate timeout limits frame extraction. FFmpeg is
included. Audio is not analyzed; sampled frames may miss events between samples.

Images support automatic local vision, explicit vision or text-only OCR.
Use `{titel}` for descriptive image names. Original images are never rewritten.

## Text recognition

Enable OCR for scanned PDFs and PNG/JPEG scans. Automatic selection uses Apple
Vision on macOS and native Windows OCR on Windows. No
separate OCR application is required. Windows recognition languages depend on
installed Windows OCR language packs; missing languages produce a clear error.
For mixed languages, enter e.g. `deu+eng`. Windows uses available requested
recognizers. UI language and OCR language are independent.

Tesseract remains an optional alternative: install it separately and configure
its executable and language data. Source installations also need the OCR extras.

## Inbox folder

Watch one folder, optionally including subfolders. Stable supported files are
added to the table. Watching never starts analysis or renaming automatically.

## Organize

Choose an existing local destination folder and an optional relative subfolder
template, such as `{jahr}/{dokumenttyp}`. `{jahr}` means year and `{monat}` means
month. Missing dates use `Ohne_Datum`; other missing values use `Unsortiert`.
These folder names remain stable across interface languages.

Files move only after confirming the review dialog. Source and destination must
be on the same filesystem/drive. Symbolic links and Windows junctions are rejected.
The Windows implementation supports local drives; network shares are
rejected. Undo restores original locations and removes only unchanged empty
folders created by the operation.
