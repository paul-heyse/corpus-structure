"""Selected gap coverage distinguishes findings, inspected empty and unavailable."""

from copy import deepcopy
from typing import Any
from unittest.mock import MagicMock

import pytest

from corpus_structure.semantic.refusals import InvalidContinuation, SemanticRefusal
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import build_registry
from corpus_structure.serve.review_bundle import (
    ReviewSelection,
    verify_review_bundle,
    write_review_bundle,
)
from corpus_structure.serve.structural_gaps import (
    METHODS,
    GapPage,
    GapRequest,
    _read_payload,
    gap_page,
)

from .test_dossier_comparison_bindings import fixture
from .test_dossier_semantic_states import applicability


def producer(report, **changes):
    return (
        dict(
            run_id=1,
            cut_id=2,
            project_id="project",
            release_id="release",
            result_revision=3,
            selected_task_id=4,
            origin_task_id=5,
            runtime_fingerprint="original",
            method=METHODS[report],
            task_status="done",
            operation_outcome="produced",
            cut_member=True,
        )
        | changes
    )


def capture(report, payload=None, **changes):
    return (
        dict(
            producer=producer(report),
            payload=payload,
            binding_producer=None,
            binding_payload=None,
            support=[],
        )
        | changes
    )


def unresolved(outcome="insufficient_evidence", operation_outcome="succeeded") -> dict[str, Any]:
    operation = dict(
        question="contextual relationship selection for located occurrence",
        operation_key="phase",
        outcome=operation_outcome,
        report_digest="proof",
        dependencies=["cue-contribution"],
        reason="candidate retrieval was not available",
    )
    decision = dict(
        occurrence_id="cue",
        decision_id="decision:proof",
        scope="rules",
        outcome=outcome,
        exclusions=[{"left": "cue", "right": "excluded"}],
        reason="No source witness for the eligible candidate.",
    )
    return dict(
        operations=[
            operation,
            dict(
                contextual=dict(
                    candidate_lists=[
                        dict(
                            occurrence_id="cue",
                            list_id="list",
                            candidates=["candidate"],
                            eligible_target_count=1,
                        )
                    ],
                    decisions=[decision] if operation_outcome == "succeeded" else [],
                    section_resolutions=[],
                )
            ),
        ],
        occurrences=[
            dict(
                id="cue-contribution", occurrence_id="cue", anchors=[{"source_piece": "See rule."}]
            )
        ],
    )


def test_unresolved_binding_preserves_candidate_and_recorded_coverage():
    name = "unresolved_binding"
    request = GapRequest(report=name, run_id=1, task_id=4, occurrence_id="cue")
    page = gap_page(request, capture(name, unresolved()))
    assert page.status == "actionable"
    assert page.rows[0].reason == "insufficient_evidence"
    assert page.rows[0].evidence["candidates"] == ["candidate"]
    assert page.rows[0].evidence["exclusions"] == [{"left": "cue", "right": "excluded"}]
    assert gap_page(request, capture(name, unresolved("selected"))).status == "empty"
    unavailable = gap_page(request, capture(name, unresolved(operation_outcome="not_run")))
    assert unavailable.status == "unavailable"
    assert unavailable.rows[0].outcome == "not_run"
    assert (
        unavailable.rows[0].evidence["operation_reason"] == "candidate retrieval was not available"
    )


def test_unresolved_binding_refuses_operation_for_a_different_occurrence():
    name = "unresolved_binding"
    payload = unresolved()
    operation = payload["operations"][0]
    operation["dependencies"] = ["other-cue"]
    operation.pop("report_digest", None)
    request = GapRequest(
        report=name,
        run_id=1,
        task_id=4,
        occurrence_id="cue",
        operation_key=operation["operation_key"],
    )
    with pytest.raises(SemanticRefusal, match="did not inspect"):
        gap_page(request, capture(name, payload))


def test_unknown_applicability_keeps_original_incompatibility_and_exact_cursor():
    name = "unknown_applicability_premise"
    request = GapRequest(report=name, run_id=1, task_id=4, limit=1)
    captured = capture(name, applicability().model_dump(mode="json"))
    first = gap_page(request, captured)
    assert first.next_cursor is not None and first.status == "actionable"
    followup = request.model_copy(update={"cursor": first.next_cursor})
    second = gap_page(followup, captured)
    assert {first.rows[0].outcome, second.rows[0].outcome} == {"unresolved", "incompatible"}
    assert first.rows[0].evidence["dimension"] == second.rows[0].evidence["dimension"] == "sense"
    assert second == gap_page(followup, captured)
    with pytest.raises(InvalidContinuation):
        gap_page(followup, {**captured, "producer": producer(name, cut_id=90)})
    with pytest.raises(SemanticRefusal, match="source"):
        gap_page(request.model_copy(update={"source_view_id": 902}), captured)
    resolved = applicability().model_dump(mode="json")
    resolved["definition"]["readings"] = resolved["definition"]["readings"][:1]
    assert gap_page(request, capture(name, resolved)).status == "empty"
    skipped = capture(name, producer=producer(name, task_status="skipped", operation_outcome=None))
    assert gap_page(request, skipped).rows[0].outcome == "skipped"


