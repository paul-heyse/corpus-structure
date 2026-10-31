"""Calibration to LLRs and conformal candidate sizing (D5 §14.3, §14.4)."""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from corpus_structure.interpret.calibration import (
    CalibrationKey,
    CalibrationTable,
    IsotonicCalibrator,
    PlattCalibrator,
    expected_calibration_error,
    logit,
)
from corpus_structure.interpret.decisions import UNKNOWN, ConformalSizer, Decision
from corpus_structure.interpret.observations import (
    Alternative,
    Observation,
    ObservationStore,
    ScoreKind,
)


def _synthetic(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Scores whose true LLR is 2 s - 1 against a prior of 0.3."""
    rng = np.random.default_rng(seed)
    scores = rng.normal(size=n)
    p = 1 / (1 + np.exp(-(2 * scores - 1 + logit(0.3))))
    return scores, (rng.random(n) < p).astype(int)


def test_platt_recovers_the_likelihood_ratio() -> None:
    scores, labels = _synthetic(20_000, seed=3)
    calibrator = PlattCalibrator.fit(scores.tolist(), labels.tolist(), ScoreKind.LOGIT)
    # LLR = posterior log-odds minus the labelled set's prior log-odds.
    implied_prior = logit(calibrator.base_rate)
    for s in (-1.0, 0.0, 1.5):
        expected = 2 * s - 1 + logit(0.3) - implied_prior
        assert calibrator.llr(s) == pytest.approx(expected, abs=0.15)


def test_isotonic_is_monotone_and_calibrated() -> None:
    scores, labels = _synthetic(5_000, seed=4)
    calibrator = IsotonicCalibrator.fit(scores.tolist(), labels.tolist())
    assert list(calibrator.values) == sorted(calibrator.values)
    held_scores, held_labels = _synthetic(5_000, seed=5)
    probabilities = [calibrator.probability(float(s)) for s in held_scores]
    assert expected_calibration_error(probabilities, held_labels.tolist()) < 0.05


def test_ece_detects_overconfidence() -> None:
    assert expected_calibration_error([0.95] * 100, [1] * 60 + [0] * 40) == pytest.approx(0.35)


def _observation(kind: ScoreKind, score: float, **extra) -> Observation:
    return Observation(
        stream="s", group="g", model="m", model_version="1", config_hash="c", input_digest="i",
        document="d", decision="dec", decision_type="t", score_kind=kind,
        alternatives=(Alternative("yes", score),), **extra,
    )  # fmt: skip


def test_calibration_table_passes_llrs_and_withholds_uncalibrated_scores() -> None:
    table = CalibrationTable()
    assert table.llr(_observation(ScoreKind.LLR, 1.25), "yes") == 1.25
    assert table.llr(_observation(ScoreKind.PROBABILITY, 0.9), "yes") is None
    assert table.llr(_observation(ScoreKind.LLR, 1.25), "no") is None
    table.register(CalibrationKey("m", "t"), PlattCalibrator(1.0, 0.0, 0.5, ScoreKind.PROBABILITY))
    assert table.llr(_observation(ScoreKind.PROBABILITY, 0.9), "yes") == pytest.approx(logit(0.9))


def test_cache_key_covers_configuration_and_store_refuses_conflicts() -> None:
    base = _observation(ScoreKind.LLR, 1.0)
    changed = _observation(ScoreKind.LLR, 1.0, reliability_grade="ocr")
    assert base.cache_key == changed.cache_key  # grade is not an input to the model output
    other_config = dataclasses.replace(base, config_hash="c2")
    assert other_config.cache_key != base.cache_key
    store = ObservationStore([base, other_config])
    assert len(store) == 2 and len(store.for_decision("dec")) == 2
    with pytest.raises(ValueError, match="different observation"):
        store.add(dataclasses.replace(base, alternatives=(Alternative("yes", 2.0),)))
    assert len(store.masked(["other"])) == 0


def test_observations_must_score_or_abstain() -> None:
    with pytest.raises(ValueError, match="an abstention has no alternatives"):
        _observation(ScoreKind.LLR, 1.0, abstained=True)
    with pytest.raises(ValueError, match="abstain explicitly"):
        dataclasses.replace(_observation(ScoreKind.LLR, 1.0), alternatives=())


def test_decisions_always_offer_unknown() -> None:
    decision = Decision.with_unknown("d", "t", ["a", "b"])
    assert decision.options[-1] == UNKNOWN and decision.candidates == ("a", "b")
    with pytest.raises(ValueError):
        Decision("d", "t", ("a", "b"))


def test_conformal_sets_reach_their_coverage() -> None:
    """Empirical coverage over many exchangeable splits is at least 1 - alpha."""
    rng = np.random.default_rng(11)
    alpha, options = 0.1, [f"o{i}" for i in range(8)]

    def draw(n: int) -> tuple[list[dict[str, float]], list[str]]:
        logits = rng.normal(size=(n, len(options)))
        truth = [options[int(np.argmax(row + rng.gumbel(size=len(options))))] for row in logits]
        probabilities = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
        return [dict(zip(options, row.tolist(), strict=True)) for row in probabilities], truth

    covered, total, sizes = 0, 0, []
    for _ in range(40):
        calibration, truth = draw(200)
        sizer = ConformalSizer.fit([p[t] for p, t in zip(calibration, truth, strict=True)], alpha)
        test, test_truth = draw(200)
        for p, t in zip(test, test_truth, strict=True):
            candidates = sizer.candidate_set(p)
            covered += t in candidates
            sizes.append(len(candidates))
            total += 1
    assert covered / total >= 1 - alpha - 0.01
    assert np.mean(sizes) < len(options)  # the sets are pruned, not everything


def test_conformal_with_too_few_points_keeps_everything() -> None:
    sizer = ConformalSizer.fit([0.9, 0.8], alpha=0.1)
    assert sizer.quantile == 1.0
    decision = sizer.decision("d", "t", {"a": 0.7, "b": 0.3, "c": 0.0})
    assert decision.options == ("a", "b", "c", UNKNOWN)
    assert math.isclose(sizer.alpha, 0.1)
