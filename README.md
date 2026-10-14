# Nomi

**Jede Datei verdient einen Namen.**

Nomi liest Dokumentinhalte mit einem konfigurierbaren Ollama-Backend und schlägt verständliche Dateinamen vor. Die Desktop-App verwendet Python und PySide6. Dateien werden ausschließlich nach einem expliziten Klick umbenannt.

## Starten

Python 3.11–3.14 installieren, anschließend im Projektordner:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m nomi
```

Windows (PowerShell):

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m nomi
```

## Verwendung

1. Ollama-Adresse eintragen, etwa `http://localhost:11434` oder die Adresse eines LAN-Servers. Der tatsächliche Port deines Routers muss bekannt sein; Nomi errät ihn nicht.
2. **Modelle laden** anklicken oder einen vorhandenen Modellnamen eingeben. Unterstützt wird die native Ollama-API `/api/tags` und `/api/chat`, einschließlich strukturierter JSON-Ausgaben.
3. Dateien/Ordner hineinziehen oder über den Dateidialog auswählen. Unterordner sind optional. Symbolische Links werden nicht importiert.
4. Ausgewählte Dateien analysieren. Namensvorschläge prüfen, bearbeiten und unerwünschte Dateien per Checkbox abwählen.
5. **Auswahl umbenennen**. Umbenennungsaktionen können während derselben Sitzung schrittweise rückgängig gemacht werden.

Schema-Felder: `{datum}`, `{absender}`, `{dokumenttyp}`, `{titel}`, `{empfaenger}`, `{kennung}`.

- Standard: `{datum}_{absender}_{dokumenttyp}`
- Mit Rechnungsnummer/anderem belegtem Kennzeichen: `{datum}_{absender}_{dokumenttyp}_{kennung}`
- Mit Empfänger/Zweck: `{datum}_{absender}_{dokumenttyp}_{empfaenger}_{titel}`

Unbekannte Angaben und erkannte Platzhalter bleiben leer. Die Originalendung bleibt erhalten. Deutsche Datumsangaben werden in `YYYY-MM-DD` umgewandelt. Ein vorgeschlagenes Datum muss als vollständiges Datum im übermittelten Textausschnitt belegt sein; erkennbare Vertragsbeginn-/Zeitraumdaten werden weggelassen und im Status angezeigt. Diese konservative Prüfung kann auch ein korrektes Datum weglassen und ersetzt keine fachliche Kontrolle.

Bei bereits belegten oder im Analyseauftrag mehrfach vorgeschlagenen Namen ergänzt Nomi sichtbare Nummern wie `_2`. Vorschläge werden nur innerhalb desselben Analyseauftrags reserviert; manuelle Änderungen und Auswahländerungen werden zusätzlich auf Konflikte geprüft. Beim tatsächlichen Umbenennen erfolgt nochmals die verbindliche Konfliktprüfung. Nummern unterscheiden Dateien, bestätigen aber nicht, ob Inhalte identisch sind.

## Optionale OCR mit Tesseract

OCR ist standardmäßig aus. Aktiviere **OCR für gescannte PDF-Seiten** für Bild-PDFs oder gemischte Dokumente. Nur Seiten mit weniger als 30 extrahierten Buchstaben/Ziffern werden zusätzlich erkannt. Die Original-PDF bleibt unverändert; es wird keine durchsuchbare PDF erzeugt. Erfasster Text wird wie normaler PDF-Text an das konfigurierte Backend gesendet.

Installation der optionalen Python-Bibliotheken in der Projektumgebung:

```sh
.venv/bin/python -m pip install -e '.[ocr]'
```

Tesseract wird zusätzlich als Systemprogramm benötigt. Auf macOS:

```sh
brew install tesseract tesseract-lang
```

