"""Scores and agreement outputs (D7 §5.4, §3.3; instruments §5.3, §6).

All intervals: 95% percentile intervals from ``N_BOOT`` = 1,000 bootstrap resamples over units
(fixed seed), reported with n = number of units. Resamples whose denominator is zero are
skipped (NaN-aware percentiles).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np

from .align import TIERS, UnitAlignment
from .keys import BatchKeys, mismatch_causes

N_BOOT = 1000
BOOT_SEED = 20261028


def _bare(p: str) -> str:
    return p.split(":", 1)[1] if ":" in p else p


@dataclass
class UnitCounts:
    unit: str
    by_pred: dict  # (predicate, tier) -> [n_ref, n_pred, matched_ref, matched_pred]


def _items(claims: dict[str, dict], groups: list[list[str]]) -> list[tuple[str, set[str]]]:
    """Scoring items of one side: each alternatives group is one item (D7 §5.3; overlapping
    groups are merged), every other claim is its own item. Item predicate: that of the group's
    first listed reading."""
    parent = {r: r for r in claims}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first: dict[str, str] = {}
    for g in groups:
        g = [r for r in g if r in claims]
        for r in g[1:]:
            ra, rb = find(g[0]), find(r)
            if ra != rb:
                parent[rb] = ra
        if g:
            first.setdefault(find(g[0]), g[0])
    members: dict[str, set[str]] = defaultdict(set)
    for r in claims:
        members[find(r)].add(r)
    out = []
    for root, ms in members.items():
        head = first.get(root, root) if len(ms) > 1 else next(iter(ms))
        out.append((_bare(claims[head]["predicate"]), ms))
    return out


def unit_counts(ua: UnitAlignment, tiers: Iterable[str] = TIERS) -> UnitCounts:
    """Counts by predicate and tier. An alternatives group counts once on its side and is
    matched when any of its readings is matched at the tier; its other readings are neither
    misses nor extra matches (D7 §5.3, symmetric for prediction groups). Without groups,
    matched_ref == matched_pred == the number of matched pairs."""
    out: dict = defaultdict(lambda: [0, 0, 0, 0])
    ref_items = _items(ua.ref_claims, [g for g, _ in ua.alternatives_ref])
    pred_items = _items(ua.pred_claims, [g for g, _ in ua.alternatives_pred])
    preds = {p for p, _ in ref_items} | {p for p, _ in pred_items}
    for t in tiers:
        mr = {a for a, _ in ua.matches.get(t, [])}
        mp = {b for _, b in ua.matches.get(t, [])}
        for p in preds:
            out[(p, t)]
        for p, ms in ref_items:
            out[(p, t)][0] += 1
            out[(p, t)][2] += bool(ms & mr)
        for p, ms in pred_items:
            out[(p, t)][1] += 1
            out[(p, t)][3] += bool(ms & mp)
    return UnitCounts(ua.unit, dict(out))


def agreement_rows(alignments: Iterable[UnitAlignment], tiers: Iterable[str] = TIERS) -> list[dict]:
    """Rows of ``agreement.tsv``: unit x predicate x tier (items: an alternatives group is one)."""
    rows = []
    for ua in alignments:
        for (p, t), (nr, np_, mr, mp) in sorted(unit_counts(ua, tiers).by_pred.items()):
            rows.append({"unit": ua.unit, "predicate": p, "tier": t, "n_ref": nr, "n_pred": np_,
                         "matched": mr, "matched_pred": mp, "ref_only": nr - mr, "pred_only": np_ - mp})
    return rows


def write_tsv(rows: list[dict], path) -> None:
    from pathlib import Path

    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    cols = list(rows[0])
    lines = ["\t".join(cols)] + ["\t".join(str(r[c]) for c in cols) for r in rows]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ratio(num, den):
    return num / den if den else float("nan")


def bootstrap(n_units: int, stat: Callable[[np.ndarray], float], n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> tuple[float, float]:
    if n_units == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    vals = np.array([stat(rng.integers(0, n_units, n_units)) for _ in range(n_boot)], dtype=float)
    if np.all(np.isnan(vals)):
        return (float("nan"), float("nan"))
    return (float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5)))


def _est(values: np.ndarray, fn) -> dict:
    """values: per-unit array of components; fn(idx) -> statistic over the units idx."""
    n = values.shape[0]
    point = fn(np.arange(n))
    lo, hi = bootstrap(n, fn)
    return {"value": point, "ci95": [lo, hi], "n_units": n}


def _prf_from(s) -> tuple[float, float, float]:
    """(precision, recall, F1) from summed [n_ref, n_pred, matched_ref, matched_pred]."""
    p, r = _ratio(s[3], s[1]), _ratio(s[2], s[0])
    if math.isnan(p) or math.isnan(r):
        return p, r, float("nan")
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


_KEYS = ("n_ref", "n_pred", "matched_ref", "matched_pred")


def _totals(a) -> dict:
    d = dict(zip(_KEYS, map(int, a)))
    d["matched"] = d["matched_ref"]
    return d


def prf(alignments: list[UnitAlignment], tiers: Iterable[str] = TIERS) -> dict:
    """Precision, recall, F1 per tier: micro, macro over predicates, per predicate.

    ``tiers`` may add ``full_nocascade`` / ``evidence_nocascade`` (see ``align``)."""
    tiers = tuple(tiers)
    counts = [unit_counts(ua, tiers) for ua in alignments]
    preds = sorted({p for uc in counts for (p, _) in uc.by_pred})
    out: dict = {}
    for t in tiers:
        arr = np.array([[sum(v[k] for (p, tt), v in uc.by_pred.items() if tt == t) for k in range(4)] for uc in counts], dtype=float).reshape(-1, 4)
        per = np.array([[[uc.by_pred.get((p, t), [0, 0, 0, 0])[k] for k in range(4)] for p in preds] for uc in counts], dtype=float).reshape(len(counts), len(preds), 4)

        def stat(i, a=arr):
            return lambda idx: _prf_from(a[idx].sum(0))[i]

        def macro(idx, a=per):
            s = a[idx].sum(0)
            f = [_prf_from(x)[2] for x in s if x[0] + x[1] > 0]
            f = [x for x in f if not math.isnan(x)] or ([0.0] * len(f))
            return float(np.mean(f)) if f else float("nan")

        tier = {"precision": _est(arr, stat(0)), "recall": _est(arr, stat(1)), "f1": _est(arr, stat(2)),
                "macro_f1": _est(per, macro), "totals": _totals(arr.sum(0))}
        tier["per_predicate"] = {}
        for k, p in enumerate(preds):
            sub = per[:, k, :]
            tier["per_predicate"][p] = {"totals": _totals(sub.sum(0)),
                                        "f1": _est(sub, lambda idx, a=sub: _prf_from(a[idx].sum(0))[2])}
        out[t] = tier
    return out


def cascade_summary(alignments: list[UnitAlignment]) -> dict:
    """Core-matched pairs failing the full tier only because a cited premise failed core."""
    return {"cascaded": sum(len(ua.cascaded) for ua in alignments),
            "by_unit": {ua.unit: ua.cascaded for ua in alignments if ua.cascaded}}


def _share(per_unit: list[tuple[int, int]]) -> dict:
    arr = np.array(per_unit, dtype=float).reshape(-1, 2)
    return _est(arr, lambda idx: _ratio(arr[idx, 0].sum(), arr[idx, 1].sum())) | {"totals": [int(arr[:, 0].sum()), int(arr[:, 1].sum())]}


def unsupported_recall(alignments: list[UnitAlignment]) -> dict:
    return _share([(len(ua.unsupported_pairs), ua.unsupported_n[0]) for ua in alignments])


def binding_accuracy(alignments: list[UnitAlignment]) -> dict:
    """Over symbols of formula values in core-aligned claims: kind and target equal (D7 §5.4)."""
    res = _share([(sum(b["correct"] for b in ua.bindings), len(ua.bindings)) for ua in alignments])
    kinds: dict = defaultdict(lambda: [0, 0])
    for ua in alignments:
        for b in ua.bindings:
            kinds[b["ref_bind"]][0] += b["correct"]
            kinds[b["ref_bind"]][1] += 1
    res["by_kind"] = {k: v for k, v in sorted(kinds.items())}
    return res


def scope_accuracy(alignments: list[UnitAlignment]) -> dict:
    return _share([(sum(s["correct"] for s in ua.scopes), len(ua.scopes)) for ua in alignments])


def alternatives_summary(alignments: list[UnitAlignment]) -> dict:
    out: dict = defaultdict(int)
    for ua in alignments:
        for _, o in ua.alternatives_ref:
            out[f"ref_{o}"] += 1
        for _, o in ua.alternatives_pred:
            out[f"pred_{o}"] += 1
    return dict(out)


def field_breakdown(alignments: list[UnitAlignment]) -> dict:
    """Full-tier failures among core-matched pairs, by field; plus bindings/extent diagnostics."""
    out: dict = defaultdict(int)
    n = 0
    for ua in alignments:
        for e, f in ua.field_failures.items():
            n += 1
            for x in f:
                out[x] += 1
            for x in ua.diagnostics.get(e, []):
                out[f"diag:{x}"] += 1
    return {"core_matched": n, "failures": dict(sorted(out.items())),
            "cascaded": sum(len(ua.cascaded) for ua in alignments)}


def kappas(alignments: list[UnitAlignment]) -> dict:
    """Cohen's kappa on core-aligned claims for categorical fields (statsmodels)."""
    from statsmodels.stats.inter_rater import cohens_kappa

    fields = {
        "modality": lambda c: (c.get("qualifiers") or {}).get("modality", "asserted"),
        "polarity": lambda c: (c.get("qualifiers") or {}).get("polarity", "positive"),
        "statement_role": lambda c: c.get("statement_role") or "none",
    }
    out = {}
    for name, get in fields.items():
        pairs = [(get(ua.ref_claims[a]), get(ua.pred_claims[b])) for ua in alignments for a, b in ua.matches.get("core", [])]
        cats = sorted({x for p in pairs for x in p})
        if not pairs:
            out[name] = {"kappa": None, "n": 0}
            continue
        tab = np.zeros((len(cats), len(cats)))
        for x, y in pairs:
            tab[cats.index(x), cats.index(y)] += 1
        if len(cats) < 2:
            out[name] = {"kappa": None, "n": len(pairs), "note": f"single category {cats[0]!r}; kappa undefined"}
            continue
        k = cohens_kappa(tab, return_results=True)
        out[name] = {"kappa": float(k.kappa), "n": len(pairs), "categories": cats}
    return out


