## Nomi – Jede Datei verdient einen Namen.

Die erste öffentliche Download-Version: Dateien, Bilder und Videos mit lokaler KI verständlich benennen. Vorschläge prüfen und bearbeiten, Änderungen ausdrücklich bestätigen und innerhalb derselben Sitzung rückgängig machen.

### Downloads ohne Installer

- **Windows 10/11, x64: `Nomi-0.11.0-windows-x64.exe`** – einzelne EXE starten. Technische Vorschau; CPU-Ausführung. Keine separate Installation von Python, Ollama, llama.cpp oder FFmpeg erforderlich. Beim Start entpackt sich die Anwendung vorübergehend ins Temp-Verzeichnis.
- **Mac mit Apple Silicon, macOS 14.8 oder neuer: `Nomi-0.11.0-macos-arm64.zip`** – entpacken, `Nomi.app` nach Programme ziehen und öffnen. OCR über Apple Vision ist enthalten.
- **`SHA256SUMS.txt`** enthält die Prüfsummen der Downloads; **`LICENSE.txt`** die MIT-Lizenz von Nomi. Lizenzen und passende FFmpeg-Quellen sind zusätzlich in der Anwendung enthalten. Die optionalen `notices.zip`-Archive enthalten die Drittanbieter-Hinweise und Paketversionen.

KI-Modelle werden getrennt heruntergeladen: etwa 2,5 GB für Qwen, für Bild-/Videoanalyse zusätzlich etwa 1,7 GB. Mistral ist optional. Ein Cloud-Konto ist nicht erforderlich.

### Grenzen dieser Version

- Windows ist eine erste technische Vorschau: Text-PDFs, DOCX, Textdateien sowie Bilder und Videos mit Vision-Modell. Scan-OCR wird dort nicht mitgeliefert; optional kann vorhandenes Tesseract verwendet werden. Einsortieren in andere Ordner ist dort deaktiviert. Umbenennen und Rückgängig funktionieren im ursprünglichen Ordner auf Dateisystemen mit Hardlink-Unterstützung, beispielsweise NTFS.
- Die Windows-EXE ist nicht digital signiert. Die Mac-App ist ad hoc signiert, aber noch nicht mit Apple Developer ID signiert oder notarisiert. Die Betriebssysteme können deshalb Sicherheitsmeldungen anzeigen.
- Keine Pakete für Intel-Macs, Windows ARM oder Linux. Die KI kann falsche Vorschläge machen: zunächst Testkopien verwenden.

Automatische Prüfungen erfolgen mit synthetischen Dateien. Die Windows-EXE wird auf Windows Server 2022 gebaut und mit Qt, PDF/DOCX-/Bild-/Videovorschau, sicherem Umbenennen, Rückgängig und tatsächlicher Qwen-Inferenz geprüft. Eine manuelle Prüfung auf einem privaten Windows-10/11-PC steht noch aus. Die Mac-App wird auf macOS 14 gebaut und einschließlich OCR, Einsortieren und Rückgängig geprüft.

[Erste Schritte](https://github.com/mbosch81/nomi/blob/main/docs/START.md) · [Download-Hilfe](https://github.com/mbosch81/nomi/blob/main/docs/DOWNLOAD.md) · [Changelog](https://github.com/mbosch81/nomi/blob/main/CHANGELOG.md) · [Probleme melden](https://github.com/mbosch81/nomi/issues)
