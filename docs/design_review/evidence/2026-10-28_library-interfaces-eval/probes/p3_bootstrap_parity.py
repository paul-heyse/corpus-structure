"""P3: scipy.stats.bootstrap against the spike's own resampler (instruments/scores.py).

Input: the recorded S0 A-versus-B agreement table (unit x predicate x tier counts) and its
score.json, from the design-spikes evidence. Nothing is re-aligned; only the scoring step runs.

Questions:
  a. Does the spike resampler, fed the per-unit counts from agreement.tsv, reproduce the recorded
     intervals (sanity of the reconstruction)?
  b. Does scipy.stats.bootstrap(paired=True, vectorized=True, method="percentile",
     n_resamples=1000, rng=default_rng(seed)) give the same intervals bit for bit?
  c. What does scipy do when some resamples have an undefined statistic (zero denominator), as for
     a rare predicate's F1?
  d. Can one call give per-predicate intervals (vectorized over a leading axis), and a paired
     difference between two runs on the same units?
  e. Page-cluster resampling: same statistic over per-page count sums.

Run (spike venv: scipy 1.18.1, numpy 2.5.4):
    build/spike-venv/bin/python -I probes/p3_bootstrap_parity.py [recorded|sorted]
"""

from __future__ import annotations

import csv
import json
import math
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[5]
SPIKE = REPO / "docs/design_review/evidence/2026-10-28_design-spikes"
CMP = SPIKE / "results/s0/compare/a_vs_b"
N_BOOT, SEED = 1000, 20261028  # instruments/scores.py constants

sys.path.insert(0, str(SPIKE / "code"))
from instruments.scores import _prf_from, bootstrap as spike_bootstrap  # noqa: E402

rows = list(csv.DictReader((CMP / "agreement.tsv").open(), delimiter="\t"))
# Unit order matters: bootstrap indices address array positions. The recorded run used the
# sample's order (T1..T4, U5..U12); a lexicographic sort (U10 before U5) changes every interval.
UNIT_ORDER = sys.argv[1] if len(sys.argv) > 1 else "recorded"
units = (json.loads((CMP / "score.json").read_text())["units"] if UNIT_ORDER == "recorded"
         else sorted({r["unit"] for r in rows}))
preds = sorted({r["predicate"] for r in rows})
recorded = json.loads((CMP / "score.json").read_text())["tiers"]
sample = json.loads((SPIKE / "sample.json").read_text())


def counts(tier: str) -> np.ndarray:
    """(n_units, 4): n_ref, n_pred, matched_ref, matched_pred summed over predicates."""
    a = np.zeros((len(units), 4))
    for r in rows:
        if r["tier"] == tier:
            a[units.index(r["unit"])] += [int(r[k]) for k in ("n_ref", "n_pred", "matched", "matched_pred")]
    return a


def per_pred(tier: str) -> np.ndarray:
    """(n_units, n_preds, 4)."""
    a = np.zeros((len(units), len(preds), 4))
    for r in rows:
        if r["tier"] == tier:
            a[units.index(r["unit"]), preds.index(r["predicate"])] = [
                int(r[k]) for k in ("n_ref", "n_pred", "matched", "matched_pred")]
    return a


def f1_vec(nr, np_, mr, mp, axis=-1):
    """Micro F1 from summed counts along ``axis`` (vectorized; NaN when undefined)."""
    nr, np_, mr, mp = (x.sum(axis=axis) for x in (nr, np_, mr, mp))
    with np.errstate(invalid="ignore", divide="ignore"):
        p, r = mp / np_, mr / nr
        f = np.where(p + r > 0, 2 * p * r / (p + r), 0.0)
    return np.where(np.isnan(p) | np.isnan(r), np.nan, f)


