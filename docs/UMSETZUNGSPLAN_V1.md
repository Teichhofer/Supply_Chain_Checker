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

**Ergebnis:** Lauffähiges Grundgerüst mit klarer Projektstruktur und dokumentierten Einstiegspunkten.

**Akzeptanzkriterien:**
- `python -m supply_chain_checker --help` liefert CLI-Hilfe.
- Standardordner sind dokumentiert und im README erklärt.

### Task 0.2: Qualitäts-Tooling aktivieren
- Linter/Formatter/Type-Checks konfigurieren (z. B. Ruff, Black, MyPy).
- Test-Setup (pytest + coverage) konfigurieren.

**Ergebnis:** Reproduzierbare Qualitätschecks lokal und in CI.

**Akzeptanzkriterien:**
- Ein einziger Quality-Command (z. B. `make check` oder dokumentierter gleichwertiger Ablauf) ist vorhanden.
- Coverage-Report wird erzeugt.

### Task 0.3: Fehler- und Logging-Konzept als ADR festhalten
- Fehlerklassen definieren (Konfiguration, PDF, OCR, LLM, Parsing, IO, Status).
- Logging-Events und Struktur festlegen.

**Ergebnis:** Teamweit verbindliche Leitlinie für Fehlerbehandlung und Logging.

**Akzeptanzkriterien:**
- Dokument in `docs/` vorhanden.
- Alle Kernmodule verwenden benannte Logger.

---

## Phase 1 – Konfiguration & Core-Infrastruktur (Tag 1–2)

### Task 1.1: YAML-Konfigurationsmodell implementieren
- Konfigurationsschema für Pfade, Logging, LLM, Prompts, Parameter definieren.
- Validierung und sinnvolle Defaults implementieren.

**Ergebnis:** Typisiertes, validiertes Konfigurationsmodell mit klaren Defaults.

**Akzeptanzkriterien:**
- Fehlerhafte Konfiguration bricht kontrolliert mit klarer Fehlermeldung ab.
- Beispielkonfiguration deckt alle Pflichtfelder ab.

### Task 1.2: Logging-Setup umsetzen
- File-Logging + Level aus YAML.
- Einheitliches Log-Format (Zeit, Level, Modul, Run-ID, Nachricht).

**Ergebnis:** Zentrales Logging-Setup mit konfigurierbaren Levels und konsistentem Format.

**Akzeptanzkriterien:**
- Start/Ende jedes Laufs im Log sichtbar.
- Konfigurierbare Level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) funktionieren.

### Task 1.3: Run-Kontext und Lauf-ID
- Pro Lauf eindeutige `run_id`/Timestamp erzeugen.
- Lauf-ID in CSV und Logs durchreichen.

**Ergebnis:** Zentraler Laufkontext zur Korrelation von Logs und Artefakten.

**Akzeptanzkriterien:**
- Extraktions- und Bewertungsdateien sind eindeutig je Lauf.
- Korrelation zwischen Logeinträgen und CSV möglich.

---

## Phase 2 – Statusverwaltung & Dateiauswahl (Tag 2)

### Task 2.1: Status-Service implementieren
- Statusdatei laden/schreiben.
- Felder: Dateiname + Verarbeitungszeitpunkt (optional Hash erweiterbar).

**Ergebnis:** Persistenter Status-Service zur Nachverfolgung verarbeiteter Dateien.

**Akzeptanzkriterien:**
- Statusdatei wird bei Start gelesen und nach Verarbeitung aktualisiert.
- Einträge enthalten mindestens Dateiname und Zeitstempel.

### Task 2.2: Beschädigte Statusdatei robust behandeln
- Kontrollierter Fallback (z. B. leere Liste + Warnung) oder harter Abbruch je Konfiguration.
- Immer mit sauberem Logging.

**Ergebnis:** Defensives Fehlerverhalten bei inkonsistentem Statuszustand.

**Akzeptanzkriterien:**
- Defekte Statusdatei erzeugt klaren Logeintrag mit Fehlerdomäne.
- Verhalten (Fallback oder Abbruch) ist konfigurierbar und reproduzierbar.

