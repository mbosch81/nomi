# Fragen und Antworten

[← Zur Produktübersicht](../README.md) · [Download](DOWNLOAD.md) · [Erste Schritte](START.md)

## Ist Nomi kostenlos?

Nomi ist Open Source und steht unter der [MIT-Lizenz](../LICENSE). Die lokale
Analyse benötigt kein kostenpflichtiges Cloud-Konto. Werkzeuge und Modelle haben
eigene Lizenzbedingungen.

## Verlassen meine Dateien den Mac?

Im Modus **Lokal · llama.cpp** werden Dokumenttexte, Bilder und Video-Einzelbilder
auf deinem Mac verarbeitet. Für den ersten Modelldownload kontaktiert Nomi
Hugging Face; Dokumentinhalte werden dabei nicht mitgesendet.

Im Modus **Ollama · Server** gehen die ausgewählten Inhalte an die eingestellte
Adresse. Ob dieser Server weitere Dienste einbezieht, hängt von dessen Einrichtung ab.
Nomi wechselt nicht selbstständig in einen Cloud-Dienst.

Einstellungen und Modelle bleiben lokal gespeichert. Die begrenzte Wiedererkennung
und Rückgängig-Liste werden nur für die laufende Sitzung gehalten. Es wird keine
dauerhafte Dokumenten- oder Änderungshistorie angelegt.

## Kann ich Nomi offline verwenden?

Ja, im lokalen Modus mit bereits heruntergeladenen Modellen. Die App und die für
deine Dateitypen nötigen Modelle müssen zuvor geladen sein. Ein externer
Ollama-Server muss erreichbar bleiben, wenn du diesen Modus verwendest.

## Muss ich weitere Programme installieren?

Beim fertigen Mac-Paket sind Python, Texterkennung, lokale KI-Laufzeit und
Video-Werkzeuge enthalten. Die KI-Modelle lädt Nomi getrennt herunter.
Eine separate Installation von Ollama, FFmpeg oder Tesseract ist für den lokalen
Standardbetrieb nicht erforderlich.

## Warum dauert die erste Analyse länger?

Der erste Durchlauf kann einen Modelldownload und das Laden des Modells enthalten.
Auch die Texterkennung kann beim ersten Aufruf länger brauchen. Mehr Dateien,
lange Dokumente, mehr Video-Einzelbilder oder ein größeres Modell benötigen mehr Zeit.
Die Oberfläche bleibt während Analyse und Modell-Laden bedienbar.

**Abbrechen** stoppt weitere Verarbeitung. Eine schon laufende KI-Anfrage kann
noch bis zur Antwort oder zum eingestellten Zeitlimit dauern.

## Wie viel Speicher brauche ich?

Zusätzlich zur App etwa 2,5 GB für das Standard-Dokumentmodell Qwen und weitere
1,7 GB für das Bild-/Videomodell SmolVLM2. Mistral ist eine Alternative mit etwa
4,4 GB Download. Nicht verwendete lokale Modelle lassen sich über die
[Modellverwaltung](SETTINGS.md#ki) in den Papierkorb verschieben.

Der Arbeitsspeicherbedarf liegt über diesen Dateigrößen. Eine pauschal getestete
Mindest-RAM-Ausstattung für jede Datei und jedes Modell gibt es derzeit nicht.

## Welche Grenzen gelten für Dokumente und Bilder?

- Dokumente werden auf einen Textausschnitt von maximal 16.000 Zeichen begrenzt;
  bei PDFs berücksichtigt die Analyse höchstens die ersten 20 Seiten.
- DOCX wird als Text einschließlich Tabellen gelesen. Word-Seitenlayout und
  eingebettete Bilder werden nicht als vollständiges Dokumentbild ausgewertet.
- Passwortgeschützte PDFs werden nicht analysiert.
- Die direkte Bildanalyse unterstützt PNG/JPEG bis 100 MB und 48 Megapixel und
  bereitet kleinere Bilder für das Modell auf.
- HEIC, DOC, DOCM, ODT, E-Mail-Dateien und Audiodateien werden derzeit nicht unterstützt.

Die Vorschau kann andere Grenzen haben als die Analyse, zum Beispiel eine
maximale PDF-Größe von 200 MB.

## Warum lässt Nomi ein Datum weg?

Ein Datumswert soll aus dem Dokument belegt sein. Mehrdeutige Angaben sowie erkannte
Vertragsbeginn- oder Zeitraumdaten können deshalb weggelassen werden. Auch ein
korrektes Datum kann dabei fehlen. Bei reiner Bild-/Videoanalyse werden Datumsangaben
konservativ entfernt. Prüfe den Vorschlag und ergänze den Namen bei Bedarf selbst.

## Was erkennt Nomi in Videos?

Nomi betrachtet verteilte Einzelbilder. Kurze oder wichtige Szenen können zwischen
diesen Stichproben liegen. Die Analyse ist keine vollständige Beschreibung der
Handlung und enthält keine Audioauswertung.

Unterstützte Container sind MP4, MOV, M4V, MKV, WEBM, AVI und TS. Der enthaltene
Codec muss ebenfalls unterstützt sein: aktuell H.264, HEVC, MPEG-4, MJPEG, ProRes,
VP8 oder VP9. AV1 wird derzeit nicht ausgewertet. Videos ohne bestimmbare Länge,
über 24 Stunden oder über 48 Megapixel werden abgewiesen.

## Werden Originale verändert oder überschrieben?

Nomi bearbeitet keine Dokument- oder Medieninhalte. Namen und gegebenenfalls
Speicherorte ändern sich erst durch deine Bestätigung. Bestehende Zieldateien
werden nicht überschrieben. Bei Fehlern versucht Nomi, ausgeführte Änderungen
zurückzunehmen; verbleibende Aktionen werden gemeldet.

Nomi ist eine frühe Testversion. Die Prüfung der Namen bleibt notwendig, und
Rückgängig innerhalb der Sitzung ersetzt keine Sicherung wichtiger Dateien.

## Kann ich Dateien auf ein anderes Laufwerk einsortieren?

Derzeit nur innerhalb desselben Dateisystems. Es gibt keinen automatischen
Kopier-/Lösch-Wechsel auf andere Laufwerke. Auch Dateisysteme ohne die benötigte
Hardlink-Unterstützung können die Aktion ablehnen. Die Quelle bleibt bei dieser
Ablehnung erhalten.

## Warum wird eine bekannte Datei noch einmal analysiert?

Der Sitzungsspeicher ist begrenzt. Ein Neustart, Änderungen an der Datei oder den
Analyse-Einstellungen sowie das Verdrängen älterer Ergebnisse können eine erneute
Analyse nötig machen. **Erneut analysieren …** berechnet Vorschläge immer neu.

## Etwas funktioniert nicht – wie melde ich es?

Öffne ein [GitHub-Issue](https://github.com/mbosch81/nomi/issues) und nenne:

- Nomi-Version, macOS-Version und Mac-Modell.
- Dateityp und gewähltes KI-Modell.
- Die Schritte und die angezeigte Fehlermeldung.

Nutze möglichst eine nachgestellte Beispieldatei. Lade keine vertraulichen
Dokumente, Passwörter oder Zugangsdaten hoch. Vorschläge und gewünschte Funktionen
sind ebenfalls willkommen.