def key_agreement(alignments: list[UnitAlignment], keys_ref: dict[str, BatchKeys], keys_pred: dict[str, BatchKeys], tier: str = "core") -> dict:
    """For pairs aligned at ``tier``: shares whose claim / meaning keys coincide, and causes."""
    out = {"pairs": 0, "claim_key_equal": 0, "meaning_key_equal": 0, "claim_causes": defaultdict(int), "meaning_causes": defaultdict(int), "examples": []}
    for ua in alignments:
        ka, kb = keys_ref[ua.unit], keys_pred[ua.unit]
        for a, b in ua.matches.get(tier, []):
            out["pairs"] += 1
            if ka.claim.get(a) is not None and ka.claim.get(a) == kb.claim.get(b):
                out["claim_key_equal"] += 1
            else:
                cs = mismatch_causes(ka, a, kb, b)
                for c in cs:
                    out["claim_causes"][c] += 1
                if len(out["examples"]) < 20:
                    out["examples"].append((ua.unit, a, b, cs))
            if ka.meaning.get(a) is not None and ka.meaning.get(a) == kb.meaning.get(b):
                out["meaning_key_equal"] += 1
            else:
                for c in mismatch_causes(ka, a, kb, b, meaning=True):
                    out["meaning_causes"][c] += 1
    out["claim_causes"] = dict(out["claim_causes"])
    out["meaning_causes"] = dict(out["meaning_causes"])
    return out


