"""Local interpretation custody shared by report binding and its native realization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from .identity import canonical_bytes


def _digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


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
    if request["selection"]["scope_id"] != report["constraint_id"] or not set(dependencies) <= {
        dep["key"] for dep in request["dependencies"]
    }:
        raise ValueError("local interpretation request omits scope or dependencies")
    if report["probability_standing"] != "provisional_candidate_relative":
        raise ValueError("local interpretation cannot claim calibrated or factual probability")
    joint = any(len(factor["scope"]) > 1 for factor in request["potentials"])
    mode = "coupled" if joint else "independent" if request["potentials"] else "feasibility"
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