### Task 2.3: PDF-Dateifilterung
- Alle PDFs im Eingabeordner erkennen.
- Bereits verarbeitete Dateien überspringen.

**Ergebnis:** Deterministische Auswahl der zu verarbeitenden neuen PDFs.

**Akzeptanzkriterien:**
- Nur neue PDFs werden verarbeitet.
- Defekte Statusdatei führt nicht zu stillen Fehlern.

---

## Phase 3 – Extraktionspipeline (`extract`) (Tag 3–4)

### Task 3.1: PDF-Reader + OCR-Fallback
- Direkte Textextraktion zuerst.
- OCR nur bei unbrauchbarem/leerem Text.

**Ergebnis:** Robuste Texterfassung mit bevorzugter Direkt-Extraktion und bedarfsabhängigem OCR-Fallback.

**Akzeptanzkriterien:**
- Bei vorhandenem maschinenlesbarem Text wird OCR nicht aufgerufen.
- Bei leerem/unbrauchbarem Text wird OCR aufgerufen und das Ereignis geloggt.

### Task 3.2: Extraktions-LLM-Schicht integrieren
- Prompt-Builder für Produktextraktion.
- LLM-Aufruf gekapselt via Interface.

**Ergebnis:** Austauschbare LLM-Extraktionsschicht ohne API-Leak in die Business-Logik.

**Akzeptanzkriterien:**
- Extraktion nutzt nur das definierte LLM-Interface.
- Prompt-Erstellung ist separat testbar.

### Task 3.3: Parsing und Normalisierung
- LLM-Ausgabe robust in Produktobjekte überführen.
- Pflicht-/Optionalfelder konsistent setzen.
- Unsichere Extraktionen markieren (`extraktionsstatus`, `extraktionshinweis`).

**Ergebnis:** Konsistente, validierte Produktdatensätze inklusive Unsicherheitskennzeichnung.

**Akzeptanzkriterien:**
- Ungültige oder unvollständige LLM-Antworten führen zu kontrollierten Parsing-Fehlern.
- Unsichere Extraktionen sind eindeutig markiert statt verworfen.

### Task 3.4: Extraktions-CSV schreiben
- Pro Lauf neue Datei mit Pflichtspalten.
- Dateinamenkonvention inkl. Timestamp/Run-ID.

**Ergebnis:** Versionierte, nachvollziehbare Extraktionsartefakte pro Lauf.

**Akzeptanzkriterien:**
- Pro Lauf wird genau eine neue Extraktions-CSV erstellt.
- Pflichtspalten sind vollständig vorhanden.

### Task 3.5: Fehlerisolation auf Dokumentebene
- Fehler in einer PDF dürfen Lauf nicht stoppen.
- Fehler erfassen und zur nächsten Datei weitergehen.

**Ergebnis:** Fehlertoleranter Extraktionslauf mit Fortschritt trotz Einzeldokument-Fehlern.

**Akzeptanzkriterien:**
- `extract` verarbeitet mehrere PDFs robust.
- Ausgabe enthält auch unsichere/teilweise Extraktionen mit Kennzeichnung.

---

## Phase 4 – Bewertungspipeline (`assess`) (Tag 4–5)

### Task 4.1: Neueste Extraktions-CSV auswählen
- Erkennungslogik auf Dateinamen/Timestamp.
- Fehlerfall „keine Extraktionsdatei vorhanden“ sauber behandeln.

**Ergebnis:** Verlässliche Ermittlung der aktuellen Arbeitsgrundlage für Bewertungen.

**Akzeptanzkriterien:**
- `assess` nutzt automatisch die neueste Extraktionsdatei.
- Fehlende Extraktionsdatei führt zu klarer, kontrollierter Fehlermeldung.

### Task 4.2: Einzelbewertung pro Produkt
- Genau 1 LLM-Request pro Produkt.
- Keine Batch-Requests.

**Ergebnis:** Deterministischer Bewertungsfluss mit klarer Zuordnung je Produkt.

**Akzeptanzkriterien:**
- Für N Produkte werden genau N Bewertungsrequests erstellt.
- Fehlende/fehlerhafte Antworten beeinflussen andere Produkte nicht.

