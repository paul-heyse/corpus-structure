"""Retained scope meaning and selective reads stay independent of execution reuse."""

from __future__ import annotations

import json
from hashlib import sha256
from types import SimpleNamespace
from typing import cast

import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument

from corpus_structure.core.method import SourceViewDraft
from corpus_structure.ingest.pdf_hierarchy import _section_text_policy_bytes, organize, snapshot
from corpus_structure.ingest.pdf_methods import PdfIngestConfig, _drafts
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference


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
    "case", ["exact", "partial", "missing-ancestor", "missing-universe", "qualified-old-policy"]
)
def test_retained_coverage_preserves_exact_scope_partial_and_policy_without_recomputation(case):
    document = DoclingDocument(name="retained source coverage")
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
    elif case == "missing-universe":
        coverage = [
            row
            for row in coverage
            if not (row["section_pointer"] == parent and row["universe"] == "cell")
        ]
    elif case == "qualified-old-policy":
        next(
            row
            for row in coverage
            if row["section_pointer"] == child and row["universe"] == "inline"
        )["policy"] = "native-font-token-vector-v2"
    before = canonical_bytes(coverage)
    health = {
        "conversion": "success",
        "display_coverage": "complete",
        "inline_coverage": "unknown",
        "cell_coverage": "unknown",
        "formula_outcomes": [],
    }
    (analysis,) = _drafts(
        1,
        pin,
        organized.document,
        health,
        (child,),
        "descendants",
        "current",
        recognition_coverage=coverage,
    )
    (context,) = _drafts(
        1,
        pin,
        organized.document,
        health,
        (parent,),
        "direct",
        "current",
        analysis_eligible=False,
        recognition_coverage=coverage,
    )
    assert analysis.native_product == context.native_product == pin
    assert analysis.analysis_eligible is True and context.analysis_eligible is False
    assert context.health["inline_coverage"] == (
        "unknown" if case == "missing-ancestor" else "partial" if case == "partial" else "complete"
    )
    assert context.health["cell_coverage"] == (
        "unknown"
        if case in {"missing-ancestor", "missing-universe"}
        else "partial"
        if case == "partial"
        else "complete"
    )
    assert analysis.health["inline_coverage"] == ("partial" if case == "partial" else "complete")
    assert analysis.health["candidate_policy"] == (
        "native-font-token-vector-v2"
        if case == "qualified-old-policy"
        else "native-font-token-vector-ocr-word-v3"
    )
    assert canonical_bytes(coverage) == before


def test_enrichment_recipe_changes_with_actual_captured_classification_policy():
    from corpus_structure.semantic.pdf_transforms import PdfEnrichmentOptions, PreparedPdfTransform

    native = {"recipe": b"{}".hex()}
    first = PreparedPdfTransform(
        None,
        None,
        {
            "mode": "enriched",
            "native": native,
            "options": PdfEnrichmentOptions().model_dump(mode="json"),
        },
    )
    changed = PreparedPdfTransform(
        None,
        None,
        {
            "mode": "enriched",
            "native": native,
            "options": PdfEnrichmentOptions(crop_padding_points=2).model_dump(mode="json"),
        },
    )
    assert first.recipe_bytes() != changed.recipe_bytes()
    assert json.loads(first.recipe_bytes())["crop_padding_points"] == 0.75
    assert json.loads(changed.recipe_bytes())["crop_padding_points"] == 2


@pytest.mark.parametrize("historical_aggregate", [False, True])
def test_selected_publication_projection_does_not_hydrate_whole_native(
    monkeypatch, historical_aggregate
):
    from corpus_structure.ingest import pdf_section_views
    from corpus_structure.semantic.operations import BoundReader, OperationConflict

    pin = ProductReference(3, "organized", "a" * 64)
    draft = SourceViewDraft(
        "selected",
        1,
        pin,
        "#/groups/0",
        "direct",
        "text",
        ({"start": 0, "end": 4, "kind": "native_text", "item_ref": "#/texts/0"},),
        ("#/groups/0", "#/texts/0"),
        (),
        {"conversion": "success"},
        b"{}",
    )
    requests = []
    published = object()
    reader = object.__new__(BoundReader)
    from corpus_structure.semantic.types import PreparedRelease

    reader.prepared = cast(
        PreparedRelease,
        SimpleNamespace(
            release_id="consumer",
            manifest=json.dumps(
                {
                    "dependencies": [
                        [
                            "execution/implementation/pdf/section-text-recipe.json",
                            sha256(_section_text_policy_bytes()).hexdigest(),
                        ]
                    ]
                }
            ),
        ),
    )

    def selected(reference):
        assert reference == pin
        return None, None, None if historical_aggregate else published

    monkeypatch.setattr(reader, "_native_product_input", selected)

    def forbidden(*args, **kwargs):
        raise AssertionError("selected publication projection cannot hydrate a whole document")

    monkeypatch.setattr(reader, "native_document", forbidden)

    def project(actual, **options):
        assert actual is published
        requests.append(options)
        return (draft,)

    monkeypatch.setattr(pdf_section_views, "published_section_drafts", project)
    if historical_aggregate:
        with pytest.raises(OperationConflict, match="record-backed publication"):
            reader.native_section_drafts(
                pin,
                document_id=1,
                selections=(),
                membership="direct",
                scope=None,
                consumer_release="consumer",
            )
        assert requests == []
    else:
        assert reader.native_section_drafts(
            pin,
            document_id=1,
            selections=(),
            membership="direct",
            scope=None,
            consumer_release="consumer",
        ) == (draft,)
        assert requests[0]["document_id"] == 1
