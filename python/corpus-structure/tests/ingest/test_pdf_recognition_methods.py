"""Retained integrated adoption is a pure view projection, without another recognizer."""

import json
import logging
from typing import Any
from types import SimpleNamespace

import pytest
from corpus_structure.semantic.product_reference import ProductReference
from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    GroupLabel,
    ProvenanceItem,
    Size,
)
from pydantic import ValidationError

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.ingest import pdf_recognition_methods as methods
from corpus_structure.ingest.pdf import PdfConversion, publication_payload
from corpus_structure.ingest.pdf_hierarchy import snapshot


def test_retained_integrated_projection_keeps_pin_without_inference_or_reconciliation(monkeypatch):
    document = DoclingDocument(name="Retained selected source")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    section = document.add_group(label=GroupLabel.SECTION, name="1 Selected")
    document.add_text(
        label=DocItemLabel.TEXT,
        text="selected content",
        parent=section,
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=10, t=20, r=100, b=40), charspan=(0, 16)),
    )
    native = snapshot(document)
    payload = publication_payload(
        PdfConversion("a" * 64, b"{}", native, "success", (), (), (), None),
        product_key="integrated",
        schema_digest="b" * 64,
        section_refs=frozenset({section.self_ref}),
    )
    reference = ProductReference(12, "integrated", "c" * 64)
    seen = []

    def retained(pin):
        seen.append(pin)
        return SimpleNamespace(values=lambda: payload)

    def refuse(*args, **kwargs):
        raise AssertionError("retained integrated adoption cannot perform inference")

    monkeypatch.setattr(methods, "RecognitionWorker", refuse)
    monkeypatch.setattr(methods, "_consumer_release", lambda ctx: "d" * 64)
    cfg = methods.PdfIntegratedIngestConfig(integrated_product=reference, membership="descendants")
    unit: Any = SimpleNamespace(ref=UnitRef(TaskUnitType.DOCUMENT, 1, "retained"))
    ctx: Any = SimpleNamespace(
        reader=SimpleNamespace(native_document=retained),
        run=SimpleNamespace(options={}),
        logger=logging.getLogger(__name__),
    )
    result = methods.IngestPdfIntegrated().run([unit], cfg, ctx)[0]
    assert result.outcome == ObservationOutcome.EMPTY, result.error
    assert seen == [reference]
    assert not result.native_products
    assert len(result.source_views) == 1
    assert result.source_views[0].native_product == reference
    assert "selected content" in result.source_views[0].text
    archived = json.loads(methods.IngestPdfIntegrated().original_recipe(cfg))
    assert archived["integrated_product"] == reference.values()
    assert "recognition" not in archived
    assert methods.IngestPdfIntegrated().original_recipe(
        cfg.model_copy(
            update={
                "weights_digest": "e" * 64,
                "max_regions": 1,
            }
        )
    ) == methods.IngestPdfIntegrated().original_recipe(cfg)


def test_retained_and_standard_pins_have_exclusive_roles():
    reference = ProductReference(12, "integrated", "c" * 64)
    with pytest.raises(ValidationError, match="either a Standard input"):
        methods.PdfIntegratedIngestConfig(native_product=reference, integrated_product=reference)


def test_recovery_policy_rejects_unbounded_or_undeclared_recipes():
    for changed in (
        {"max_attempts": 2},
        {"min_identical_character_run": 63},
        {"permitted_recipe_id": "unreviewed"},
        {"eligible_finish_reason": "stop"},
    ):
        with pytest.raises(ValidationError):
            methods.PdfRecognitionRecoveryPolicy.model_validate(changed)
