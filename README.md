# Nomi

### Jede Datei verdient einen Namen.

Aus `scan_0042.pdf`, `IMG_1083.jpg` und `clip_07.mp4` werden Namen, mit denen du
etwas anfangen kannst. Nomi erkennt Dokumentinhalte, Bildmotive und Video-Szenen,
schlägt passende Dateinamen vor und sortiert Dateien auf Wunsch in deine Ordner.

**Du prüfst die Vorschläge. Du entscheidest, was geändert wird.**

[**macOS-Testversion herunterladen →**](https://github.com/mbosch81/nomi/actions/workflows/tests.yml?query=branch%3Amain)
· [In wenigen Schritten starten](docs/START.md)
· [Fragen und Antworten](docs/FAQ.md)

Kostenlos und Open Source · Lokale KI möglich · Kein Cloud-Konto für die Analyse nötig

> **Aktueller Download:** Die Testversion liegt derzeit in GitHub Actions. Dafür
> ist eine GitHub-Anmeldung erforderlich. Wähle den neuesten erfolgreichen Lauf
> und dort **Nomi-macos** unter **Artifacts**.
> [Download und Voraussetzungen](docs/DOWNLOAD.md)

![Vom Import über den Namensvorschlag bis zur geprüften Ablage](docs/images/workflow.svg)

## Weniger suchen. Dateien wiederfinden.

- **Rechnungen und Verträge verständlich benennen.** Datum, Absender, Dokumenttyp
  oder Rechnungsnummer können Teil des Namens werden.
- **Fotos und Videos beschreiben lassen.** Nomi erkennt sichtbare Motive auch dann,
  wenn kein Text vorhanden ist.
- **Ganze Ordner gemeinsam bearbeiten.** Vorschläge ansehen, einzelne Dateien
  abwählen und Namen direkt korrigieren.
- **Eine einheitliche Ablage schaffen.** Eigene Namensregeln und Ordner wie
  `2026/Rechnung` verwenden.
- **Die Kontrolle behalten.** Vor der Ausführung zeigt Nomi die Änderungen;
  bestehende Dateien werden nicht überschrieben. Rückgängig ist in derselben
  geöffneten Sitzung möglich.

Beispiele mit fiktiven Inhalten und angepassten Vorlagen:

| Vorher | Möglicher neuer Name |
| --- | --- |
| `scan_0042.pdf` | `2026-10-16_Mueller_GmbH_Rechnung_R-42.pdf` |
| `IMG_1083.jpg` | `Haus_mit_rotem_Dach.jpg` |
| `clip_07.mp4` | `Video_Fahrradtour_am_See.mp4` |

## So benutzt du Nomi

1. **Dateien hinzufügen.** Dateien oder Ordner ins Fenster ziehen. Unterordner
   lassen sich bei Bedarf einbeziehen.
2. **Auswahl analysieren.** Nomi erstellt Vorschläge im Hintergrund. Beim ersten
   lokalen Durchlauf werden die benötigten KI-Modelle heruntergeladen.
3. **Vorschläge prüfen.** Die Vorschau hilft beim Abgleich. Namen sind editierbar;
   unerwünschte Dateien kannst du abwählen.
4. **Änderungen bestätigen.** **Auswahl umbenennen** öffnet die Übersicht. Erst
   **Jetzt umbenennen** beziehungsweise **Jetzt ausführen** verändert deine Dateien.

Für den Einstieg brauchst du beim fertigen Mac-Paket weder Python noch eine
separate Installation von Ollama, Tesseract oder FFmpeg.
[Die erste Einrichtung Schritt für Schritt →](docs/START.md)

## Was kannst du importieren?

| Dateien | Was Nomi auswertet |
| --- | --- |
| PDF | Dokumenttext; gescannte Seiten mit eingeschalteter Texterkennung |
| DOCX | Text und Tabellen, auch Kopf- und Fußzeilen |
| TXT, Markdown, CSV | Enthaltenen Text |
| PNG, JPG, JPEG | Bildmotive oder Text über die wählbare Texterkennung |
| MP4, MOV, M4V, MKV, WEBM, AVI, TS | Verteilte Einzelbilder aus dem Video |

Die Videoanalyse wertet keinen Ton aus. Nicht jeder Video-Codec wird unterstützt.
HEIC, DOC und ODT gehören derzeit nicht zu den unterstützten Formaten.
[Mehr zu Formaten und Grenzen →](docs/FAQ.md)

## Deine Ablage, deine Regeln

Im Zahnrad-Menü findest du Vorlagen für Rechnungen, Verträge, Dokumente, Fotos und
Videos. Passe Trennzeichen, Umlaute, Schreibweise und Namenslänge an; die
Beispielvorschau zeigt sofort die Wirkung.

Optional kannst du einen Zielordner und ein Schema wie `{jahr}/{dokumenttyp}`
wählen. Die Bestätigung zeigt dann die vollständigen Zielpfade. Das Einsortieren
funktioniert aktuell innerhalb desselben Dateisystems.

Ein überwachter Eingangsordner nimmt neue Dateien in die Liste auf. Analysieren
und Umbenennen bleiben deine Entscheidung.
[Einstellungen und Vorlagen kennenlernen →](docs/SETTINGS.md)

## Lokal arbeiten

Im lokalen Modus bleiben Dokumenttexte, Bilder und Video-Einzelbilder auf deinem
Mac. Nomi lädt die benötigten Modelle einmalig herunter; danach ist die Analyse
mit diesen Modellen auch ohne Internet möglich.

Für Dokumente steht Qwen als Standard bereit, alternativ Mistral. Für Bilder und
Videos verwendet die automatische lokale Auswahl SmolVLM2. Wer schon einen
Ollama-Server nutzt, kann diesen stattdessen eintragen. Dann gehen die ausgewählten
Inhalte an die konfigurierte Serveradresse.
[Datenschutz und Speicherbedarf →](docs/FAQ.md)

## Bereit zum Ausprobieren?

[**Testbuilds für macOS öffnen →**](https://github.com/mbosch81/nomi/actions/workflows/tests.yml?query=branch%3Amain)

Nomi ist eine frühe Testversion für Macs mit Apple Silicon. Die Pakete sind noch
nicht von Apple notarisiert. Starte mit wenigen Testkopien und prüfe die
vorgeschlagenen Namen: KI kann Inhalte falsch erkennen oder Angaben weglassen.
[Passenden Download finden →](docs/DOWNLOAD.md)

[Fehler melden oder einen Wunsch einreichen](https://github.com/mbosch81/nomi/issues)
· [Änderungen je Version (English)](CHANGELOG.md)
· [Entwicklung und eigene Builds](docs/DEVELOPMENT.md)

Nomi steht unter der [MIT-Lizenz](LICENSE). Enthaltene Werkzeuge und KI-Modelle
haben eigene Lizenzbedingungen.
