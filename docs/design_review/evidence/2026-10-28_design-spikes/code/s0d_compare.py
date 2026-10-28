"""S0-C/D/E: align two folders of stored batches unit by unit (D7 §5) and write the agreement outputs.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0d_compare.py REF_DIR PRED_DIR NAME [--symmetric] [--units T1,T2]

Writes results/s0/compare/NAME/: agreement.tsv (unit x predicate x tier), score.json (tiers with
bootstrap intervals, binding/scope accuracy, unsupported, alternatives, fields, kappa, cascade,
key agreement), alignment.txt (instruments.align.describe per unit, for hand checking; fuzzy and
near-miss label pairs are listed there), and with --symmetric also the reverse direction and
the symmetrized F1 (D7 §3.3).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
from instruments.align import Side, align_unit, describe  # noqa: E402
from instruments.keys import compute_keys  # noqa: E402
from instruments.scores import agreement_rows, key_agreement, score, symmetrized, write_tsv  # noqa: E402
from instruments.values import ValueComparator  # noqa: E402

EVIDENCE = CODE.parent
S1 = EVIDENCE / "results" / "s1"
SAMPLE = json.loads((EVIDENCE / "sample.json").read_text())
RENDITIONS = json.loads((S1 / "renditions.json").read_text())
MANUAL = EVIDENCE / "results" / "s0" / "manual_equivalence.tsv"


def _name(page: str) -> str:
    return page.replace("/", "__").removesuffix(".html")


def side_for(unit: str, batch: dict) -> Side:
    meta = SAMPLE["units"][unit]
    segs = [json.loads(x) for x in (S1 / "segments" / f"{_name(meta['page'])}.jsonl").read_text().splitlines()]
    spans = {s["key"]: (s["start"], s["end"]) for s in segs}
    sents = []
    for p in meta["parts"]:
        spans[p["segment_key"]] = (p["start"], p["end"])
        for s in p["sentences"]:
            spans[s["key"]] = (s["start"], s["end"])
            sents.append((s["start"], s["end"]))
    return Side(batch, spans, sents, unit=unit)


def comparator(unit: str) -> ValueComparator:
    macros = RENDITIONS[SAMPLE["units"][unit]["page"]]["parse_detail"]["macros"]
    if MANUAL.exists():
        return ValueComparator.with_manual_tsv(MANUAL, macros=macros)
    return ValueComparator(macros=macros)


def run(ref_dir: Path, pred_dir: Path, units: list[str]):
    out, keys_r, keys_p, pending, log = [], {}, {}, [], []
    for u in units:
        r = json.loads((ref_dir / f"{u}.json").read_text())
        p = json.loads((pred_dir / f"{u}.json").read_text())
        cmp = comparator(u)
        ua = align_unit(side_for(u, r), side_for(u, p), comparator=cmp)
        out.append(ua)
        macros = RENDITIONS[SAMPLE["units"][u]["page"]]["parse_detail"]["macros"]
        keys_r[u], keys_p[u] = compute_keys(r, macros=macros), compute_keys(p, macros=macros)
        pending += [(u, x) for x in cmp.pending]
        log += [(u, e.tier, e.equal, e.a, e.b) for e in cmp.log if e.tier not in ("canonical",)]
    return out, keys_r, keys_p, pending, log


def _clean(o):
    if isinstance(o, float) and math.isnan(o):
        return None
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return o


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", type=Path)
    ap.add_argument("pred", type=Path)
    ap.add_argument("name")
    ap.add_argument("--symmetric", action="store_true")
    ap.add_argument("--units")
    a = ap.parse_args()
    units = a.units.split(",") if a.units else [u for u in SAMPLE["units"]
                                                if (a.ref / f"{u}.json").exists() and (a.pred / f"{u}.json").exists()]
    out = EVIDENCE / "results" / "s0" / "compare" / a.name
    out.mkdir(parents=True, exist_ok=True)
    ab, kr, kp, pending, log = run(a.ref, a.pred, units)
    write_tsv(agreement_rows(ab), out / "agreement.tsv")
    sc = score(ab)
    sc["keys_core"] = key_agreement(ab, kr, kp, "core")
    sc["keys_full"] = key_agreement(ab, kr, kp, "full")
    sc["units"] = units
    sc["pending_value_comparisons"] = [list(map(str, x)) for x in pending]
    sc["non_canonical_value_decisions"] = [list(map(str, x)) for x in log]
    if a.symmetric:
        ba, *_ = run(a.pred, a.ref, units)
        sc["symmetrized"] = symmetrized(ab, ba)
    (out / "score.json").write_text(json.dumps(_clean(sc), indent=1, ensure_ascii=False, default=str) + "\n")
    (out / "alignment.txt").write_text("\n".join(describe(ua) for ua in ab) + "\n")
    t = sc["tiers"]
    print(a.name, "units", len(units), "|", "  ".join(
        f"{k}: P {t[k]['precision']['value']:.2f} R {t[k]['recall']['value']:.2f} F1 {t[k]['f1']['value']:.2f}"
        for k in ("core", "full", "evidence")), "| pending", len(pending))
    return 0


if __name__ == "__main__":
    sys.exit(main())
