# Frequently asked questions

## Does Nomi change files automatically?

No. Analysis creates proposals. You review the complete plan and confirm changes.
A watched inbox folder only imports files into the list.

## Can I undo changes?

Yes, during the current session. Nomi checks that renamed files are unchanged and
that original destinations are free. Undo never overwrites another file. Keep the
session open until you are satisfied with the changes.

## Do I need Ollama, FFmpeg or an OCR installation?

The downloadable app includes llama.cpp and FFmpeg. Ollama is optional. macOS OCR
uses Apple Vision. Windows uses the built-in Windows OCR engine;
available languages depend on installed Windows language packs. Older 0.11.0 Windows downloads require optional Tesseract for scan OCR.

## Does my content leave my computer?

Local llama.cpp analysis and system OCR run locally. Model weights initially
download from Hugging Face. With Ollama, document excerpts and images/video samples
are sent to your configured server. An upstream router may forward them elsewhere.

## Why are some fields missing or names incorrect?

AI can misread, omit or invent information. Nomi flags missing fields and checks
whether a proposed document date appears in the source text. Review all proposals.
Use reanalysis instructions or edit a proposal directly.

## Does video analysis listen to audio?

No. It samples a configurable number of frames. It does not transcribe speech or
analyze every frame. Use a vision-capable model.

## Can I switch the interface language?

German and English are available under General settings. Restart Nomi to
apply the choice. Template field identifiers, existing filenames and document
contents stay unchanged. OCR recognition language is configured separately.

## Why does organization refuse a location?

Source and destination must be on the same filesystem/drive. Nomi rejects
symbolic links, Windows junctions, occupied destinations and unsafe paths. Windows
organization uses local drives; network shares are unsupported. Older 0.11.0 Windows downloads do not provide organization.

## Where are models stored?

macOS: `~/Library/Application Support/Nomi/models`. Windows:
`%LOCALAPPDATA%\Nomi\models`. Source installations on Linux use the XDG data
folder. Manage installed models from AI settings; only unused Nomi-managed models
can be moved to Trash.

## What formats are supported?

PDF, DOCX, TXT, Markdown, CSV, PNG and JPEG, plus common video containers such as
MP4, MOV, MKV, WebM and AVI. Support depends on readable content and bundled codecs.
DOCX extraction reads document text, not an exact page layout. PDF analysis reads
up to 20 pages and sends up to 16,000 characters to the model. OCR and previews
have additional resource limits to keep the application responsive.
