# Supply Chain Checker – Konkreter Umsetzungsplan (V1)

Dieser Plan übersetzt die bisherigen Projektgedanken in umsetzbare Arbeitspakete mit klaren Ergebnissen, Akzeptanzkriterien und Reihenfolge.

## 1) Zielbild und Liefergegenstand

**Liefergegenstand V1:**
Ein lokal ausführbares, testbares Python-CLI mit den Kommandos `extract` und `assess`, das PDFs robust verarbeitet, Produkte strukturiert extrahiert, diese Produkte separat bewertet und alle Ergebnisse nachvollziehbar protokolliert.

**Nicht-Ziele V1:**
GUI/Web-App, Datenbank, externe Live-Datenquellen, verpflichtendes Docker, Parallelisierung um jeden Preis.

---

## 2) Projektphasen mit Tasks

## Phase 0 – Projektaufsetzung & Standards (Tag 1)

### Task 0.1: Repository- und Basisstruktur finalisieren
- `src/`, `tests/`, `config/`, `data/`, `logs/`, `sample_data/` konsistent anlegen.
- Einstiegspunkte prüfen (`__main__.py`, CLI-Modul).

**Ergebnis:** lauffähiges Grundgerüst.

**Akzeptanzkriterien:**
- `python -m supply_chain_checker --help` liefert CLI-Hilfe.
- Standardordner sind dokumentiert und im README erklärt.

### Task 0.2: Qualitäts-Tooling aktivieren
- Linter/Formatter/Type-Checks konfigurieren (z. B. Ruff, Black, MyPy).
- Test-Setup (pytest + coverage) konfigurieren.

**Ergebnis:** reproduzierbare Qualitätschecks lokal und in CI.

**Akzeptanzkriterien:**
- Ein einziger Quality-Command (z. B. `make check` oder Dokumentation gleichwertig) ist vorhanden.
- Coverage-Report wird erzeugt.

### Task 0.3: Fehler- und Logging-Konzept als ADR festhalten
- Fehlerklassen definieren (Konfiguration, PDF, OCR, LLM, Parsing, IO, Status).
- Logging-Events und Struktur festlegen.

**Ergebnis:** Teamweit klare Leitlinie für Implementierung.

**Akzeptanzkriterien:**
- Dokument in `docs/` vorhanden.
- Alle Kernmodule verwenden benannte Logger.

---

## Phase 1 – Konfiguration & Core-Infrastruktur (Tag 1–2)

### Task 1.1: YAML-Konfigurationsmodell implementieren
- Konfigurationsschema für Pfade, Logging, LLM, Prompts, Parameter definieren.
- Validierung und sinnvolle Defaults implementieren.

**Akzeptanzkriterien:**
- Fehlerhafte Konfiguration bricht kontrolliert mit klarer Fehlermeldung ab.
- Beispielkonfiguration deckt alle Pflichtfelder ab.

### Task 1.2: Logging-Setup umsetzen
- File-Logging + Level aus YAML.
- Einheitliches Log-Format (Zeit, Level, Modul, Run-ID, Nachricht).

**Akzeptanzkriterien:**
- Start/Ende jedes Laufs im Log sichtbar.
- Konfigurierbare Level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) funktionieren.

### Task 1.3: Run-Kontext und Lauf-ID
- Pro Lauf eindeutige `run_id`/Timestamp erzeugen.
- Lauf-ID in CSV und Logs durchreichen.

**Akzeptanzkriterien:**
- Extraktions- und Bewertungsdateien sind eindeutig je Lauf.
- Korrelation zwischen Logeinträgen und CSV möglich.

---

## Phase 2 – Statusverwaltung & Dateiauswahl (Tag 2)

### Task 2.1: Status-Service implementieren
- Statusdatei laden/schreiben.
- Felder: Dateiname + Verarbeitungszeitpunkt (optional Hash erweiterbar).

### Task 2.2: Beschädigte Statusdatei robust behandeln
- Kontrollierter Fallback (z. B. leere Liste + Warnung) oder harter Abbruch je Konfiguration.
- Immer mit sauberem Logging.

### Task 2.3: PDF-Dateifilterung
- Alle PDFs im Eingabeordner erkennen.
- Bereits verarbeitete Dateien überspringen.

**Akzeptanzkriterien (Phase 2):**
- Nur neue PDFs werden verarbeitet.
- Defekte Statusdatei führt nicht zu stillen Fehlern.

---

## Phase 3 – Extraktionspipeline (`extract`) (Tag 3–4)

