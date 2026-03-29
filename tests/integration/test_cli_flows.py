"""Integration tests for end-to-end CLI command flows."""

from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook, load_workbook

from supply_chain_checker import cli
from supply_chain_checker.services.llm.base import LlmClientError, LlmRequestContext

_MINIMAL_CONFIG = """
paths:
  input_dir: data/input
  output_dir: data/output
  state_dir: data/state
  logs_dir: logs
logging:
  level: INFO
  file_name: app.log
llm:
  provider: openai
  model: gpt-4.1-mini
  timeout_seconds: 30
  max_retries: 2
  temperature: 0.0
parameters:
  use_ocr_fallback: true
  max_products_per_document: 100
  max_assessment_reason_words: 100
  on_corrupt_status_file: abort
prompts:
  extraction: "Extract from {document_name}: {document_text}"
  assessment: "Assess {product_name} from {supplier}"
"""


def test_extract_end_to_end_uses_mocked_ocr_and_llm(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(_MINIMAL_CONFIG, encoding="utf-8")

    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "invoice_ocr.pdf").write_text("raw-bytes", encoding="utf-8")

    def _direct_extractor(_pdf_path: Path) -> str:
        return "  "

    def _ocr_engine(_pdf_path: Path) -> str:
        return "Widget A quantity 10 supplier ACME"

    def _mock_extract_products(self, *, prompt: str, context: LlmRequestContext) -> str:
        assert "invoice_ocr.pdf" in prompt
        assert context == LlmRequestContext(run_id=context.run_id, command="extract")
        return (
            '{"products": ['
            '{"product_name": "Widget A", "quantity": "10", '
            '"supplier": "ACME", "extraction_status": "confirmed"}]}'
        )

    monkeypatch.setattr(cli, "extract_text_with_pypdf", _direct_extractor)
    monkeypatch.setattr(cli, "_run_ocr_placeholder", _ocr_engine)
    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.OpenAIClient.extract_products",
        _mock_extract_products,
    )
    monkeypatch.setattr(
        "sys.argv", ["supply-chain-checker", "extract", "--config", str(config_file)]
    )

    assert cli.main() == 0

    extraction_files = list((tmp_path / "data" / "output").glob("extraction_*.xlsx"))
    assert len(extraction_files) == 1

    rows = list(
        load_workbook(extraction_files[0], read_only=True, data_only=True).active.iter_rows(
            values_only=True
        )
    )

    assert len(rows) == 2
    assert rows[1][1] == "invoice_ocr.pdf"
    assert rows[1][2] == "Widget A"
    assert rows[1][7] == "confirmed"

    log_content = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "run.started" in log_content
    assert "ocr.started" in log_content
    assert "ocr.succeeded" in log_content
    assert "csv.write.succeeded" in log_content


def test_assess_end_to_end_from_extraction_csv_with_mocked_llm(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(_MINIMAL_CONFIG, encoding="utf-8")

    output_dir = tmp_path / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    extraction_xlsx = output_dir / "extraction_20260327T120000Z_runabc123456.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "run_id",
            "document_name",
            "product_name",
            "quantity",
            "supplier",
            "manufacturer",
            "article_number",
            "extraction_status",
            "extraction_hint",
        ]
    )
    ws.append(["run1", "invoice_1.pdf", "Widget A", "10", "ACME", "", "", "confirmed", ""])
    wb.save(extraction_xlsx)

    def _mock_assess_product(self, *, prompt: str, context: LlmRequestContext) -> str:
        assert "Widget A" in prompt
        assert context.command == "assess"
        return json.dumps(
            {
                "risikostufe": 2,
                "preisänderung_prozent": 1.5,
                "begründung": "Lieferkette derzeit stabil.",
            }
        )

    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.OpenAIClient.assess_product",
        _mock_assess_product,
    )
    monkeypatch.setattr(
        "sys.argv", ["supply-chain-checker", "assess", "--config", str(config_file)]
    )

    assert cli.main() == 0

    assessment_files = list(output_dir.glob("assessment_*.xlsx"))
    assert len(assessment_files) == 1

    rows = list(
        load_workbook(assessment_files[0], read_only=True, data_only=True).active.iter_rows(
            values_only=True
        )
    )

    assert len(rows) == 2
    assert rows[1][9] == "assessed"
    assert rows[1][11] == 2
    assert rows[1][12] == 1.5

    status_payload = json.loads(
        (tmp_path / "data" / "state" / "processed_files.json").read_text(encoding="utf-8")
    )
    assert status_payload["processed_files"] == []

    log_content = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "assessment.input.selected" in log_content
    assert "assessment.succeeded" in log_content
    assert "run.finished" in log_content


