"""Smoke tests for package main module."""

from __future__ import annotations

from runpy import run_module

from openpyxl import Workbook


def test_module_main_executes(monkeypatch, capsys, tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "paths:\n"
        "  input_dir: data/input\n"
        "  output_dir: data/output\n"
        "  state_dir: data/state\n"
        "  logs_dir: logs\n"
        "logging:\n"
        "  level: INFO\n"
        "  file_name: app.log\n"
        "llm:\n"
        "  provider: openai\n"
        "  model: gpt-4.1-mini\n"
        "  timeout_seconds: 30\n"
        "  max_retries: 2\n"
        "  temperature: 0.0\n"
        "prompts:\n"
        '  extraction: "Extract from {document_name}: {document_text}"\n'
        '  assessment: "Assess {product_name}"\n'
        "parameters:\n"
        "  use_ocr_fallback: true\n"
        "  max_products_per_document: 100\n"
        "  max_assessment_reason_words: 100\n"
        "  on_corrupt_status_file: abort\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
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
    sheet.append(["run123", "invoice.pdf", "Widget", "1", "ACME", "", "", "confirmed", ""])
    workbook.save(output_dir / "extraction_20260327T120000Z_run123abc456.xlsx")
    monkeypatch.setattr(
        "sys.argv", ["supply_chain_checker", "assess", "--config", str(config_file)]
    )

    try:
        run_module("supply_chain_checker", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0

    stdout = capsys.readouterr().out
    assert "Command='assess'" in stdout