def symmetrized(ab: list[UnitAlignment], ba: list[UnitAlignment]) -> dict:
    """D7 §3.3: A as reference and B as prediction, then symmetrized: per tier, the mean of the
    two directions' F1 (equal by construction when matching is symmetric; a difference is reported)."""
    fa, fb = prf(ab), prf(ba)
    out = {}
    for t in TIERS:
        x, y = fa[t]["f1"]["value"], fb[t]["f1"]["value"]
        out[t] = {"agreement": (x + y) / 2 if not (math.isnan(x) or math.isnan(y)) else float("nan"),
                  "a_ref": fa[t]["f1"], "b_ref": fb[t]["f1"], "asymmetric": not math.isclose(x, y, abs_tol=1e-12) if not (math.isnan(x) or math.isnan(y)) else False}
    return out


def score(alignments: list[UnitAlignment]) -> dict:
    return {
        "tiers": prf(alignments),
        "unsupported_recall": unsupported_recall(alignments),
        "binding_accuracy": binding_accuracy(alignments),
        "scope_accuracy": scope_accuracy(alignments),
        "alternatives": alternatives_summary(alignments),
        "field_breakdown": field_breakdown(alignments),
        "kappa": kappas(alignments),
        "cascade": cascade_summary(alignments),
        "nocascade_tiers": prf(alignments, ("full_nocascade", "evidence_nocascade")),
    }