### Task 4.3: Bewertungs-Prompt mit Platzhaltern
- Platzhalter für Produktname, Lieferant, Menge, Hersteller, Artikelnummer etc.
- Konfigurierbare Prompt-Vorlagen aus YAML.

**Ergebnis:** Wiederverwendbares, konfigurierbares Prompt-Template für Produktbewertungen.

**Akzeptanzkriterien:**
- Prompt wird vollständig aus Produktdaten + YAML-Vorlage generiert.
- Prompt-Änderungen sind ohne Codeänderung über Konfiguration möglich.

### Task 4.4: Strukturierte Antwortverarbeitung
- Pflichtfelder: `risikostufe` (1–10), `preisänderung_prozent`, `begründung` (<=100 Wörter).
- Parsing-Fehler als Status/Grund markieren, nicht verwerfen.

**Ergebnis:** Validierte Bewertungsdaten mit transparenter Behandlung von Parse-Problemen.

**Akzeptanzkriterien:**
- Pflichtfelder werden validiert und normiert gespeichert.
- Parsing-Fehler führen zu Statusmarkierung statt Datenverlust.

### Task 4.5: Skip-Logik bei unbewertbaren Produkten
- Unvollständige/unsichere Produkte überspringen, aber in CSV behalten.
- `bewertungsstatus` + `skip_reason` setzen.

**Ergebnis:** Nachvollziehbare Skip-Strategie ohne Verlust der Prozesshistorie.

**Akzeptanzkriterien:**
- Übersprungene Produkte bleiben in der Bewertungs-CSV enthalten.
- Skip-Grund ist maschinenlesbar und im Log sichtbar.

### Task 4.6: Bewertungs-CSV + Konsolenausgabe
- Neue CSV pro Lauf.
- Mindestausgabe auf Konsole: Produktname, Lieferant, Risikostufe, Preisänderung, Status.

**Ergebnis:** Vollständiges Bewertungsergebnis als Datei und operative Sichtbarkeit in der Konsole.

**Akzeptanzkriterien:**
- Pro Lauf wird eine neue Bewertungs-CSV erzeugt.
- Fehler/Skips sind transparent und nachvollziehbar.

---

## Phase 5 – LLM-Abstraktion & Anbietertrennung (parallel zu 3/4)

### Task 5.1: Abstraktes LLM-Interface
- Einheitliche Methoden für Extraktion/Bewertung.
- Keine API-Details außerhalb der Adapter.

**Ergebnis:** Stabiles Abstraktionslayer zwischen Fachlogik und LLM-Anbieter.

**Akzeptanzkriterien:**
- Services konsumieren ausschließlich das Interface.
- Anbieterwechsel erfordert keine Änderung in Extraktions-/Bewertungsservices.

### Task 5.2: OpenAI-Adapter implementieren
- Konfigurierbares Modell/Timeout/Retry.
- Fehler in domänenspezifische Fehlerklassen mappen.

**Ergebnis:** Produktionsnaher erster LLM-Adapter mit robustem Fehlerhandling.

**Akzeptanzkriterien:**
- Modell, Timeout und Retry sind über YAML steuerbar.
- API-Fehler werden als `LlmClientError` (oder Subtypen) weitergegeben.

### Task 5.3: Prompt-Building vom API-Code trennen
- Prompt-Module unabhängig testbar.

**Ergebnis:** Entkoppeltes Prompting mit hoher Testbarkeit.

**Akzeptanzkriterien:**
- Prompt-Building enthält keine API-Aufrufe.
- Prompt-Builder sind per Unit-Tests validiert.

---

## Phase 6 – Tests mit hoher Abdeckung (Tag 5–7)

### Task 6.1: Unit-Tests
- Konfigurationsladen & Validierung.
- Status-Service inkl. beschädigter Datei.
- Parser für Extraktion/Bewertung.
- CSV-Writer.
- Prompt-Builder.

**Ergebnis:** Hohe funktionale Sicherheit auf Komponentenebene.

**Akzeptanzkriterien:**
- Für alle Kernservices existieren Unit-Tests.
- Kritische Randfälle und Fehlerszenarien sind abgedeckt.

