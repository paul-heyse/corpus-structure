"""Independent occurrence counts and group-resampling failure cases."""

from dataclasses import replace

import pytest

from corpus_structure.evaluate.record_statistics import (
    GroupContribution as Contribution,
)
from corpus_structure.evaluate.record_statistics import (
    GroupRatioProcedure as Procedure,
)
from corpus_structure.evaluate.record_statistics import (
    grouped_ratio,
    paired_group_difference,
)


@pytest.fixture
def procedure():
    return Procedure(
        population="independent statistics origin sample",
        source_cut="cut-1",
        guideline="guideline-1",
        acceptance_policy="frozen-policy-1",
        grouping_policy="original-and-related-editions-together-1",
        assumptions="origin groups sampled independently; descriptive development cohort",
        minimum_groups=3,
        seed=42,
        resamples=499,
        batch=31,
    )


def test_ratio_is_ratio_of_group_contributions_not_mean_of_group_ratios(procedure):
    rows = (
        Contribution("large", "definition", 90, 100, 110, 100),
        Contribution("small", "definition", 0, 1, 2, 1),
        Contribution("no-output", "definition", 0, 0, 8, 2),
    )
    precision = grouped_ratio(rows, family="definition", metric="precision", procedure=procedure)
    recall = grouped_ratio(rows, family="definition", metric="recall", procedure=procedure)
    capture = grouped_ratio(rows, family="definition", metric="capture_recall", procedure=procedure)
    assert precision.estimate == 90 / 101
    assert recall.estimate == 90 / 120
    assert capture.estimate == 103 / 120
    assert recall.groups == 3
    assert recall.interval_status == "computed"
    assert recall.release_gate == "unestablished"
    # Sampling only the no-output origin makes precision undefined; keep that outcome.
    assert precision.interval_status == "unestablished"
    assert "undefined denominator" in precision.reason
    assert precision.lower is None


def test_group_order_and_bootstrap_batch_do_not_change_seeded_result(procedure):
    rows = (
        Contribution("a", "measurement", 1, 2, 4, 3),
        Contribution("b", "measurement", 5, 9, 10, 8),
        Contribution("c", "measurement", 3, 3, 5, 4),
    )
    left = grouped_ratio(rows, family="measurement", metric="recall", procedure=procedure)
    right = grouped_ratio(rows[::-1], family="measurement", metric="recall", procedure=procedure)
    other_batch = grouped_ratio(
        rows, family="measurement", metric="recall", procedure=replace(procedure, batch=1)
    )
    assert left == right
    assert (left.lower, left.upper) == (other_batch.lower, other_batch.upper)
    assert left.lower is not None and left.estimate is not None and left.upper is not None
    assert left.lower <= left.estimate <= left.upper


def test_zero_errors_and_many_records_cannot_certify_lower_bound(procedure):
    rows = tuple(Contribution(str(i), "table", 1000, 1000, 1000, 1000) for i in range(5))
    result = grouped_ratio(rows, family="table", metric="precision", procedure=procedure)
    assert result.estimate == 1
    assert result.interval_status == "unestablished"
    assert result.lower is result.upper is None
    assert "degenerate" in result.reason
    assert result.release_gate == "unestablished"


def test_one_book_thousands_of_records_still_one_group(procedure):
    result = grouped_ratio(
        [Contribution("book", "assertion", 999, 1000, 2000, 1800)],
        family="assertion",
        metric="recall",
        procedure=procedure,
    )
    assert result.groups == 1
    assert result.estimate == 999 / 2000
    assert result.interval_status == "unestablished"
    assert "insufficient" in result.reason


def test_empty_population_and_empty_predictions_are_explicit(procedure):
    result = grouped_ratio([], family="formula_context", metric="precision", procedure=procedure)
    assert result.denominator == result.numerator == 0
    assert result.estimate is None
    rows = [Contribution(str(i), "formula_context", 0, 0, 10, 2) for i in range(3)]
    recall = grouped_ratio(rows, family="formula_context", metric="recall", procedure=procedure)
    assert recall.estimate == 0
    assert recall.denominator == 30
    assert recall.interval_status == "unestablished"


