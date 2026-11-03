"""Independent occurrence counts and group-resampling failure cases."""

from dataclasses import replace
from fractions import Fraction
from itertools import combinations
from math import comb
from random import Random

import pytest

from corpus_structure.evaluate.record_statistics import (
    FinitePopulationPrecisionProcedure,
    finite_population_precision,
    grouped_ratio,
    paired_group_difference,
)
from corpus_structure.evaluate.record_statistics import (
    GroupContribution as Contribution,
)
from corpus_structure.evaluate.record_statistics import (
    GroupRatioProcedure as Procedure,
)


@pytest.fixture
def finite_procedure():
    return FinitePopulationPrecisionProcedure(
        population="held-out finite statistics cut",
        source_cut="held-out-cut-1",
        guideline="guideline-1",
        acceptance_policy="frozen-policy-1",
        frame_id="accepted-records-1",
        sample_id="assessment-srs-1",
        assumptions=(
            "Complete accepted-record frame; ordered frame, size and seed frozen before labels; "
            "SRS without replacement; conditional on adjudicated reference correctness."
        ),
        population_size=100,
        sample_size=50,
        seed=7,
        confidence=0.95,
    )


def finite_case(procedure):
    frame = tuple(f"record:{index}" for index in range(procedure.population_size))
    sample = tuple(Random(procedure.seed).sample(frame, procedure.sample_size))
    return frame, sample


def test_finite_zero_errors_has_nonperfect_exact_bound(finite_procedure):
    frame, sample = finite_case(finite_procedure)
    result = finite_population_precision(
        frame, sample, family="definition", correct=50, procedure=finite_procedure
    )
    # Independent finite combinatorics: five population errors would escape a size-50
    # sample with probability <5%; four errors would escape with probability >5%.
    assert Fraction(comb(95, 50), comb(100, 50)) < Fraction(1, 20)
    assert Fraction(comb(96, 50), comb(100, 50)) > Fraction(1, 20)
    assert result.estimate == 1
    assert result.lower_correct == 96
    assert result.lower == 0.96
    assert result.errors == 0
    assert result.interval_status == "computed"
    assert result.scope == "frozen_accepted_record_frame_only"
    assert result.release_gate == "unestablished"
    assert result.procedure == finite_procedure
    assert len(result.frame_digest) == len(result.sample_digest) == 64
    assert (
        finite_population_precision(
            frame, sample[::-1], family="definition", correct=50, procedure=finite_procedure
        )
        == result
    )


def test_finite_census_reports_exact_point_bound(finite_procedure):
    procedure = replace(finite_procedure, sample_size=100)
    frame, _ = finite_case(procedure)
    # A census needs membership, not a random ordering of every member.
    result = finite_population_precision(
        frame, frame, family="assertion", correct=97, procedure=procedure
    )
    assert result.estimate == result.lower == 0.97
    assert result.lower_correct == 97
    assert result.errors == 3
    assert result.interval_status == "census"
    assert "no sampling uncertainty" in result.reason
    assert result.release_gate == "unestablished"


def test_finite_large_population_approaches_zero_error_binomial_limit(finite_procedure):
    procedure = replace(finite_procedure, population_size=10_000, sample_size=59)
    frame, sample = finite_case(procedure)
    result = finite_population_precision(
        frame, sample, family="measurement", correct=59, procedure=procedure
    )
    binomial_lower = 0.05 ** (1 / 59)
    assert result.lower is not None
    assert binomial_lower <= result.lower < binomial_lower + 59 / 10_000
    assert result.lower >= 0.95


@pytest.mark.parametrize(("population", "size"), [(0, 0), (10, 0)])
def test_empty_finite_cases_do_not_pass_by_vacuity(finite_procedure, population, size):
    procedure = replace(finite_procedure, population_size=population, sample_size=size)
    frame, sample = finite_case(procedure)
    result = finite_population_precision(
        frame, sample, family="formula_context", correct=0, procedure=procedure
    )
    assert result.estimate is result.lower is result.lower_correct is None
    assert result.interval_status == "unestablished"
    assert "empty" in result.reason
    assert result.release_gate == "unestablished"


