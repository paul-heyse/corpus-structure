"""Target retained reconciliation keeps exact candidates and source uncertainty."""

import json
from contextlib import contextmanager
from hashlib import sha256

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

from corpus_structure.ingest.pdf import PdfConversion, publication_payload
from corpus_structure.ingest.pdf_hierarchy import snapshot
from corpus_structure.ingest.pdf_recognition import PdfRecognitionRecoveryPolicy
from corpus_structure.semantic.pdf_transforms import (
    PdfIntegrationOptions,
    SelectedPdfInput,
    integration_draft,
)
from corpus_structure.semantic.product_reference import ProductReference


def test_deterministic_integration_retains_typed_candidates_and_distinct_health_rows(
    tmp_path, monkeypatch
):
    from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate
    from corpus_structure.ingest.pdf_streaming import PdfStreamSpool
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
    from corpus_structure.semantic.pdf_lowering_context import capture_pdf_lowering
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
    formula = document.add_text(label=DocItemLabel.FORMULA, text="x+1", parent=section)
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
    # These assessments are correct for the input only. Reusing pointer spellings in
    # the reconciled output must not transfer either formula or scoped completeness.
    values["health"]["formula_outcomes"] = [{"pointer": formula.self_ref, "outcome": "succeeded"}]
    values["health"]["display_coverage"] = "complete"
    values["recognition_coverage"] = [
        {
            "section_pointer": section.self_ref,
            "membership": "descendants",
            "universe": "inline",
            "coverage": "complete",
        }
    ]
    reference = ProductReference(12, "organized", "c" * 64)
    observed = []
    captures = []

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

    def assert_draft(draft):
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
        assert draft.health["display_coverage"] == "partial"
        assert draft.health["formula_outcomes"] == [
            {
                "pointer": formula.self_ref,
                "outcome": "unknown",
                "error": "no attributable inference outcome",
            }
        ]
        assert "recognition_coverage" not in draft.metadata
        assert values["health"]["formula_outcomes"][0]["outcome"] == "succeeded"
        coverage = list(draft.companions["coverage"])
        assert coverage and all(row["outcome"] == "unknown" for row in coverage)
        observed.append(candidates[0])

    options = PdfIntegrationOptions(integration_policy={})
    selected = SelectedPdfInput(
        values,
        original,
        b"{}",
        capture_pdf_lowering(context).callback_policy(),
        reference,
        capture(reference, tmp_path / "candidate-input"),
        ((section.self_ref, "descendants"),),
        context,
        None,
    )
    # This kernel has no execution/admission authority. An empty supplied reading
    # inventory remains unknown; the DDO operation separately requires inspected reports.
    with contextmanager(integration_draft)(
        selected, b"{}", (), tmp_path / "selected", options
    ) as draft:
        assert_draft(draft)
    assert len(observed) == 1


def test_recovery_policy_rejects_unbounded_or_undeclared_recipes():
    for changed in (
        {"max_attempts": 2},
        {"min_identical_character_run": 63},
        {"permitted_recipe_id": "unreviewed"},
        {"eligible_finish_reason": "stop"},
    ):
        with pytest.raises(ValidationError):
            PdfRecognitionRecoveryPolicy.model_validate(changed)
