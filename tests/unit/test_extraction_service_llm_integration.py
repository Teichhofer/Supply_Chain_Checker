"""Tests for extraction service LLM integration through interface boundaries."""

from __future__ import annotations

from pathlib import Path

from supply_chain_checker.models import ExtractedProduct
from supply_chain_checker.services.extraction_service import ExtractionService
from supply_chain_checker.services.llm.base import LlmRequestContext


class DummyPdfReader:
    def read_text(
        self,
        _pdf_path: Path,
        *,
        use_ocr_fallback: bool,
        run_id: str | None,
        command: str,
    ) -> str:
        assert use_ocr_fallback is True
        assert run_id == "run123"
        assert command == "extract"
        return "Document body"


class DummyLlmClient:
    def __init__(self) -> None:
        self.prompt = ""
        self.context: LlmRequestContext | None = None

    def extract_products(self, *, prompt: str, context: LlmRequestContext) -> str:
        self.prompt = prompt
        self.context = context
        return '{"products": [{"product_name": "Screw", "quantity": "100", "supplier": "ACME"}]}'


def test_extract_products_uses_llm_interface_and_returns_structured_products() -> None:
    llm = DummyLlmClient()
    service = ExtractionService(pdf_reader=DummyPdfReader(), llm_client=llm)

    products = service.extract_products_from_document(
        pdf_path=Path("invoice.pdf"),
        extraction_prompt_template=(
            "Name={document_name}; Limit={max_products_per_document}; Text={document_text}"
        ),
        max_products_per_document=8,
        use_ocr_fallback=True,
        run_id="run123",
    )

    assert len(products) == 1
    assert isinstance(products[0], ExtractedProduct)
    assert "Name=invoice.pdf" in llm.prompt
    assert "Limit=8" in llm.prompt
    assert llm.context == LlmRequestContext(run_id="run123", command="extract")
