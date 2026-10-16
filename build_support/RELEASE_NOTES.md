# Nomi — every file deserves a name

## Downloads

- **Windows x64:** run the single EXE; no installer or separate Python, llama.cpp,
  Ollama or FFmpeg installation is required.
- **Apple Silicon Mac:** extract the ZIP and open Nomi.app (macOS 14.8 or newer).

Model weights download separately from Hugging Face. Qwen is the default document
model; Mistral is also available. SmolVLM2 handles images and sampled video frames.

## Next version

- Choose German or English in General settings; restart Nomi to apply the language.
- Central translation catalog for additional languages.
- Built-in Windows OCR using the operating system's available recognition languages.
- Safe organization into local destination folders on Windows, with confirmation,
  collision protection, rollback and undo.
- Platform-neutral local-analysis wording and English documentation.

## Limits

Windows OCR languages depend on installed Windows language packs. Windows
organization supports local drives, not network shares. Source and destination
must be on the same filesystem/drive. Symbolic links and junctions are rejected.
Video analysis samples frames and does not transcribe audio. Review AI proposals
before confirming changes; undo is available during the current session.

The Windows EXE is unsigned. The Mac app is ad hoc signed, without Apple Developer
ID signing or notarization. No Intel Mac, Windows ARM or Linux binaries are provided.
The existing 0.11.0 assets retain their original feature limits; these next-version
changes require a new package. See the README and changelog for current status.
