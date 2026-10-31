"""Exact inference against brute-force enumeration (D5 §14.5)."""

from __future__ import annotations

import itertools
import math

import numpy as np
import pytest

from corpus_structure.interpret.factors import FactorBudgetExceeded, FactorGraph, Infeasible


def _brute(domains: dict[str, tuple[str, ...]], score) -> dict[tuple[str, ...], float]:
    names = list(domains)
    weights = {}
    for values in itertools.product(*(domains[n] for n in names)):
        weights[values] = math.exp(score(dict(zip(names, values, strict=True))))
    total = sum(weights.values())
    return {k: w / total for k, w in weights.items()}


def test_unary_factors_alone_give_independent_softmax() -> None:
    graph = FactorGraph()
    graph.add_variable("a", ("x", "y", "z"))
    graph.add_unary("e", "a", {"x": 1.0, "y": 0.5})
    marginal = graph.infer().marginal("a")
    expected = np.exp([1.0, 0.5, 0.0]) / np.exp([1.0, 0.5, 0.0]).sum()
    assert [marginal[o] for o in ("x", "y", "z")] == pytest.approx(expected.tolist())


def test_pairwise_marginals_and_map_match_enumeration() -> None:
    rng = np.random.default_rng(7)
    domains: dict[str, tuple[str, ...]] = {
        "a": ("a0", "a1", "a2"),
        "b": ("b0", "b1"),
        "c": ("c0", "c1", "c2", "c3"),
    }
    ab = rng.normal(size=(3, 2))
    cb = rng.normal(size=(4, 2))  # scope (c, b): axes not in declaration order
    ua = rng.normal(size=3)
    graph = FactorGraph()
    for name, domain in domains.items():
        graph.add_variable(name, domain)
    graph.add_unary("ua", "a", dict(zip(domains["a"], ua.tolist(), strict=True)))
    graph.add_function(
        "ab", ("a", "b"), lambda s: ab[domains["a"].index(s["a"]), domains["b"].index(s["b"])]
    )
    graph.add_function(
        "cb", ("c", "b"), lambda s: cb[domains["c"].index(s["c"]), domains["b"].index(s["b"])]
    )
    posterior = graph.infer()

    def score(s: dict[str, str]) -> float:
        i, j, k = (domains[n].index(s[n]) for n in ("a", "b", "c"))
        return ua[i] + ab[i, j] + cb[k, j]

    joint = _brute(domains, score)
    for position, name in enumerate(("a", "b", "c")):
        marginal = posterior.marginal(name)
        for option in domains[name]:
            expected = sum(p for k, p in joint.items() if k[position] == option)
            assert marginal[option] == pytest.approx(expected)
    best = max(joint, key=lambda k: joint[k])
    assert posterior.map_assignment() == dict(zip(("a", "b", "c"), best, strict=True))
    event = posterior.probability(lambda s: s["a"] == "a1" or s["c"] == "c3", ("a", "c"))
    assert event == pytest.approx(sum(p for k, p in joint.items() if k[0] == "a1" or k[2] == "c3"))


def test_events_across_independent_components() -> None:
    graph = FactorGraph()
    graph.add_variable("a", ("t", "f"))
    graph.add_variable("b", ("t", "f"))
    graph.add_unary("ua", "a", {"t": math.log(3.0)})  # P(a = t) = 0.75
    posterior = graph.infer()
    assert len(graph.components()) == 2
    both = posterior.probability(lambda s: s["a"] == "t" and s["b"] == "t", ("a", "b"))
    assert both == pytest.approx(0.75 * 0.5)


def test_hard_constraints_zero_excluded_states() -> None:
    graph = FactorGraph()
    graph.add_variable("a", ("x", "y"))
    graph.add_variable("b", ("x", "y"))
    graph.add_constraint("differ", ("a", "b"), lambda s: s["a"] != s["b"])
    graph.add_unary("ua", "a", {"x": 2.0})
    posterior = graph.infer()
    assert posterior.marginal("b")["x"] == pytest.approx(1.0 - posterior.marginal("a")["x"])


def test_infeasible_constraints_are_refused() -> None:
    graph = FactorGraph()
    graph.add_variable("a", ("x", "y"))
    graph.add_constraint("never", ("a",), lambda s: False)
    with pytest.raises(Infeasible):
        graph.infer()


def test_budget_refuses_large_components() -> None:
    graph = FactorGraph()
    for name in "abc":
        graph.add_variable(name, tuple(str(i) for i in range(10)))
    graph.add_function("ab", ("a", "b"), lambda s: 0.0)
    graph.add_function("bc", ("b", "c"), lambda s: 0.0)
    with pytest.raises(FactorBudgetExceeded):
        graph.infer(budget=999)
    assert graph.infer(budget=1000).marginal("a")["0"] == pytest.approx(0.1)


def test_factor_shape_and_values_are_checked() -> None:
    graph = FactorGraph()
    graph.add_variable("a", ("x", "y"))
    with pytest.raises(ValueError, match="finite or -inf"):
        graph.add_unary("bad", "a", {"x": math.nan})
    with pytest.raises(KeyError):
        graph.add_unary("bad", "a", {"z": 1.0})
