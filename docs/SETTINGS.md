# Nomi an deine Ablage anpassen

[← Zur Produktübersicht](../README.md) · [Erste Schritte](START.md) · [Hilfe](FAQ.md)

Das **Zahnrad** öffnet die Einstellungen. Auf dem Mac geht das auch mit **⌘,**.
Während einer Analyse oder beim Laden eines Modells sind die betroffenen Felder
gesperrt. Einstellungen werden lokal gespeichert.

## Allgemein

Für **Dokumente**, **Bilder** und **Videos** gibt es getrennte Namensschemata.
Wähle eine Vorlage und klicke auf **Vorlage übernehmen**. Rechnungen und Verträge
passen das Dokumentenschema an; Fotos und Videos das jeweilige Bild- oder
Videoschema. Anschließend kannst du die Vorlage bearbeiten.

| Feld | Bedeutung |
| --- | --- |
| `{datum}` | Erkanntes Dokumentdatum, zum Beispiel `2026-10-16` |
| `{absender}` | Aussteller oder Absender |
| `{dokumenttyp}` | Zum Beispiel Rechnung oder Vertrag |
| `{titel}` | Kurze Beschreibung des Inhalts |
| `{empfaenger}` | Erkannter Empfänger |
| `{kennung}` | Belegte Kennung, zum Beispiel eine Rechnungsnummer |

Beispiel für Rechnungen: `{datum}_{absender}_Rechnung_{kennung}`.
Für Fotos eignet sich `{titel}`, für Videos etwa `Video_{titel}`.
Unbekannte Angaben bleiben leer. Die Dateiendung bleibt erhalten.

Unter den Vorlagen stellst du Leerzeichen oder Unterstriche, Schreibweise,
Umlaut-Ersetzung, maximale Namenslänge und Windows-/NAS-Kompatibilität ein.
Die synthetischen Beispiele zeigen die Wirkung sofort. Die Länge zählt den
vollständigen Namen einschließlich Endung und berücksichtigt auch mehrbyteige Zeichen.

Die Regeln gelten für neue Vorschläge. Manuelle Korrekturen sind weiterhin möglich;
Gültigkeit und maximale Länge werden vor der Ausführung erneut geprüft. Neue
Einstellungen ändern bestehende Vorschläge nicht automatisch: Starte dafür eine
neue Analyse. Ein leeres Bild- oder Videoschema verwendet das Dokumentenschema.

## KI

**Lokal · llama.cpp** verarbeitet deine Dateien auf deinem Mac. Die automatische
Modellwahl verwendet das ausgewählte Textmodell für Dokumente und SmolVLM2 für
Bilder und Videos. Es ist jeweils nur ein Modell gleichzeitig geladen.

| Modell | Gedacht für | Ungefährer Download |
| --- | --- | --- |
| Qwen3 4B | Standard für Dokumente | 2,5 GB |
| Mistral 7B Instruct | Alternative für Dokumente | 4,4 GB |
| SmolVLM2 2.2B samt Projektor | Bilder und Video-Einzelbilder | 1,7 GB |

Die Dateigröße ist keine Angabe zum gesamten Arbeitsspeicherbedarf. Ein größeres
Modell ist auch nicht automatisch für jede Datei besser.

**Beim Start laden** lädt bei automatischer Auswahl das gewählte, bereits vorhandene
Textmodell. Fehlende Modelle werden beim Analysieren heruntergeladen. Für eigene
GGUF-Dateien schalte die automatische Modellwahl aus und wähle Modell und gegebenenfalls
Vision-Projektor selbst.

**Installierte Modelle verwalten …** zeigt Speicherbedarf und Ladezustand.
Entlade ein Modell, bevor du es entfernst. Entfernen verschiebt unterstützte Dateien
aus dem Nomi-Modellordner in den Papierkorb; externe Modelldateien werden nicht gelöscht.

**Ollama · Server** ist für einen vorhandenen Server gedacht: Adresse eintragen,
**Modelle laden** wählen und das gewünschte Modell einstellen. Bei Ollama bleibt das
gewählte Servermodell maßgeblich; für Bilder und Videos muss es bildfähig sein.
Die Inhalte werden dann an diese Adresse gesendet.

## Video

