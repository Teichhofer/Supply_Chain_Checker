# Supply Chain Checker

Lokales Python-CLI zur Verarbeitung von PDFs, Extraktion von Produkten und Risiko-Bewertung via LLM.

## Projektstruktur

```text
supply-chain-checker/
├─ README.md
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
│     ├─ __init__.py
│     ├─ __main__.py
│     ├─ cli.py
│     ├─ config.py
│     ├─ logging_setup.py
│     ├─ models/
│     │  └─ __init__.py
│     ├─ services/
│     │  ├─ __init__.py
│     │  ├─ pdf_reader.py
│     │  ├─ ocr_service.py
│     │  ├─ extraction_service.py
│     │  ├─ assessment_service.py
│     │  ├─ status_service.py
│     │  ├─ csv_service.py
│     │  └─ llm/
│     │     ├─ __init__.py
│     │     ├─ base.py
│     │     └─ openai_client.py
│     ├─ parsers/
│     │  └─ __init__.py
│     └─ utils/
│        └─ __init__.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/
└─ sample_data/
```

## CLI (geplant)

```bash
python -m supply_chain_checker extract --config config/config.example.yaml
python -m supply_chain_checker assess --config config/config.example.yaml
```
