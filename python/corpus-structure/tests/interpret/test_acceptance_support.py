"""Thresholds, value of information and corpus support (D5 §14.1, §14.7, §14.8)."""

from __future__ import annotations

import math

import pytest

from corpus_structure.interpret.acceptance import (
    Outcome,
    accepts,
    binary_check_outcomes,
    evi,
    expected_utility,
    plan_escalations,
    realized_utility,
)
from corpus_structure.interpret.records import RecordRegistry, RecordType
from corpus_structure.interpret.support import (
    SourceEvidence,
    clustered_support,
    corpus_support,
    effective_count,
)

CLAIM = RecordType("claim", value=1.0, cost=4.0)  # tau = 0.8


def test_threshold_is_where_expected_utility_turns_positive() -> None:
    assert CLAIM.threshold == pytest.approx(0.8)
    assert expected_utility(0.8, CLAIM) == pytest.approx(0.0)
    assert expected_utility(0.9, CLAIM) == pytest.approx(0.9 - 0.4)
    assert accepts(0.8, CLAIM) and not accepts(0.79, CLAIM)
    assert realized_utility(True, False, CLAIM) == -4.0
    assert realized_utility(False, False, CLAIM) == 0.0


def test_registry_refuses_duplicates() -> None:
    registry = RecordRegistry([CLAIM])
    with pytest.raises(ValueError):
        registry.register(CLAIM)
    with pytest.raises(KeyError):
        registry["missing"]


def test_evi_hand_calculation() -> None:
    # A perfect check on p = 0.6: accept on yes (+1), withhold on no; before, withhold (0).
    outcomes = [Outcome(0.6, 1.0), Outcome(0.4, 0.0)]
    assert evi(0.6, outcomes, CLAIM) == pytest.approx(0.6)


def test_evi_is_zero_when_no_outcome_changes_the_decision() -> None:
    # Already sure: both outcomes leave the record accepted.
    outcomes = binary_check_outcomes(0.99, sensitivity=0.6, specificity=0.6)
    assert all(o.posterior > CLAIM.threshold for o in outcomes)
    assert evi(0.99, outcomes, CLAIM) == pytest.approx(0.0, abs=1e-12)


def test_binary_outcomes_are_consistent_with_the_prior() -> None:
    outcomes = binary_check_outcomes(0.3, sensitivity=0.9, specificity=0.8)
    assert sum(o.probability for o in outcomes) == pytest.approx(1.0)
    assert sum(o.probability * o.posterior for o in outcomes) == pytest.approx(0.3)
    with pytest.raises(ValueError, match="average"):
        evi(0.5, [Outcome(0.5, 0.9), Outcome(0.5, 0.9)], CLAIM)


def test_escalations_are_chosen_by_value_per_cost() -> None:
    plan = plan_escalations(
        [
            ("d1", "llm", 0.30, 1.0),
            ("d1", "parser", 0.20, 0.2),  # better ratio for the same decision
            ("d2", "llm", 0.05, 1.0),  # not worth its cost
            ("d3", "llm", 0.50, 1.0),
        ],
        cpu_price=0.1,
    )
    assert [(e.decision, e.action) for e in plan] == [("d1", "parser"), ("d3", "llm")]


def test_effective_count() -> None:
    assert effective_count(12, 1.0) == pytest.approx(1.0)
    assert effective_count(12, 0.0) == pytest.approx(12.0)
    assert effective_count(0, 0.5) == 0.0


def test_copies_of_one_source_count_once() -> None:
    source = SourceEvidence("s", reliability=0.9, likelihood_ratio=5.0)
    single = corpus_support(0.0, [source])
    copies = corpus_support(0.0, [source] * 12, rho=1.0)
    independent = corpus_support(0.0, [source] * 12, rho=0.0)
    assert copies.log_odds == pytest.approx(single.log_odds)
    assert independent.log_odds == pytest.approx(12 * single.log_odds)
    assert single.log_odds == pytest.approx(math.log(0.9 * 5.0 + 0.1))


def test_unreliable_sources_carry_no_information() -> None:
    assert corpus_support(-1.0, [SourceEvidence("s", 0.0, 50.0)]).log_odds == pytest.approx(-1.0)


def test_clusters_are_independent_of_each_other() -> None:
    source = SourceEvidence("s", reliability=1.0, likelihood_ratio=math.e)
    # Twelve documents from one origin plus three independent ones: four sources.
    support = clustered_support(0.0, [[source] * 9, [source], [source], [source]], rho_within=1.0)
    assert support.k == 12 and support.k_eff == pytest.approx(4.0)
    assert support.log_odds == pytest.approx(4.0)