### Task 6.2: Integrationstests für CLI-Flows
- `extract` End-to-End mit gemocktem LLM/OCR.
- `assess` End-to-End auf Basis einer Extraktions-CSV.

**Ergebnis:** Verifizierte End-to-End-Funktionsfähigkeit der beiden Hauptkommandos.

**Akzeptanzkriterien:**
- Beide CLI-Flows sind automatisiert testbar.
- Tests prüfen Dateien, Logs und Exit-Codes.

### Task 6.3: Fehler- und Skip-Szenarien
- PDF-Fehler, API-Fehler, Parsing-Fehler, fehlende Felder.
- Sicherstellen, dass Läufe fortgesetzt werden.

**Ergebnis:** Nachweis der Robustheit bei partiellen Fehlern.

**Akzeptanzkriterien:**
- Fehler in Einzelfällen stoppen den Gesamtlauf nicht.
- Fehler und Skips sind in Logs/CSV eindeutig sichtbar.

### Task 6.4: „Neueste Extraktionsdatei“-Auswahl testen
- Mehrere Dateien, korrekte Auswahl, Grenzfälle.

**Ergebnis:** Verlässliche Dateiauswahl ohne Race-/Sortierfehler.

**Akzeptanzkriterien:**
- Bei mehreren Dateien wird konsistent die neueste Datei gewählt.
- Grenzfälle (gleicher Timestamp, ungültige Namen) sind getestet.

### Task 6.5: Logging-relevante Pfade testen
- Kritische Events werden erzeugt (Start/Ende, Skip, Fehler).

**Ergebnis:** Absicherung der observability-relevanten Pfade.

**Akzeptanzkriterien:**
- Erwartete Eventnamen werden in Tests überprüft.
- Recoverable Fehler sind `WARNING`, nicht-recoverable Fehler `ERROR`.

### Task 6.6: Coverage-Ziel und Restplan
- Coverage messen und gegen Ziel 100 % prüfen.
- Bei Abweichung Restlücken priorisieren und dokumentieren.

**Ergebnis:** Transparente Qualitätseinschätzung inklusive Maßnahmenplan.

**Akzeptanzkriterien:**
- Zielwert 100 % Coverage erreicht oder begründet knapp darunter.
- Für verbleibende Lücken existiert ein dokumentierter Restplan.

---

## Phase 7 – Dokumentation, Beispielkonfiguration, Abschluss (Tag 7)

### Task 7.1: README vervollständigen
- Architekturüberblick, Installation, Konfiguration, CLI-Beispiele, Grenzen V1, Erweiterbarkeit.

**Ergebnis:** Vollständige Onboarding-Dokumentation für Entwickler und Betreiber.

**Akzeptanzkriterien:**
- Alle Pflichtthemen sind im README enthalten.
- CLI-Beispiele sind direkt ausführbar.

### Task 7.2: Beispielkonfiguration und Beispielordner
- `config.example.yaml` vollständig und nutzbar.
- Struktur für `data/input`, `data/output`, `data/state`, `logs` erklären.

**Ergebnis:** Sofort nutzbarer Beispiel-Setup für lokale Erstinbetriebnahme.

**Akzeptanzkriterien:**
- Beispielkonfiguration funktioniert ohne manuelle Ergänzung außer Secrets.
- Verzeichnisstruktur ist nachvollziehbar dokumentiert.

### Task 7.3: Betriebs- und Troubleshooting-Hinweise
- Häufige Fehlerbilder (API-Key fehlt, OCR fehlt, Parsing-Probleme).
- Checkliste zur Fehlersuche.

**Ergebnis:** Betriebsleitfaden für typische Support- und Fehlerfälle.

**Akzeptanzkriterien:**
- Mindestens die Top-Fehlerbilder sind mit Lösungsschritten dokumentiert.
- Eine kurze Runbook-Checkliste ist enthalten.

---

## 3) Backlog im umsetzbaren Task-Format (für Tickets)

## Epic A – CLI & Konfiguration