def test_all_incorrect_finite_sample_has_zero_lower_bound(finite_procedure):
    frame, sample = finite_case(finite_procedure)
    result = finite_population_precision(
        frame, sample, family="table", correct=0, procedure=finite_procedure
    )
    assert result.lower_correct == result.lower == result.estimate == 0
    assert result.interval_status == "computed"


def test_finite_bounds_against_all_small_population_samples(finite_procedure):
    # Enumerate actual finite populations/samples rather than asking SciPy to compute
    # the expectation. For each possible population total, noncoverage is at most 5%.
    for population in range(1, 9):
        for size in range(1, population + 1):
            procedure = replace(finite_procedure, population_size=population, sample_size=size)
            frame, sample = finite_case(procedure)
            lower = {
                correct: finite_population_precision(
                    frame, sample, family="definition", correct=correct, procedure=procedure
                ).lower_correct
                for correct in range(size + 1)
            }
            for total_correct in range(population + 1):
                rejected = 0
                samples = tuple(combinations(range(population), size))
                for selected in samples:
                    correct = sum(index < total_correct for index in selected)
                    bound = lower[correct]
                    assert bound is not None
                    rejected += bound > total_correct
                assert Fraction(rejected, len(samples)) <= Fraction(1, 20)
            bounds = tuple(value for value in lower.values() if value is not None)
            assert len(bounds) == size + 1
            assert bounds == tuple(sorted(bounds))


@pytest.mark.parametrize(
    "change",
    [
        {"population_size": -1},
        {"population_size": True},
        {"population_size": 99},
        {"sample_size": -1},
        {"sample_size": True},
        {"sample_size": 49},
        {"seed": -1},
        {"seed": True},
        {"confidence": 0},
        {"confidence": 1},
        {"confidence": float("nan")},
        {"confidence": float("inf")},
        {"confidence": True},
        {"population": ""},
        {"source_cut": ""},
        {"guideline": ""},
        {"acceptance_policy": ""},
        {"frame_id": ""},
        {"sample_id": ""},
        {"assumptions": ""},
        {"selection": "cluster_convenience_sample"},
    ],
)
def test_finite_procedure_requires_explicit_valid_design(finite_procedure, change):
    frame, sample = finite_case(finite_procedure)
    with pytest.raises(ValueError):
        finite_population_precision(
            frame,
            sample,
            family="table",
            correct=50,
            procedure=replace(finite_procedure, **change),
        )


@pytest.mark.parametrize("correct", [-1, 51, True, 1.5])
def test_finite_correct_count_is_bounded_integer(finite_procedure, correct):
    frame, sample = finite_case(finite_procedure)
    with pytest.raises(ValueError):
        finite_population_precision(
            frame, sample, family="table", correct=correct, procedure=finite_procedure
        )


@pytest.mark.parametrize(
    "change",
    [
        "frame_duplicate",
        "frame_shape",
        "sample_duplicate",
        "outside",
        "convenience",
        "frame_order",
        "family",
    ],
)
def test_finite_identities_and_actual_selection_are_checked(finite_procedure, change):
    frame, sample = finite_case(finite_procedure)
    family = "table"
    if change == "frame_duplicate":
        frame = (*frame[:-1], frame[0])
    elif change == "frame_shape":
        frame = "record-identities"
    elif change == "sample_duplicate":
        sample = (*sample[:-1], sample[0])
    elif change == "outside":
        sample = (*sample[:-1], "outside-frame")
    elif change == "convenience":
        sample = frame[:50]
    elif change == "frame_order":
        frame = frame[::-1]
    else:
        family = "unknown"
    with pytest.raises(ValueError):
        finite_population_precision(
            frame, sample, family=family, correct=50, procedure=finite_procedure
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
