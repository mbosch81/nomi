# Getting started

## Open Nomi

Download the package for your computer from the
[public releases](https://github.com/mbosch81/nomi/releases/latest).
On Windows, run the EXE. On macOS, extract the ZIP and move Nomi.app to Applications.
There is no installer and no separate Python, Ollama, llama.cpp or FFmpeg setup.
See [download requirements](DOWNLOAD.md) for platform and signing limitations.

## Choose your language and model

Open the gear button. In the next version, **General → Language** offers German and
English. Restart Nomi after changing the language. Recognition languages for OCR
are configured separately.

Under **AI**, keep automatic model selection enabled for the easiest start.
Qwen is the default document model, with Mistral also available. SmolVLM2 handles
images and video frames. Missing model files download when analysis starts;
allow several gigabytes of disk space. Only one local model stays loaded at a time.
An existing Ollama server is optional.

## Import and analyze

Drag files or folders onto the main window, or use **Add files** / **Select folder**.
Enable **Include subfolders** if needed. The supported files appear in the table.

Use the checkboxes to choose what to analyze. **Select all** and **Deselect all**
change the whole selection. Click a row to preview the file. Drag column borders
to resize them, or double-click a border to fit the contents.

Click **Analyze selected**. The window remains responsive. **Cancel** stops new
work; an active model request may finish or reach its configured timeout first.
Completed proposals remain available. Reanalyze selected rows to retry or supply
additional naming instructions.

## Review and rename

Edit a proposal in the table or preview panel. Missing information and conflicts
are shown in the status. Deselect any file you do not want to change.

Click **Rename selected** to open the review dialog. This step leaves files
unchanged. Check every destination and confirm with **Rename now** or
**Confirm changes**. Existing destinations are never overwritten.

**Undo** restores names and locations during the current session. If a file has
been changed or an original name is occupied, Nomi refuses to overwrite it.
Resolve the conflict before retrying. Closing Nomi ends session undo availability.
