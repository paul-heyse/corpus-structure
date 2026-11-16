"""Independent finite correspondence meaning, without a native producer or source lookup."""

from dataclasses import replace
from math import exp, sqrt
from threading import Event

import pytest

from corpus_structure.methods.table_interpretation import (
    TableCorrespondenceBinding,
    TableCorrespondencePremise,
    table_correspondence_request,
)
from corpus_structure.semantic.record_interpretation import interpret_local


def inputs():
    edges = [
        dict(
            id=key,
            axis=axis,
            role="value_role",
            disjoint=key == "a3",
            direct=False,
            evidence=("source", key),
        )
        for key, axis in (("a1", "A"), ("a2", "A"), ("a3", "A"), ("b1", "B"), ("b2", "B"))
    ]
    premises = tuple(
        TableCorrespondencePremise(
            key,
            "alternative",
            {edge: TableCorrespondenceBinding("exact", ("source", edge)) for edge in candidates},
        )
        for key, candidates in (("M1", ("a1", "b1")), ("M2", ("a2",)))
    )
    return edges, premises


def request(edges=None, premises=None):
    default_edges, default_premises = inputs()
    return table_correspondence_request(
        default_edges if edges is None else edges,
        default_premises if premises is None else premises,
        source_revision="independent-source",
        source_projection="independent-projection",
        scope_id="explicit-local-question",
        dependency_ids=("source", "a1", "a2", "a3", "b1", "b2"),
    )


def test_competing_correspondence_preserves_local_choices_and_union_once():
    value = request()
    assert value is not None and value.correspondence_status == "ambiguous"
    assert [d.key for d in value.decisions] == ["M", "A", "B"]
    assert [[c.key for c in d.candidates] for d in value.decisions] == [
        ["unresolved", "M1", "M2"],
        ["unresolved", "a1", "a2", "a3"],
        ["unresolved", "b1", "b2"],
    ]
    assert value.constraints[0].allowed == (True, True, True, False)
    result = interpret_local(value)
    assert result.outcome.value == "completed", result.detail
    # Independent enumeration: unresolved9 + M1(2*4*4) + M2(2*4*3).
    assert result.log_partition is not None
    assert exp(result.log_partition) == pytest.approx(65)
    assert result.search.positive_states == 27
    marginals = {(m.decision, m.candidate): m.probability for m in result.marginals}
    assert marginals["M", "unresolved"] == pytest.approx(9 / 65)
    assert marginals["A", "a3"] == 0
    assert marginals["B", "b2"] == pytest.approx(19 / 65)
    assert marginals["B", "unresolved"] == pytest.approx(19 / 65)
    assert [(event.event, event.probability) for event in result.event_probabilities] == [
        ("any-value_role", pytest.approx(60 / 65))
    ]
    assert [tuple(c.candidate for c in a.choices) for a in result.alternatives] == [
        ("M1", "a1", "b1"),
        ("M1", "unresolved", "b1"),
        ("M1", "a1", "unresolved"),
        ("M1", "a1", "b2"),
        ("M1", "a2", "b1"),
    ]
    assert result.omitted_candidate_mass == "unknown"


def test_correspondence_keeps_cancellation_limits_and_cooperative_callback_polling():
    value = request()
    assert value is not None
    stop = Event()
    stop.set()
    assert interpret_local(value, cancellation=stop).outcome.value == "cancelled"

    class LeaseLost(Exception):
        pass

    polls = 0

    def check_active():
        nonlocal polls
        polls += 1
        if polls == 3:
            raise LeaseLost

    with pytest.raises(LeaseLost):
        interpret_local(value, check_active=check_active)
    for key, limit in (("max_states", 1), ("max_workspace_bytes", 1), ("max_seconds", 0)):
        limited = interpret_local(replace(value, limits=replace(value.limits, **{key: limit})))
        assert limited.outcome.value == "resource_limit"
        assert limited.alternatives == limited.marginals == ()


def test_correspondence_fixed_overlap_and_missing_premises_are_distinct():
    _edges, premises = inputs()
    assert request(premises=()) is None
    fixed = replace(premises[0], standing="fixed")
    value = request(premises=(fixed,))
    assert value is not None and value.correspondence_status == "fixed"
    assert [d.key for d in value.decisions] == ["A", "B"]
    result = interpret_local(value)
    assert result.outcome.value == "completed" and result.log_partition is not None
    assert exp(result.log_partition) == pytest.approx(16)
    overlap = replace(
        fixed, bindings={"a1": TableCorrespondenceBinding("overlap", ("source", "a1"))}
    )
    value = request(premises=(overlap,))
    assert value is not None
    result = interpret_local(value)
    assert result.outcome.value == "completed" and result.log_partition is not None
    assert exp(result.log_partition) == pytest.approx((2 + sqrt(2)) * 3)


@pytest.mark.parametrize(
    "defect",
    [
        "foreign-candidate",
        "foreign-evidence",
        "duplicate-edge",
        "duplicate-premise",
        "empty-bindings",
        "axis-role",
    ],
)
def test_correspondence_refuses_foreign_or_ambiguous_input_references(defect):
    edges, premises = inputs()
    if defect == "foreign-candidate":
        premises = (
            replace(
                premises[0], bindings={"outside": TableCorrespondenceBinding("exact", ("source",))}
            ),
        )
    elif defect == "foreign-evidence":
        premises = (
            replace(
                premises[0], bindings={"a1": TableCorrespondenceBinding("exact", ("outside",))}
            ),
        )
    elif defect == "duplicate-edge":
        edges.append(edges[0])
    elif defect == "duplicate-premise":
        premises = (*premises, premises[0])
    elif defect == "empty-bindings":
        premises = (replace(premises[0], bindings={}),)
    else:
        edges[0] = {**edges[0], "role": "header"}
    with pytest.raises(ValueError, match=r"foreign|distinct|competing|actual candidate"):
        request(edges, premises)
