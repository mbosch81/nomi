# Nomi

**Jede Datei verdient einen Namen.**

Nomi liest Dokumentinhalte mit lokalem llama.cpp oder einem konfigurierbaren Ollama-Backend und schlägt verständliche Dateinamen vor. Die Desktop-App verwendet Python und PySide6. Dateien werden ausschließlich nach einem expliziten Klick umbenannt.

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

1. **Lokal · llama.cpp** verwenden: in den Einstellungen **Qwen3 4B** oder **Mistral 7B Instruct v0.3** auswählen und **Ausgewähltes Modell herunterladen / laden** anklicken oder eine vorhandene GGUF-Datei auswählen. Danach **Modell laden**; mit **Beim Start laden** lädt Nomi die gewählte Datei künftig automatisch im Hintergrund.
2. Alternativ **Ollama · Server** wählen, Adresse eintragen und **Modelle laden** anklicken oder einen Modellnamen eingeben. Unterstützt werden `/api/tags` und `/api/chat` mit strukturierten JSON-Ausgaben. Der Server-Port muss bekannt sein; Nomi errät ihn nicht.
3. Dateien/Ordner hineinziehen oder über den Dateidialog auswählen. Unterordner sind optional. Symbolische Links werden nicht importiert.
4. Ausgewählte Dateien analysieren. Namensvorschläge prüfen, bearbeiten und unerwünschte Dateien per Checkbox abwählen.
5. **Auswahl umbenennen**. Umbenennungsaktionen können während derselben Sitzung schrittweise rückgängig gemacht werden.

## Lokale KI mit llama.cpp

Die macOS-App enthält eine auf Release **b11622** fixierte llama.cpp-Runtime. Es wird kein separater Ollama- oder llama.cpp-Dienst benötigt. Nomi startet einen eigenen `llama-server` auf `127.0.0.1` mit freiem Port und zufälligem Sitzungsschlüssel; Schlüssel werden weder gespeichert noch protokolliert. Lokale HTTP-Anfragen umgehen System-Proxys. Es gibt keinen automatischen Wechsel zu Ollama oder einem Cloud-Anbieter. Beim normalen Schließen oder Wechsel zu Ollama beendet Nomi nur den selbst gestarteten Prozess.

Als Standard wird das offizielle **Qwen3-4B-Q4_K_M.gguf** angeboten (2.497.280.256 Bytes, etwa 2,5 GB, Apache-2.0). Downloadquelle und Revision sind festgelegt; beim Download werden Größe und SHA-256 geprüft. Abbruch/Fehler entfernt die temporäre Datei; bestehende abweichende Modelle werden nicht überschrieben. Modelle gehören weder in Git noch ins App-Bundle. Speicherort auf macOS: `~/Library/Application Support/Nomi/models/`, auf Linux im XDG-Datenverzeichnis, unter Windows in LocalAppData.

Zusätzlich ist **Mistral 7B Instruct v0.3 Q4_K_M** auswählbar (4.372.812.000 Bytes, etwa 4,4 GB, Apache-2.0). Die GGUF-Quantisierung stammt von [bartowski auf Hugging Face](https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/tree/61fd4167fff3ab01ee1cfe0da183fa27a944db48). Auch hier sind Revision, Größe und SHA-256 festgelegt. Der Modellkatalog setzt den passenden Dateipfad; nach Download und Laden wird diese Datei beim nächsten Start verwendet. Ein vorhandenes geprüftes Modell wird wiederverwendet. Qwen3 bleibt der Standard; Mistral benötigt mehr Arbeitsspeicher.

Bei deinem ersten Start ohne Modell ist ein einmaliger Download über die Schaltfläche nötig. Danach lädt **Beim Start laden** die vorhandene, konfigurierte GGUF-Datei ohne erneuten Download. Es wird ein Modell gleichzeitig geladen. Ladezustand, Download-Prozent und Fehler erscheinen in der Statuszeile; Analyse ist erst nach Betriebsbereitschaft möglich. Abbruch während des Startens beendet den Kindprozess. Ein aktiver Download reagiert spätestens nach dem Netzwerk-Timeout (30 s). Abgebrochene Downloads werden derzeit nicht fortgesetzt.