Auf Debian/Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng`. Unter Windows Tesseract separat installieren, danach in Nomi den vollständigen Programmpfad (z.B. `C:\Program Files\Tesseract-OCR\tesseract.exe`) eintragen. In PowerShell: `.\.venv\Scripts\python.exe -m pip install -e ".[ocr]"`. Windows ist noch nicht praktisch geprüft.

OCR-Sprache: standardmäßig `deu+eng`; die entsprechenden Sprachdaten müssen installiert sein (`tesseract --list-langs`). Im Feld **Programm** kann ein vollständiger Tesseract-Pfad angegeben werden, z.B. `/opt/homebrew/bin/tesseract`. Fehler bei fehlender Installation oder fehlenden Sprachdaten erscheinen in der betroffenen Tabellenzeile.

Seiten werden einzeln mit bis zu 300 dpi und maximal 12 Megapixeln gerendert. Temporäre Bilder werden nach jeder Seite auch bei Abbruch/Fehler entfernt. Das eingestellte Timeout gilt je OCR-Seite sowie für die HTTP-Anfrage, nicht für das gesamte Dokument. Abbruch beendet einen laufenden Tesseract-Prozess; während des Renderns wirkt er nach der aktuellen Renderoperation. OCR-Qualität hängt von Scan, Schrift und Sprache ab; Seiten mit vorhandenem, aber fehlerhaftem Text können unter Umständen nicht als OCR-Kandidaten erkannt werden.

Technische Referenzen: [Tesseract-CLI](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [PDFium-Python-API](https://pypdfium2.readthedocs.io/en/stable/python_api.html).

## Grenzen der Version 0.2

- Text-PDFs, optional gescannte PDF-Seiten via Tesseract, UTF-8/Windows-1252-Texte, Markdown und CSV; keine allgemeine Bildanalyse oder DOCX-Verarbeitung.
- Pro Dokument maximal 16.000 Zeichen und bei PDFs die ersten 20 Seiten. Angaben außerhalb dieses Ausschnitts werden nicht berücksichtigt. Begrenzte PDF-/Textauszüge werden in der Tabelle kenntlich gemacht.
- Jede Datei wird einzeln analysiert; die UI bleibt dabei bedienbar. Abbruch wirkt nach der laufenden Anfrage, deren Timeout konfigurierbar ist.
- Die KI kann sich irren. Vorschläge müssen geprüft werden. Datumsprüfung und Prompt reduzieren Fehler; Absender, Dokumenttyp, Titel und Kennzeichen können weiterhin falsch zugeordnet werden. Sammelakten und mehrere Datumsangaben bleiben besonders prüfpflichtig.
- Ausgewählte Umbenennungen werden vorher auf Konflikte geprüft. Bestehende Dateien werden nicht überschrieben. Für die Umbenennung wird ein Hardlink mit anschließendem Entfernen des alten Verzeichniseintrags verwendet. Dateisysteme ohne Hardlink-Unterstützung (z. B. manche USB-/Netzlaufwerke) werden mit einem Fehler abgewiesen.
- Eine Fehlersituation führt zu einem bestmöglichen Rollback. Bei unvollständiger Rückabwicklung werden die verbleibenden Umbenennungen gemeldet und in der Sitzungshistorie zur Wiederherstellung behalten. Gleichzeitige externe Dateiänderungen und Stromausfälle sind nicht transaktional abgesichert.
- Rückgängig verweigert die Aktion bei veränderten Dateien oder neu belegten Originalnamen. Historie ist derzeit nur im Arbeitsspeicher vorhanden.
- Noch keine signierten Installer, automatische Updates oder integrierte llama.cpp-Runtime. macOS wurde in der Entwicklungsumgebung getestet; Windows erfordert noch einen eigenen Plattformtest.

## Datenschutz

Dokumenttext wird an die eingestellte Backend-Adresse gesendet. Ein Ollama-kompatibler Router kann Cloud-Fallback verwenden. Nomi kann dieses Routing nicht erkennen. Es gibt keinen automatischen Cloud-Fallback in Nomi selbst. Einstellungen werden lokal über Qt gespeichert; Dokumentinhalte werden nicht protokolliert.

## Architektur

- `nomi/core.py`: Extraktion, Backend-Protokoll, Ollama-Anbindung, Namensvalidierung und Umbenennung.
- `nomi/app.py`: PySide6-Oberfläche und sequenzieller Analyse-Worker.
- `nomi/ocr.py`: optionale PDFium-Rasterung und abbrechbare Tesseract-Prozesse.
- Die Provider-Grenze ermöglicht später eine lokale llama.cpp-Implementierung.

## Tests

```sh
python -m unittest discover -s tests -v
```

Synthetische Testdaten werden nur in temporären Ordnern erzeugt. Keine produktiven Dokumente sind Bestandteil des Projekts.

## Verifizierter Entwicklungsstand (14.10.2026)

- Installation in der vorhandenen `.venv` mit Python 3.14.8, PySide6 6.10.3 und pypdf 6.20.1 abgeschlossen; `pip check` erfolgreich. Alle 34 Tests bestehen; einschließlich echter Tesseract-OCR, OCR im Qt-Worker, Prozessabbruch/-timeout, Datumsbelegung, Namenssuffixen und manuellen Konflikten. OCR-Integrationstests werden ohne optionale Bibliotheken bzw. Tesseract übersprungen.
- PySide6 ist auf `>=6.9,<6.11` begrenzt: Mit 6.12.0 trat beim Schließen nach nativer Tabellenbearbeitung ein QObject-Absturz auf. Derselbe Ablauf inklusive Schließen wurde mit 6.10.3 erfolgreich wiederholt (Exit-Code 0).
- Core-, HTTP-Vertrags- und Qt-Tests laufen mit synthetischen Dokumenten. Sie prüfen unter anderem Konflikte, bestehende Zieldateien, doppelte Quellen, Rollback und teilweise fehlgeschlagene Rückabwicklungen, veränderte Dateien, Import, Auswahl, Analyse, Modellladen und Abbruch.
- Die macOS-Oberfläche wurde gestartet und visuell geprüft; nativer Dateiimport, manuelles Bearbeiten, Umbenennen und Rückgängig wurden am Testdokument bedient und überprüft. Drag-and-drop wird zusätzlich über Qt-Ereignisse getestet.
- Die Ollama-API wurde zusätzlich mit einem echten LAN-Ollama und `mistral:latest` geprüft: strukturierte Antworten und vollständige Extraktion/Generierung/Umbenennung/Rückgängig für synthetische Text-PDFs, TXT, Markdown und CSV erfolgreich. Erster Aufruf etwa 13 s, Folgeaufrufe etwa 0,5–0,7 s (kleiner Testdatensatz, keine allgemeine Leistungsgarantie).
- Der echte Qt-Worker wurde gegen dieses Backend geprüft: Modellliste laden, Abbruch nach laufender Anfrage bei weiterhin reagierender Oberfläche, ungültiges Modell und nicht erreichbare Adresse. Ein HTTP-Timeout wurde zusätzlich mit künstlich verkürzter Frist ausgelöst.
- Nachprüfung mit 28 privaten lokalen PDFs: 28 formal gültige Vorschläge, davon vier Dokumente mit OCR; keine Originale verändert (SHA-256-Prüfung). Sieben Datumsvorschläge wurden konservativ weggelassen. Private Dokumente, Inhalte und Auswertungen sind nicht Bestandteil dieses Repositorys.
- macOS: Tesseract 5.5.3 mit deu/eng, PDFium und Pillow praktisch geprüft. Andere Modelle, schwierige Scans und Windows benötigen weitere Tests. Laufende HTTP-Anfragen enden bei Abbruch weiterhin erst mit Antwort oder Timeout.

## Lizenz

MIT — siehe [LICENSE](LICENSE). Die Lizenz gilt für Nomi; Abhängigkeiten und verwendete Modelle haben eigene Lizenzbedingungen.

## macOS-App bauen (Version 0.2.1)

```sh
.venv/bin/python -m pip install -e '.[ocr,build]'
.venv/bin/python -m PyInstaller --noconfirm build_support/Nomi.spec
```

Die Anwendung liegt anschließend unter `dist/Nomi.app` und lässt sich per Doppelklick starten. Python, Qt und die OCR-Python-Bibliotheken sind enthalten; Tesseract und Sprachdaten werden weiterhin separat benötigt. Beim Finder-Start werden auch die üblichen Homebrew-Pfade nach Tesseract durchsucht. Für einen Ollama-Server im LAN benötigt Nomi die macOS-Berechtigung für das lokale Netzwerk. Die App erklärt diesen Zugriff im Systemdialog; gegebenenfalls unter Systemeinstellungen → Datenschutz & Sicherheit → Lokales Netzwerk für Nomi erlauben. [Apple-Dokumentation](https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy).

Ein lokaler Build übernimmt Prozessorarchitektur und macOS-Version des Build-Rechners als konservative Mindestanforderung. Der Entwicklungsbuild wurde auf Apple Silicon/macOS 27 gebaut und ist kein getesteter universeller Intel-/ARM-Build. Für ältere Systeme auf einem passenden Build-Rechner bauen. Die GitHub-Variante wird auf dem im Workflow angegebenen macOS-Runner erstellt.

Das Bundle ist lokal ad hoc signiert, jedoch nicht mit einer Apple Developer ID signiert oder notarisiert. Es ist derzeit ein Entwicklungsbuild, kein fertiger öffentlicher Installer. Ein automatischer Upload zu GitHub Releases findet nicht statt.

Offline-Selbsttest für das gebaute Bundle (nur temporäre synthetische Dateien, keine Netzwerkaufrufe oder Änderungen an persönlichen Einstellungen):

```sh
dist/Nomi.app/Contents/MacOS/Nomi --self-test
```

Der Selbsttest prüft echte Tesseract-OCR, Qt, Umbenennen und Rückgängig. Tesseract mit englischen Sprachdaten muss installiert sein. Er steht auch unter `python -m nomi --self-test` zur Verfügung.

## Automatische Prüfungen

GitHub Actions prüft Pull Requests und Pushes mit Python 3.11/3.14 auf Ubuntu sowie Python 3.14 auf macOS. OCR und der Offline-Selbsttest gehören dazu. Nach erfolgreichen Tests wird ein macOS-Bundle gebaut, mit reduziertem Finder-ähnlichem Suchpfad geprüft und als ZIP-Artefakt am Workflow-Lauf gespeichert. Die Action-Versionen sind auf Commit-Hashes fixiert. Workflow und Build sind unter `.github/workflows/tests.yml` bzw. `build_support/Nomi.spec` beschrieben.
