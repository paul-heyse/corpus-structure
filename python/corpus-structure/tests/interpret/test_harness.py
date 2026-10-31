"""Shapley values, Möbius dividends and the bootstrap on games with known answers (D5 §14.9)."""

from __future__ import annotations

import numpy as np
import pytest

from corpus_structure.interpret.harness import (
    MAX_GROUPS,
    GainDecomposition,
    Interval,
    cluster_bootstrap,
    interaction_index,
    mobius,
    shapley,
    subsets,
)


def glove(s: frozenset[str]) -> float:
    """One left glove `l` and two right gloves: a pair is worth 1."""
    return float("l" in s and bool(s & {"r1", "r2"}))


def test_glove_game_shapley_values() -> None:
    phi = shapley(("l", "r1", "r2"), glove)
    assert phi["l"] == pytest.approx(2 / 3)
    assert phi["r1"] == pytest.approx(1 / 6) and phi["r2"] == pytest.approx(1 / 6)


def test_mobius_dividends_reconstruct_the_game() -> None:
    groups = ("l", "r1", "r2")
    dividends = mobius(groups, glove)
    assert dividends[frozenset({"l", "r1"})] == pytest.approx(1.0)
    assert dividends[frozenset({"l", "r1", "r2"})] == pytest.approx(-1.0)
    for s in subsets(groups):
        assert sum(d for t, d in dividends.items() if t <= s) == pytest.approx(glove(s))


def test_additive_game_has_no_interactions() -> None:
    weights = {"a": 1.0, "b": 2.0, "c": -0.5}

    def additive(s: frozenset[str]) -> float:
        return sum(weights[g] for g in s)

    groups = tuple(weights)
    assert shapley(groups, additive) == pytest.approx(weights)
    assert interaction_index(groups, additive, "a", "b") == pytest.approx(0.0)
    assert all(abs(d) < 1e-12 for t, d in mobius(groups, additive).items() if len(t) > 1)


def test_pure_synergy_and_redundancy_signs() -> None:
    def both(s: frozenset[str]) -> float:
        return float({"a", "b"} <= s)

    def either(s: frozenset[str]) -> float:
        return float(bool(s & {"a", "b"}))

    assert interaction_index(("a", "b", "c"), both, "a", "b") == pytest.approx(1.0)
    assert interaction_index(("a", "b", "c"), either, "a", "b") == pytest.approx(-1.0)


def test_enumeration_is_bounded() -> None:
    with pytest.raises(ValueError, match="limited"):
        subsets([str(i) for i in range(MAX_GROUPS + 1)])


def test_gain_decomposition_telescopes() -> None:
    split = GainDecomposition(
        independent=2.0, assembly_closure=3.5, disambiguation=5.0, coverage=5.5
    )
    assert sum(split.gains.values()) == pytest.approx(split.total) == pytest.approx(3.5)


def test_cluster_bootstrap_resamples_documents() -> None:
    per_document = {f"doc{i}": float(i % 3) for i in range(30)}
    interval = cluster_bootstrap(per_document, resamples=500, seed=1)
    assert isinstance(interval, Interval)
    assert interval.estimate == pytest.approx(30.0)
    assert interval.lower < interval.estimate < interval.upper
    vectors = cluster_bootstrap(
        {"d1": np.array([1.0, 0.0]), "d2": np.array([1.0, 2.0])}, resamples=200
    )
    assert isinstance(vectors, list) and len(vectors) == 2
    assert vectors[0].lower == vectors[0].upper == 2.0  # identical documents: no spread
