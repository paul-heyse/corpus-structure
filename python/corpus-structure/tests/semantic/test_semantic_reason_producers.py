"""Actual released policy producers preserve machine reasons independently of prose."""

from dataclasses import replace
from typing import Any

import pytest

from corpus_structure.semantic.analytics import AnalysisScope, CandidateInput
from corpus_structure.semantic.arrow_publication import AppendPublication
from corpus_structure.semantic.domain_operations import (
    ReleasedRulesPolicy,
    _project_cut,
)
from corpus_structure.semantic.proposals import (
    ProposalFrame,
    ProposalSentence,
    locate_proposal,
)
from corpus_structure.semantic.refusals import SemanticReason, decode_semantic_reason
from semantic.semantic_reason_producers_support import release as release
from semantic.proposals_support import native_frame


def cut(
    *,
    language="latex",
    expression="x",
    condition=None,
    unresolved=False,
    incompatible=False,
    custom_binding=False,
):
    prepared = release(custom_binding)
    frame = native_frame(ProposalFrame(
        "unit", "The source names x.", (ProposalSentence("s", "sentence", 0, 19),)
    ))
    raw: dict[str, Any] = {
        "unit_ref": "unit",
        "entities": [{"id": "person", "class_iri": "https://example.org/Person"}],
        "claims": [
            {
                "id": "claim",
                "subject": "person",
                "predicate": "https://example.org/name",
                "object": {
                    "kind": "expression",
                    "form": "formula",
                    "language": language,
                    "expression": expression,
                },
                "qualification": {"modality": "asserted", "polarity": True},
                "establishment": "stated",
                "evidence": [{"sentence": "s", "quote": "The source names x.", "role": "primary"}],
            }
        ],
    }
    if custom_binding:
        raw["claims"][0]["object"]["bindings"] = [{"kind": "custom_binding", "symbol": "x"}]
    if condition is not None:
        raw["claims"][0]["qualification"]["condition"] = condition
    if unresolved:
        raw["entities"][0]["reference"] = {"description": "Unresolved external source identity"}
    if incompatible:
        import copy

        raw["claims"][0]["object"]["bindings"] = [{"kind": "free", "symbol": "x"}]
        other = copy.deepcopy(raw["claims"][0])
        other["id"] = "other"
        other["object"]["bindings"] = [{"kind": "constant", "symbol": "x"}]
        raw["claims"].append(other)
    stored = locate_proposal(prepared, raw, frame).stored.model_dump(
        mode="python", exclude_unset=True
    )
    observation = {
        "id": 7,
        "observation_key": "observation:reasons",
        "payload_definition": "AgentStoredBatch",
        "payload": stored,
    }
    descriptor = {
        "math": {},
        "content": {"macros": {}},
        "text": frame.text,
        "source_uri": "source:test",
        "provider": "agent.test",
        "version": "7",
        "frame": frame,
    }
    job = {
        "id": 1,
        "project_id": "project",
        "release_id": prepared.release_id,
        "input_realization_id": "in",
        "input_revision": 0,
    }
    return _project_cut(
        prepared, job, {"id": 1}, [observation], {7: descriptor}, [], [], "out", {}, {}
    )


def evaluate(inputs, scratch):
    policy = ReleasedRulesPolicy(inputs.prepared)
    packet = CandidateInput.from_admitted_cut(
        inputs.prepared, inputs, decision_universe=policy.version
    )
    with AnalysisScope(packet, scratch_path=scratch) as scope:
        fused = scope.fuse(scope.relation("candidate_input")).to_arrow_table()
        return policy.evaluate(inputs, scope, fused)


