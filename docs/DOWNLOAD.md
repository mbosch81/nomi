# Nomi herunterladen

[← Zur Produktübersicht](../README.md) · [Erste Schritte](START.md)

## Die aktuelle Testversion finden

Nomi ist derzeit als Mac-Testbuild über GitHub Actions verfügbar. Ein öffentliches
GitHub-Release mit direktem Download gibt es noch nicht. Für den aktuellen
Downloadweg brauchst du eine GitHub-Anmeldung.

1. Öffne die [Nomi-Testbuilds](https://github.com/mbosch81/nomi/actions/workflows/tests.yml?query=branch%3Amain).
2. Wähle den neuesten Lauf mit einem **grünen Haken**.
3. Scrolle zu **Artifacts** und lade **Nomi-macos** herunter.
4. Entpacke den Download. Falls darin noch `Nomi-macos.zip` liegt, entpacke auch
   dieses Archiv, bis du **Nomi.app** siehst.
5. Ziehe **Nomi.app** in deinen Ordner **Programme** und öffne sie dort.

Die ZIP-Dateien „Source code“ beziehungsweise der GitHub-Knopf „Download ZIP“
enthalten den Quellcode. Für die fertige Anwendung brauchst du das oben genannte
App-Paket.

Downloads aus GitHub Actions laufen nach einiger Zeit ab. Fehlt bei einem älteren
Lauf das Paket, wähle einen neueren erfolgreichen Lauf.
[GitHubs Downloadanleitung](https://docs.github.com/de/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)

## Passt Nomi zu deinem Mac?

| Voraussetzung | Aktueller Stand |
| --- | --- |
| Prozessor | Apple Silicon, zum Beispiel M1, M2, M3 oder M4 |
| macOS | Der am 16. Oktober 2026 geprüfte GitHub-Testbuild benötigt macOS 14.8 oder neuer |
| Internet | Für den App-Download und das erstmalige Laden der KI-Modelle |
| Freier Speicher | Zusätzlich zur App etwa 2,5 GB für Qwen; für Bilder/Video weitere etwa 1,7 GB |
| Arbeitsspeicher | Der Bedarf liegt über der Modelldateigröße und hängt von Modell, Datei und übrigen Apps ab |

Für Intel-Macs, Windows und Linux wird aktuell kein fertiges, hier zugesichertes
Download-Paket angeboten. Informationen zu eigenen Builds stehen in der
[Entwicklerdokumentation](DEVELOPMENT.md).

Die Mindestversion hängt vom jeweiligen Build ab. Ein separat bereitgestellter
lokaler Build kann eine neuere macOS-Version benötigen als das GitHub-Paket;
beispielsweise wurde der lokale Build von Version 0.10.0 auf macOS 27 erstellt.

## Beim Öffnen erscheint eine macOS-Meldung

Die Testpakete sind noch nicht mit einer Apple Developer ID signiert und
notarisiert. macOS kann deshalb das Öffnen einschränken. Verwende ausschließlich
Dateien aus diesem Projekt und beachte
[Apples Hinweise zum sicheren Öffnen von Apps](https://support.apple.com/de-de/102445).

Meldet macOS eine unpassende Version oder Architektur, prüfe zuerst die
Voraussetzungen des Pakets. Bei einem beschädigten Download lade die Datei neu.

## Danach

Öffne Nomi und folge den [ersten Schritten](START.md). Die lokale Analyse braucht
kein Cloud-Konto. Die benötigten Modelle werden getrennt vom App-Paket geladen.
