"""Shared controlled inputs and builders for local interpretation reports support."""

import pytest

from corpus_structure.semantic import record_interpretation as ri


def joint_events():
    return (
        ri.CompositeEvent(
            "actor-or-first",
            "actor role or first target",
            ((ri.Choice("role", "actor"),), (ri.Choice("target", "first"),)),
        ),
        ri.CompositeEvent(
            "object-and-second",
            "object role and second target",
            ((ri.Choice("role", "object"), ri.Choice("target", "second")),),
        ),
    )


def assert_joint_probabilities(result, displayed):
    # The four fixture weights are 1, 2, 3, and 4.
    assert {
        (m["decision"], m["candidate"]): m["probability"] for m in result["marginals"]
    } == pytest.approx(
        {
            ("role", "actor"): 0.3,
            ("role", "object"): 0.7,
            ("target", "first"): 0.4,
            ("target", "second"): 0.6,
        }
    )
    assert {e["event"]: e["probability"] for e in result["event_probabilities"]} == pytest.approx(
        {"actor-or-first": 0.6, "object-and-second": 0.4}
    )
    assert [a["probability"] for a in result["alternatives"]] == pytest.approx(
        [0.4, 0.3, 0.2, 0.1][:displayed]
    )


def forge_joint_probability(result, case):
    if case == "marginal":
        for marginal in result["marginals"]:
            if marginal["decision"] == "target":
                marginal["probability"] = 0.65 if marginal["candidate"] == "first" else 0.35
        return
    event, probability = {
        "zero_event": ("object-and-second", 0),
        "overclaimed_event": ("actor-or-first", 0.8),
        "double_counted_union": ("actor-or-first", 0.7),
    }[case]
    next(e for e in result["event_probabilities"] if e["event"] == event)["probability"] = (
        probability
    )