@pytest.mark.parametrize(
    "arguments,code,actual",
    [
        ({"language": "python"}, "unsupported_interpretation", "python"),
        ({"expression": r"\frac{"}, "preparation_failed", "failed"),
        (
            {
                "condition": {
                    "kind": "escape",
                    "text": "source condition",
                    "reason": "uninterpreted",
                }
            },
            "unsupported_interpretation",
            "escape",
        ),
        ({"unresolved": True}, "missing_operands", "unresolved endpoints"),
    ],
)
def test_actual_policy_persists_expected_inability(arguments, code, actual, tmp_path):
    inputs = cut(**arguments)
    decision = evaluate(inputs, tmp_path)
    reasons = [
        row.semantic_reason
        for row in decision.assessments
        if row.operation_id == "operation.not_checkable" and row.semantic_reason is not None
    ]
    assert any(reason.code == code and reason.actual == actual for reason in reasons)
    assert all(
        reason.release_id == inputs.prepared.release_id and reason.operation == "evaluate"
        for reason in reasons
    )
    assert all(
        reason.references == (inputs.candidates[0].occurrence_id,)
        or reason.references[0] == inputs.candidates[0].occurrence_id
        for reason in reasons
    )


def test_actual_assessment_reason_identity_survives_changed_human_wording(monkeypatch, tmp_path):
    inputs = cut(language="python")
    first = evaluate(inputs, tmp_path / "first")
    monkeypatch.setattr(SemanticReason, "render", lambda self: "different human wording")
    second = evaluate(inputs, tmp_path / "second")
    before = next(row for row in first.assessments if row.operation_id == "operation.not_checkable")
    after = next(row for row in second.assessments if row.operation_id == "operation.not_checkable")
    assert before.reason != after.reason
    assert before.assessment_id == after.assessment_id
    assert before.semantic_reason == after.semantic_reason


def test_actual_comparison_and_both_transports_retain_structured_cause(tmp_path):
    inputs = cut(incompatible=True)
    decision = evaluate(inputs, tmp_path)
    comparisons = [
        row for row in decision.assessments if row.operation_id == "scientific.value_equivalence"
    ]
    assert len(comparisons) == 2 and all(
        row.semantic_reason is not None and row.semantic_reason.code == "incompatible_bindings"
        for row in comparisons
    )
    batch = replace(inputs.batch, assessment=decision.assessments).bind_preparation(inputs.prepared)
    frozen = AppendPublication.from_rows(batch)
    assert frozen.content == batch.content
    import json

    rows = frozen.relations["assessment"].to_pylist()
    first = next(row for row in rows if row["semantic_reason"] is not None)
    assert decode_semantic_reason(json.loads(first["semantic_reason"])) in [
        row.semantic_reason for row in decision.assessments
    ]
    assert isinstance(json.loads(batch.content)[2]["assessment"][0][-1], (dict, type(None)))


def test_actual_preparation_failure_is_an_owned_reason(tmp_path):
    inputs = cut(custom_binding=True)
    decision = evaluate(inputs, tmp_path)
    reason = next(
        row.semantic_reason
        for row in decision.assessments
        if row.operation_id == "operation.not_checkable"
    )
    assert reason is not None
    assert reason.code == "preparation_failed" and reason.actual == "analysis_binding_kind"


def test_runtime_or_admission_preparation_errors_remain_failures(monkeypatch, tmp_path):
    from corpus_structure.semantic import analysis_contracts
    from corpus_structure.semantic.types import Diagnostic, PreparationError

    inputs = cut()

    def incompatible(*args, **kwargs):
        raise PreparationError(
            (Diagnostic("unsupported_analysis_implementation", "release", "runtime mismatch"),)
        )

    monkeypatch.setattr(analysis_contracts, "prepare_interpretation_context", incompatible)
    with pytest.raises(PreparationError, match="runtime mismatch"):
        evaluate(inputs, tmp_path)


def test_actual_reading_boundary_does_not_flatten_programming_value_errors(monkeypatch, tmp_path):
    from corpus_structure.semantic import analysis_contracts

    inputs = cut()

    def broken(*args, **kwargs):
        raise ValueError("injected programming failure")

    monkeypatch.setattr(analysis_contracts, "prepare_interpretation_context", broken)
    with pytest.raises(ValueError, match="injected programming failure"):
        evaluate(inputs, tmp_path)
