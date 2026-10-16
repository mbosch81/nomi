# Deine ersten Dateien mit Nomi benennen

[← Zur Produktübersicht](../README.md) · [Download](DOWNLOAD.md) · [Hilfe](FAQ.md)

## 1. Nomi öffnen

Lade das [passende Mac-Paket](DOWNLOAD.md) und öffne **Nomi.app** aus dem Ordner
**Programme**. Für den ersten Versuch reichen drei bis fünf Kopien typischer Dateien.

## 2. Die lokale KI verwenden

Öffne das **Zahnrad → KI**. Wähle **Lokal · llama.cpp** und lasse
**Modell passend zur Datei automatisch wählen** eingeschaltet.

- **Dokumente:** Qwen ist der Standard. Mistral steht als Alternative bereit.
- **Bilder und Videos:** Nomi verwendet SmolVLM2.
- **Gescannte PDFs:** Schalte unter **Texterkennung** zusätzlich
  **OCR für PDF- und Bildscans** ein. Auf dem Mac ist die Texterkennung bereits enthalten.

Du musst keinen eigenen KI-Server einrichten. Beim ersten Analysieren lädt Nomi
fehlende Modelle herunter. In der Statuszeile siehst du den Fortschritt. Vorhandene
Modelle werden wiederverwendet; der erste Durchlauf dauert daher häufig länger.

Wenn du bereits einen Ollama-Server verwendest, findest du die alternative
Einrichtung unter [KI-Einstellungen](SETTINGS.md#ki).

## 3. Dateien hinzufügen

Ziehe Dateien oder einen Ordner ins Hauptfenster. Alternativ verwende
**Dateien hinzufügen** oder **Ordner auswählen**. Mit **Unterordner einbeziehen**
werden auch passende Dateien in den darunterliegenden Ordnern importiert.

Die Checkboxen bestimmen, welche Dateien am nächsten Schritt teilnehmen.
**Alle auswählen** und **Alle abwählen** helfen bei größeren Listen.

## 4. Analysieren und prüfen

Klicke auf **Auswahl analysieren**. Nomi arbeitet die Dateien im Hintergrund ab.

- Wähle eine Zeile, um die Datei rechts in der Vorschau anzusehen.
- Bearbeite den vorgeschlagenen Namen in der Tabelle oder im Feld über der Vorschau.
- Beachte Hinweise auf fehlende Angaben oder Namenskonflikte.
- Wähle Dateien ab, die du noch nicht ändern möchtest.

Ist ein Vorschlag unpassend, markiere die betreffenden Dateien über ihre Checkboxen
und wähle **Erneut analysieren …**. Du kannst einen Hinweis wie „kürzer benennen“
oder „den Zweck hervorheben“ ergänzen. Diese Aktion berechnet die Vorschläge neu.

Bei Videos erscheinen nach erfolgreicher Analyse die tatsächlich ausgewerteten
Einzelbilder mit Zeitpositionen. Du kannst sie einzeln größer ansehen.

## 5. Bestätigen

**Auswahl umbenennen** öffnet die Übersicht der geplanten Änderungen. Prüfe dort
alte und neue Namen. Falls du Einsortieren aktiviert hast, siehst du zusätzlich
die vollständigen Quell- und Zielpfade.

Erst **Jetzt umbenennen** beziehungsweise **Jetzt ausführen** führt die angezeigte
Aktion aus. **Zurück** schließt die Übersicht ohne Änderung. Konflikte und ungültige
Ziele blockieren die Bestätigung; bestehende Dateien werden nicht überschrieben.

## 6. Rückgängig machen

Solange Nomi geöffnet bleibt, kannst du abgeschlossene Aktionen mit **Rückgängig**
zurücknehmen. Das gilt auch für das optionale Einsortieren.

Nach dem Beenden ist diese Rückgängig-Liste nicht mehr verfügbar. Wurde eine Datei
inzwischen außerhalb von Nomi verändert oder ist ihr ursprünglicher Name neu
belegt, kann die Wiederherstellung blockiert sein.

## Als Nächstes

Passe unter **Allgemein** die [Vorlagen und Namensregeln](SETTINGS.md#allgemein) an.
Wenn du auch eine Ordnerstruktur aufbauen möchtest, richte anschließend
[Einsortieren](SETTINGS.md#einsortieren) ein.