def test_run_end_to_end_executes_extract_then_assess(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(_MINIMAL_CONFIG, encoding="utf-8")

    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "invoice_ocr.pdf").write_text("raw-bytes", encoding="utf-8")

    def _direct_extractor(_pdf_path: Path) -> str:
        return "  "

    def _ocr_engine(_pdf_path: Path) -> str:
        return "Widget A quantity 10 supplier ACME"

    def _mock_extract_products(self, *, prompt: str, context: LlmRequestContext) -> str:
        assert "invoice_ocr.pdf" in prompt
        assert context.command == "extract"
        return (
            '{"products": ['
            '{"product_name": "Widget A", "quantity": "10", '
            '"supplier": "ACME", "extraction_status": "confirmed"}]}'
        )

    def _mock_assess_product(self, *, prompt: str, context: LlmRequestContext) -> str:
        assert "Widget A" in prompt
        assert context.command == "assess"
        return json.dumps(
            {
                "risikostufe": 3,
                "preisänderung_prozent": 4.0,
                "begründung": "Sequential run validated.",
            }
        )

    monkeypatch.setattr(cli, "extract_text_with_pypdf", _direct_extractor)
    monkeypatch.setattr(cli, "_run_ocr_placeholder", _ocr_engine)
    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.OpenAIClient.extract_products",
        _mock_extract_products,
    )
    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.OpenAIClient.assess_product",
        _mock_assess_product,
    )
    monkeypatch.setattr("sys.argv", ["supply-chain-checker", "run", "--config", str(config_file)])

    assert cli.main() == 0

    output_dir = tmp_path / "data" / "output"
    extraction_files = list(output_dir.glob("extraction_*.xlsx"))
    assessment_files = list(output_dir.glob("assessment_*.xlsx"))
    assert len(extraction_files) == 1
    assert len(assessment_files) == 1

    rows = list(
        load_workbook(assessment_files[0], read_only=True, data_only=True).active.iter_rows(
            values_only=True
        )
    )

    assert len(rows) == 2
    assert rows[1][2] == "Widget A"
    assert rows[1][9] == "assessed"
    assert rows[1][11] == 3

    log_content = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "command.received" in log_content
    assert "assessment.succeeded" in log_content


def test_extract_continues_after_llm_failure_for_single_document(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(_MINIMAL_CONFIG, encoding="utf-8")

    input_dir = tmp_path / "data" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "invoice_fail.pdf").write_text("raw-bytes", encoding="utf-8")
    (input_dir / "invoice_ok.pdf").write_text("raw-bytes", encoding="utf-8")

    def _direct_extractor(pdf_path: Path) -> str:
        return f"Text for {pdf_path.name}"

    def _mock_extract_products(self, *, prompt: str, context: LlmRequestContext) -> str:
        assert context.command == "extract"
        if "invoice_fail.pdf" in prompt:
            raise LlmClientError("provider unreachable")
        return (
            '{"products": ['
            '{"product_name": "Widget A", "quantity": "10", '
            '"supplier": "ACME", "extraction_status": "confirmed"}]}'
        )

    monkeypatch.setattr(cli, "extract_text_with_pypdf", _direct_extractor)
    monkeypatch.setattr(
        "supply_chain_checker.services.llm.openai_client.OpenAIClient.extract_products",
        _mock_extract_products,
    )
    monkeypatch.setattr(
        "sys.argv", ["supply-chain-checker", "extract", "--config", str(config_file)]
    )

    assert cli.main() == 0

    extraction_files = list((tmp_path / "data" / "output").glob("extraction_*.xlsx"))
    assert len(extraction_files) == 1

    rows = list(
        load_workbook(extraction_files[0], read_only=True, data_only=True).active.iter_rows(
            values_only=True
        )
    )

    assert len(rows) == 3
    assert rows[1][1] == "invoice_fail.pdf"
    assert rows[1][7] == "uncertain"
    assert rows[1][8] == "Document processing failed: LlmClientError"
    assert rows[2][2] == "Widget A"