### Task 3.1: PDF-Reader + OCR-Fallback
- Direkte Textextraktion zuerst.
- OCR nur bei unbrauchbarem/leerem Text.

### Task 3.2: Extraktions-LLM-Schicht integrieren
- Prompt-Builder für Produktextraktion.
- LLM-Aufruf gekapselt via Interface.

### Task 3.3: Parsing und Normalisierung
- LLM-Ausgabe robust in Produktobjekte überführen.
- Pflicht-/Optionalfelder konsistent setzen.
- Unsichere Extraktionen markieren (`extraktionsstatus`, `extraktionshinweis`).

### Task 3.4: Extraktions-CSV schreiben
- Pro Lauf neue Datei mit Pflichtspalten.
- Dateinamenkonvention inkl. Timestamp/Run-ID.

### Task 3.5: Fehlerisolation auf Dokumentebene
- Fehler in einer PDF dürfen Lauf nicht stoppen.
- Fehler erfassen und zur nächsten Datei weitergehen.

**Akzeptanzkriterien (Phase 3):**
- `extract` verarbeitet mehrere PDFs robust.
- Ausgabe enthält auch unsichere/teilweise Extraktionen mit Kennzeichnung.

---

## Phase 4 – Bewertungspipeline (`assess`) (Tag 4–5)

### Task 4.1: Neueste Extraktions-CSV auswählen
- Erkennungslogik auf Dateinamen/Timestamp.
- Fehlerfall „keine Extraktionsdatei vorhanden“ sauber behandeln.

### Task 4.2: Einzelbewertung pro Produkt
- Genau 1 LLM-Request pro Produkt.
- Keine Batch-Requests.

### Task 4.3: Bewertungs-Prompt mit Platzhaltern
- Platzhalter für Produktname, Lieferant, Menge, Hersteller, Artikelnummer etc.
- Konfigurierbare Prompt-Vorlagen aus YAML.

### Task 4.4: Strukturierte Antwortverarbeitung
- Pflichtfelder: `risikostufe` (1–10), `preisänderung_prozent`, `begründung` (<=100 Wörter).
- Parsing-Fehler als Status/Grund markieren, nicht verwerfen.

### Task 4.5: Skip-Logik bei unbewertbaren Produkten
- Unvollständige/unsichere Produkte überspringen, aber in CSV behalten.
- `bewertungsstatus` + `skip_reason` setzen.

### Task 4.6: Bewertungs-CSV + Konsolenausgabe
- Neue CSV pro Lauf.
- Mindestausgabe auf Konsole: Produktname, Lieferant, Risikostufe, Preisänderung, Status.

**Akzeptanzkriterien (Phase 4):**
- `assess` nutzt automatisch die neueste Extraktionsdatei.
- Fehler/Skips sind transparent und nachvollziehbar.

---

## Phase 5 – LLM-Abstraktion & Anbietertrennung (parallel zu 3/4)

### Task 5.1: Abstraktes LLM-Interface
- Einheitliche Methoden für Extraktion/Bewertung.
- Keine API-Details außerhalb der Adapter.

### Task 5.2: OpenAI-Adapter implementieren
- Konfigurierbares Modell/Timeout/Retry.
- Fehler in domänenspezifische Fehlerklassen mappen.

### Task 5.3: Prompt-Building vom API-Code trennen
- Prompt-Module unabhängig testbar.

**Akzeptanzkriterien:**
- Austausch des Anbieters erfordert primär neuen Adapter statt Refactoring der Business-Logik.

---

## Phase 6 – Tests mit hoher Abdeckung (Tag 5–7)

### Task 6.1: Unit-Tests
- Konfigurationsladen & Validierung.
- Status-Service inkl. beschädigter Datei.
- Parser für Extraktion/Bewertung.
- CSV-Writer.
- Prompt-Builder.

### Task 6.2: Integrationstests für CLI-Flows
- `extract` End-to-End mit gemocktem LLM/OCR.
- `assess` End-to-End auf Basis einer Extraktions-CSV.

### Task 6.3: Fehler- und Skip-Szenarien
- PDF-Fehler, API-Fehler, Parsing-Fehler, fehlende Felder.
- Sicherstellen, dass Läufe fortgesetzt werden.

### Task 6.4: „Neueste Extraktionsdatei“-Auswahl testen
- Mehrere Dateien, korrekte Auswahl, Grenzfälle.

