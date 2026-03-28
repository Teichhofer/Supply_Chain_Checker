# Supply Chain Checker

Supply Chain Checker ist ein lokales Python-CLI-Tool zur Verarbeitung von PDF-Dokumenten (z. B. Rechnungen oder Lieferscheinen). Es extrahiert Produkte aus PDFs und bewertet diese anschließend pro Produkt mit einem LLM hinsichtlich Lieferkettenrisiko.

Version 1 (MVP) ist bewusst pragmatisch gehalten, setzt aber auf klare Architektur, robustes Fehlerhandling, strukturiertes Logging und gute Erweiterbarkeit.

---

## 1) Architekturüberblick

Die Verarbeitung ist in zwei voneinander getrennte CLI-Schritte aufgeteilt:

1. **`extract`**
   - Liest neue PDFs aus `data/input`.
   - Versucht zuerst direkte Textextraktion.
   - Nutzt OCR nur bei fehlendem/brauchbarem Text.
   - Extrahiert Produkte per LLM.
   - Schreibt Ergebnisse als Extraktions-CSV nach `data/output`.
   - Markiert verarbeitete Dokumente in der Statusdatei.

2. **`assess`**
   - Nimmt die neueste Extraktions-CSV aus `data/output`.
   - Bewertet jedes Produkt einzeln per LLM.
   - Schreibt Bewertungs-CSV nach `data/output`.
   - Gibt Bewertungsergebnisse zusätzlich in der Konsole aus.

### Wichtige Module (src/supply_chain_checker)

- `cli.py`: CLI-Einstiegspunkt (`extract`, `assess`) und Run-Orchestrierung.
- `config.py`: Laden und Validieren der YAML-Konfiguration.
- `logging_setup.py`: Logging-Konfiguration inkl. Run-ID-bezogener Logs.
- `services/pdf_reader.py`: Direkte PDF-Extraktion + OCR-Fallback.
- `services/ocr_service.py`: OCR-Anbindung (gekapselt).
- `services/extraction_service.py`: Dokumentweise Produktextraktion.
- `services/assessment_service.py`: Produktweise Risikobewertung.
- `services/csv_service.py`: Lesen/Schreiben von Extraktions- und Bewertungs-CSVs.
- `services/status_service.py`: Tracking bereits verarbeiteter PDFs.
- `services/llm/openai_client.py`: OpenAI-Adapter für LLM-Aufrufe.
- `parsers/*`: Parser für LLM-Antwortformate.

### Fehler- und Logging-Konzept

Die Implementierung nutzt Domänenfehler (u. a. Konfiguration, PDF, OCR, LLM, Parsing, IO, Status) und stabile Event-Namen im Logging. Recoverable Fehler auf Dokument-/Produktebene werden isoliert behandelt, damit ein Lauf möglichst vollständig durchläuft.

Referenz: `docs/ADR-0003-fehler-und-logging-konzept.md`.

---

## 2) Installation

### Voraussetzungen

- Python **3.11+**
- optional: OCR-Engine auf dem Host (nur relevant, wenn OCR-Fallback benötigt wird)
- OpenAI API Key als Umgebungsvariable `OPENAI_API_KEY` (für echte LLM-Requests)

### Setup (lokal)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Optional für Entwicklung/Checks:

```bash
pip install -e .[dev]
```

---

## 3) Konfiguration

Nutze die Beispielkonfiguration als Startpunkt:

```bash
cp config/config.example.yaml config/config.yaml
cp config/secrets.example.env config/secrets.env
```

Danach Secrets laden (enthält u. a. den API Key):

```bash
source config/secrets.env
```

### Bedeutung der Verzeichnisse

- `data/input`: Neue, zu verarbeitende PDFs.
- `data/output`: Laufbezogene CSV-Artefakte (`extraction_*.csv`, `assessment_*.csv`).
- `data/state`: Statusdateien (z. B. bereits verarbeitete PDFs).
- `logs`: Laufbezogene Logdateien.

Die Verzeichnisse werden beim CLI-Start automatisch angelegt, falls sie fehlen.

---

## 4) CLI-Beispiele (direkt ausführbar)

Nach Installation via `pip install -e .` sind beide Varianten ausführbar.

### Variante A: Konsolen-Skript

```bash
supply-chain-checker extract --config config/config.yaml
supply-chain-checker assess --config config/config.yaml
```

### Variante B: Modulaufruf

```bash
python -m supply_chain_checker extract --config config/config.yaml
python -m supply_chain_checker assess --config config/config.yaml
```

