"""Review view tests keep observed execution distinct from semantic assessment."""

import pytest

from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import ReviewComparison, ReviewSelection
from corpus_structure.serve.review_views import compose_review_views


def request(**kwargs):
    return ReviewSelection(selections=(ContributionRequest(run_id=1),), **kwargs)


def test_zero_emission_and_missing_public_witness_do_not_invent_semantic_failure():
    values = list(
        compose_review_views(
            request(),
            iter(
                [
                    (
                        "inventory",
                        {
                            "selection_index": 0,
                            "population": "operation",
                            "row": {
                                "operation_key": "empty",
                                "outcome": "succeeded",
                                "emitted_count": 0,
                            },
                        },
                    ),
                    (
                        "inventory",
                        {
                            "selection_index": 0,
                            "population": "assessment",
                            "row": {
                                "contribution_id": "c1",
                                "outcome": "no_public_assessment",
                                "scope": "public_only",
                            },
                        },
                    ),
                ]
            ),
        )
    )
    gap = next(row for name, row in values if name == "gaps")
    assert gap["semantic_miss"] == "not_established"
    assessment = next(row for name, row in values if name == "assessment_matrix")
    assert assessment["assessment_state"] == "no_public_assessment"
    assert assessment["private_assessment_state"] == "unknown_on_ordinary_reader"


def evaluation(identity, *, judgment="supported", frame="f", error=None):
    return {
        "kind": "evaluation",
        "project_id": "project",
        "set_id": 10,
        "value": {
            "id": identity,
            "project_id": "project",
            "set_id": 10,
            "run_id": identity,
            "reference_snapshot": [{"pass_id": 20}],
            "result": {
                "protocol": "source-operation-evaluation-1",
                "set_id": 10,
                "reference_snapshot": [{"pass_id": 20}],
                "frame_digest": frame,
                "units": [
                    {
                        "unit_id": 1,
                        "direction": "source_first",
                        "cases": [
                            {
                                "case_id": "mean",
                                "facet": "definition",
                                "judgment": judgment,
                                "error_category": error,
                            }
                        ],
                    }
                ],
            },
        },
    }


def test_grade_history_and_explicit_current_selection_remain_distinct():
    values = list(
        compose_review_views(
            request(selected_evaluation_ids=(2,)),
            iter(
                [
                    (
                        "assessment_history",
                        evaluation(1, judgment="unsupported", error="missing_output"),
                    ),
                    ("assessment_history", evaluation(2)),
                ]
            ),
        )
    )
    matrix = [row for name, row in values if name == "assessment_matrix"]
    assert [row["selected_for_current_assessment"] for row in matrix] == [False, True]
    assert [row["evaluation_id"] for row in matrix] == [1, 2]
    assert not any(name == "changes" for name, _ in values)


def test_explicit_comparison_uses_frozen_reference_compatibility():
    selection = request(
        comparisons=(ReviewComparison(baseline_evaluation_id=1, revised_evaluation_id=2),)
    )
    rows = [
        ("assessment_history", evaluation(1, judgment="unsupported", error="missing_output")),
        ("assessment_history", evaluation(2)),
    ]
    values = list(compose_review_views(selection, iter(rows)))
    changes = next(row for name, row in values if name == "changes")
    assert changes["outcome"] == "comparable"
    assert len(changes["changes"]["newly_captured"]) == 1
    assert changes["revised_state"]["judgment_counts"]["supported"] == 1
    rows[1] = ("assessment_history", evaluation(2, judgment="unsupported", error="wrong_structure"))
    changes = next(
        row for name, row in compose_review_views(selection, iter(rows)) if name == "changes"
    )
    assert changes["revised_state"]["persistent_unsupported_count"] == 1
    assert changes["revised_state"]["cases"][0]["cause"] == "unknown"
    rows[1] = ("assessment_history", evaluation(2, frame="different-grain"))
    changes = next(
        row for name, row in compose_review_views(selection, iter(rows)) if name == "changes"
    )
    assert changes["outcome"] == "incomparable"
    assert "same frozen" in changes["reason"]
    assert "revised_state" not in changes


def test_selected_grade_unavailable_is_refused_without_fallback():
    with pytest.raises(ValueError, match="absent from captured authorized history"):
        list(compose_review_views(request(selected_evaluation_ids=(22,)), iter([])))


def test_composer_settles_source_generator_on_interruption():
    settled = []

    def source():
        try:
            yield (
                "inventory",
                {
                    "selection_index": 0,
                    "population": "contribution",
                    "row": {"contribution_id": "c1"},
                },
            )
            raise RuntimeError("capture failed")
        finally:
            settled.append(True)

    with pytest.raises(RuntimeError, match="capture failed"):
        list(compose_review_views(request(), source()))
    assert settled == [True]
