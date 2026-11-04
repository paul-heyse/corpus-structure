"""Paired immutable grading controls; these are not population-quality evidence."""

from copy import deepcopy

import pytest

from corpus_structure.evaluate.record_alignment import FAMILIES, TIERS
from corpus_structure.evaluate.record_gaps import compare_evaluations, inspect_gaps
from corpus_structure.evaluate.record_references import EVALUATION_PROTOCOL
from corpus_structure.evaluate.semantic import ReferenceError


def evaluation(identity=1):
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
