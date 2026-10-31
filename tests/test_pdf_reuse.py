"""Exact retained enrichment reuse and immutable current-consumer projection roles."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument

from corpus_structure.core.method import (
    MethodContext,
    MethodSettings,
    SourceViewRef,
    UnitRef,
    UnitView,
)
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.ingest.pdf_hierarchy import organize, snapshot
from corpus_structure.ingest.pdf_methods import (
    EnrichPdfMath,
    IngestPdf,
    PdfEnrichConfig,
    PdfIngestConfig,
    _drafts,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.parsing_products import ProductReference


def test_projection_role_is_in_identity_before_construction():
    document = DoclingDocument(name="independent role identity")
    document.add_heading(text="1: Parent", level=1)
    document.add_text(label=DocItemLabel.TEXT, text="Native source.")
    organized = organize(snapshot(document), PdfIngestConfig().section_policy())

    def build(eligible):
        return _drafts(
            1,
            ProductReference(7, "math-enriched", "a" * 64),
            organized.document,
            {"conversion": "success", "formula_outcomes": []},
            (organized.sections[0].group_ref,),
            "direct",
            "current",
            analysis_eligible=eligible,
        )

    (analysis,) = build(True)
    (context,) = build(False)
    assert analysis.key != context.key
    assert analysis.recipe_digest != context.recipe_digest
    assert analysis.projection_digest == context.projection_digest
    assert analysis.analysis_eligible is True and context.analysis_eligible is False


@pytest.mark.parametrize(
    "case",
    [
        "exact",
        "partial",
        "missing-ancestor",
        "missing-universe",
        "wrong-policy",
        "wrong-recipe",
        "same-key-mismatch",
    ],
)
def test_exact_retained_enrichment_reuses_pin_without_worker_or_native_output(monkeypatch, case):
    document = DoclingDocument(name="retained enrichment input")
    document.add_heading(text="1: Parent", level=1)
    document.add_text(label=DocItemLabel.TEXT, text="Parent context.")
    document.add_heading(text="1.1: Child", level=2)
    document.add_text(label=DocItemLabel.TEXT, text="Child source.")
    organized = organize(snapshot(document), PdfIngestConfig().section_policy())
    parent, child = (section.group_ref for section in organized.sections)
    pin = ProductReference(7, "math-enriched", "a" * 64)
    coverage = [
        dict(
            section_pointer=section,
            membership=membership,
            universe=universe,
            policy=policy,
            outcome="partial" if case == "partial" else "complete",
        )
        for section, membership in ((child, "descendants"), (parent, "direct"))
        for universe, policy in (
            ("display", "detected-native-display-v1"),
            ("inline", "native-font-token-vector-ocr-word-v3"),
            ("cell", "all-nonempty-selected-cells-v1"),
        )
    ]
    if case == "missing-ancestor":
        coverage = [row for row in coverage if row["section_pointer"] != parent]
    if case == "missing-universe":
        coverage.pop()
    if case == "wrong-policy":
        coverage[0]["policy"] = "native-font-token-vector-v2"
    health = {
        "conversion": "success",
        "display_coverage": "complete",
        "inline_coverage": "unknown",
        "cell_coverage": "unknown",
        "formula_outcomes": [],
    }
    (existing,) = _drafts(
        1,
        pin,
        organized.document,
        health,
        (child,),
        "descendants",
        "current",
        recognition_coverage=coverage,
    )
    view = SourceViewRef(
        11,
        existing.key,
        1,
        pin,
        child,
        "descendants",
        existing.projection_digest,
        existing.recipe_digest,
    )
    if case == "same-key-mismatch":
        view = replace(view, projection_digest="c" * 64)
    values = {
        "document": json.loads(organized.document.payload),
        "artifact_digest": "b" * 64,
        "health": health,
        "recognition_coverage": coverage,
        "items": [],
        "source_scope": "whole_document",
        "native_schema_version": organized.document.schema_version,
    }
    original = canonical_bytes(values)
    method = EnrichPdfMath(IngestPdf())
    calls = []
    monkeypatch.setattr(method, "original_recipe", lambda cfg: b"exact-native-recipe")

    def forbid(*args, **kwargs):
        calls.append("runtime")
        raise RuntimeError("unexpected runtime acquisition")

    monkeypatch.setattr(method.producer, "_runtime", forbid)
    monkeypatch.setattr(method.producer, "_worker", forbid)
    monkeypatch.setattr(
        "corpus_structure.ingest.pdf_methods._consumer_release", lambda ctx: "current"
    )
    monkeypatch.setattr(
        "corpus_structure.ingest.pdf_methods._require_enrichment_operation", lambda *args: None
    )

    def no_publication(*args, **kwargs):
        raise AssertionError("reuse cannot fabricate a new native producer")

    reader = SimpleNamespace(
        source_views=lambda: (view,),
        native_document=lambda reference: SimpleNamespace(
            values=lambda: values,
            recipe_bytes=b"different" if case == "wrong-recipe" else b"exact-native-recipe",
            original=b"retained",
            schema_bytes=b"schema",
        ),
        prepare_pdf_product=no_publication,
        native_product_reference=no_publication,
    )
    run = SimpleNamespace(reader=reader)
    ctx = MethodContext(
        run,
        reader,
        MethodSettings(data_dir=Path("."), model_cache=Path(".")),
        logging.getLogger(__name__),
    )
    unit = UnitView(UnitRef(TaskUnitType.DOCUMENT, 1, "document"), run)
    (result,) = method.run((unit,), PdfEnrichConfig(), ctx)
    if case == "same-key-mismatch":
        assert calls == []
        assert result.outcome is ObservationOutcome.FAILED
        assert result.error is not None and "custody" in result.error
        assert result.native_products == () and result.source_views == ()
        return
    if case not in {"exact", "partial"}:
        assert calls == ["runtime"]
        assert result.outcome is ObservationOutcome.FAILED
        assert result.error is not None
        assert "unexpected runtime" in result.error
        return
    assert calls == []
    assert result.outcome is ObservationOutcome.EMPTY
    assert result.native_products == ()
    # Existing analysis view remains selected; only the missing ancestor context is emitted.
    assert len(result.source_views) == 1
    context = result.source_views[0]
    assert context.native_product == pin and context.section_pointer == parent
    assert context.membership == "direct" and context.analysis_eligible is False
    assert context.replaces_source_view_id is None and context.key != existing.key
    assert context.health["inline_coverage"] == ("partial" if case == "partial" else "complete")
    assert canonical_bytes(values) == original
