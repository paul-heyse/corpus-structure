"""Local consumer preserves independent inputs even when no inference policy exists."""

from dataclasses import replace
from math import log
from threading import Event

import pytest

from corpus_structure.methods.local_interpretation import interpret_contribution_question
from corpus_structure.semantic import record_interpretation as ri


def request():
    return ri.LocalInterpretationRequest(
        decisions=(ri.Decision("role", (ri.Candidate("actor"), ri.Candidate("object"))),),
        potentials=(ri.LogPotential("role-evidence", ("role",), (log(3), log(1)), ("source",)),),
        constraints=(),
        dependencies=tuple(
            ri.Dependency(k, v, "v1")
            for k, v in (
                ("source", ri.DependencyKind.OBSERVATION),
                ("model", ri.DependencyKind.MODEL),
                ("ontology", ri.DependencyKind.ONTOLOGY),
                ("policy", ri.DependencyKind.POLICY),
            )
        ),
        selection=ri.CandidateSelection("question", ("source",)),
        model_dependency_id="model",
        ontology_dependency_id="ontology",
        policy_dependency_id="policy",
    )


def run(**kwargs):
    return interpret_contribution_question(
        question_id="question",
        contributions=({"contribution_id": "span", "literal": "Alice"},),
        dependency_ids=("source",),
        **kwargs,
    )


def test_no_policy_preserves_local_inputs_without_record_or_scores():
    output = run()
    assert output["outcome"] == "not_run"
    assert output["contribution_ids"] == ["span"]
    assert output["probability_standing"] == "not_computed"
    assert "request" not in output and "result" not in output
    assert output == run()


def test_supplied_policy_seals_actual_local_result_without_acceptance():
    output = run(request=request())
    assert output["outcome"] == "completed"
    assert output["result"]["marginals"][0]["probability"] == pytest.approx(0.75)
    assert output["contribution_ids"] == ["span"]
    assert output["probability_standing"] == "provisional_candidate_relative"
    assert "accepted" not in output
    assert output["request_digest"] and output["result_digest"] and output["seal"]


def test_missing_dependency_or_foreign_scope_refuses_before_execution():
    with pytest.raises(ValueError, match="dependencies"):
        run(request=replace(request(), dependencies=request().dependencies[1:]))
    with pytest.raises(ValueError, match="scope"):
        run(request=replace(request(), selection=ri.CandidateSelection("other", ("source",))))


def test_cancelled_local_solve_keeps_input_inventory_but_no_partial_probability():
    cancellation = Event()
    cancellation.set()
    output = run(request=request(), cancellation=cancellation)
    assert output["outcome"] == "cancelled"
    assert output["contribution_ids"] == ["span"]
    assert output["result"]["marginals"] == []
    assert output["result"]["event_probabilities"] == []


def test_local_consumer_requires_consumed_contribution_dependency_closure():
    with pytest.raises(ValueError, match="contribution dependencies"):
        interpret_contribution_question(
            question_id="question",
            contributions=(
                {"contribution_id": "span", "computation_dependencies": ("linguistic-profile",)},
            ),
            dependency_ids=("source",),
        )
