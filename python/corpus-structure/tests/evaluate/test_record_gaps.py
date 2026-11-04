"""Paired immutable grading controls; these are not population-quality evidence."""

from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.evaluate.record_alignment import FAMILIES, TIERS
from corpus_structure.evaluate.record_gaps import compare_evaluations, inspect_gaps
from corpus_structure.evaluate.record_references import EVALUATION_PROTOCOL
from corpus_structure.evaluate.semantic import ReferenceError


def evaluation(identity=1) -> dict[str, Any]:
    counts = dict(reference=2, prediction=2, matched=1, precision=0.5, recall=0.5, f1=0.5)
    return dict(
        id=identity,
        project_id="p",
        run_id=identity,
        set_id=3,
        content_digest=str(identity) * 64,
        reference_snapshot=[dict(unit_id=4, pass_id=5, frame_id=6)],
        result=dict(
            protocol=EVALUATION_PROTOCOL,
            release_id="r",
            comparison_policy="strict-source-occurrence-1",
            grain="accepted_source_record_occurrence",
            partition="development",
            sampling_digest="a" * 64,
            output_realization_id=f"output:{identity}",
            quality_claim="not_established",
            families={family: {tier: dict(counts) for tier in TIERS} for family in FAMILIES},
            units=[
                dict(
                    unit="u",
                    origin_group="o",
                    guideline_version="g",
                    reference_policy_version="ref",
                    prediction_policy_version="pred",
                    tiers={tier: dict(counts) for tier in TIERS},
                    families={
                        family: {tier: dict(counts) for tier in TIERS} for family in FAMILIES
                    },
                    matches={tier: ["correct"] for tier in TIERS},
                    gap_evidence=dict(
                        unit_id=4,
                        pass_id=5,
                        frame_id=6,
                        source_view_id=7,
                        source_run_id=8,
                        source_cut_id=9,
                        run_id=identity,
                        cut_id=10,
                        cohort="targeted",
                        tasks=[],
                        gaps=[],
                    ),
                )
            ],
        ),
    )


def test_paired_correct_gain_retains_new_errors_and_per_origin_losses():
    old, new = evaluation(), evaluation(2)
    for tier in TIERS:
        new["result"]["families"]["table"][tier].update(prediction=4, matched=2)
        new["result"]["units"][0]["matches"][tier] = ["new-correct"]
    comparison = compare_evaluations(old, new)
    assert comparison["families"]["table"]["full"]["correct_change"] == 1
    assert comparison["families"]["table"]["full"]["error_change"] == 1
    assert comparison["paired_units"] == [
        dict(unit="u", origin_group="o", extra_correct=["new-correct"], lost_correct=["correct"])
    ]
    assert comparison["quality_claim"] == "not_established"
    assert comparison["decision_owner"] == "M1-15 coordinator"


@pytest.mark.parametrize(
    "change", ["set", "snapshot", "sampling", "release", "policy", "unit", "origin", "denominator"]
)
def test_changed_reference_or_target_refuses_paired_claim(change):
    old, new = evaluation(), evaluation(2)
    if change == "set":
        new["set_id"] = 9
    elif change == "snapshot":
        new["reference_snapshot"][0]["pass_id"] = 99
    elif change in ("sampling", "release"):
        new["result"]["sampling_digest" if change == "sampling" else "release_id"] = "changed"
    elif change == "denominator":
        new["result"]["families"]["table"]["full"]["reference"] += 1
    else:
        field = {"policy": "prediction_policy_version", "unit": "unit", "origin": "origin_group"}[
            change
        ]
        new["result"]["units"][0][field] = "changed"
    with pytest.raises(ReferenceError):
        compare_evaluations(old, new)


def test_inspection_preserves_empty_unit_and_does_not_synthesize_missing_diagnostics():
    frozen = evaluation()
    original = deepcopy(frozen)
    inspected = inspect_gaps(frozen)
    assert inspected["units"][0]["tasks"] == []
    assert inspected["units"][0]["gaps"] == []
    assert inspected["sampling_digest"] == "a" * 64
    assert frozen == original
    del frozen["result"]["units"][0]["gap_evidence"]
    with pytest.raises(ReferenceError, match="predates"):
        inspect_gaps(frozen)


