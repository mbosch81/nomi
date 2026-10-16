# Nomi herunterladen

[← Zur Produktübersicht](../README.md) · [Erste Schritte](START.md)

## Direkte Downloads ohne Anmeldung

[**Alle öffentlichen Releases →**](https://github.com/mbosch81/nomi/releases/latest)

| Dein Computer | Download | Starten |
| --- | --- | --- |
| Windows 10/11, 64 Bit (x64) | [Einzelne EXE](https://github.com/mbosch81/nomi/releases/download/v0.11.0/Nomi-0.11.0-windows-x64.exe) | Speichern und doppelklicken; kein Installer |
| Mac mit Apple Silicon, macOS 14.8 oder neuer | [Mac-App als ZIP](https://github.com/mbosch81/nomi/releases/download/v0.11.0/Nomi-0.11.0-macos-arm64.zip) | Entpacken, **Nomi.app** nach **Programme** ziehen und öffnen |

Die Pakete enthalten Python, Qt, llama.cpp und FFmpeg. Du brauchst dafür keine
separaten Installationen. Die Windows-EXE entpackt ihre Bestandteile beim Start
vorübergehend ins Temp-Verzeichnis. Die Mac-App ist ein einzelnes App-Paket.

Die ZIP-Dateien **Source code** enthalten den Quellcode. Wähle für die fertige App
die oben verlinkte EXE beziehungsweise das Mac-ZIP. **SHA256SUMS.txt** im Release
enthält Prüfsummen; **LICENSE.txt** enthält Nomis MIT-Lizenz.

## Windows: erste technische Vorschau

Die EXE enthält die lokale CPU-Runtime. Text-PDFs, DOCX, TXT, Markdown und CSV
können direkt analysiert werden. Bilder und Videos lassen sich mit dem
Vision-Modell beschreiben. Umbenennen und Rückgängig benötigen ein Dateisystem mit
Hardlink-Unterstützung, zum Beispiel NTFS. Bei fehlender Unterstützung bricht Nomi
mit einem Fehler ab, ohne auf überschreibendes Umbenennen auszuweichen.

Scan-OCR wird unter Windows noch nicht mitgeliefert; optional lässt sich ein bereits
vorhandenes Tesseract verwenden. Einsortieren in andere Ordner ist deaktiviert.
Die EXE wird automatisiert auf Windows Server 2022 einschließlich echter lokaler
Qwen-Inferenz geprüft. Eine manuelle Prüfung auf einem privaten Windows-10/11-PC
steht noch aus. Windows ARM wird nicht als eigenes Paket angeboten.

## Mac: Apple Silicon

Die Mac-App enthält die Texterkennung über Apple Vision. Sie benötigt keine
separate Installation von Tesseract. Das veröffentlichte ARM64-Paket wird auf
macOS 14 gebaut und benötigt macOS 14.8 oder neuer. Ein Intel-Mac-Paket gibt es
zurzeit nicht. Lokale Eigenbauten können eine neuere macOS-Version voraussetzen.

## Modelle und Speicher

Beim ersten Einsatz der lokalen KI lädt Nomi die passenden Modelle herunter:
etwa **2,5 GB für Qwen**, für Bilder/Video zusätzlich **1,7 GB für SmolVLM2**.
Mistral mit etwa **4,4 GB** ist optional. Danach funktionieren vorhandene Modelle
ohne Internet. Der Arbeitsspeicherbedarf liegt über der Größe der Modelldatei.

## Sicherheitsmeldung beim Öffnen

Die Windows-EXE ist noch nicht digital signiert; Windows kann deshalb eine
SmartScreen-Meldung anzeigen. Die Mac-App ist ad hoc signiert, aber nicht mit einer
Apple Developer ID signiert oder notarisiert. macOS kann das Öffnen einschränken.
Verwende ausschließlich Dateien aus dem offiziellen Nomi-Repository und beachte
[Apples Hinweise zum Öffnen von Apps](https://support.apple.com/de-de/102445).

Starte mit wenigen Testkopien und prüfe die KI-Vorschläge. Lies anschließend die
[ersten Schritte](START.md). Für Linux stehen derzeit nur eigene Builds zur Verfügung.
