"""The evaluation harness: what each stream group contributes, and what only groups together do
(D5 §14.9).

`V(S)` is the realized utility of the records the layer accepts when only the observations of
stream groups `S` are present (layer masking over cached observations, so no parser re-runs).
From `V` over every subset of the groups:

- the Möbius (Harsanyi) dividend `d(T) = sum_{S <= T} (-1)^{|T| - |S|} V(S)` is the value that
  appears only when every group in `T` is present; a positive pair dividend is synergy, a
  negative one redundancy, and `V(N) = sum_T d(T)`;
- the Shapley value `phi_i = sum_{S <= N - i} |S|! (n - |S| - 1)! / n! [V(S + i) - V(S)]` shares
  `V(N) - V(empty)` among the groups;
- the Shapley interaction index `I_ij` averages the pair's second difference over coalitions.

Exact enumeration is affordable for the eight-or-so groups of the plan (256 subsets);
`MAX_GROUPS` refuses more, since sampling estimates would need their own error accounting.
`V` is a sum over documents, so uncertainty comes from resampling documents (the cluster
bootstrap), never sentences, which would treat correlated decisions as independent.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

MAX_GROUPS = 12

ValueFunction = Callable[[frozenset[str]], float]


def _check(groups: Sequence[str]) -> tuple[str, ...]:
    names = tuple(groups)
    if len(set(names)) != len(names):
        raise ValueError("stream groups repeat")
    if len(names) > MAX_GROUPS:
        raise ValueError(f"exact enumeration is limited to {MAX_GROUPS} groups, got {len(names)}")
    return names


def subsets(groups: Sequence[str]) -> list[frozenset[str]]:
    names = _check(groups)
    return [frozenset(c) for r in range(len(names) + 1) for c in itertools.combinations(names, r)]


def value_table(groups: Sequence[str], value: ValueFunction) -> dict[frozenset[str], float]:
    """`V(S)` for every subset, each evaluated once."""
    return {s: float(value(s)) for s in subsets(groups)}


def _table(
    groups: Sequence[str], value: ValueFunction | Mapping[frozenset[str], float]
) -> dict[frozenset[str], float]:
    return dict(value) if isinstance(value, Mapping) else value_table(groups, value)


def mobius(
    groups: Sequence[str], value: ValueFunction | Mapping[frozenset[str], float]
) -> dict[frozenset[str], float]:
    table = _table(groups, value)
    dividends: dict[frozenset[str], float] = {}
    for t in subsets(groups):
        dividends[t] = sum(
            (-1) ** (len(t) - r) * table[frozenset(s)]
            for r in range(len(t) + 1)
            for s in itertools.combinations(sorted(t), r)
        )
    return dividends


def shapley(
    groups: Sequence[str], value: ValueFunction | Mapping[frozenset[str], float]
) -> dict[str, float]:
    names = _check(groups)
    table = _table(names, value)
    n = len(names)
    phi: dict[str, float] = {}
    for i in names:
        rest = [g for g in names if g != i]
        total = 0.0
        for r in range(len(rest) + 1):
            weight = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
            for s in itertools.combinations(rest, r):
                coalition = frozenset(s)
                total += weight * (table[coalition | {i}] - table[coalition])
        phi[i] = total
    return phi


def interaction_index(
    groups: Sequence[str],
    value: ValueFunction | Mapping[frozenset[str], float],
    i: str,
    j: str,
) -> float:
    """The Shapley interaction index of the pair `(i, j)`."""
    names = _check(groups)
    if i == j or i not in names or j not in names:
        raise ValueError("the pair must be two distinct groups")
    table = _table(names, value)
    n = len(names)
    rest = [g for g in names if g not in (i, j)]
    total = 0.0
    for r in range(len(rest) + 1):
        weight = math.factorial(r) * math.factorial(n - r - 2) / math.factorial(n - 1)
        for s in itertools.combinations(rest, r):
            c = frozenset(s)
            total += weight * (table[c | {i, j}] - table[c | {i}] - table[c | {j}] + table[c])
    return total


@dataclass(frozen=True, slots=True)
class GainDecomposition:
    """The joint layer's gain over independent reading, split by mechanism.

    Evaluated on one fixed set of observations, the configurations are nested:

    1. `independent`: each decision read alone from its unary evidence;
    2. `assembly_closure`: plus conjunctive assembly and deductive closure on those marginals;
    3. `disambiguation`: plus the cross-decision factors, over the same candidate sets;
    4. `coverage`: plus the wider candidate sets that joint inference can afford.
    """

    independent: float
    assembly_closure: float
    disambiguation: float
    coverage: float

    @property
    def gains(self) -> dict[str, float]:
        return {
            "assembly_closure": self.assembly_closure - self.independent,
            "disambiguation": self.disambiguation - self.assembly_closure,
            "coverage": self.coverage - self.disambiguation,
        }

    @property
    def total(self) -> float:
        return self.coverage - self.independent


@dataclass(frozen=True, slots=True)
class Interval:
    estimate: float
    lower: float
    upper: float


def cluster_bootstrap(
    per_document: Mapping[str, float | np.ndarray],
    *,
    resamples: int = 2000,
    level: float = 0.95,
    seed: int = 0,
) -> Interval | list[Interval]:
    """Percentile interval of a document-additive total, resampling whole documents.

    Values may be scalars or equal-length vectors (one Shapley value per group, say); a vector
    gives one interval per component.
    """
    if not per_document:
        raise ValueError("the bootstrap needs at least one document")
    rows = np.array([np.atleast_1d(np.asarray(v, dtype=float)) for v in per_document.values()])
    rng = np.random.default_rng(seed)
    n = rows.shape[0]
    draws = rng.integers(0, n, size=(resamples, n))
    totals = rows[draws].sum(axis=1)
    tail = (1.0 - level) / 2.0
    lower = np.quantile(totals, tail, axis=0)
    upper = np.quantile(totals, 1.0 - tail, axis=0)
    estimate = rows.sum(axis=0)
    intervals = [
        Interval(float(e), float(lo), float(hi))
        for e, lo, hi in zip(estimate, lower, upper, strict=True)
    ]
    scalar = all(np.ndim(v) == 0 for v in per_document.values())
    return intervals[0] if scalar else intervals