out: dict = {"unit_order": UNIT_ORDER, "units": len(units), "predicates": len(preds)}
for tier in ("core", "full", "evidence"):
    a = counts(tier)
    point = _prf_from(a.sum(0))[2]
    spike = spike_bootstrap(len(a), lambda idx, a=a: _prf_from(a[idx].sum(0))[2])
    sp = stats.bootstrap(tuple(a.T), f1_vec, paired=True, vectorized=True, method="percentile",
                         n_resamples=N_BOOT, rng=np.random.default_rng(SEED))
    out[tier] = {
        "recorded": [recorded[tier]["f1"]["value"], *recorded[tier]["f1"]["ci95"]],
        "spike_recomputed": [point, *spike],
        "scipy_percentile": [point, float(sp.confidence_interval.low), float(sp.confidence_interval.high)],
        "bit_identical_spike_vs_scipy": [spike[0] == sp.confidence_interval.low, spike[1] == sp.confidence_interval.high],
    }
    if tier == "core":
        bca = stats.bootstrap(tuple(a.T), f1_vec, paired=True, vectorized=True, method="BCa",
                              n_resamples=N_BOOT, rng=np.random.default_rng(SEED))
        out[tier]["scipy_bca"] = [float(bca.confidence_interval.low), float(bca.confidence_interval.high)]

# c/d: per-predicate intervals in one call (predicates on a leading axis), NaN behaviour
pp = per_pred("core")  # (units, preds, 4)
data = tuple(np.moveaxis(pp[..., k], 0, -1) for k in range(4))  # each (preds, units)
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    res = stats.bootstrap(data, f1_vec, paired=True, vectorized=True, method="percentile",
                          n_resamples=N_BOOT, rng=np.random.default_rng(SEED), axis=-1)
    warned = sorted({type(x.message).__name__ for x in w})
lo, hi = res.confidence_interval
dist = res.bootstrap_distribution  # (preds, n_resamples)
nan_aware = np.nanpercentile(dist, [2.5, 97.5], axis=-1)
spike_pp = {p: spike_bootstrap(len(units), lambda idx, k=k: _prf_from(pp[idx, k].sum(0))[2]) for k, p in enumerate(preds)}
out["per_predicate_core"] = {
    "scipy_warnings": warned,
    "predicates_with_nan_interval_scipy": [p for k, p in enumerate(preds) if math.isnan(lo[k])],
    "predicates_with_some_undefined_resamples": [p for k, p in enumerate(preds) if np.isnan(dist[k]).any()],
    "nan_aware_from_distribution_equals_spike": all(
        (math.isnan(spike_pp[p][0]) and math.isnan(nan_aware[0, k])) or
        (spike_pp[p][0] == nan_aware[0, k] and spike_pp[p][1] == nan_aware[1, k]) for k, p in enumerate(preds)),
}

# d: paired difference between two "runs" on the same units (core vs full tier stand in for runs)
c, f = counts("core"), counts("full")
diff = stats.bootstrap((*c.T, *f.T), lambda *x, axis=-1: f1_vec(*x[:4], axis=axis) - f1_vec(*x[4:], axis=axis),
                       paired=True, vectorized=True, method="percentile", n_resamples=N_BOOT,
                       rng=np.random.default_rng(SEED))
out["paired_difference_core_minus_full"] = {
    "point": float(_prf_from(c.sum(0))[2] - _prf_from(f.sum(0))[2]),
    "ci95": [float(diff.confidence_interval.low), float(diff.confidence_interval.high)],
    "share_of_resamples_le_0": float((diff.bootstrap_distribution <= 0).mean()),
}

# e: cluster (page) bootstrap: sum counts per page, resample pages
page_of = {u: sample["units"][u]["page"] for u in units}
pages = sorted(set(page_of.values()))
pc = np.zeros((len(pages), 4))
for i, u in enumerate(units):
    pc[pages.index(page_of[u])] += c[i]
cl = stats.bootstrap(tuple(pc.T), f1_vec, paired=True, vectorized=True, method="percentile",
                     n_resamples=N_BOOT, rng=np.random.default_rng(SEED))
out["page_cluster_core"] = {"pages": len(pages),
                            "ci95": [float(cl.confidence_interval.low), float(cl.confidence_interval.high)]}

print(json.dumps(out, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x)))