Wähle **1 bis 12 Einzelbilder pro Video**; Standard sind **5**. Mehr Bilder können
mehr Szenen erfassen, brauchen aber mehr Zeit und Speicher. Das zusätzliche
Zeitlimit begrenzt die Bildentnahme.

Die Bilder werden über die Videolänge verteilt. Nach der Analyse zeigt die Vorschau
die verwendete Stichprobe mit Zeitpositionen. Ton wird nicht ausgewertet.
Eine eigene FFmpeg-Installation ist beim Mac-Paket nicht erforderlich.

## Bilder

- **Automatisch:** Bei lokaler automatischer Modellwahl übernimmt das Vision-Modell
  Motive und Szenen. Im manuellen lokalen Modus hängt das vom geladenen Modell ab;
  ohne Vision verwendet Nomi den OCR-Weg. Bei Ollama bleibt der automatische Modus bei OCR.
- **Bildinhalt mit Vision-Modell:** Wertet das Bild direkt aus. Bei Ollama ist dafür
  ausdrücklich ein bildfähiges Servermodell erforderlich.
- **Nur Text erkennen (OCR):** Geeignet für fotografierte oder gescannte Dokumente;
  zusätzlich die Texterkennung einschalten.

Für Motivnamen sollte die Bildvorlage `{titel}` enthalten. Bei reiner Bildanalyse
werden Datumsangaben konservativ weggelassen.

## Texterkennung

Schalte **OCR für PDF- und Bildscans** für gescannte PDFs oder Bilder im OCR-Modus ein.
**Automatisch** verwendet im Mac-Paket die enthaltene Apple-Texterkennung.
Deutsch und Englisch sind voreingestellt.

PDF-Seiten mit wenig vorhandenem Text werden zusätzlich erkannt. Die Verarbeitung
macht aus einem Scan keine neue durchsuchbare PDF und verändert nicht den Dateiinhalt.
Tesseract ist eine separat einzurichtende Alternative für fortgeschrittene Anwender.

## Eingangsordner

Wähle einen Ordner und aktiviere die Überwachung; Unterordner sind optional.
Während Nomi geöffnet ist, werden passende Dateien nach einer kurzen Stabilitätsprüfung
in die Liste aufgenommen. Auch bereits vorhandene Dateien können importiert werden.

Die Überwachung startet weder Analyse noch Umbenennung automatisch. Sie pausiert
während Analyse und Modell-Laden. Vollständig abgeschlossene Kopiervorgänge können
nicht in jedem Fall erkannt werden; warte bei großen laufenden Übertragungen ab.

## Einsortieren

1. Aktiviere **Beim Umbenennen in Zielordner einsortieren**.
2. Wähle einen vorhandenen **Zielordner**.
3. Lege das **Unterordner-Schema** fest. Die Beispielvorschau hilft bei der Kontrolle.

| Schema | Mögliches Ziel unter deinem Zielordner |
| --- | --- |
| `{jahr}/{dokumenttyp}` | `2026/Rechnung` |
| `{jahr}/{monat}/{absender}` | `2026/10/Mueller_GmbH` |
| Leer lassen | Datei direkt im gewählten Zielordner |

Zusätzlich zu den Namensfeldern stehen hier `{jahr}` und `{monat}` zur Verfügung.
Die Werte stammen aus der Analyse. Fehlt das Datum, verwendet Nomi `Ohne_Datum`;
andere fehlende Werte erhalten `Unsortiert`. Namen und Ordner folgen den eingestellten
Namensregeln. Dynamische Ordnerfelder benötigen vorher eine erfolgreiche Analyse.

Die Übersicht zeigt alle vollständigen Zielpfade. Erst die Bestätigung erstellt
Unterordner und verschiebt die Dateien. Quelle und Ziel müssen aktuell auf demselben
Dateisystem liegen; symbolische Links werden abgewiesen. Bestimmte USB- und Netzlaufwerke
unterstützen die erforderliche Verschiebeoperation möglicherweise nicht.

**Rückgängig** stellt Namen und Speicherorte wieder her. Nomi entfernt dabei nur
selbst angelegte, weiterhin leere Ordner. Bereits vorhandene oder inzwischen gefüllte
Ordner bleiben erhalten. Die Rückgängig-Liste gilt bis zum Beenden der App.
