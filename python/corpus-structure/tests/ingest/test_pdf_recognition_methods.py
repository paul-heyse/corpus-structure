"""Retained integrated adoption is a pure view projection, without another recognizer."""

import json
import logging
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest
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
from corpus_structure.semantic.product_reference import ProductReference


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

    def retained(pin, *, include_candidate_pages=True):
        seen.append(pin)
        assert include_candidate_pages is False
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


def test_live_integration_retains_typed_candidates_and_distinct_valid_health_rows(
    tmp_path, monkeypatch
):
    from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate
    from corpus_structure.ingest.pdf_streaming import PdfStreamSpool
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
    from corpus_structure.semantic.pdf_payloads import EncodedPagePayload, prepare_payload_family

    monkeypatch.chdir(tmp_path)
    context = trusted_pdf_context()
    family = prepare_payload_family(context)
    document = DoclingDocument(name="Live integration source custody control")
    document.add_page(page_no=1, size=Size(width=100, height=100))
    section = document.add_group(label=GroupLabel.SECTION, name="1 Selected")
    document.add_text(
        label=DocItemLabel.TEXT,
        text="source text",
        parent=section,
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=10, t=10, r=50, b=20), charspan=(0, 11)),
    )
    original = b"%PDF-independent-fixture"
    values = publication_payload(
        PdfConversion(
            sha256(original).hexdigest(), b"{}", snapshot(document), "success", (), (), (), None
        ),
        product_key="organized",
        schema_digest="b" * 64,
        section_refs=frozenset({section.self_ref}),
    )
    values.pop("inline_candidate_pages", None)
    reference = ProductReference(12, "organized", "c" * 64)
    observed = []
    captures = []

    def native(pin, *, include_candidate_pages=True):
        assert pin == reference and include_candidate_pages is False
        return SimpleNamespace(values=lambda: values, original=original, schema_bytes=b"{}")

    def capture(pin, directory):
        assert pin == reference
        spool = PdfStreamSpool(directory, payload_family=family)
        spool.capture_candidates(
            CandidatePage(
                1,
                True,
                False,
                (InlineCandidate(1, "x", 1, -0.0, 3.5, 4, "TOPLEFT", None, "source"),),
                True,
            )
        )
        source = spool.candidate_source
        captures.append((source, source.encoded(1)))

        def refuse(*args, **kwargs):
            raise AssertionError("live integration must not hydrate candidate pages")

        source.iter_pages = refuse
        return source

    class NoProviderWorker:
        def __init__(self, **kwargs):
            pass

        def recognize_pages(self, *args, **kwargs):
            # Empty recognition evidence intentionally establishes no coverage/fidelity.
            return iter(())

    def retain(unit, draft):
        candidates = list(draft.metadata["inline_candidate_pages"])
        assert len(candidates) == 1 and isinstance(candidates[0], EncodedPagePayload)
        assert captures[0][0].replays[1].path.exists()
        assert candidates[0] == captures[0][1]
        native_health, integration_health = draft.companions["health"]
        flattened = {**native_health["health"], "source_scope": native_health["source_scope"]}
        flattened.pop("formula_outcomes", None)
        context.boundary.validate_json("PdfRecordNativeHealth", json.dumps(flattened))
        context.boundary.validate_json("PdfProductHealth", json.dumps(integration_health))
        assert integration_health["source_fidelity"] == "unassessed"
        assert "integration_health" not in native_health
        coverage = list(draft.companions["coverage"])
        assert coverage and all(row["outcome"] == "unknown" for row in coverage)
        observed.append(candidates[0])
        return ProductReference(20, "integrated", "d" * 64)

    monkeypatch.setattr(methods, "RecognitionWorker", NoProviderWorker)
    monkeypatch.setattr(methods, "_consumer_release", lambda ctx: "release")
    monkeypatch.setattr(methods, "_drafts", lambda *args, **kwargs: ())
    cfg = methods.PdfIntegratedIngestConfig(native_product=reference)
    settings = SimpleNamespace(
        nemotron_python="unused",
        nemotron_worker="unused",
        nemotron_endpoint="unused",
        nemotron_receipts=tmp_path,
        nemotron_timeout_seconds=1,
    )
    ctx: Any = SimpleNamespace(
        reader=SimpleNamespace(
            native_document=native,
            capture_pdf_candidates=capture,
            pdf_context=lambda: context,
        ),
        run=SimpleNamespace(options={}),
        settings=settings,
        check_active=lambda: None,
        retain_pdf_records=retain,
        logger=logging.getLogger(__name__),
    )
    unit: Any = SimpleNamespace(ref=UnitRef(TaskUnitType.DOCUMENT, 1, "fixture"))
    result = methods.IngestPdfIntegrated().run([unit], cfg, ctx)[0]
    assert result.outcome == ObservationOutcome.EMPTY, result.error
    assert len(observed) == 1


def test_recovery_policy_rejects_unbounded_or_undeclared_recipes():
    for changed in (
        {"max_attempts": 2},
        {"min_identical_character_run": 63},
        {"permitted_recipe_id": "unreviewed"},
        {"eligible_finish_reason": "stop"},
    ):
        with pytest.raises(ValidationError):
            methods.PdfRecognitionRecoveryPolicy.model_validate(changed)
