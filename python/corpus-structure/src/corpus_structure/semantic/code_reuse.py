"""Optional bounded explanations of the code custody used by an operation."""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CodeReuseFact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    standing: Literal["unresolved", "proven_exclusion", "runtime_observation"]
    module: str | None = None
    line: int | None = None
    reason: str
    semantic_owner: str = "determining code custody"
    dependency_path: tuple[str, ...] = ()


class CodeReuseExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    entry_point: str
    tier: str
    process_id: int
    eligible: bool
    outcome: Literal["derived", "reused", "withheld", "unknown"]
    code_identity: str | None
    observed_identity: str
    facts: tuple[CodeReuseFact, ...]
    omitted: int = 0
    next_action: str | None = None


_COLLECTOR: ContextVar[list[CodeReuseExplanation] | None] = ContextVar(
    "code_reuse_explanation", default=None
)


@contextmanager
def explain_code_reuse(enabled=True):
    if not enabled:
        yield []
        return
    records: list[CodeReuseExplanation] = []
    token = _COLLECTOR.set(records)
    try:
        yield records
    finally:
        _COLLECTOR.reset(token)


def code_reuse_report(
    code,
    *,
    entry_point: str,
    tier: str,
    outcome: Literal["derived", "reused", "withheld", "unknown"] = "unknown",
    limit=16,
):
    selected = tuple(
        CodeReuseFact(
            standing="unresolved",
            module=item.module,
            line=item.line,
            reason=item.reason,
        )
        for item in code.unknowns[:limit]
    )
    return CodeReuseExplanation(
        entry_point=entry_point,
        tier=tier,
        process_id=os.getpid(),
        eligible=code.complete,
        outcome=outcome,
        code_identity=code.digest,
        observed_identity=code.observed_digest,
        facts=selected,
        omitted=max(0, len(code.unknowns) - len(selected)),
        next_action="Resolve the attributed dependency with its semantic owner before reusing this tier."
        if not code.complete
        else None,
    )


def record_code_reuse(
    code,
    *,
    entry_point: str,
    tier: str,
    outcome: Literal["derived", "reused", "withheld", "unknown"] = "unknown",
):
    collector = _COLLECTOR.get()
    if collector is not None:
        report = code_reuse_report(code, entry_point=entry_point, tier=tier, outcome=outcome)
        # One operation can revisit the same captured owner. Keep its latest actual
        # outcome while retaining distinct entry points and tiers.
        collector[:] = [
            prior for prior in collector if (prior.entry_point, prior.tier) != (entry_point, tier)
        ]
        collector.append(report)


class ReuseExplanationReport(BaseModel):
    version: Literal[1] = 1
    availability: Literal["available", "unavailable"]
    reports: tuple[CodeReuseExplanation, ...] = ()
    reason: str | None = None


def explanation_report(records):
    return ReuseExplanationReport(
        availability="available" if records else "unavailable",
        reports=tuple(records),
        reason=None if records else "The owning operation retained no code reuse explanation.",
    )


def attach_reuse_explanation(result, records):
    return {**result, "reuse_explanation": explanation_report(records).model_dump(mode="json")}


def retain_reuse_explanation(invocation, records):
    report = explanation_report(records)
    path = invocation.directory / "reuse-explanation.json"
    path.write_text(report.model_dump_json() + "\n")
    invocation.publish("reuse_explanation", path)
    return report