### Ticket A1: CLI-Basis mit Subcommands `extract`/`assess` und `--config`
**Ergebnis:** Einheitlicher CLI-Einstiegspunkt für beide Hauptprozesse.

**Akzeptanzkriterien:**
- `extract` und `assess` sind als Subcommands verfügbar.
- `--config` wird von beiden Kommandos korrekt verarbeitet.

### Ticket A2: YAML-Loader mit Schema-Validierung
**Ergebnis:** Fehlertoleranter Konfigurations-Loader mit klaren Validierungsfehlern.

**Akzeptanzkriterien:**
- Ungültige Konfiguration führt zu `ConfigurationError`.
- Pflichtfelder werden strikt geprüft.

### Ticket A3: Laufkontext (`run_id`, Timestamp, Pfade) zentralisieren
**Ergebnis:** Einheitliche Laufmetadaten in allen Services.

**Akzeptanzkriterien:**
- `run_id` ist in Logs und Artefakten vorhanden.
- Pfade und Laufparameter werden zentral erzeugt und verteilt.

## Epic B – Verarbeitung `extract`

### Ticket B1: PDF-Dateien finden + Statusfilter
**Ergebnis:** Verarbeitungsmenge enthält ausschließlich neue PDFs.

**Akzeptanzkriterien:**
- Bereits verarbeitete Dateien werden übersprungen.
- Dateisuche verarbeitet nur `.pdf`-Dateien.

### Ticket B2: PDF-Text direkt extrahieren
**Ergebnis:** Primärer Reader liefert Text aus maschinenlesbaren PDFs.

**Akzeptanzkriterien:**
- Lesbare PDFs werden ohne OCR verarbeitet.
- Reader-Fehler werden als `PdfProcessingError` gemappt.

### Ticket B3: OCR-Fallback bei fehlendem Text
**Ergebnis:** OCR ergänzt fehlende Extraktion robust.

**Akzeptanzkriterien:**
- OCR startet nur bei leerem/unbrauchbarem Text.
- OCR-Fehler werden als `OcrProcessingError` gemappt.

### Ticket B4: LLM-Extraktion implementieren
**Ergebnis:** Produktdaten werden per LLM aus Dokumenttext extrahiert.

**Akzeptanzkriterien:**
- LLM-Aufruf läuft über das abstrahierte Interface.
- Fehlgeschlagene Calls stoppen den Gesamtlauf nicht.

### Ticket B5: Extraktionsparser + Unsicherheitsmarkierung
**Ergebnis:** LLM-Antworten werden in robuste Produktobjekte normalisiert.

**Akzeptanzkriterien:**
- Parser setzt Pflichtfelder oder markiert Datensatz als unsicher.
- Parse-Fehler werden als `ParsingError` geloggt.

### Ticket B6: Extraktions-CSV schreiben
**Ergebnis:** Persistente Extraktionsdatei pro Lauf.

**Akzeptanzkriterien:**
- CSV enthält definierte Pflichtspalten.
- Dateiname enthält Run-Kontext (Timestamp/`run_id`).

### Ticket B7: Statusdatei nach erfolgreicher Dokumentverarbeitung aktualisieren
**Ergebnis:** Fortschritt wird laufend und konsistent gespeichert.

**Akzeptanzkriterien:**
- Erfolgreiche Dokumente werden unmittelbar im Status registriert.
- Schreibfehler werden als `StatusTrackingError` oder `StorageIOError` behandelt.

## Epic C – Verarbeitung `assess`

### Ticket C1: Neueste Extraktions-CSV finden
**Ergebnis:** Bewertungsworkflow startet mit aktuellster Extraktionsbasis.

**Akzeptanzkriterien:**
- Auswahl funktioniert deterministisch über Timestamp/Dateikonvention.
- Kein Treffer führt zu klarer Fehlermeldung und Exit-Code.

### Ticket C2: Produktweise Bewertungsrequests (1 Produkt = 1 Request)
**Ergebnis:** Feingranulare Bewertung mit isolierbarem Fehlerverhalten.

**Akzeptanzkriterien:**
- Für jedes Produkt genau ein Request.
- Fehler einzelner Produkte beeinflussen andere nicht.

