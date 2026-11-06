"""Private local-question consumer of retained contributions and actual factor policies.

This is a pure preparation/sealing boundary. Native report admission and source custody
remain with their existing owners; a seal is attribution, never publication authority.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from threading import Event
from typing import Any

from corpus_structure.methods.record_readings import _digest, _sealed_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_interpretation import (
    LocalInterpretationRequest,
    interpret_local,
)


def interpret_contribution_question(
    *,
    question_id: str,
    contributions: Sequence[Mapping[str, Any]],
    dependency_ids: tuple[str, ...],
    request: LocalInterpretationRequest | None = None,
    cancellation: Event | None = None,
    unavailable_reason: str | None = None,
    unavailable_policy_version: str | None = None,
) -> dict[str, Any]:
    """Seal a declared local question without requiring an assembled record.

    The caller supplies a source-authenticated, bounded selection and all consumed
    computation dependencies. A request must preserve that dependency closure. With no
    applicable real policy the retained products remain useful and inference is not_run.
    """
    if not question_id or not dependency_ids or any(not key for key in dependency_ids):
        raise ValueError("local question requires identity and consumed dependencies")
    if len(set(dependency_ids)) != len(dependency_ids):
        raise ValueError("local question dependencies must be unique")
    identities: dict[str, Mapping[str, Any]] = {}
    for contribution in contributions:
        key = contribution.get("contribution_id")
        if not isinstance(key, str) or not key:
            raise ValueError("local question requires identified retained contributions")
        if key in identities and identities[key] != contribution:
            raise ValueError("conflicting retained contribution identity")
        if not set(contribution.get("computation_dependencies", ())) <= set(dependency_ids):
            raise ValueError("local question omits retained contribution dependencies")
        identities[key] = contribution
    retained = [identities[key] for key in sorted(identities)]
    row: dict[str, Any] = dict(
        constraint_id=question_id,
        contribution_ids=sorted(identities),
        retained_input_digest=_digest(retained),
        dependencies=sorted(dependency_ids),
        independent_baseline="retained_independent_contributions",
        probability_standing="not_computed",
        coupling_enabled=False,
        policy_mode="not_run",
        policy_version=unavailable_policy_version or "table-interpretation-1",
    )
    if request is None:
        row.update(
            outcome="not_run",
            reason=unavailable_reason or "applicable real local factor policy unavailable",
        )
    else:
        if request.selection.scope_id != question_id:
            raise ValueError("local interpretation scope differs from declared question")
        if not set(dependency_ids) <= {dep.key for dep in request.dependencies}:
            raise ValueError("local interpretation omits retained computation dependencies")
        from corpus_structure.semantic.local_interpretation_reports import local_policy_mode

        mode, joint = local_policy_mode(asdict(request))
        policy = next(
            (d for d in request.dependencies if d.key == request.policy_dependency_id), None
        )
        if policy is None:
            raise ValueError("local interpretation policy dependency unavailable")
        row.update(
            coupling_enabled=joint,
            policy_mode=mode,
            policy_version=policy.revision,
        )
        request_row = _sealed_value(asdict(request))
        result = _sealed_value(asdict(interpret_local(request, cancellation=cancellation)))
        row.update(
            request=request_row,
            request_digest=_digest(request_row),
            result=result,
            result_digest=_digest(result),
            outcome=result["outcome"],
            probability_standing=result["probability_standing"],
            reason="private candidate-relative interpretation; no admission authority",
        )
    row["seal"] = _digest(row)
    return row


def local_question_operation(
    *,
    question: str,
    contributions: Sequence[Mapping[str, Any]],
    dependency_ids: tuple[str, ...],
    request: LocalInterpretationRequest | None = None,
    cancellation: Event | None = None,
    unavailable_reason: str | None = None,
    unavailable_policy_version: str | None = None,
) -> dict[str, Any]:
    """Released operation row; exact SourceValue encoding preserves numerical report bytes."""
    from corpus_structure.semantic.observations import source_value

    question_id = local_constraint_id(question, contributions, dependency_ids)
    report = interpret_contribution_question(
        question_id=question_id,
        contributions=contributions,
        dependency_ids=dependency_ids,
        request=request,
        cancellation=cancellation,
        unavailable_reason=unavailable_reason,
        unavailable_policy_version=unavailable_policy_version,
    )
    report["contribution_ids"] = tuple(report["contribution_ids"])
    report["dependencies"] = tuple(report["dependencies"])
    for field in ("request", "result"):
        if field in report:
            report[field] = source_value(json.loads(canonical_bytes(report[field])))
            report[field + "_digest"] = _digest(report[field])
    report["seal"] = _digest({key: value for key, value in report.items() if key != "seal"})
    outcome = report["outcome"]
    operation_outcome = (
        "succeeded"
        if outcome == "completed"
        else (
            "limited"
            if outcome == "resource_limit"
            else "not_run"
            if outcome == "not_run"
            else "failed"
        )
    )
    return dict(
        operation_key=question_id,
        question=question,
        operation_version="local-interpretation-2",
        outcome=operation_outcome,
        inspected_count=len(report["contribution_ids"]),
        emitted_count=0,
        computation_dependencies=tuple(sorted(dependency_ids)),
        reason=report["reason"],
        local_interpretation=report,
    )


def local_constraint_id(question, contributions, dependency_ids):
    from corpus_structure.semantic.contributions import operation_identity

    return operation_identity(
        "local-interpretation-2",
        question,
        sorted(row["contribution_id"] for row in contributions),
        sorted(dependency_ids),
    )
