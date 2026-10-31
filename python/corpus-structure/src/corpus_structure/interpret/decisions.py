"""Typed decisions and conformal candidate sizing (D5 §14.4).

A decision is one choice interpretation makes: which antecedent a reference denotes, which role
a quantity plays, which entity a mention links to. Its options always include `UNKNOWN`, so the
model can say that none of the candidates is right instead of being forced onto the least bad
one; a record built on an `UNKNOWN` decision is never accepted.

Candidate generators propose more options than inference should carry. Split-conformal
calibration sizes the set: with nonconformity `s(x, y) = 1 - p(y | x)` from a generator, and
`q` the `ceil((n + 1)(1 - alpha)) / n` empirical quantile of the true options' nonconformity on
`n` labelled decisions, the set `{y : s(x, y) <= q}` contains the true option with probability at
least `1 - alpha` on exchangeable data. That bound is what makes candidate recall an explicit,
measured budget rather than a top-k guess.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Decision:
    """One typed choice; `options` lists the candidates and always ends with `UNKNOWN`."""

    id: str
    decision_type: str
    options: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.options or self.options[-1] != UNKNOWN:
            raise ValueError(f"{self.id}: options must end with {UNKNOWN}")
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"{self.id}: options repeat")
        if self.options.count(UNKNOWN) != 1:
            raise ValueError(f"{self.id}: {UNKNOWN} appears once")

    @classmethod
    def with_unknown(cls, id: str, decision_type: str, candidates: Sequence[str]) -> Decision:
        return cls(id, decision_type, (*candidates, UNKNOWN))

    @property
    def candidates(self) -> tuple[str, ...]:
        return self.options[:-1]


@dataclass(frozen=True, slots=True)
class ConformalSizer:
    """A split-conformal threshold for one generator and decision type."""

    alpha: float
    quantile: float
    n: int

    @classmethod
    def fit(cls, true_option_probabilities: Sequence[float], alpha: float) -> ConformalSizer:
        """Fit from `p(y_true | x)` on `n` labelled calibration decisions."""
        if not 0.0 < alpha < 1.0:
            raise ValueError("alpha must lie in (0, 1)")
        scores = np.sort(1.0 - np.asarray(true_option_probabilities, dtype=float))
        n = scores.size
        if n == 0:
            raise ValueError("conformal calibration needs labelled decisions")
        rank = math.ceil((n + 1) * (1.0 - alpha))
        # Too few calibration points for this alpha: every candidate stays (q = 1).
        quantile = 1.0 if rank > n else float(scores[rank - 1])
        return cls(alpha=alpha, quantile=quantile, n=n)

    def candidate_set(self, probabilities: Mapping[str, float]) -> tuple[str, ...]:
        """The options whose nonconformity is within the threshold, most probable first."""
        kept = [(p, o) for o, p in probabilities.items() if 1.0 - p <= self.quantile]
        return tuple(o for _, o in sorted(kept, key=lambda item: (-item[0], item[1])))

    def decision(self, id: str, decision_type: str, probabilities: Mapping[str, float]) -> Decision:
        """A decision over the conformal candidate set, with `UNKNOWN` appended."""
        candidates = [o for o in self.candidate_set(probabilities) if o != UNKNOWN]
        return Decision.with_unknown(id, decision_type, candidates)
