"""Score -> log-likelihood ratio, per model, decision type and reliability grade (D5 §14.3).

Joint inference adds evidence as log-likelihood ratios, `log P(e | z) / P(e | not z)`, so each
stream's raw score is first calibrated. A calibrator is fitted on labelled decisions of one
`CalibrationKey`; the posterior it gives on that labelled set embeds the set's base rate, so the
likelihood ratio is the posterior log-odds minus the prior log-odds:

    LLR(s) = logit(P(z | s)) - logit(base_rate)

This is what lets several calibrated streams be added in one factor model without counting the
prior once per stream. Scores of kind `LLR` pass through unchanged. An observation without a
fitted calibrator yields no evidence (`None`); interpretation treats it as uncalibrated, never as
a guess.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from corpus_structure.interpret.observations import Observation, ScoreKind

_EPS = 1e-6


def logit(p: float) -> float:
    p = min(max(p, _EPS), 1.0 - _EPS)
    return math.log(p / (1.0 - p))


def sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    z = math.exp(x)
    return z / (1.0 + z)


def _feature(score: float, kind: ScoreKind) -> float:
    """The scale a calibrator is fitted on: probabilities on the logit scale, others raw."""
    return logit(score) if kind is ScoreKind.PROBABILITY else float(score)


@dataclass(frozen=True, slots=True)
class CalibrationKey:
    model: str
    decision_type: str
    reliability_grade: str = "default"

    @classmethod
    def of(cls, observation: Observation) -> CalibrationKey:
        return cls(observation.model, observation.decision_type, observation.reliability_grade)


class Calibrator(Protocol):
    @property
    def base_rate(self) -> float: ...

    def probability(self, score: float) -> float: ...

    def llr(self, score: float) -> float: ...


def _check_labelled(
    scores: Sequence[float], labels: Sequence[int]
) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=float)
    if x.shape != y.shape or x.ndim != 1:
        raise ValueError("scores and labels must be equal-length sequences")
    if not np.isin(y, (0.0, 1.0)).all():
        raise ValueError("labels must be 0 or 1")
    if y.min() == y.max():
        raise ValueError("calibration needs both positive and negative labels")
    return x, y


@dataclass(frozen=True, slots=True)
class PlattCalibrator:
    """`P(z | s) = sigmoid(a f(s) + b)`, with Platt's smoothed targets."""

    a: float
    b: float
    base_rate: float
    kind: ScoreKind

    @classmethod
    def fit(
        cls, scores: Sequence[float], labels: Sequence[int], kind: ScoreKind, *, ridge: float = 1e-3
    ) -> PlattCalibrator:
        raw, y = _check_labelled(scores, labels)
        x = np.array([_feature(float(s), kind) for s in raw])
        positives = float(y.sum())
        negatives = float(len(y) - positives)
        target = np.where(y == 1.0, (positives + 1) / (positives + 2), 1 / (negatives + 2))
        a, b = 0.0, logit((positives + 1) / (len(y) + 2))
        for _ in range(100):
            p = 1.0 / (1.0 + np.exp(-(a * x + b)))
            w = p * (1 - p)
            grad = np.array([np.dot(p - target, x) + ridge * a, float(np.sum(p - target))])
            hess = np.array(
                [[np.dot(w, x * x) + ridge, np.dot(w, x)], [np.dot(w, x), float(w.sum()) + 1e-12]]
            )
            step = np.linalg.solve(hess, grad)
            a, b = a - float(step[0]), b - float(step[1])
            if float(np.abs(step).max()) < 1e-10:
                break
        return cls(a=a, b=b, base_rate=float(y.mean()), kind=kind)

    def probability(self, score: float) -> float:
        return sigmoid(self.a * _feature(score, self.kind) + self.b)

    def llr(self, score: float) -> float:
        return self.a * _feature(score, self.kind) + self.b - logit(self.base_rate)


@dataclass(frozen=True, slots=True)
class IsotonicCalibrator:
    """A monotone step map fitted by pool-adjacent-violators, read by linear interpolation."""

    knots: tuple[float, ...]
    values: tuple[float, ...]
    base_rate: float

    @classmethod
    def fit(cls, scores: Sequence[float], labels: Sequence[int]) -> IsotonicCalibrator:
        x, y = _check_labelled(scores, labels)
        order = np.argsort(x, kind="stable")
        xs, ys = x[order], y[order]
        # Pool equal scores first, then merge adjacent blocks that violate monotonicity.
        blocks: list[list[float]] = []  # [sum_y, weight, mean_x]
        for value in np.unique(xs):
            mask = xs == value
            blocks.append([float(ys[mask].sum()), float(mask.sum()), float(value)])
        merged: list[list[float]] = []
        for block in blocks:
            merged.append(block)
            while len(merged) > 1 and merged[-2][0] / merged[-2][1] > merged[-1][0] / merged[-1][1]:
                top = merged.pop()
                below = merged[-1]
                weight = below[1] + top[1]
                below[2] = (below[2] * below[1] + top[2] * top[1]) / weight
                below[0] += top[0]
                below[1] = weight
        knots = tuple(block[2] for block in merged)
        values = tuple(block[0] / block[1] for block in merged)
        return cls(knots=knots, values=values, base_rate=float(y.mean()))

    def probability(self, score: float) -> float:
        p = float(np.interp(score, self.knots, self.values))
        return min(max(p, _EPS), 1.0 - _EPS)

    def llr(self, score: float) -> float:
        return logit(self.probability(score)) - logit(self.base_rate)


class CalibrationTable:
    """The fitted calibrators in force, and the LLR an observation contributes to an option."""

    def __init__(self, calibrators: Mapping[CalibrationKey, Calibrator] | None = None) -> None:
        self._calibrators: dict[CalibrationKey, Calibrator] = dict(calibrators or {})

    def register(self, key: CalibrationKey, calibrator: Calibrator) -> None:
        self._calibrators[key] = calibrator

    def get(self, key: CalibrationKey) -> Calibrator | None:
        return self._calibrators.get(key)

    def llr(self, observation: Observation, option: str) -> float | None:
        """The option's LLR from this observation; `None` when unscored or uncalibrated."""
        score = observation.score_of(option)
        if score is None:
            return None
        if observation.score_kind is ScoreKind.LLR:
            return score
        calibrator = self._calibrators.get(CalibrationKey.of(observation))
        return None if calibrator is None else calibrator.llr(score)


def expected_calibration_error(
    probabilities: Sequence[float], labels: Sequence[int], bins: int = 10
) -> float:
    """Equal-width-bin ECE, the D5 §6 recalibration trigger (ECE > 0.05)."""
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray(labels, dtype=float)
    if p.shape != y.shape or p.size == 0:
        raise ValueError("probabilities and labels must be non-empty and equal length")
    index = np.minimum((p * bins).astype(int), bins - 1)
    total = 0.0
    for b in range(bins):
        mask = index == b
        if mask.any():
            total += float(mask.sum()) * abs(float(p[mask].mean()) - float(y[mask].mean()))
    return total / p.size