def test_pairing_keeps_no_output_and_shared_origin_indices(procedure):
    left = [Contribution(str(i), "definition", i, i + 2, 10, 8) for i in range(3)]
    right = [Contribution(str(i), "definition", i + 1, i + 3, 10, 8) for i in range(3)]
    difference = paired_group_difference(
        left, right, family="definition", metric="recall", procedure=procedure
    )
    # Every group improves one correct occurrence with the same ten-reference denominator.
    assert difference.estimate == pytest.approx(0.1)
    # Last-bit subtraction differences cannot manufacture a nondegenerate interval.
    assert difference.interval_status == "unestablished"
    assert difference.lower is None
    assert difference.release_gate == "unestablished"
    precision = paired_group_difference(
        left, right, family="definition", metric="precision", procedure=procedure
    )
    assert precision.estimate == pytest.approx(6 / 12 - 3 / 9)
    assert precision.interval_status == "computed"
    assert (
        precision.lower is not None
        and precision.estimate is not None
        and precision.upper is not None
    )
    assert precision.lower <= precision.estimate <= precision.upper


@pytest.mark.parametrize("change", ["group", "reference", "omit"])
def test_pairing_refuses_changed_population_or_missing_zero_group(procedure, change):
    left = [Contribution(str(i), "definition", 0, 0, 10, 0) for i in range(3)]
    right = list(left)
    if change == "group":
        right[0] = replace(right[0], group="another-book")
    elif change == "reference":
        right[0] = replace(right[0], reference=11)
    else:
        right.pop()
    with pytest.raises(ValueError, match="universe"):
        paired_group_difference(
            left, right, family="definition", metric="recall", procedure=procedure
        )


@pytest.mark.parametrize(
    "row",
    [
        Contribution("a", "unknown", 0, 0, 0, 0),
        Contribution("", "definition", 0, 0, 0, 0),
        Contribution("a", "definition", 2, 1, 3, 3),
        Contribution("a", "definition", 1, 1, 1, 0),
        Contribution("a", "definition", 0, 0, 1, 2),
        Contribution("a", "definition", -1, 0, 1, 0),
        Contribution("a", "definition", True, 1, 1, 1),
    ],
)
def test_invalid_counts_refuse(procedure, row):
    with pytest.raises(ValueError):
        grouped_ratio([row], family="definition", metric="recall", procedure=procedure)


def test_duplicate_groups_and_unknown_metrics_refuse(procedure):
    row = Contribution("a", "definition", 0, 0, 1, 0)
    with pytest.raises(ValueError, match="duplicate"):
        grouped_ratio([row, row], family="definition", metric="recall", procedure=procedure)
    with pytest.raises(ValueError, match="metric"):
        grouped_ratio([row], family="definition", metric="unknown", procedure=procedure)


@pytest.mark.parametrize(
    "change",
    [
        {"minimum_groups": 1},
        {"seed": -1},
        {"resamples": 1},
        {"batch": 0},
        {"confidence": float("nan")},
        {"confidence": 1},
        {"grouping_policy": ""},
    ],
)
def test_unfrozen_or_invalid_procedure_refuses(procedure, change):
    with pytest.raises(ValueError):
        grouped_ratio(
            [], family="table", metric="precision", procedure=replace(procedure, **change)
        )


def test_counts_that_cannot_survive_float_transport_refuse(procedure):
    row = Contribution("a", "definition", 0, 1, 2**53 + 1, 0)
    with pytest.raises(ValueError):
        grouped_ratio([row], family="definition", metric="recall", procedure=procedure)
    rows = [Contribution(str(i), "definition", 1, 2**53, 2**53, 1) for i in range(2)]
    with pytest.raises(ValueError, match="exact float64"):
        grouped_ratio(rows, family="definition", metric="precision", procedure=procedure)
