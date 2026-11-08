"""Correct seals do not make malformed numerical products valid."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pytest

from corpus_structure.methods.local_interpretation import (
    local_constraint_id,
    local_question_operation,
)
from corpus_structure.semantic import record_interpretation as ri
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.local_interpretation_reports import (
    validate_local_interpretation_report,
)
from corpus_structure.semantic.observations import source_python, source_value

from .test_local_interpretation import local_request


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


def operation(*, limits=None, offset=0, hard_zero=False, events=None):
    rows = (dict(contribution_id="retained", computation_dependencies=("source",)),)
    question = "local numerical control"
    identity = local_constraint_id(question, rows, ("source",))
    request = local_request()
    request = replace(
        request,
        selection=replace(request.selection, scope_id=identity),
        potentials=tuple(
            replace(
                p,
                values=tuple(
                    -float("inf") if hard_zero and i == 0 else v + offset
                    for i, v in enumerate(p.values)
                ),
            )
            for p in request.potentials
        ),
        events=events
        or (ri.CompositeEvent("actor", "actor role", ((ri.Choice("role", "actor"),),)),),
        limits=limits or request.limits,
    )
    return local_question_operation(
        question=question, contributions=rows, dependency_ids=("source",), request=request
    ), rows


def forged(change, **kwargs):
    actual, rows = operation(**kwargs)
    actual = deepcopy(actual)
    report = actual["local_interpretation"]
    request, result = source_python(report["request"]), source_python(report["result"])
    change(request, result)
    for key, value in (("request", request), ("result", result)):
        report[key] = source_value(value)
        report[key + "_digest"] = sha256(canonical_bytes(report[key])).hexdigest()
    report["seal"] = sha256(
        canonical_bytes({k: v for k, v in report.items() if k != "seal"})
    ).hexdigest()
    return actual, rows


@pytest.mark.parametrize(
    "case",
    (
        "probability",
        "unknown_decision",
        "unknown_candidate",
        "missing_marginal",
        "normalization",
        "event_membership",
        "partial_assignment",
        "unknown_assignment",
        "duplicate_assignment",
        "factor_axis",
        "factor_size",
        "duplicate_candidate",
        "exact_support",
        "log_partition",
        "constraint_support",
        "constraint_kind",
    ),
)
def test_resealed_malformed_local_products_refuse(case):
    def mutate(request, result):
        if case == "probability":
            result["marginals"][0]["probability"] = 2
        if case == "unknown_decision":
            result["marginals"][0]["decision"] = "foreign"
        if case == "unknown_candidate":
            result["marginals"][0]["candidate"] = "foreign"
        if case == "missing_marginal":
            result["marginals"].pop()
        if case == "normalization":
            result["marginals"][0]["probability"] = 0
        if case == "event_membership":
            result["event_probabilities"][0]["event"] = "foreign"
        if case == "partial_assignment":
            result["alternatives"][0]["choices"].pop()
        if case == "unknown_assignment":
            result["alternatives"][0]["choices"][0]["candidate"] = "foreign"
        if case == "duplicate_assignment":
            result["alternatives"][1] = deepcopy(result["alternatives"][0])
        if case == "factor_axis":
            request["potentials"][0]["scope"][0] = "foreign"
        if case == "factor_size":
            request["potentials"][0]["values"].pop()
        if case == "duplicate_candidate":
            request["decisions"][0]["candidates"][1] = deepcopy(
                request["decisions"][0]["candidates"][0]
            )
        if case == "exact_support":
            result["exact_retained_support"] = False
        if case == "log_partition":
            result["log_partition"] = None
        if case == "constraint_support":
            request["constraints"] = [
                dict(
                    key="hard-mask",
                    scope=["role"],
                    allowed=[False, False],
                    dependency_ids=["source"],
                )
            ]
        if case == "constraint_kind":
            request["constraints"] = [
                dict(key="bad-mask", scope=["role"], values=[0, 0], dependency_ids=["source"])
            ]

    actual, rows = forged(mutate)
    with pytest.raises(ValueError):
        validate_local_interpretation_report(actual, rows)


def test_valid_negative_logs_and_truncated_display_do_not_require_unit_display_mass():
    actual, rows = operation(limits=ri.SearchLimits(displayed_alternatives=1), offset=-100)
    result = source_python(actual["local_interpretation"]["result"])
    assert result["log_partition"] < 0 and result["alternatives"][0]["probability"] < 1
    validate_local_interpretation_report(actual, rows)


@pytest.mark.parametrize("displayed", (2, 4))
def test_joint_probabilities_agree_with_partial_and_complete_display(displayed):
    actual, rows = operation(
        limits=ri.SearchLimits(displayed_alternatives=displayed), events=joint_events()
    )
    assert_joint_probabilities(source_python(actual["local_interpretation"]["result"]), displayed)
    validate_local_interpretation_report(actual, rows)


@pytest.mark.parametrize(
    ("case", "displayed"),
    (("zero_event", 2), ("overclaimed_event", 2), ("marginal", 2), ("double_counted_union", 4)),
)
def test_resealed_joint_probabilities_outside_displayed_bounds_refuse(case, displayed):
    actual, rows = forged(
        lambda request, result: forge_joint_probability(result, case),
        limits=ri.SearchLimits(displayed_alternatives=displayed),
        events=joint_events(),
    )
    claim = "marginal" if case == "marginal" else "event"
    with pytest.raises(ValueError, match=f"{claim} probability differs from displayed support"):
        validate_local_interpretation_report(actual, rows)


def test_limited_result_retains_no_probability_or_exact_support_claim():
    actual, rows = operation(limits=ri.SearchLimits(max_states=1))
    assert actual["outcome"] == "limited"
    validate_local_interpretation_report(actual, rows)


def test_explicit_negative_infinity_is_retained_as_hard_zero_support():
    actual, rows = operation(hard_zero=True)
    result = source_python(actual["local_interpretation"]["result"])
    assert result["search"]["positive_states"] == 3
    validate_local_interpretation_report(actual, rows)
