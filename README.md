# Supply Chain Checker

Supply Chain Checker ist ein lokales Python-CLI-Tool, das beliebige PDFs einliest, bei Bedarf per OCR Text gewinnt und mit Hilfe eines LLMs daraus erwähnte Produkte strukturiert extrahiert. Anschließend bewertet es jedes Produkt einzeln anhand konfigurierbarer Prompts hinsichtlich Lieferkettenrisiko, Risikostufe und erwarteter Preisänderung und speichert die Ergebnisse als CSV.

---

## Überblick

Das Projekt ist als schnell lauffähiges, aber sauber aufgebautes MVP konzipiert.  
Der Fokus liegt auf:

- robuster PDF-Verarbeitung
- OCR-Fallback bei nicht durchsuchbaren Dokumenten
- LLM-gestützter Produktextraktion
- separater Risikobewertung pro Produkt
- sauberem Fehlerhandling
- ausführlichem Logging
- guter Testbarkeit
- klarer Erweiterbarkeit

Supply Chain Checker arbeitet vollständig lokal als **CLI-Anwendung** und wird über eine **YAML-Konfigurationsdatei** gesteuert.

---

## Hauptfunktionen

### 1. Produktextraktion aus PDFs
- verarbeitet automatisch alle neuen PDFs in einem konfigurierten Eingabeverzeichnis
- liest vorhandenen PDF-Text direkt aus
- nutzt OCR nur dann, wenn kein brauchbarer Text vorhanden ist
- extrahiert mit Hilfe eines LLMs alle im Dokument erwähnten Produkte
- speichert die Ergebnisse pro Lauf in einer neuen CSV-Datei

### 2. Risikobewertung pro Produkt
- verwendet automatisch die neueste Extraktions-CSV
- bewertet jedes Produkt einzeln per LLM
- nutzt dafür einen konfigurierbaren Prompt aus der YAML-Datei
- erzeugt pro Lauf eine neue Bewertungs-CSV
- zeigt die Ergebnisse zusätzlich in der Konsole an

### 3. Statusverwaltung
- merkt sich bereits verarbeitete PDFs über eine Statusdatei
- überspringt bekannte Dateien in späteren Läufen

### 4. Robuste Verarbeitung
- Fehler in einzelnen PDFs stoppen nicht den gesamten Lauf
- Fehler in einzelnen Produkten stoppen nicht den gesamten Lauf
- unvollständige oder unsichere Einträge werden gekennzeichnet statt still verworfen

---

## Geplanter Ablauf

Das Tool arbeitet in zwei getrennten Schritten:

### Schritt 1: Extraktion
1. PDFs aus dem Eingabeverzeichnis finden
2. prüfen, ob die Datei bereits verarbeitet wurde
3. Text direkt extrahieren oder OCR ausführen
4. Produkte per LLM aus dem Dokument extrahieren
5. Ergebnisse in einer Extraktions-CSV speichern
6. Statusdatei aktualisieren

### Schritt 2: Bewertung
1. neueste Extraktions-CSV laden
2. jedes Produkt einzeln bewerten
3. Risikoergebnis strukturiert erfassen
4. neue Bewertungs-CSV erzeugen
5. Resultate zusätzlich in der Konsole ausgeben

---

## Extrahierte Produktdaten

### Pflichtfelder
- Produktname
- Dokumentenname / Quelle
- Menge
- Lieferant

### Optionale Felder
- Hersteller
- Artikelnummer

Wenn ein Produkt nicht sicher oder nicht vollständig extrahiert werden kann, wird es trotzdem gespeichert und entsprechend gekennzeichnet.

---

## Bewertungsergebnis pro Produkt

Für jedes bewertbare Produkt soll das System mindestens liefern:

- **Begründung** als Freitext mit maximal 100 Wörtern
- **Risikostufe** auf einer Skala von 1 bis 10
- **geschätzte Preisänderung in Prozent**

Produkte, die nicht sinnvoll bewertet werden können, werden in der Ausgabedatei als übersprungen markiert, inklusive Begründung.

---

## Technische Eckdaten

- **Sprache:** Python
- **Ausführung:** lokales CLI-Tool
- **Konfiguration:** YAML
- **Zwischenspeicherung:** CSV
- **Ausgabe:** CSV + Konsolenausgabe
- **LLM in V1:** OpenAI API
- **Architekturziel:** LLM-Anbindung austauschbar kapseln

---

## Projektstruktur

Eine mögliche Zielstruktur des Projekts:

```text
supply-chain-checker/
├─ README.md
├─ AGENTS.md
├─ pyproject.toml
├─ requirements.txt
├─ .env.example
├─ config/
│  └─ config.example.yaml
├─ data/
│  ├─ input/
│  ├─ output/
│  └─ state/
├─ logs/
├─ src/
│  └─ supply_chain_checker/
│     ├─ cli.py
│     ├─ config.py
│     ├─ logging_setup.py
│     ├─ models/
│     ├─ services/
│     │  ├─ pdf_reader.py
│     │  ├─ ocr_service.py
│     │  ├─ extraction_service.py
│     │  ├─ assessment_service.py
│     │  ├─ status_service.py
│     │  ├─ csv_service.py
│     │  └─ llm/
│     │     ├─ base.py
│     │     └─ openai_client.py
│     ├─ parsers/
│     └─ utils/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/
└─ sample_data/
```

## CLI-Kommandos

Mindestens diese Befehle werden unterstützt:

```bash
python -m supply_chain_checker extract --config config/config.yaml
python -m supply_chain_checker assess --config config/config.yaml
```