def applicable_evaluation(identity, release) -> dict[str, Any]:
    value = evaluation(identity)
    result = value["result"]
    result["release_id"] = release
    result["reference_release_id"] = "r"
    actual_view = 70 + identity
    result["applicability"] = dict(
        protocol="source-record-reference-applicability-1",
        comparison_policy="strict-source-occurrence-1",
        reference_release_id="r",
        prediction_release_id=release,
        run_id=identity,
        cut_id=10,
        source_run_id=8,
        source_cut_id=9,
        contract_digest="c" * 64,
        guideline_digest="d" * 64,
        reference_policy_version="ref",
        prediction_policy_version="pred",
        views=[
            dict(
                reference_view_id=7,
                prediction_view_id=actual_view,
                reference_key="original-view",
                prediction_key=f"actual-view-{identity}",
                physical_digest="e" * 64,
            )
        ],
    )
    unit = result["units"][0]
    unit["release_id"] = release
    unit["reference_release_id"] = "r"
    unit["correspondence"] = [
        dict(
            reference_pin=dict(source_view_id=7),
            prediction_pin=dict(source_view_id=actual_view),
            physical_digest="e" * 64,
        )
    ]
    return value


def test_native_applicability_pairs_distinct_actual_releases_with_original_correct_ids():
    old, new = (
        applicable_evaluation(1, "implementation-1"),
        applicable_evaluation(2, "implementation-2"),
    )
    new["result"]["units"][0]["matches"]["full"] = ["new-original-reference-correct"]
    result = compare_evaluations(old, new)
    assert result["reference_release_id"] == "r"
    assert result["baseline_prediction_release_id"] == "implementation-1"
    assert result["revised_prediction_release_id"] == "implementation-2"
    assert result["reference_applicability"]["provenance"] == "native_applicability_both_sides"
    assert result["paired_units"][0]["extra_correct"] == ["new-original-reference-correct"]
    assert "release_id" not in result


def test_legacy_original_native_grade_compares_without_regrade_or_inventing_applicability():
    old, new = evaluation(), applicable_evaluation(2, "implementation-2")
    original = deepcopy(old)
    result = compare_evaluations(old, new)
    assert result["reference_applicability"]["provenance"] == "legacy_original_side_native_grade"
    assert result["baseline_prediction_release_id"] == result["reference_release_id"] == "r"
    assert old == original and "applicability" not in old["result"]


@pytest.mark.parametrize(
    "change",
    [
        "contract",
        "physical",
        "guideline",
        "old_release",
        "source_cut",
        "omitted_closure",
        "unit_denominator",
        "unit_family_denominator",
        "actual_run",
    ],
)
def test_cross_release_comparison_refuses_changed_or_unbound_premises(change):
    old, new = (
        applicable_evaluation(1, "implementation-1"),
        applicable_evaluation(2, "implementation-2"),
    )
    if change == "contract":
        new["result"]["applicability"]["contract_digest"] = "f" * 64
    elif change == "physical":
        new["result"]["applicability"]["views"][0]["physical_digest"] = "f" * 64
        new["result"]["units"][0]["correspondence"][0]["physical_digest"] = "f" * 64
    elif change == "guideline":
        new["result"]["applicability"]["guideline_digest"] = "f" * 64
    elif change == "old_release":
        old = evaluation()
        old["result"]["release_id"] = "foreign-original"
    elif change == "source_cut":
        old = evaluation()
        old["result"]["units"][0]["gap_evidence"]["source_cut_id"] = 999
    elif change == "omitted_closure":
        new["result"]["units"][0]["correspondence"] = []
    elif change == "unit_denominator":
        new["result"]["units"][0]["tiers"]["full"]["reference"] += 1
    elif change == "unit_family_denominator":
        new["result"]["units"][0]["families"]["table"]["full"]["reference"] += 1
    else:
        new["result"]["applicability"]["run_id"] = 999
    with pytest.raises(ReferenceError):
        compare_evaluations(old, new)