Die Engine nutzt bis zu 8.192 Kontexttokens, einen Analyseplatz und nach Möglichkeit GPU-Offloading (auf macOS Metal). Thinking ist für die strukturierte Metadatenextraktion deaktiviert. Der Arbeitsspeicherbedarf liegt über der reinen GGUF-Dateigröße; andere gewählte Modelle können deutlich mehr RAM benötigen. Ein zu langer Token-Kontext führt zu einem Fehler, nicht zu einem Cloud-Fallback. Die Namensqualität bleibt modellabhängig und muss geprüft werden.

Für Entwickler aus dem Quellcode (macOS) wird die Runtime einmal vorbereitet:

```sh
.venv/bin/python build_support/fetch_llama.py
```

Der App-Build führt diesen Schritt automatisch aus. Die offiziellen ARM64-/x64-Archive werden mit festgelegten SHA-256-Prüfsummen geprüft; die Runtime-Lizenz wird im App-Bundle mitgeliefert. Auf anderen Plattformen kann eine vorhandene `llama-server`-Installation aus dem Suchpfad verwendet werden; entsprechende Pakete sind noch nicht gebaut oder praktisch geprüft.

Quellen: [llama.cpp b11622](https://github.com/ggml-org/llama.cpp/releases/tag/b11622), [Qwen3-4B-GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF/tree/bc640142c66e1fdd12af0bd68f40445458f3869b).

Schema-Felder: `{datum}`, `{absender}`, `{dokumenttyp}`, `{titel}`, `{empfaenger}`, `{kennung}`.

- Standard: `{datum}_{absender}_{dokumenttyp}`
- Mit Rechnungsnummer/anderem belegtem Kennzeichen: `{datum}_{absender}_{dokumenttyp}_{kennung}`
- Mit Empfänger/Zweck: `{datum}_{absender}_{dokumenttyp}_{empfaenger}_{titel}`

Unbekannte Angaben und erkannte Platzhalter bleiben leer. Die Originalendung bleibt erhalten. Deutsche Datumsangaben werden in `YYYY-MM-DD` umgewandelt. Ein vorgeschlagenes Datum muss als vollständiges Datum im übermittelten Textausschnitt belegt sein; erkennbare Vertragsbeginn-/Zeitraumdaten werden weggelassen und im Status angezeigt. Diese konservative Prüfung kann auch ein korrektes Datum weglassen und ersetzt keine fachliche Kontrolle.

Bei bereits belegten oder im Analyseauftrag mehrfach vorgeschlagenen Namen ergänzt Nomi sichtbare Nummern wie `_2`. Vorschläge werden nur innerhalb desselben Analyseauftrags reserviert; manuelle Änderungen und Auswahländerungen werden zusätzlich auf Konflikte geprüft. Beim tatsächlichen Umbenennen erfolgt nochmals die verbindliche Konfliktprüfung. Nummern unterscheiden Dateien, bestätigen aber nicht, ob Inhalte identisch sind.

## OCR: Apple Vision auf macOS

OCR bleibt standardmäßig aus. Aktiviere **OCR für gescannte PDF-Seiten** für Bild-PDFs oder gemischte Dokumente. Unter **Automatisch** verwendet Nomi auf macOS **Apple Vision**, auf anderen Plattformen Tesseract. Apple Vision benötigt beim Nutzer keine separate Installation: Der native Helfer ist im App-Bundle enthalten und verwendet die macOS-Systemframeworks. Bei einem Vision-Fehler wird nicht heimlich auf Tesseract gewechselt.

Die OCR-Sprachen sind standardmäßig `deu+eng` (Deutsch und Englisch); für Vision sind auch `de-DE+en-US` möglich. Nicht unterstützte Sprachkombinationen führen zu einer verständlichen Fehlermeldung. Tesseract bleibt im Auswahlfeld ausdrücklich verfügbar; nur dann wird das Feld für seinen Programmpfad angezeigt.

Nur Seiten mit weniger als 30 extrahierten Buchstaben/Ziffern werden zusätzlich erkannt. Die Original-PDF bleibt unverändert; es wird keine durchsuchbare PDF erzeugt. OCR läuft lokal. Der erkannte Text wird anschließend wie normaler PDF-Text an das konfigurierte Ollama-Backend gesendet.

### Entwicklung aus dem Quellcode

```sh
.venv/bin/python -m pip install -e '.[ocr]'
# Nur für macOS-Entwickler: Helfer einmal mit Apples Swift-Compiler bauen.
.venv/bin/python build_support/build_vision.py
```

Der Swift-Compiler wird ausschließlich beim Entwickeln/Bauen benötigt, nicht auf dem Mac eines App-Nutzers. Der macOS-App-Build kompiliert den Helfer automatisch aus `native/VisionOCR.swift`. Der generierte Helfer unter `nomi/bin/` wird nicht in Git eingecheckt. Die Swift-Build-Werkzeuge müssen auf dem Build-Rechner vorhanden sein.

### Optionales Tesseract für andere Plattformen oder einen Vergleich

Unter macOS: `brew install tesseract tesseract-lang`. Unter Debian/Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng`. Unter Windows Tesseract separat installieren und gegebenenfalls den Programmpfad eintragen. Die Python-Bibliotheken bleiben in allen Fällen über `.[ocr]` installierbar. Windows ist noch nicht praktisch geprüft.

### Grenzen und Abbruch

Seiten werden einzeln mit bis zu 300 dpi und maximal 12 Megapixeln gerendert. Temporäre Bilder werden nach jeder Seite auch bei Abbruch/Fehler entfernt. Beide OCR-Backends laufen in eigenen Prozessen; das eingestellte Timeout gilt je OCR-Seite sowie für die HTTP-Anfrage, nicht für das gesamte Dokument. Abbruch beendet einen laufenden OCR-Prozess; während des Renderns wirkt er nach der aktuellen Renderoperation.

Vision verwendet die genaue Erkennung mit Sprachkorrektur, OCR-Revision 3 und CPU-Ausführung. Das vermeidet Initialisierungsverzögerungen der GPU/ANE bei kurzlebigen Helferprozessen und ist keine pauschale Aussage zur besten Geschwindigkeit jeder Hardware. Die Erkennungsqualität hängt weiterhin von Scan, Schrift und Sprache ab. Seiten mit vorhandenem, aber fehlerhaftem Text können als OCR-Kandidaten übersehen werden.

Technische Referenzen: [Apple Vision](https://developer.apple.com/documentation/vision/recognizing-text-in-images), [Tesseract-CLI](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [PDFium-Python-API](https://pypdfium2.readthedocs.io/en/stable/python_api.html).

## Grenzen der Version 0.6

- Text-PDFs, optional gescannte PDF-Seiten via Apple Vision oder Tesseract, UTF-8/Windows-1252-Texte, Markdown und CSV; zusätzlich PNG- und JPEG-Scans bei aktivierter OCR; keine allgemeine Bildanalyse oder DOCX-Verarbeitung.
- Pro Dokument maximal 16.000 Zeichen und bei PDFs die ersten 20 Seiten. Angaben außerhalb dieses Ausschnitts werden nicht berücksichtigt. Begrenzte PDF-/Textauszüge werden in der Tabelle kenntlich gemacht.
- Jede Datei wird einzeln analysiert; die UI bleibt dabei bedienbar. Abbruch wirkt nach der laufenden Anfrage, deren Timeout konfigurierbar ist.
- Die KI kann sich irren. Vorschläge müssen geprüft werden. Datumsprüfung und Prompt reduzieren Fehler; Absender, Dokumenttyp, Titel und Kennzeichen können weiterhin falsch zugeordnet werden. Sammelakten und mehrere Datumsangaben bleiben besonders prüfpflichtig.
- Ausgewählte Umbenennungen werden vorher auf Konflikte geprüft. Bestehende Dateien werden nicht überschrieben. Für die Umbenennung wird ein Hardlink mit anschließendem Entfernen des alten Verzeichniseintrags verwendet. Dateisysteme ohne Hardlink-Unterstützung (z. B. manche USB-/Netzlaufwerke) werden mit einem Fehler abgewiesen.
- Eine Fehlersituation führt zu einem bestmöglichen Rollback. Bei unvollständiger Rückabwicklung werden die verbleibenden Umbenennungen gemeldet und in der Sitzungshistorie zur Wiederherstellung behalten. Gleichzeitige externe Dateiänderungen und Stromausfälle sind nicht transaktional abgesichert.
- Rückgängig verweigert die Aktion bei veränderten Dateien oder neu belegten Originalnamen. Historie ist derzeit nur im Arbeitsspeicher vorhanden.
- Noch keine Developer-ID-signierten Installer oder automatischen Updates. macOS wurde in der Entwicklungsumgebung getestet; Windows erfordert noch einen eigenen Plattformtest.

## Datenschutz

Im lokalen llama.cpp-Modus wird Dokumenttext ausschließlich über die interne Loopback-Verbindung verarbeitet. Beim Modelldownload wird Hugging Face kontaktiert; Dokumentinhalte werden nicht mitgesendet. Im Ollama-Modus wird Dokumenttext an die eingestellte Backend-Adresse gesendet. Ein Ollama-kompatibler Router kann Cloud-Fallback verwenden. Nomi kann dieses Routing nicht erkennen. Es gibt keinen automatischen Cloud-Fallback in Nomi selbst. Einstellungen werden lokal über Qt gespeichert; Dokumentinhalte werden nicht protokolliert.

## Architektur

- `nomi/core.py`: Extraktion, Backend-Protokoll, Ollama-Anbindung, Namensvalidierung und Umbenennung.
- `nomi/app.py`: PySide6-Oberfläche, sequenzieller Analyse-Worker und asynchrones Modell-Laden.
- `nomi/llama_backend.py`: eigener llama.cpp-Prozess, strukturierte Inferenz und Lebenszyklus.
- `nomi/local_model.py`: Modellpfade, Modellkatalog und verifizierte atomare GGUF-Downloads.
- `nomi/ocr.py`: optionale PDFium-Rasterung, OCR-Backend-Schnittstelle und abbrechbare Vision-/Tesseract-Prozesse.
- `native/VisionOCR.swift`: lokaler Apple-Vision-Helfer, beim Build in die App eingebunden.
- Ollama und llama.cpp verwenden denselben Metadaten-Prompt, dasselbe JSON-Schema und dieselbe konservative Datumsprüfung.

## Tests

```sh
python -m unittest discover -s tests -v
```

Synthetische Testdaten werden nur in temporären Ordnern erzeugt. Keine produktiven Dokumente sind Bestandteil des Projekts.

## Verifizierter Entwicklungsstand (14.10.2026)

- Installation in der vorhandenen `.venv` mit Python 3.14.8, PySide6 6.10.3 und pypdf 6.20.1 abgeschlossen; `pip check` erfolgreich. Alle 65 Tests bestehen; einschließlich echter Vision-OCR, optionaler Tesseract-OCR, OCR im Qt-Worker, Prozessabbruch/-timeout, verifiziertem Modelldownload, lokalem Autoload, Prozesswechsel, Datumsbelegung, Namenssuffixen und manuellen Konflikten. Plattformspezifische OCR-Integrationstests werden ohne die passenden Bibliotheken/Backends übersprungen. Die macOS-CI baut und prüft Vision ohne Tesseract-Installation; die Linux-CI prüft Tesseract.
- PySide6 ist auf `>=6.9,<6.11` begrenzt: Mit 6.12.0 trat beim Schließen nach nativer Tabellenbearbeitung ein QObject-Absturz auf. Derselbe Ablauf inklusive Schließen wurde mit 6.10.3 erfolgreich wiederholt (Exit-Code 0).
- Core-, HTTP-Vertrags- und Qt-Tests laufen mit synthetischen Dokumenten. Sie prüfen unter anderem Konflikte, bestehende Zieldateien, doppelte Quellen, Rollback und teilweise fehlgeschlagene Rückabwicklungen, veränderte Dateien, Import, Auswahl, Analyse, Modellladen und Abbruch.
- Die macOS-Oberfläche wurde gestartet und visuell geprüft; nativer Dateiimport, manuelles Bearbeiten, Umbenennen und Rückgängig wurden am Testdokument bedient und überprüft. Drag-and-drop wird zusätzlich über Qt-Ereignisse getestet.
- Die Ollama-API wurde zusätzlich mit einem echten LAN-Ollama und `mistral:latest` geprüft: strukturierte Antworten und vollständige Extraktion/Generierung/Umbenennung/Rückgängig für synthetische Text-PDFs, TXT, Markdown und CSV erfolgreich. Erster Aufruf etwa 13 s, Folgeaufrufe etwa 0,5–0,7 s (kleiner Testdatensatz, keine allgemeine Leistungsgarantie).
- Der echte Qt-Worker wurde gegen dieses Backend geprüft: Modellliste laden, Abbruch nach laufender Anfrage bei weiterhin reagierender Oberfläche, ungültiges Modell und nicht erreichbare Adresse. Ein HTTP-Timeout wurde zusätzlich mit künstlich verkürzter Frist ausgelöst.
- Nachprüfung mit 28 privaten lokalen PDFs: 28 formal gültige Vorschläge, davon vier Dokumente mit OCR; keine Originale verändert (SHA-256-Prüfung). Sieben Datumsvorschläge wurden konservativ weggelassen. Private Dokumente, Inhalte und Auswertungen sind nicht Bestandteil dieses Repositorys.
- macOS: Apple Vision und Tesseract 5.5.3 mit Deutsch/Englisch, PDFium und Pillow praktisch geprüft. Vision und Tesseract wurden zusätzlich auf denselben vier privaten PDFs verglichen; Originale unverändert. Textübereinstimmung ersetzt dabei keine Qualitätsbewertung anhand manueller Referenztexte. Andere Modelle, schwierige Scans und Windows benötigen weitere Tests. Laufende HTTP-Anfragen enden bei Abbruch weiterhin erst mit Antwort oder Timeout.

## Lizenz

MIT — siehe [LICENSE](LICENSE). Die Lizenz gilt für Nomi; Abhängigkeiten und verwendete Modelle haben eigene Lizenzbedingungen.

## macOS-App bauen (Version 0.6.0)

```sh
.venv/bin/python -m pip install -e '.[ocr,build]'
.venv/bin/python -m PyInstaller --noconfirm build_support/Nomi.spec
```

Die Anwendung liegt anschließend unter `dist/Nomi.app` und lässt sich per Doppelklick starten. Python, Qt, die OCR-Python-Bibliotheken, der native Vision-Helfer und llama.cpp sind enthalten. Modelldateien werden separat in den Anwendungsdaten gespeichert. Auf macOS wird keine Tesseract-Installation mehr benötigt. Wer Tesseract ausdrücklich auswählt, installiert es und seine Sprachdaten separat; dabei werden auch die üblichen Homebrew-Pfade durchsucht. Für einen Ollama-Server im LAN benötigt Nomi die macOS-Berechtigung für das lokale Netzwerk. Die App erklärt diesen Zugriff im Systemdialog; gegebenenfalls unter Systemeinstellungen → Datenschutz & Sicherheit → Lokales Netzwerk für Nomi erlauben. [Apple-Dokumentation](https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy).

Ein lokaler Build übernimmt Prozessorarchitektur und macOS-Version des Build-Rechners als konservative Mindestanforderung. Der Entwicklungsbuild wurde auf Apple Silicon/macOS 27 gebaut und ist kein getesteter universeller Intel-/ARM-Build. Für ältere Systeme auf einem passenden Build-Rechner bauen. Die GitHub-Variante wird auf dem im Workflow angegebenen macOS-Runner erstellt.

Das Bundle ist lokal ad hoc signiert, jedoch nicht mit einer Apple Developer ID signiert oder notarisiert. Es ist derzeit ein Entwicklungsbuild, kein fertiger öffentlicher Installer. Ein automatischer Upload zu GitHub Releases findet nicht statt.

Offline-Selbsttest für das gebaute Bundle (nur temporäre synthetische Dateien, keine Netzwerkaufrufe oder Änderungen an persönlichen Einstellungen):

```sh
dist/Nomi.app/Contents/MacOS/Nomi --self-test
```

Der Selbsttest prüft das automatische OCR-Backend, Qt, Umbenennen und Rückgängig. Auf macOS verwendet er den mitgelieferten Vision-Helfer und benötigt kein Tesseract; auf Linux wird Tesseract mit englischen Sprachdaten benötigt. Er steht auch unter `python -m nomi --self-test` zur Verfügung.

## Automatische Prüfungen

GitHub Actions prüft Pull Requests und Pushes mit Python 3.11/3.14 auf Ubuntu sowie Python 3.14 auf macOS. OCR und der Offline-Selbsttest gehören dazu. Nach erfolgreichen Tests wird ein macOS-Bundle einschließlich llama.cpp gebaut, mit reduziertem Finder-ähnlichem Suchpfad auf OCR und native Runtime geprüft und als ZIP-Artefakt am Workflow-Lauf gespeichert. Die Action-Versionen sind auf Commit-Hashes fixiert. Workflow und Build sind unter `.github/workflows/tests.yml` bzw. `build_support/Nomi.spec` beschrieben.

### Zusätzliche llama.cpp-Prüfungen

```sh
# Laufzeit und abhängige Bibliotheken prüfen, ohne Modell/Netzwerk:
dist/Nomi.app/Contents/MacOS/Nomi --runtime-check
# Echte lokale Inferenz: Standardmodell muss bereits vorhanden sein.
# Nur synthetischer Scan in temporärem Ordner, keine Änderungen an persönlichen Einstellungen.
dist/Nomi.app/Contents/MacOS/Nomi --llama-self-test
```

Lokal mit dem echten Standardmodell und fertigem Bundle geprüft: automatisches Laden, Apple-Vision-OCR, strukturierte lokale Generierung, Umbenennen, Rückgängig und Beenden des eigenen Servers. Gemessene Beispielzeiten: Modellstart 1,2–6,8 s je nach Cachezustand, OCR plus Generierung etwa 2,7–27,2 s für den kurzen synthetischen Scan. Insbesondere die Initialisierung nativer OCR-Frameworks kann beim ersten Aufruf länger dauern; die Oberfläche bleibt dabei bedienbar. Das ist keine allgemeine Leistungsgarantie. Die CI verwendet für Modell-Lebenszyklus und API-Tests einen synthetischen Kindprozess und lädt keine mehrgigabytegroßen Gewichte.

### Einstellungen

Das Zahnrad oben rechts öffnet die Einstellungen. Backend, Modell, Namensschema, Zeitlimit und OCR werden auch über **Einstellungen → Einstellungen …** konfiguriert. Auf macOS liegt der Eintrag im Nomi-App-Menü und ist mit **⌘,** erreichbar. Änderungen gelten direkt und werden beim Schließen des Einstellungsfensters gespeichert. Während laufender Analyse oder Modellinitialisierung sind die betroffenen Felder gesperrt. Im Hauptfenster bleiben Import, Dateiliste, Analyse und Umbenennung.

### PNG- und JPEG-Scans

PNG, JPG und JPEG können über Dateidialog und Drag-and-drop importiert werden. Dafür OCR in den Einstellungen aktivieren. Die Texterkennung arbeitet im Analyse-Worker; Bildinhalte werden nicht an ein Vision-Sprachmodell gesendet. EXIF-Drehung wird berücksichtigt, Transparenz für OCR weiß hinterlegt und große Bilder auf maximal 12 Megapixel verkleinert. Eingaben über 48 Megapixel werden abgewiesen. Die Normalisierung erfolgt ausschließlich an temporären Kopien; Originaldateien und Dateiendungen bleiben erhalten.

### Lokale Dokumentvorschau

Die ausgewählte Datei erscheint rechts neben der Tabelle. Die Bereiche sind über den Trenner in der Breite verstellbar. PDFs lassen sich seitenweise durchblättern, Bilder und PDF-Seiten einpassen oder mit 100/150 Prozent betrachten. TXT, Markdown und CSV werden als reiner Text angezeigt (maximal 256 KiB). PDF-Vorschauen sind auf Dateien bis 200 MB begrenzt, Bildvorschauen auf 48 Megapixel. Die Vorschau lädt im Hintergrund und benötigt weder OCR noch einen KI-Dienst. Veraltete Ergebnisse nach einem Dateiwechsel werden verworfen. Passwortgeschützte oder beschädigte Dateien zeigen einen Hinweis. Das Namensfeld über der Vorschau ist mit der Tabelle synchronisiert. Umbenennen bleibt eine separate Aktion. Die Vorschau öffnet Quellen nur lesend und speichert keine Dokumentkopien.