### Ticket C3: Bewertungsparser mit Feldvalidierung
**Ergebnis:** Strukturierte, validierte Bewertungsdaten.

**Akzeptanzkriterien:**
- `risikostufe`, `preisänderung_prozent`, `begründung` werden validiert.
- Verletzungen werden als Status + Grund dokumentiert.

### Ticket C4: Skip-Logik bei unvollständigen/unsicheren Datensätzen
**Ergebnis:** Kontrolliertes Überspringen ohne Datenverlust.

**Akzeptanzkriterien:**
- Übersprungene Einträge bleiben in der Ausgabe.
- `bewertungsstatus` und `skip_reason` sind gesetzt.

### Ticket C5: Bewertungs-CSV schreiben
**Ergebnis:** Nachvollziehbare Ergebnisdatei pro Bewertungslauf.

**Akzeptanzkriterien:**
- Pro Lauf entsteht genau eine neue Bewertungs-CSV.
- Alle verarbeiteten Produkte sind enthalten.

### Ticket C6: Ergebniszeilen auf der Konsole ausgeben
**Ergebnis:** Operative Sichtbarkeit wichtiger Bewertungsergebnisse.

**Akzeptanzkriterien:**
- Pro Produkt wird mindestens Name, Lieferant, Risiko, Preisänderung, Status ausgegeben.
- Skips und Fehler sind in der Ausgabe erkennbar.

## Epic D – LLM & Integrationen

### Ticket D1: LLM-Interface definieren
**Ergebnis:** Anbieterunabhängige Schnittstelle für LLM-Operationen.

**Akzeptanzkriterien:**
- Interface deckt Extraktion und Bewertung ab.
- Business-Services enthalten keine anbieterabhängigen API-Details.

### Ticket D2: OpenAI-Client als Adapter implementieren
**Ergebnis:** Erste konkrete Provider-Integration über Adapter-Muster.

**Akzeptanzkriterien:**
- Konfigurierbares Modell/Timeout/Retry.
- Fehler werden domänenspezifisch gemappt und geloggt.

### Ticket D3: Retry-/Timeout-/Fehler-Mapping sauber kapseln
**Ergebnis:** Wiederverwendbare Resilienzlogik für LLM-Calls.

**Akzeptanzkriterien:**
- Retry-/Timeout-Verhalten ist zentral implementiert und testbar.
- Aufrufer erhalten nur domänenspezifische Exceptions.

## Epic E – Qualitätssicherung

### Ticket E1: Unit-Tests für alle Services
**Ergebnis:** Hohe Abdeckung zentraler Modulverantwortungen.

**Akzeptanzkriterien:**
- Jeder Service besitzt mindestens einen fokussierten Unit-Test.
- Kritische Fehlerpfade sind abgedeckt.

### Ticket E2: Integrationstests für beide CLI-Flows
**Ergebnis:** Reproduzierbare End-to-End-Validierung.

**Akzeptanzkriterien:**
- `extract` und `assess` laufen als Integrationstest.
- Artefakte und Exit-Codes werden geprüft.

### Ticket E3: Fehler- und Fortsetzungslogik testen
**Ergebnis:** Nachweis, dass Einzelfehler den Gesamtprozess nicht abbrechen.

**Akzeptanzkriterien:**
- Simulierte Fehlerfälle führen zu erwarteten Warnungen/Statuswerten.
- Lauf wird nach Einzelfehlern fortgesetzt.

### Ticket E4: Coverage-Report in CI integrieren
**Ergebnis:** Automatisches Qualitäts-Gate für Testabdeckung.

**Akzeptanzkriterien:**
- CI erzeugt Coverage-Report pro Pipeline-Lauf.
- Unterschreitung definierter Schwellen wird sichtbar signalisiert.

## Epic F – Dokumentation

### Ticket F1: README finalisieren
**Ergebnis:** Vollständige Projektdokumentation für Nutzung und Weiterentwicklung.

**Akzeptanzkriterien:**
- Installation, Konfiguration, CLI-Aufrufe und Grenzen V1 sind beschrieben.
- README ermöglicht reproduzierbaren Schnellstart.
