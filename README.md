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

Schema-Felder: `{datum}`, `{absender}`, `{dokumenttyp}`, `{titel}`. Beispiel: `{datum}_{absender}_{dokumenttyp}`. Unbekannte Angaben bleiben leer. Die Originalendung bleibt erhalten.

## Grenzen der Version 0.1

- Text-PDFs, UTF-8/Windows-1252-Texte, Markdown und CSV; noch keine OCR, Bildanalyse oder DOCX-Verarbeitung.
- Pro Dokument maximal 16.000 Zeichen und bei PDFs die ersten 20 Seiten. Angaben außerhalb dieses Ausschnitts werden nicht berücksichtigt.
- Jede Datei wird einzeln analysiert; die UI bleibt dabei bedienbar. Abbruch wirkt nach der laufenden Anfrage, deren Timeout konfigurierbar ist.
- Die KI kann sich irren. Vorschläge müssen geprüft werden; kein Datum oder Absender wird durch die Anwendung erfunden.
- Ausgewählte Umbenennungen werden vorher auf Konflikte geprüft. Bestehende Dateien werden nicht überschrieben. Für die Umbenennung wird ein Hardlink mit anschließendem Entfernen des alten Verzeichniseintrags verwendet. Dateisysteme ohne Hardlink-Unterstützung (z. B. manche USB-/Netzlaufwerke) werden mit einem Fehler abgewiesen.
- Eine Fehlersituation führt zu einem bestmöglichen Rollback. Bei unvollständiger Rückabwicklung werden die verbleibenden Umbenennungen gemeldet und in der Sitzungshistorie zur Wiederherstellung behalten. Gleichzeitige externe Dateiänderungen und Stromausfälle sind nicht transaktional abgesichert.
- Rückgängig verweigert die Aktion bei veränderten Dateien oder neu belegten Originalnamen. Historie ist derzeit nur im Arbeitsspeicher vorhanden.
- Noch keine signierten Installer, automatische Updates oder integrierte llama.cpp-Runtime. macOS wurde in der Entwicklungsumgebung getestet; Windows erfordert noch einen eigenen Plattformtest.

## Datenschutz

Dokumenttext wird an die eingestellte Backend-Adresse gesendet. Ein Ollama-kompatibler Router kann Cloud-Fallback verwenden. Nomi kann dieses Routing nicht erkennen. Es gibt keinen automatischen Cloud-Fallback in Nomi selbst. Einstellungen werden lokal über Qt gespeichert; Dokumentinhalte werden nicht protokolliert.

## Architektur

- `nomi/core.py`: Extraktion, Backend-Protokoll, Ollama-Anbindung, Namensvalidierung und Umbenennung.
- `nomi/app.py`: PySide6-Oberfläche und sequenzieller Analyse-Worker.
- Die Provider-Grenze ermöglicht später eine lokale llama.cpp-Implementierung.

## Tests

```sh
python -m unittest discover -s tests -v
```

Synthetische Testdaten werden nur in temporären Ordnern erzeugt. Keine produktiven Dokumente sind Bestandteil des Projekts.

## Verifizierter Entwicklungsstand (14.10.2026)

- Installation in der vorhandenen `.venv` mit Python 3.14.8, PySide6 6.10.3 und pypdf 6.20.1 abgeschlossen; `pip check` erfolgreich. Alle 19 Tests bestehen.
- PySide6 ist auf `>=6.9,<6.11` begrenzt: Mit 6.12.0 trat beim Schließen nach nativer Tabellenbearbeitung ein QObject-Absturz auf. Derselbe Ablauf inklusive Schließen wurde mit 6.10.3 erfolgreich wiederholt (Exit-Code 0).
- Core-, HTTP-Vertrags- und Qt-Tests laufen mit synthetischen Dokumenten. Sie prüfen unter anderem Konflikte, bestehende Zieldateien, doppelte Quellen, Rollback und teilweise fehlgeschlagene Rückabwicklungen, veränderte Dateien, Import, Auswahl, Analyse, Modellladen und Abbruch.
- Die macOS-Oberfläche wurde gestartet und visuell geprüft; nativer Dateiimport, manuelles Bearbeiten, Umbenennen und Rückgängig wurden am Testdokument bedient und überprüft. Drag-and-drop wird zusätzlich über Qt-Ereignisse getestet.
- Die Ollama-API wurde gegen einen lokalen synthetischen HTTP-Server geprüft. Noch kein Test der Modellgenerierung mit einem echten Ollama-Backend; Qualität, Latenz und modellspezifische Unterstützung strukturierter Antworten bleiben offen.
- Kein OCR- oder Windows-Plattformtest. Abbruch wartet weiterhin auf das Ende der laufenden Anfrage (bis zum eingestellten Timeout).

## Lizenz

MIT — siehe [LICENSE](LICENSE). Die Lizenz gilt für Nomi; Abhängigkeiten und verwendete Modelle haben eigene Lizenzbedingungen.
