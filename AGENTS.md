# AGENTS.md

## Projektname
Supply Chain Checker

## Zweck
Supply Chain Checker ist ein lokales CLI-Tool in Python zur Verarbeitung beliebiger PDF-Dokumente.
Das Tool extrahiert Produkte aus Dokumenten wie Rechnungen, Lieferscheinen oder sonstigen PDFs und bewertet diese Produkte anschließend mit Hilfe eines LLMs hinsichtlich ihres Risikos bei definierten Szenarien.

Die erste Version ist bewusst als schnell lauffähiges MVP ausgelegt, legt aber großen Wert auf:
- sauberes Fehlerhandling
- umfassendes Logging
- hohe Testbarkeit
- klare Architektur
- leichte Erweiterbarkeit

## Produktziel
Das Tool soll:
1. PDFs aus einem konfigurierten Eingabeverzeichnis einlesen
2. vorhandenen Text direkt extrahieren
3. OCR nur dann verwenden, wenn kein brauchbarer Text vorhanden ist
4. mit Hilfe eines LLMs alle im Dokument erwähnten Produkte extrahieren
5. die extrahierten Produkte als CSV zwischenspeichern
6. in einem zweiten Schritt jedes Produkt einzeln per LLM bewerten
7. das Ergebnis als neue CSV ausgeben
8. die Bewertung zusätzlich in der Konsole anzeigen

## Geltungsbereich von Version 1
Version 1 umfasst ausschließlich:
- lokales CLI-Programm
- Python als Programmiersprache
- YAML-Konfiguration
- Verarbeitung aller neuen PDFs in einem Eingabeordner
- Statusdatei zur Erkennung bereits verarbeiteter PDFs
- CSV-Zwischenspeicherung pro Lauf
- CSV-Ausgabe pro Lauf
- gekapselte LLM-Integration
- OpenAI API als erste konkrete LLM-Implementierung
- keine externen Live-Datenquellen
- keine Weboberfläche
- keine Datenbank
- keine Benutzerverwaltung

## Arbeitsprinzipien
1. **Architektur vor Geschwindigkeit**: Modular, nachvollziehbar und testbar statt Ein-Datei-Lösung.
2. **Fehler isolieren**: Fehler in einer PDF oder bei einem Produkt dürfen den gesamten Lauf nicht abbrechen.
3. **Logging ist Pflicht**: Jeder wichtige Verarbeitungsschritt muss sauber geloggt werden.
4. **Erweiterbarkeit sicherstellen**: LLM-Anbindung, PDF-Verarbeitung und Ausgabe gekapselt aufbauen.
5. **Keine versteckte Magie**: Explizite und lesbare Lösungen bevorzugen.
6. **Tests sind Teil der Implementierung**: Code ohne Tests gilt nicht als fertig; Ziel ist 100 % Codeabdeckung.
7. **Verbindliche Qualitätsregel**: Bei fehlgeschlagenen Tests muss so lange nachgebessert werden, bis alle Tests erfolgreich sind; Aufgaben gelten erst dann als abgeschlossen.

## Technische Leitplanken
- **Programmiersprache:** Python
- **Laufzeit:** Lokales CLI-Tool
- **Konfiguration:** YAML

## CLI-Kommandos
Mindestens diese Befehle müssen unterstützt werden:
- `extract`
- `assess`

Beispiele:
```bash
python -m supply_chain_checker extract --config config/config.yaml
python -m supply_chain_checker assess --config config/config.yaml
```

## Verbindliche Leitlinie: Fehler- und Logging-Konzept (ab Task 0.3)

### Fehlerdomänen
Implementierungen müssen Fehler in folgende Domänen einordnen:
- Konfiguration (`ConfigurationError`)
- PDF-Verarbeitung (`PdfProcessingError`)
- OCR (`OcrProcessingError`)
- LLM (`LlmClientError`)
- Parsing (`ParsingError`)
- IO (`StorageIOError`)
- Status (`StatusTrackingError`)

Regel: Fehler möglichst quellenah in Domänenfehler übersetzen; einzelne fehlerhafte Dokumente/Produkte dürfen den gesamten Lauf nicht stoppen.

### Logging-Regeln
- Jedes Kernmodul verwendet einen benannten Logger (`logging.getLogger(__name__)`).
- Logs verwenden stabile Eventnamen (z. B. `run.started`, `config.load.failed`, `pdf.read.failed`, `assessment.succeeded`).
- Recoverable Fehler auf Dokument-/Produkt-Ebene als `WARNING`, nicht-recoverable Run-Fehler als `ERROR`.
- Event-Logs sollen, wenn verfügbar, Felder wie `event`, `run_id`, `command`, `document_path`, `product_name`, `error_type` enthalten.

### Referenz
Die vollständige Richtlinie ist in `docs/ADR-0003-fehler-und-logging-konzept.md` dokumentiert und bei neuen Implementierungen verbindlich zu beachten.