def test_supported_comparison_gap_requires_authorized_summary_and_inspected_binding():
    name = "unconnected_supported_comparison"
    _, _, _, reference, payload, *_ = fixture()
    request = GapRequest(
        report=name,
        run_id=reference.run_id,
        task_id=reference.selected_task_id,
        binding_task=dict(run_id=12, task_id=8),
    )
    primary = producer(name) | reference.model_dump(mode="json", exclude={"product_id"})
    comparison = dict(
        producer=primary,
        payload=payload["report"],
        binding_producer=dict(task_status="done"),
        binding_payload=dict(
            product_id="dossier",
            root=None,
            predecessors=[reference.model_dump(mode="json")],
            bound=[],
        ),
        support=[dict(assertion_id="published", claim_id="exact-comparison")],
    )
    page = gap_page(request, comparison)
    assert page.status == "actionable"
    assert page.rows[0].evidence["support"] == comparison["support"]
    sides = page.rows[0].evidence["sides"]
    assert isinstance(sides, dict) and sides.keys() == {"left", "right"}
    bound = deepcopy(comparison)
    bound["binding_payload"]["bound"].append(reference.model_dump(mode="json"))
    assert gap_page(request, bound).status == "empty"
    one_side = deepcopy(comparison)
    one_side["binding_payload"]["bound_sides"] = [
        {"reference": reference.model_dump(mode="json"), "side": "left"}
    ]
    uncovered = gap_page(request, one_side).rows[0].evidence["sides"]
    assert isinstance(uncovered, dict) and set(uncovered) == {"right"}
    uninspected = gap_page(request, {**comparison, "binding_payload": None})
    assert uninspected.status == "unavailable"
    assert uninspected.rows[0].reason == "binding_production_unavailable"
    unsupported = gap_page(request, {**comparison, "support": []})
    assert unsupported.status == "unavailable"
    assert unsupported.rows[0].evidence == {}
    with pytest.raises(ValueError, match="protected"):
        GapRequest.model_validate({**request.model_dump(), "protected_labels": True})


def test_pre_hydration_budget_and_named_registry():
    registry = build_registry(GENERIC)
    assert all(registry[name].result is GapPage for name in METHODS)
    request = GapRequest(report="unresolved_binding", run_id=1, task_id=4, max_bytes=100)
    conn = MagicMock()
    conn.scalar.return_value = 200
    with pytest.raises(SemanticRefusal, match="byte budget"):
        _read_payload(conn, producer(request.report), request)
    assert conn.scalar.call_count == 1


def test_detached_gap_replays_same_pages_and_rejects_substitution(tmp_path):
    name = "unknown_applicability_premise"
    request = GapRequest(report=name, run_id=1, cut_id=2, task_id=4, limit=1)
    captured = capture(name, applicability().model_dump(mode="json"))
    selection = ReviewSelection(structural_gap_selections=(request,))
    first = gap_page(request, captured)
    second = gap_page(request.model_copy(update={"cursor": first.next_cursor}), captured)
    rows = [
        ("structural_gap_sources", dict(selection_index=0, **captured)),
        ("structural_gaps", dict(selection_index=0, **first.model_dump(mode="json"))),
        ("structural_gaps", dict(selection_index=0, **second.model_dump(mode="json"))),
    ]
    output = tmp_path / "valid"
    manifest = write_review_bundle(selection, output, iter(rows))
    assert verify_review_bundle(output) == manifest
    rows[0] = (
        "structural_gap_sources",
        dict(selection_index=0, **{**captured, "producer": producer(name, origin_task_id=12)}),
    )
    output = tmp_path / "forged"
    with pytest.raises(ValueError, match="differs from selected producer evidence"):
        write_review_bundle(selection, output, iter(rows))


def test_exact_detached_gap_rejects_consistent_projection_substitution(tmp_path):
    name = "unknown_applicability_premise"
    request = GapRequest(report=name, run_id=1, cut_id=2, task_id=4)
    original = applicability().model_dump(mode="json")
    selection = ReviewSelection(
        structural_gap_selections=(request,), require_original_gap_reports=True
    )
    custody = {
        "selection_index": 0,
        "bodies": {"producer": {"structural_product": original}, "binding": None},
        "assertions": [],
    }

    def rows(payload):
        captured = capture(name, payload)
        page = gap_page(request, captured)
        return iter(
            [
                ("structural_gap_sources", dict(selection_index=0, **captured)),
                ("structural_gap_custody", custody),
                ("structural_gaps", dict(selection_index=0, **page.model_dump(mode="json"))),
            ]
        )

    manifest = write_review_bundle(selection, tmp_path / "original", rows(original))
    assert verify_review_bundle(tmp_path / "original") == manifest
    changed = deepcopy(original)
    changed["definition"]["readings"] = changed["definition"]["readings"][:1]
    with pytest.raises(ValueError, match="differs from the original producer report"):
        write_review_bundle(selection, tmp_path / "changed", rows(changed))
