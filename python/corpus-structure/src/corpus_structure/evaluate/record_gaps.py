"""Protected inspection and paired comparison of immutable record evaluations.

This module reads existing evaluator products. It neither authors reference labels nor
decides adoption, invents causal stages, or exposes an ordinary producer/MCP route.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from corpus_structure.semantic.metadata import table

from .record_alignment import FAMILIES, TIERS
from .record_references import EVALUATION_PROTOCOL
from .semantic import ReferenceError


def read_evaluation(conn, *, project_id: str, evaluation_id: int) -> Mapping[str, Any]:
    """Read through the caller's evaluator connection; database grants remain authority."""
    evaluations = table("eval.reference_evaluation")
    row = (
        conn.execute(
            select(evaluations).where(
                evaluations.c.id == evaluation_id, evaluations.c.project_id == project_id
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ReferenceError("unknown immutable evaluation in the selected project")
    if row["result"].get("protocol") != EVALUATION_PROTOCOL:
        raise ReferenceError("gap inspection requires a source-record evaluation")
    return row


def inspect_gaps(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    """Retain no-output/zero-reference units and their exact invocation evidence."""
    result = evaluation["result"]
    if any("gap_evidence" not in unit for unit in result["units"]):
        raise ReferenceError("evaluation predates native gap evidence; grade the frozen set again")
    return dict(
        evaluation_id=evaluation["id"],
        content_digest=evaluation["content_digest"],
        set_id=evaluation["set_id"],
        release_id=result["release_id"],
        output_realization_id=result["output_realization_id"],
        partition=result["partition"],
        sampling_digest=result["sampling_digest"],
        quality_claim=result["quality_claim"],
        units=[
            dict(unit=unit["unit"], origin_group=unit["origin_group"], **unit["gap_evidence"])
            for unit in result["units"]
        ],
    )


def compare_evaluations(baseline: Mapping[str, Any], revised: Mapping[str, Any]) -> dict[str, Any]:
    """Paired family gain/regression on one frozen cohort; no population inference.

    Run this separately for a targeted gap cohort and a broad regression cohort.
    Reference changes require a new baseline rather than a misleading paired result.
    """
    before, after = baseline["result"], revised["result"]
    if (
        any(baseline[key] != revised[key] for key in ("project_id", "set_id", "reference_snapshot"))
        or any(
            before.get(key) != after.get(key)
            for key in (
                "protocol",
                "release_id",
                "comparison_policy",
                "grain",
                "partition",
                "sampling_digest",
            )
        )
        or before.get("protocol") != EVALUATION_PROTOCOL
    ):
        raise ReferenceError(
            "comparison requires the same frozen reference/sampling/release target"
        )
    old_units = {unit["unit"]: unit for unit in before["units"]}
    new_units = {unit["unit"]: unit for unit in after["units"]}
    if (
        old_units.keys() != new_units.keys()
        or len(old_units) != len(before["units"])
        or len(new_units) != len(after["units"])
    ):
        raise ReferenceError("comparison requires the complete identical unit population")
    pairs = []
    for name, old in old_units.items():
        new = new_units[name]
        if any(
            old.get(key) != new.get(key)
            for key in (
                "origin_group",
                "guideline_version",
                "reference_policy_version",
                "prediction_policy_version",
            )
        ):
            raise ReferenceError("comparison changed unit origin/guideline/policy")
        pairs.append(
            dict(
                unit=name,
                origin_group=old["origin_group"],
                extra_correct=sorted(set(new["matches"]["full"]) - set(old["matches"]["full"])),
                lost_correct=sorted(set(old["matches"]["full"]) - set(new["matches"]["full"])),
            )
        )
    families = {}
    for family in FAMILIES:
        families[family] = {}
        for tier in TIERS:
            b, a = before["families"][family][tier], after["families"][family][tier]
            if b["reference"] != a["reference"]:
                raise ReferenceError("comparison changed an independent family denominator")
            families[family][tier] = dict(
                baseline=b,
                revised=a,
                correct_change=a["matched"] - b["matched"],
                error_change=(a["prediction"] - a["matched"]) - (b["prediction"] - b["matched"]),
                missing_change=(a["reference"] - a["matched"]) - (b["reference"] - b["matched"]),
            )
    return dict(
        baseline_evaluation_id=baseline["id"],
        revised_evaluation_id=revised["id"],
        baseline_content_digest=baseline["content_digest"],
        revised_content_digest=revised["content_digest"],
        set_id=baseline["set_id"],
        release_id=before["release_id"],
        sampling_digest=before["sampling_digest"],
        partition=before["partition"],
        families=families,
        paired_units=pairs,
        quality_claim="not_established",
        decision_owner="M1-15 coordinator",
    )
