# ADR-0003: Fehler- und Logging-Konzept

- **Status:** Accepted
- **Datum:** 2026-03-27
- **Kontext:** Task 0.3

## Kontext
Version 1 des Supply Chain Checker soll robust auf fehlerhafte Eingaben reagieren, ohne den gesamten Lauf abzubrechen. Zusätzlich muss die Verarbeitung über konsistente Logs nachvollziehbar sein.

## Entscheidung

### 1) Fehlerklassen (Domänen)
Für die erste Iteration werden Fehler in klar benannte Domänen aufgeteilt. Jede Domäne erhält eine eigene Exception-Klasse, abgeleitet von einer gemeinsamen `SupplyChainCheckerError`-Basisklasse.

- `ConfigurationError`: Ungültige oder fehlende Konfiguration, YAML-Validierung, Pflichtfelder.
- `PdfProcessingError`: Fehler beim Öffnen/Lesen/Interpretieren von PDF-Inhalten.
- `OcrProcessingError`: Fehler beim OCR-Fallback (Engine-Aufruf, Bildkonvertierung, OCR-Ergebnisformat).
- `LlmClientError`: Fehler bei LLM-Kommunikation (Authentifizierung, API-Timeout, ungültige Antwortstruktur).
- `ParsingError`: Fehler beim Extrahieren strukturierter Daten aus LLM- oder PDF-Text.
- `StorageIOError`: Datei-/Verzeichnis-/CSV-I/O-Probleme.
- `StatusTrackingError`: Fehler beim Lesen/Schreiben der Statusdatei verarbeiteter PDFs.

**Leitlinie zur Verwendung:**
- Fehler werden so nah wie möglich an der Quelle in eine Domänen-Exception übersetzt.
- Services fangen Domänen-Exceptions modulbezogen ab, loggen strukturiert und laufen mit dem nächsten Dokument/Produkt weiter.
- Der CLI-Prozess endet nur bei nicht-recoverbaren Initialisierungsfehlern (z. B. Konfiguration nicht ladbar).

### 2) Logging-Architektur

#### Benannte Logger pro Kernmodul
Jedes Kernmodul deklariert am Modulanfang:

```python
import logging
logger = logging.getLogger(__name__)
```

Kernmodule (V1):
- `cli.py`
- `config.py`
- `logging_setup.py`
- `services/pdf_reader.py`
- `services/ocr_service.py`
- `services/extraction_service.py`
- `services/assessment_service.py`
- `services/csv_service.py`
- `services/status_service.py`
- `services/llm/openai_client.py`

#### Event-Struktur
Logs müssen als strukturierte Events mit stabilen Feldern geschrieben werden:

Pflichtfelder:
- `event`: Maschinenlesbarer Eventname (z. B. `pdf.process.started`)
- `run_id`: ID eines CLI-Laufs
- `module`: Quellmodul (`__name__`)
- `command`: `extract` oder `assess` (falls verfügbar)
- `document_path`: betroffene PDF (falls verfügbar)
- `product_id` / `product_name`: betroffenes Produkt (falls verfügbar)

Empfohlene Zusatzfelder:
- `duration_ms`
- `status` (`started`, `success`, `failed`, `skipped`)
- `error_type`
- `error_message`

#### Log-Level-Konvention
- `DEBUG`: Technische Details, Zwischenschritte, Prompt-Metadaten ohne sensible Inhalte.
- `INFO`: Normale Verarbeitungsschritte und fachliche Zustände.
- `WARNING`: Recoverable Fehler (einzelnes Dokument/Produkt konnte nicht verarbeitet werden).
- `ERROR`: Nicht-recoverable Fehler auf Run-Ebene oder Modulinitialisierung.

### 3) Standardisierte Events

#### Run-Ebene
- `run.started`
- `run.finished`
- `run.failed`

#### Konfiguration
- `config.load.started`
- `config.load.succeeded`
- `config.load.failed`

#### PDF/OCR/Extraktion
- `pdf.discovery.completed`
- `pdf.read.started`
- `pdf.read.failed`
- `ocr.started`
- `ocr.succeeded`
- `ocr.failed`
- `extraction.started`
- `extraction.succeeded`
- `extraction.failed`

#### Assessment
- `assessment.started`
- `assessment.succeeded`
- `assessment.failed`

#### I/O und Status
- `csv.write.started`
- `csv.write.succeeded`
- `csv.write.failed`
- `status.read.failed`
- `status.write.failed`

## Konsequenzen

### Vorteile
- Einheitliche Fehlerklassifikation für bessere Testbarkeit und Monitoring.
- Klare Trennung recoverable vs. nicht-recoverable Fehler.
- Saubere Basis für spätere JSON-Logs/Telemetry.

### Nachteile
- Anfangs höherer Implementierungsaufwand durch Exception-Mapping und Eventkonvention.

## Umsetzungsleitlinie (verbindlich für V1)
1. Jede neue Service-/CLI-Datei definiert einen benannten Logger über `logging.getLogger(__name__)`.
2. Fehler werden nicht stumm geschluckt; sie werden in Domänen-Exceptions überführt und mit Eventnamen geloggt.
3. Neue Logs verwenden stabile Eventnamen gemäß ADR oder erweitern diese Liste konsistent.
