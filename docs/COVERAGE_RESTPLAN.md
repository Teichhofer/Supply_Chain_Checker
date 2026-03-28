# Coverage-Status und Restplan (Phase 6.6)

## Messung
- Messkommando: `python -m pytest --cov=src/supply_chain_checker --cov-report=term-missing`
- Stand: **100 % Line Coverage** für `src/supply_chain_checker`.

## Bewertung
- Das Ziel von Phase 6.6 (100 % Coverage) ist aktuell erfüllt.
- Es bestehen daher keine offenen Coverage-Lücken im aktuellen Code-Stand.

## Restplan bei zukünftigen Abweichungen
Falls die Coverage bei künftigen Änderungen unter 100 % fällt, wird wie folgt priorisiert:
1. **Kern-CLI-Flows (`extract`, `assess`)** zuerst absichern.
2. **Fehlerdomänen** (Configuration/PDF/OCR/LLM/Parsing/IO/Status) mit Negativtests ergänzen.
3. **Logging-Pfade** (Start/Ende/Skip/Fehler + Level WARNING/ERROR) gezielt erweitern.
4. **Dateiauswahl-Logik** für Extraktions-CSV (Timestamp-Tie/invalid names) regressionssicher halten.

## Definition of Done
- Keine ungetesteten neuen Branches in Kernservices.
- Coverage wieder bei 100 % oder mit begründeter, dokumentierter Ausnahme.
