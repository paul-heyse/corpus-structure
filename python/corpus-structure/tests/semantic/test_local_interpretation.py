"""Independent local questions challenge the shared exact retained-support executor."""

from dataclasses import replace
from math import inf, log
from threading import Event
from typing import Any, cast

import pytest

from corpus_structure.semantic import record_interpretation as ri
from semantic.local_interpretation_support import local_request as local_request


def test_role_only_without_identity_template_or_event():
    result = ri.interpret_local(replace(local_request(), marginal_decisions=("role",)))
    assert result.outcome is ri.Outcome.COMPLETED
    assert result.event_probabilities == ()
    assert {(m.decision, m.candidate): m.probability for m in result.marginals} == pytest.approx(
        {("role", "actor"): 0.3, ("role", "object"): 0.7}
    )
    assert result.log_partition == pytest.approx(log(10))
    assert result.search.retained_states == result.search.examined_states == 4
    assert result.alternatives[0].probability == pytest.approx(0.4)
    assert sum(a.probability for a in result.alternatives) == pytest.approx(1)
    assert result.omitted_candidate_mass == "unknown"


def test_executor_rejects_weighted_model_claiming_uniform_feasibility_control():
    result = ri.interpret_local(replace(local_request(), feasibility_control=True))
    assert result.outcome is ri.Outcome.INVALID_INPUT
    assert result.marginals == result.alternatives == result.event_probabilities == ()
    assert result.log_partition is None


def test_partial_composite_union_counts_overlapping_assignments_once():
    event = ri.CompositeEvent(
        "actor-or-first",
        "actor role or attachment to first target",
        (
            (ri.Choice("role", "actor"),),
            (ri.Choice("target", "first"),),
            (ri.Choice("role", "actor"),),
        ),
    )
    result = ri.interpret_local(replace(local_request(), events=(event,), marginal_decisions=()))
    assert result.outcome is ri.Outcome.COMPLETED
    assert result.marginals == ()
    assert len(result.event_probabilities) == 1
    assert result.event_probabilities[0].event == "actor-or-first"
    assert result.event_probabilities[0].probability == pytest.approx(0.6)
    assert result.log_partition == pytest.approx(log(10))


def test_selected_local_conjunction_is_not_product_of_marginals():
    event = ri.CompositeEvent(
        "both",
        "actor attached to first",
        ((ri.Choice("role", "actor"), ri.Choice("target", "first")),),
    )
    result = ri.interpret_local(replace(local_request(), events=(event,)))
    assert result.outcome is ri.Outcome.COMPLETED
    assert result.event_probabilities[0].probability == pytest.approx(0.1)
    marginals = {(m.decision, m.candidate): m.probability for m in result.marginals}
    assert marginals["target", "first"] == pytest.approx(0.4)
    assert result.event_probabilities[0].probability != pytest.approx(0.3 * 0.4)


@pytest.mark.parametrize(
    "changes",
    [
        {"decisions": ()},
        {"marginal_decisions": ()},
        {"marginal_decisions": ("absent",)},
        {"marginal_decisions": ("role", "role")},
        {"events": (ri.CompositeEvent("event", "", ((ri.Choice("role", "actor"),),)),)},
        {"events": (ri.CompositeEvent("event", "vacuous", ((),)),)},
        {"events": (ri.CompositeEvent("event", "unknown", ((ri.Choice("absent", "actor"),),)),)},
        {"events": (ri.RecordEvent("record", ((ri.Choice("role", "actor"),),)),)},
    ],
)
def test_invalid_local_questions_have_no_partial_probabilities(changes):
    result = ri.interpret_local(replace(local_request(), **changes))
    assert result.outcome is ri.Outcome.INVALID_INPUT
    assert result.marginals == result.event_probabilities == result.alternatives == ()
    assert result.log_partition is None


@pytest.mark.parametrize(
    "case,expected",
    [
        ("cancelled", ri.Outcome.CANCELLED),
        ("states", ri.Outcome.RESOURCE_LIMIT),
        ("workspace", ri.Outcome.RESOURCE_LIMIT),
        ("elapsed", ri.Outcome.RESOURCE_LIMIT),
        ("infeasible", ri.Outcome.INFEASIBLE),
        ("nonfinite", ri.Outcome.NUMERICAL_FAILURE),
    ],
)
def test_local_failure_retains_no_partial_results(case, expected):
    request = local_request()
    cancel = Event()
    if case == "cancelled":
        cancel.set()
    if case == "states":
        request = replace(request, limits=ri.SearchLimits(max_states=3))
    if case == "workspace":
        request = replace(request, limits=ri.SearchLimits(max_workspace_bytes=1))
    if case == "elapsed":
        request = replace(request, limits=ri.SearchLimits(max_seconds=0))
    if case == "infeasible":
        request = replace(
            request,
            constraints=(ri.HardConstraint("none", ("role",), (False, False), ("source",)),),
        )
    if case == "nonfinite":
        request = replace(
            request,
            potentials=(ri.LogPotential("bad", ("role", "target"), (inf, 0, 0, 0), ("source",)),),
        )
    result = ri.interpret_local(request, cancellation=cancel)
    assert result.outcome is expected
    assert result.marginals == result.event_probabilities == result.alternatives == ()
    assert result.log_partition is None


def test_local_and_record_entrypoints_reject_wrong_request_contract():
    with pytest.raises(TypeError, match="InterpretationRequest"):
        ri.interpret_records(cast(Any, local_request()))