> Hinweis: Für einen echten End-to-End-Lauf müssen PDFs in `data/input` liegen und `OPENAI_API_KEY` gesetzt sein.

---

## 5) Beispiel-Setup für Erstinbetriebnahme

1. Umgebung erstellen und Paket installieren (siehe Installation).
2. Konfiguration kopieren:
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```
3. Secrets-Datei anlegen und laden:
   ```bash
   cp config/secrets.example.env config/secrets.env
   source config/secrets.env
   ```
4. Test-PDF(s) nach `data/input` legen.
5. Extraktion starten:
   ```bash
   supply-chain-checker extract --config config/config.yaml
   ```
6. Bewertung starten:
   ```bash
   supply-chain-checker assess --config config/config.yaml
   ```
7. Ergebnisse prüfen:
   - CSVs in `data/output`
   - Logs in `logs`

---

## 6) Grenzen von V1

Version 1 umfasst bewusst nur den MVP-Umfang:

- Nur lokales CLI (keine Weboberfläche).
- Keine Datenbank, keine User-/Rechteverwaltung.
- Keine externen Live-Datenquellen.
- Fokus auf OpenAI als erste LLM-Implementierung.
- OCR wird nur als Fallback genutzt.
- Prompt-/Antwortqualität hängt vom Eingabedokument und LLM-Verhalten ab.

---

## 7) Erweiterbarkeit

Das Projekt ist modular vorbereitet. Typische Erweiterungen:

- **Weitere LLM-Provider**: neuen Adapter unter `services/llm/` ergänzen.
- **Alternative OCR-Backends**: `ocr_service.py` austauschbar erweitern.
- **Zusätzliche Ausgabeziele**: neben CSV z. B. API/DB-Writer ergänzen.
- **Neue Parsing-Strategien**: Parser in `parsers/` erweitern.
- **Zusätzliche CLI-Kommandos**: Subcommands in `cli.py` ergänzen.

---

## 8) Betrieb & Troubleshooting

### Häufige Fehlerbilder und Lösungen

1. **`OPENAI_API_KEY` fehlt**
   - Symptom: LLM-Aufrufe schlagen mit Konfigurations-/Authentifizierungsfehler fehl.
   - Lösung:
     - `export OPENAI_API_KEY="<dein_api_key>"`
     - Lauf neu starten.

2. **OCR nicht verfügbar / OCR-Fehler**
   - Symptom: Bei nicht durchsuchbaren PDFs scheitert Verarbeitung im OCR-Schritt.
   - Lösung:
     - OCR-Abhängigkeiten im System installieren/prüfen.
     - Testweise ein durchsuchbares PDF nutzen.
     - Logs auf `ocr.*`/`pdf.*` Events prüfen.

3. **Parsing-Probleme bei LLM-Antworten**
   - Symptom: Produkte/Bewertungen werden als `uncertain` markiert oder Parsing-Fehler geloggt.
   - Lösung:
     - Prompts in `config/config.yaml` präzisieren (explizites JSON-Format).
     - Dokumentqualität prüfen (Textrauschen/Scanqualität).
     - Log-Einträge zu `parsing`/`llm` analysieren.

4. **Keine neuen Ergebnisse trotz vorhandener PDFs**
   - Symptom: Dateien werden übersprungen.
   - Ursache: PDFs bereits in Statusdatei markiert.
   - Lösung:
     - `data/state/processed_files.json` prüfen.
     - Für erneuten Lauf Statusdatei gezielt zurücksetzen.

### Kurz-Runbook (Fehlersuche)

1. Prüfen, ob `config/config.yaml` geladen werden kann.
2. Prüfen, ob `OPENAI_API_KEY` gesetzt ist.
3. Prüfen, ob Eingabedateien in `data/input` liegen.
4. Letzte Logdatei in `logs/` auf `ERROR`/`WARNING` und Eventnamen prüfen.
5. Prüfen, ob in `data/output` neue CSV-Artefakte erstellt wurden.
6. Bei OCR-/Parsing-Problemen zuerst mit einem kleinen, gut lesbaren Test-PDF reproduzieren.

---

## 9) Qualitätssicherung

Lokaler Standard-Check:

```bash
make check
```

Führt aus:

- Format-Checks
- Linting
- Type-Checks
- Tests inkl. Coverage

---

## 10) Weiterführende Dokumente

- `docs/UMSETZUNGSPLAN_V1.md` – Task-Plan für V1
- `docs/ADR-0003-fehler-und-logging-konzept.md` – verbindliche Fehler-/Logging-Richtlinie