### Task 6.5: Logging-relevante Pfade testen
- Kritische Events werden erzeugt (Start/Ende, Skip, Fehler).

**Akzeptanzkriterien (Phase 6):**
- Zielwert 100 % Coverage erreicht oder transparent begründet knapp darunter mit Restplan.

---

## Phase 7 – Dokumentation, Beispielkonfiguration, Abschluss (Tag 7)

### Task 7.1: README vervollständigen
- Architekturüberblick, Installation, Konfiguration, CLI-Beispiele, Grenzen V1, Erweiterbarkeit.

### Task 7.2: Beispielkonfiguration und Beispielordner
- `config.example.yaml` vollständig und nutzbar.
- Struktur für `data/input`, `data/output`, `data/state`, `logs` erklären.

### Task 7.3: Betriebs- und Troubleshooting-Hinweise
- Häufige Fehlerbilder (API-Key fehlt, OCR fehlt, Parsing-Probleme).
- Checkliste zur Fehlersuche.

**Akzeptanzkriterien (Phase 7):**
- Ein neuer Entwickler kann das Tool nur mit README + Beispielconfig lokal starten.

---

## 3) Backlog im umsetzbaren Task-Format (für Tickets)

## Epic A – CLI & Konfiguration
1. CLI-Basis mit Subcommands `extract`/`assess` und `--config`.
2. YAML-Loader mit Schema-Validierung.
3. Laufkontext (`run_id`, Timestamp, Pfade) zentralisieren.

## Epic B – Verarbeitung `extract`
4. PDF-Dateien finden + Statusfilter.
5. PDF-Text direkt extrahieren.
6. OCR-Fallback bei fehlendem Text.
7. LLM-Extraktion implementieren.
8. Extraktionsparser + Unsicherheitsmarkierung.
9. Extraktions-CSV schreiben.
10. Statusdatei nach erfolgreicher Dokumentverarbeitung aktualisieren.

## Epic C – Verarbeitung `assess`
11. Neueste Extraktions-CSV finden.
12. Produktweise Bewertungsrequests (1 Produkt = 1 Request).
13. Bewertungsparser mit Feldvalidierung.
14. Skip-Logik bei unvollständigen/unsicheren Datensätzen.
15. Bewertungs-CSV schreiben.
16. Ergebniszeilen auf der Konsole ausgeben.

## Epic D – LLM & Integrationen
17. LLM-Interface definieren.
18. OpenAI-Client als Adapter implementieren.
19. Retry-/Timeout-/Fehler-Mapping sauber kapseln.

## Epic E – Qualitätssicherung
20. Unit-Tests für alle Services.
21. Integrationstests für beide CLI-Flows.
22. Fehler- und Fortsetzungslogik testen.
23. Coverage-Report in CI integrieren.

## Epic F – Dokumentation
24. README finalisieren.
25. Beispielkonfiguration und Beispielablauf ergänzen.
26. Grenzen/Erweiterbarkeit dokumentieren.

---

## 4) Definition of Done (DoD)

Ein Task gilt als „done“, wenn:
1. Implementierung im richtigen Modul liegt (keine Business-Logik im CLI-Entry-Point).
2. Fehlerfälle explizit behandelt und geloggt sind.
3. Unit-/Integrationstests vorhanden und grün sind.
4. Typannotationen vorhanden sind.
5. Änderungen im README oder in Doku ergänzt sind (falls relevant).

Ein Release V1 gilt als „done“, wenn zusätzlich:
- `extract` und `assess` stabil mit Beispielkonfiguration laufen,
- pro Lauf neue CSV-Dateien erzeugt werden,
- Statusverwaltung zuverlässig funktioniert,
- LLM-Schicht austauschbar gekapselt ist,
- die Testabdeckung den Zielwert erreicht.

---

## 5) Empfohlene Reihenfolge für die tatsächliche Umsetzung

1. **Phase 0–1 zuerst**: Fundament bauen (Konfig, Logging, Qualitätsregeln).
2. **Dann Phase 2**: Status und Dateiauswahl stabil machen.
3. **Dann `extract` (Phase 3)**: End-to-End bis zur Extraktions-CSV.
4. **Dann `assess` (Phase 4)**: Auf bestehender CSV-Logik aufsetzen.
5. **Parallel Phase 5**: LLM-Abstraktion sichern.
6. **Zum Schluss Phase 6–7**: Tests auf 100 % bringen und Doku finalisieren.

So entsteht früh ein nutzbarer MVP und gleichzeitig eine belastbare, erweiterbare Basis.
