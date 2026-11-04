"""Protected inspection and paired comparison of immutable record evaluations.

This module reads existing evaluator products. It neither authors reference labels nor
decides adoption, invents causal stages, or exposes an ordinary producer/MCP route.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from corpus_structure.semantic.metadata import table

from .record_alignment import APPLICABILITY_PROTOCOL, FAMILIES, TIERS
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
        reference_release_id=result.get("reference_release_id", result["release_id"]),
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
                "comparison_policy",
                "grain",
                "partition",
                "sampling_digest",
            )
        )
        or before.get("protocol") != EVALUATION_PROTOCOL
    ):
        raise ReferenceError("comparison requires the same frozen reference/sampling target")
    provenance = _paired_applicability(baseline, revised)
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
        for tier in TIERS:
            if old["tiers"][tier]["reference"] != new["tiers"][tier]["reference"]:
                raise ReferenceError("comparison changed an independent unit denominator")
            for family in FAMILIES:
                if (
                    old["families"][family][tier]["reference"]
                    != new["families"][family][tier]["reference"]
                ):
                    raise ReferenceError(
                        "comparison changed an independent unit family denominator"
                    )
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
        baseline_prediction_release_id=before["release_id"],
        revised_prediction_release_id=after["release_id"],
        reference_release_id=provenance["reference_release_id"],
        reference_applicability=provenance,
        sampling_digest=before["sampling_digest"],
        partition=before["partition"],
        families=families,
        paired_units=pairs,
        quality_claim="not_established",
        decision_owner="M1-15 coordinator",
    )


def _checked_applicability(evaluation):
    """Consume native-validated immutable store metadata, never author a mapping.

    The public caller obtains these rows through ``read_evaluation`` with evaluator
    credentials. This pure comparison is not another protected insertion boundary.
    """
    result = evaluation["result"]
    app = result.get("applicability")
    if app is None:
        return None
    if (
        app.get("protocol") != APPLICABILITY_PROTOCOL
        or app.get("run_id") != evaluation["run_id"]
        or app.get("prediction_release_id") != result["release_id"]
        or app.get("reference_release_id") != result.get("reference_release_id")
        or app.get("comparison_policy") != result["comparison_policy"]
        or not app.get("contract_digest")
        or not app.get("guideline_digest")
    ):
        raise ReferenceError("comparison has inconsistent native applicability provenance")
    views = app.get("views", ())
    if (
        not views
        or len({row["reference_view_id"] for row in views}) != len(views)
        or len({row["prediction_view_id"] for row in views}) != len(views)
        or len({row["physical_digest"] for row in views}) != len(views)
    ):
        raise ReferenceError("comparison has incomplete or nonbijective source correspondence")
    actual = {row["reference_view_id"]: row for row in views}
    consumed = set()
    for unit in result["units"]:
        evidence = unit["gap_evidence"]
        if (
            evidence["source_run_id"] != app["source_run_id"]
            or evidence["source_cut_id"] != app["source_cut_id"]
            or evidence["run_id"] != app["run_id"]
            or evidence["cut_id"] != app["cut_id"]
            or unit["reference_policy_version"] != app["reference_policy_version"]
            or unit["prediction_policy_version"] != app["prediction_policy_version"]
        ):
            raise ReferenceError("comparison unit differs from native source/policy provenance")
        for pair in unit.get("correspondence", ()):
            original = pair["reference_pin"]["source_view_id"]
            mapped = actual.get(original)
            if (
                mapped is None
                or mapped["prediction_view_id"] != pair["prediction_pin"]["source_view_id"]
                or mapped["physical_digest"] != pair["physical_digest"]
            ):
                raise ReferenceError("comparison unit correspondence differs from frozen closure")
            consumed.add(original)
    if consumed != actual.keys():
        raise ReferenceError("comparison omitted part of the frozen source closure")
    return app


def _paired_applicability(baseline, revised):
    before, after = baseline["result"], revised["result"]
    old, new = _checked_applicability(baseline), _checked_applicability(revised)
    if old is None and new is None:
        if before["release_id"] != after["release_id"]:
            raise ReferenceError("comparison requires native applicability for a successor release")
        return dict(
            reference_release_id=before["release_id"], provenance="legacy_same_release_grades"
        )
    if old is not None and new is not None:
        keys = (
            "reference_release_id",
            "comparison_policy",
            "source_run_id",
            "source_cut_id",
            "contract_digest",
            "guideline_digest",
            "reference_policy_version",
            "prediction_policy_version",
        )

        def closure(app):
            return sorted(
                (row["reference_view_id"], row["reference_key"], row["physical_digest"])
                for row in app["views"]
            )

        if any(old[key] != new[key] for key in keys) or closure(old) != closure(new):
            raise ReferenceError(
                "comparison changed the source-reading contract or frozen physical closure"
            )
        return dict(
            reference_release_id=old["reference_release_id"],
            provenance="native_applicability_both_sides",
            contract_digest=old["contract_digest"],
            guideline_digest=old["guideline_digest"],
            source_run_id=old["source_run_id"],
            source_cut_id=old["source_cut_id"],
        )
    # An original native grade already authenticated its frozen source/frame exactly.
    # It need not be rewritten or executed again to compare a compatible successor.
    if old is not None or new is None or before["release_id"] != new["reference_release_id"]:
        raise ReferenceError(
            "legacy comparison side is not the immutable original-reference release"
        )
    views = {row["reference_view_id"] for row in new["views"]}
    for unit in before["units"]:
        evidence = unit["gap_evidence"]
        if (
            evidence["source_run_id"] != new["source_run_id"]
            or evidence["source_cut_id"] != new["source_cut_id"]
            or evidence["source_view_id"] not in views
        ):
            raise ReferenceError(
                "legacy original-side grade does not bind the frozen source closure"
            )
    return dict(
        reference_release_id=new["reference_release_id"],
        provenance="legacy_original_side_native_grade",
        contract_digest=new["contract_digest"],
        guideline_digest=new["guideline_digest"],
        source_run_id=new["source_run_id"],
        source_cut_id=new["source_cut_id"],
    )
