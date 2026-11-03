"""Source-origin grouped ratio resampling; no release or calibration authority.

Contributions must come from a frozen independent evaluation population. The caller
supplies credible origin groups and an explicitly selected procedure. Resampling groups
cannot establish their independence, population representativeness, or sample adequacy.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.stats import bootstrap

from .record_alignment import FAMILIES


@dataclass(frozen=True)
class GroupContribution:
    group: str
    family: str
    correct: int
    accepted: int
    reference: int
    captured: int


@dataclass(frozen=True)
class GroupRatioProcedure:
    population: str
    source_cut: str
    guideline: str
    acceptance_policy: str
    grouping_policy: str
    assumptions: str
    minimum_groups: int
    seed: int
    resamples: int = 9_999
    batch: int = 256
    confidence: float = 0.95


@dataclass(frozen=True)
class GroupRatioEstimate:
    family: str
    metric: str
    groups: int
    numerator: int
    denominator: int
    estimate: float | None
    lower: float | None
    upper: float | None
    interval_status: Literal["computed", "unestablished"]
    reason: str
    procedure: GroupRatioProcedure
    method: str = "source-group-paired-ratio-percentile-1"
    release_gate: Literal["unestablished"] = "unestablished"


@dataclass(frozen=True)
class PairedGroupDifference:
    family: str
    metric: str
    groups: int
    estimate: float | None
    lower: float | None
    upper: float | None
    interval_status: Literal["computed", "unestablished"]
    reason: str
    procedure: GroupRatioProcedure
    method: str = "source-group-paired-ratio-difference-percentile-1"
    release_gate: Literal["unestablished"] = "unestablished"


def _validate(procedure: GroupRatioProcedure) -> None:
    if any(
        not isinstance(value, str) or not value.strip()
        for value in (
            procedure.population,
            procedure.source_cut,
            procedure.guideline,
            procedure.acceptance_policy,
            procedure.grouping_policy,
            procedure.assumptions,
        )
    ):
        raise ValueError("group resampling requires explicit frozen population and assumptions")
    for value, minimum in (
        (procedure.minimum_groups, 2),
        (procedure.seed, 0),
        (procedure.resamples, 2),
        (procedure.batch, 1),
    ):
        if type(value) is not int or value < minimum:
            raise ValueError("invalid group-resampling count or seed")
    if not math.isfinite(procedure.confidence) or not 0 < procedure.confidence < 1:
        raise ValueError("confidence must be finite and strictly between zero and one")


def _groups(rows: Sequence[GroupContribution]) -> dict[tuple[str, str], GroupContribution]:
    result = {}
    for row in rows:
        if not isinstance(row.group, str) or not row.group.strip() or row.family not in FAMILIES:
            raise ValueError("unknown family or empty independent origin group")
        if any(
            type(value) is not int or not 0 <= value <= 2**53
            for value in (row.correct, row.accepted, row.reference, row.captured)
        ):
            raise ValueError("contributions require nonnegative integer occurrence counts")
        if row.correct > min(row.accepted, row.reference) or not (
            row.correct <= row.captured <= row.reference
        ):
            raise ValueError("contribution counts violate occurrence/capture denominators")
        key = row.group, row.family
        if key in result:
            raise ValueError("duplicate origin/family contribution; aggregate within groups first")
        result[key] = row
    return result


def _counts(rows, metric):
    match metric:
        case "precision":
            return tuple(row.correct for row in rows), tuple(row.accepted for row in rows)
        case "recall":
            return tuple(row.correct for row in rows), tuple(row.reference for row in rows)
        case "capture_recall":
            return tuple(row.captured for row in rows), tuple(row.reference for row in rows)
        case _:
            raise ValueError("unsupported record ratio metric")


def _ratio(numerator, denominator, *, axis=-1):
    n = np.sum(numerator, axis=axis, dtype=np.float64)
    d = np.sum(denominator, axis=axis, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(d > 0, n / d, np.nan)


def _bootstrap(data, statistic, procedure):
    return bootstrap(
        data,
        statistic,
        paired=True,
        vectorized=True,
        axis=-1,
        method="percentile",
        alternative="two-sided",
        confidence_level=procedure.confidence,
        n_resamples=procedure.resamples,
        batch=procedure.batch,
        rng=np.random.default_rng(procedure.seed),
    )


def _interval(result):
    distribution = result.bootstrap_distribution
    if not np.all(np.isfinite(distribution)):
        return None, None, "unestablished", "a resampled group set has undefined denominator"
    if np.ptp(distribution) <= 64 * np.finfo(np.float64).eps * max(
        1.0, float(np.max(np.abs(distribution)))
    ):
        return None, None, "unestablished", "degenerate group bootstrap cannot certify an interval"
    low, high = float(result.confidence_interval.low), float(result.confidence_interval.high)
    if not math.isfinite(low) or not math.isfinite(high):
        return None, None, "unestablished", "nonfinite group interval"
    return low, high, "computed", "descriptive interval conditional on supplied group assumptions"


def grouped_ratio(
    contributions: Sequence[GroupContribution],
    *,
    family: str,
    metric: str,
    procedure: GroupRatioProcedure,
) -> GroupRatioEstimate:
    """Resample actual origin groups, then recompute the aggregate ratio of counts.

    A group with no predictions is retained. Undefined resamples are not discarded.
    A computed descriptive interval never establishes the M1 release precision bound.
    """
    _validate(procedure)
    if family not in FAMILIES:
        raise ValueError("unsupported record family")
    groups = _groups(contributions)
    rows = tuple(row for (_, fam), row in sorted(groups.items()) if fam == family)
    numerators, denominators = _counts(rows, metric)
    numerator, denominator = sum(numerators), sum(denominators)
    if max(numerator, denominator) > 2**53:
        raise ValueError("aggregate counts exceed exact float64 integer support")
    estimate = numerator / denominator if denominator else None
    low, high, status, reason = None, None, "unestablished", "insufficient origin groups"
    if denominator == 0:
        reason = "no denominator for this population/family/metric"
    elif len(rows) >= procedure.minimum_groups:
        low, high, status, reason = _interval(
            _bootstrap(
                (
                    np.asarray(numerators, dtype=np.float64),
                    np.asarray(denominators, dtype=np.float64),
                ),
                _ratio,
                procedure,
            )
        )
    return GroupRatioEstimate(
        family,
        metric,
        len(rows),
        numerator,
        denominator,
        estimate,
        low,
        high,
        status,
        reason,
        procedure,
    )


def paired_group_difference(
    baseline: Sequence[GroupContribution],
    challenger: Sequence[GroupContribution],
    *,
    family: str,
    metric: str,
    procedure: GroupRatioProcedure,
) -> PairedGroupDifference:
    """Challenger minus baseline, with identical group indices in every resample.

    Both sides must contain the same origin/family universe and reference denominator.
    Empty outputs are explicit zero contributions, never dropped to make pairing work.
    """
    _validate(procedure)
    if family not in FAMILIES:
        raise ValueError("unsupported record family")
    left, right = _groups(baseline), _groups(challenger)
    if left.keys() != right.keys() or any(
        left[key].reference != right[key].reference for key in left
    ):
        raise ValueError("paired comparison requires the same complete group/reference universe")
    keys = tuple(key for key in sorted(left) if key[1] == family)
    ln, ld = _counts(tuple(left[key] for key in keys), metric)
    rn, rd = _counts(tuple(right[key] for key in keys), metric)
    if max(sum(ln), sum(ld), sum(rn), sum(rd)) > 2**53:
        raise ValueError("aggregate counts exceed exact float64 integer support")
    estimate = sum(rn) / sum(rd) - sum(ln) / sum(ld) if sum(ld) and sum(rd) else None
    low, high, status, reason = None, None, "unestablished", "insufficient origin groups"
    if estimate is None:
        reason = "undefined baseline or challenger denominator"
    elif len(keys) >= procedure.minimum_groups:

        def difference(a, b, c, d, *, axis=-1):
            return _ratio(c, d, axis=axis) - _ratio(a, b, axis=axis)

        low, high, status, reason = _interval(
            _bootstrap(
                tuple(np.asarray(values, dtype=np.float64) for values in (ln, ld, rn, rd)),
                difference,
                procedure,
            )
        )
    return PairedGroupDifference(
        family, metric, len(keys), estimate, low, high, status, reason, procedure
    )
