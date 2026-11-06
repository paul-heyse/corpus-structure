"""Local interpretation custody shared by report binding and its native realization."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from .identity import canonical_bytes


def _digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def local_policy_mode(request: Mapping[str, Any]) -> tuple[str, bool]:
    """Classify a declared control without confusing absent factors with uniform support."""
    potentials = request["potentials"]
    joint = any(len(factor["scope"]) > 1 for factor in potentials)
    control = request.get("feasibility_control", False)
    if type(control) is not bool:
        raise ValueError("feasibility control must be an explicit Boolean")
    if control:
        if (
            any(len(factor["scope"]) != 1 for factor in potentials)
            or not potentials
            or any(value != 0.0 for factor in potentials for value in factor["values"])
        ):
            raise ValueError("feasibility control requires explicit zero unary potentials")
        return "feasibility", False
    return ("coupled" if joint else "independent" if potentials else "feasibility"), joint


def validate_local_interpretation_values(request, result) -> None:
    """Validate the declared numerical product, without solving or rescoring it."""

    def number(value):
        try:
            return type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            return False

    def probability(value):
        return number(value) and 0 <= value <= 1

    if (
        result["outcome"]
        not in {
            "completed",
            "invalid_input",
            "infeasible",
            "numerical_failure",
            "resource_limit",
            "cancelled",
        }
        or result.get("omitted_candidate_mass") != "unknown"
    ):
        raise ValueError("local interpretation result has unsupported claim domain")
    if result.get("dependencies") != request.get("dependencies") or result.get(
        "selection"
    ) != request.get("selection"):
        raise ValueError("local interpretation result substitutes request provenance")
    if result["outcome"] != "completed":
        if (
            result.get("exact_retained_support") is not False
            or any(result.get(k) for k in ("marginals", "event_probabilities", "alternatives"))
            or result.get("log_partition") is not None
        ):
            raise ValueError("noncompleted local interpretation cannot carry probability claims")
        return
    if result.get("exact_retained_support") is not True or not number(result.get("log_partition")):
        raise ValueError("completed local interpretation requires finite exact support")
    decisions = request["decisions"]
    axes = {d["key"]: tuple(c["key"] for c in d["candidates"]) for d in decisions}
    if (
        not axes
        or len(axes) != len(decisions)
        or any(
            not isinstance(k, str)
            or not k
            or not values
            or len(values) != len(set(values))
            or any(not isinstance(v, str) or not v for v in values)
            for k, values in axes.items()
        )
    ):
        raise ValueError("local interpretation decisions/candidates must be nonempty and unique")
    if any(
        c["kind"] not in {"resolved", "unresolved", "local_new"}
        or (c["kind"] == "unresolved" and not c["reason"])
        for d in decisions
        for c in d["candidates"]
    ):
        raise ValueError("local interpretation candidate kind/reason invalid")
    dependencies = {d["key"]: d for d in request["dependencies"]}
    if len(dependencies) != len(request["dependencies"]) or any(
        not k
        or not d["revision"]
        or d["kind"]
        not in {
            "observation",
            "counterevidence",
            "rejected_alternative",
            "retrieval",
            "context",
            "selection",
            "model",
            "ontology",
            "policy",
        }
        for k, d in dependencies.items()
    ):
        raise ValueError("local interpretation dependencies must be unique and versioned")
    for field, kind in (
        ("model_dependency_id", "model"),
        ("ontology_dependency_id", "ontology"),
        ("policy_dependency_id", "policy"),
    ):
        if request[field] not in dependencies or dependencies[request[field]]["kind"] != kind:
            raise ValueError("local interpretation required dependency kind differs")

    def dependency_ids(values):
        if not values or len(values) != len(set(values)) or not set(values) <= dependencies.keys():
            raise ValueError("local interpretation computation dependency unavailable")

    dependency_ids(request["selection"]["dependency_ids"])
    table_keys, covered = set(), set()
    for table_index, table in enumerate((*request["potentials"], *request["constraints"])):
        scope = table["scope"]
        if (
            not scope
            or len(scope) != len(set(scope))
            or not set(scope) <= axes.keys()
            or not table["key"]
            or table["key"] in table_keys
        ):
            raise ValueError("local interpretation factor scope/key invalid")
        table_keys.add(table["key"])
        dependency_ids(table["dependency_ids"])
        field = "values" if table_index < len(request["potentials"]) else "allowed"
        other = "allowed" if field == "values" else "values"
        if field not in table or other in table or not isinstance(table[field], list):
            raise ValueError("local interpretation factor kind/array invalid")
        values = table[field]
        if len(values) != math.prod(len(axes[key]) for key in scope):
            raise ValueError("local interpretation factor cardinality differs from axes")
        if "values" in table:
            covered.update(scope)
            if any(not number(v) and v != {"nonfinite_float": "-inf"} for v in values):
                raise ValueError("local interpretation log potentials must be finite or hard zero")
        elif any(type(v) is not bool for v in values):
            raise ValueError("local interpretation constraint support must be boolean")
    if covered != axes.keys():
        raise ValueError("completed local interpretation lacks explicit axis support")
    for dependence in request["dependence_scopes"]:
        scope = dependence["scope"]
        if (
            not scope
            or len(scope) != len(set(scope))
            or not set(scope) <= axes.keys()
            or not dependence["reason"]
        ):
            raise ValueError("local interpretation dependence scope invalid")
        dependency_ids(dependence["dependency_ids"])
    selected = request["marginal_decisions"]
    selected = tuple(axes) if selected is None else selected
    if len(selected) != len(set(selected)) or not set(selected) <= axes.keys():
        raise ValueError("local interpretation marginal selection invalid")
    marginals = result["marginals"]
    expected = {(key, candidate) for key in selected for candidate in axes[key]}
    if (
        len(marginals) != len(expected)
        or {(m["decision"], m["candidate"]) for m in marginals} != expected
        or any(not probability(m["probability"]) for m in marginals)
    ):
        raise ValueError("local interpretation marginal membership or probability invalid")
    if any(
        not math.isclose(
            sum(m["probability"] for m in marginals if m["decision"] == key),
            1,
            rel_tol=0,
            abs_tol=1e-9,
        )
        for key in selected
    ):
        raise ValueError("local interpretation marginal normalization invalid")

    def choices(values, complete=False):
        binding = {c["decision"]: c["candidate"] for c in values}
        if (
            not binding
            or len(binding) != len(values)
            or not binding.keys() <= axes.keys()
            or any(v not in axes[k] for k, v in binding.items())
            or (complete and binding.keys() != axes.keys())
        ):
            raise ValueError("local interpretation assignment membership invalid")
        return binding

    events = request["events"]
    keys = [e["key"] for e in events]
    if len(keys) != len(set(keys)) or not all(keys) or (not selected and not events):
        raise ValueError("local interpretation event/question selection invalid")
    for event in events:
        if not event["question"].strip() or not event["derivations"]:
            raise ValueError("local interpretation event requires explicit derivations")
        for derivation in event["derivations"]:
            choices(derivation)
    actual = result["event_probabilities"]
    if (
        len(actual) != len(keys)
        or {e["event"] for e in actual} != set(keys)
        or any(not probability(e["probability"]) for e in actual)
    ):
        raise ValueError("local interpretation event membership or probability invalid")
    alternatives = result["alternatives"]
    seen = set()
    for alternative in alternatives:
        binding = choices(alternative["choices"], complete=True)
        identity = tuple(sorted(binding.items()))
        if identity in seen or not probability(alternative["probability"]):
            raise ValueError("local interpretation alternatives repeat or have invalid probability")
        seen.add(identity)
        for constraint in request["constraints"]:
            index = 0
            for key in constraint["scope"]:
                index = index * len(axes[key]) + axes[key].index(binding[key])
            if not constraint["allowed"][index]:
                raise ValueError("local interpretation alternative violates hard support")
        for potential in request["potentials"]:
            index = 0
            for key in potential["scope"]:
                index = index * len(axes[key]) + axes[key].index(binding[key])
            if potential["values"][index] == {"nonfinite_float": "-inf"}:
                raise ValueError("local interpretation alternative violates hard zero")
    search, limits = result["search"], request["limits"]
    if (
        search["limits"] != limits
        or any(
            type(limits[k]) is not int or limits[k] < minimum
            for k, minimum in (
                ("max_states", 1),
                ("block_states", 1),
                ("max_workspace_bytes", 1),
                ("displayed_alternatives", 0),
            )
        )
        or not number(limits["max_seconds"])
        or limits["max_seconds"] < 0
    ):
        raise ValueError("local interpretation search limits invalid or substituted")
    retained = math.prod(len(values) for values in axes.values())
    if (
        any(
            type(search[k]) is not int or search[k] < 0
            for k in ("retained_states", "examined_states", "positive_states")
        )
        or search["retained_states"] != retained
        or search["examined_states"] != retained
        or not 0 < search["positive_states"] <= retained
    ):
        raise ValueError("local interpretation completed support population invalid")
    if retained > limits["max_states"]:
        raise ValueError("completed local interpretation exceeds declared state support")
    displayed = limits["displayed_alternatives"]
    if (
        type(displayed) is not int
        or displayed < 0
        or len(alternatives) != min(displayed, search["positive_states"])
    ):
        raise ValueError("local interpretation alternative count differs from declared support")
    total = sum(a["probability"] for a in alternatives)
    if total > 1 + 1e-9 or (
        len(alternatives) == search["positive_states"]
        and not math.isclose(total, 1, rel_tol=0, abs_tol=1e-9)
    ):
        raise ValueError("local interpretation alternative probability mass invalid")


def validate_local_interpretation_report(
    operation: Mapping[str, Any],
    contributions: Sequence[Mapping[str, Any]],
) -> None:
    from .observations import source_python

    report = operation.get("local_interpretation")
    if report is None:
        return
    if report["seal"] != _digest({k: v for k, v in report.items() if k != "seal"}):
        raise ValueError("local interpretation seal differs from report")
    selected = report.get("contribution_ids", ())
    by_id = {row["contribution_id"]: row for row in contributions}
    if len(selected) != len(set(selected)) or not set(selected) <= by_id.keys():
        raise ValueError("local interpretation input contribution unavailable or duplicated")
    if report["retained_input_digest"] != _digest([by_id[key] for key in sorted(selected)]):
        raise ValueError("local interpretation input digest differs from retained contributions")
    if (
        report["constraint_id"] != operation["operation_key"]
        or operation["operation_version"] != "local-interpretation-2"
    ):
        raise ValueError("local interpretation differs from private operation binding")
    dependencies = report["dependencies"]
    if len(dependencies) != len(set(dependencies)) or not set(dependencies) <= set(
        operation.get("computation_dependencies", ())
    ):
        raise ValueError("local interpretation dependency closure differs from operation")
    if not dependencies or any(
        not set(by_id[key].get("computation_dependencies", ())) <= set(dependencies)
        for key in selected
    ):
        raise ValueError("local interpretation omits retained contribution dependencies")
    if operation["inspected_count"] != len(selected) or operation["emitted_count"] != 0:
        raise ValueError("local interpretation population differs from selected contributions")
    if report["outcome"] == "not_run":
        if (
            report["policy_mode"] != "not_run"
            or report["coupling_enabled"]
            or operation["outcome"] != "not_run"
            or report["probability_standing"] != "not_computed"
            or any(k in report for k in ("request", "result", "request_digest", "result_digest"))
        ):
            raise ValueError("unrun local interpretation cannot carry computed probabilities")
        return
    if not all(key in report for key in ("request", "result", "request_digest", "result_digest")):
        raise ValueError("executed local interpretation requires exact request/result custody")
    for field in ("request", "result"):
        if report[field + "_digest"] != _digest(report[field]):
            raise ValueError("local interpretation request/result digest differs")
    request, result = source_python(report["request"]), source_python(report["result"])
    validate_local_interpretation_values(request, result)
    if request["selection"]["scope_id"] != report["constraint_id"] or not set(dependencies) <= {
        dep["key"] for dep in request["dependencies"]
    }:
        raise ValueError("local interpretation request omits scope or dependencies")
    if report["probability_standing"] != "provisional_candidate_relative":
        raise ValueError("local interpretation cannot claim calibrated or factual probability")
    mode, joint = local_policy_mode(request)
    policy = next(
        (dep for dep in request["dependencies"] if dep["key"] == request["policy_dependency_id"]),
        None,
    )
    if (
        report["coupling_enabled"] != joint
        or report["policy_mode"] != mode
        or policy is None
        or report["policy_version"] != policy["revision"]
    ):
        raise ValueError("local interpretation mode or policy differs from actual factors")
    expected = (
        "succeeded"
        if report["outcome"] == "completed"
        else "limited"
        if report["outcome"] == "resource_limit"
        else "failed"
    )
    if (
        operation["outcome"] != expected
        or result["outcome"] != report["outcome"]
        or report["probability_standing"] != result["probability_standing"]
    ):
        raise ValueError("local interpretation outcome differs from actual result")
    if report["outcome"] != "completed" and (
        result.get("marginals")
        or result.get("event_probabilities")
        or result.get("alternatives")
        or result.get("log_partition") is not None
    ):
        raise ValueError("failed local interpretation cannot carry partial probabilities")
