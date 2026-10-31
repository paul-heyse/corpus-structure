"""Lineage polynomials: semiring evaluations, exact probability and bounds (D5 §14.6)."""

from __future__ import annotations

import itertools

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from corpus_structure.interpret.lineage import (
    COUNTING,
    VITERBI,
    WHY,
    Lineage,
    frechet_and,
    frechet_or,
    why_valuation,
)

x, y, z = Lineage.var("x"), Lineage.var("y"), Lineage.var("z")


def test_join_and_alternative_build_the_expected_polynomial() -> None:
    # Two derivations: x joined with y, or x joined with z.
    lineage = x * y + x * z
    assert lineage.terms == {("x", "y"): 1, ("x", "z"): 1}
    assert lineage == x * (y + z)  # distributivity


def test_semiring_evaluations() -> None:
    lineage = x * y + x * z + x * y
    assert lineage.evaluate(COUNTING, {"x": 1, "y": 1, "z": 1}) == 3
    assert lineage.evaluate(VITERBI, {"x": 0.9, "y": 0.5, "z": 0.8}) == pytest.approx(0.72)
    witnesses = (x * y + x * z + x).evaluate(WHY, why_valuation("xyz"))
    assert witnesses == frozenset({frozenset({"x"})})  # x alone suffices; supersets drop


def test_withdrawal_zeroes_a_record_only_when_no_derivation_survives() -> None:
    lineage = x * y + z
    assert not lineage.restrict("z", False).is_zero()
    assert lineage.restrict("z", False).restrict("y", False).is_zero()
    assert lineage.holds({"x", "y"}) and not lineage.holds({"x"})


NAMES: tuple[str, ...] = ("a", "b", "c", "d")
MONOMIALS = st.lists(
    st.lists(st.sampled_from("abcd"), min_size=1, max_size=3), min_size=1, max_size=4
)


@settings(max_examples=60, deadline=None)
@given(MONOMIALS, st.lists(st.floats(0.0, 1.0), min_size=4, max_size=4))
def test_probability_matches_enumeration(monomials: list[list[str]], ps: list[float]) -> None:
    lineage = Lineage({tuple(m): 1 for m in monomials})
    marginals: dict[str, float] = dict(zip(NAMES, ps, strict=True))
    expected = 0.0
    for values in itertools.product((False, True), repeat=4):
        world: dict[str, bool] = dict(zip(NAMES, values, strict=True))
        weight = np.prod([marginals[v] if world[v] else 1 - marginals[v] for v in NAMES])
        if any(all(world[v] for v in m) for m in monomials):
            expected += float(weight)
    assert lineage.probability(marginals) == pytest.approx(expected, abs=1e-12)


@settings(max_examples=60, deadline=None)
@given(st.lists(st.floats(0.0, 1.0), min_size=8, max_size=8))
def test_frechet_bounds_contain_every_joint(weights: list[float]) -> None:
    total = sum(weights)
    if total == 0:
        return
    joint = np.array(weights).reshape(2, 2, 2) / total  # any joint of three Boolean inputs
    marginals = [float(joint.sum(axis=tuple(j for j in range(3) if j != i))[1]) for i in range(3)]
    p_and = float(joint[1, 1, 1])
    p_or = 1.0 - float(joint[0, 0, 0])
    lower, upper = frechet_and(marginals)
    assert lower - 1e-12 <= p_and <= upper + 1e-12
    lower, upper = frechet_or(marginals)
    assert lower - 1e-12 <= p_or <= upper + 1e-12


def test_negative_coefficients_are_refused() -> None:
    with pytest.raises(ValueError):
        Lineage({("x",): -1})
