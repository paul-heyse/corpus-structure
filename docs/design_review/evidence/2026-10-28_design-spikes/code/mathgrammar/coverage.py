"""Coverage record of the math grammar (results/mathgrammar/).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/mathgrammar/coverage.py [--per-page 20]

1. Every LaTeX value in the S0 stored batches (reference, trace, stored passes): formula and set
   objects, qualifier values, condition operands (member x / set, cmp lhs / rhs), each parsed
   under its declared kind with the page's macro table. Status, detected kind, failure category;
   to_sympy outcome; and whether the tree's canonical form equals the token-level form of the
   instruments before I-R1 (values.canonical_latex at 9223fb3), i.e. whether keys move.
2. A seeded, stratified sample of math spans from the 78 first-pass pages: per page up to N
   inline and N display spans (seed 20261028), from results/s1 for the 4 spike pages and from
   s1_adapter.adapt(page) for the others; parsed under any_value.
Writes values.tsv, spans.tsv, summary.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))

import mathgrammar as M  # noqa: E402
from mathgrammar.printer import strip_delimiters  # noqa: E402

EVIDENCE = CODE.parent
S0 = EVIDENCE / "results" / "s0"
S1 = EVIDENCE / "results" / "s1"
OUT = EVIDENCE / "results" / "mathgrammar"
REPO = EVIDENCE.parents[3]
INDEX = REPO / "docs/statistics_corpus/index/siegrist_sections.tsv"
SAMPLE = json.loads((EVIDENCE / "sample.json").read_text())
REN = json.loads((S1 / "renditions.json").read_text())
SEED = 20261028


def _old_canonical():
    """values.canonical_latex as it was before I-R1 (git 9223fb3), for the key-stability check."""
    import subprocess
    import types

    src = subprocess.run(["git", "-C", str(REPO), "show",
                          "9223fb3:docs/design_review/evidence/2026-10-28_design-spikes/code/instruments/values.py"],
                         capture_output=True, text=True, check=True).stdout
    mod = types.ModuleType("values_9223fb3")
    sys.modules[mod.__name__] = mod
    exec(compile(src, "values_9223fb3", "exec"), mod.__dict__)  # noqa: S102 - our own committed source
    return mod.canonical_latex


def batch_values() -> list[tuple[str, str, str]]:
    """(unit, kind, latex) for every LaTeX value in the S0 stored batches."""
    out = set()

    def walk(o, unit):
        if isinstance(o, dict):
            if o.get("t") in ("formula", "set") and isinstance(o.get("latex"), str):
                out.add((unit, "formula" if o["t"] == "formula" else "set_expr", o["latex"]))
            if o.get("op") in ("member", "cmp", "forall"):
                for k in ("x", "lhs", "rhs", "var"):
                    if isinstance(o.get(k), str):
                        out.add((unit, "formula", o[k]))
                if isinstance(o.get("set"), str):
                    out.add((unit, "set_expr", o["set"]))
            for v in o.values():
                walk(v, unit)
        elif isinstance(o, list):
            for v in o:
                walk(v, unit)

    dirs = [S0 / "reference", S0 / "trace_stored", *(S0 / "stored").glob("pass_*")]
    for d in dirs:
        for f in sorted(d.glob("[TU]*.json")):
            b = json.loads(f.read_text())
            walk(b.get("batch", b), f.stem)
    return sorted(out)


def macros_for_unit(unit: str) -> dict:
    page = SAMPLE["units"].get(unit, {}).get("page")
    return REN.get(page, {}).get("parse_detail", {}).get("macros", {}) if page else {}


def first_pass_pages() -> list[str]:
    with INDEX.open() as f:
        return [r["path"] for r in csv.DictReader(f, delimiter="\t") if r["first_pass"] == "yes"]


def page_spans(page: str) -> tuple[list[tuple[str, str]], dict]:
    stem = page.replace("/", "__").removesuffix(".html")
    seg_f, txt_f = S1 / "segments" / f"{stem}.jsonl", S1 / "canonical" / f"{stem}.txt"
    if seg_f.exists() and txt_f.exists() and page in REN:
        text = txt_f.read_text(encoding="utf-8")
        segs = [json.loads(x) for x in seg_f.read_text().splitlines() if x.strip()]
        macros = REN[page]["parse_detail"]["macros"]
    else:
        from s1_adapter import adapt

        r = adapt(page)
        text, segs, macros = r["text"], r["segments"], r["rendition"]["parse_detail"]["macros"]
    spans = [(s["kind"], text[s["start"]:s["end"]]) for s in segs if s["kind"].startswith("math")]
    return spans, macros


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-page", type=int, default=10, help="spans per page and math kind")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    old = _old_canonical()
    from instruments.values import merged_macros

    # ---- 1. S0 values
    rows = []
    for unit, kind, latex in batch_values():
        page_macros = macros_for_unit(unit)
        mm = merged_macros(page_macros)  # as values.py passes it (D2 §12.1 fallback under the page)
        t0 = time.perf_counter()
        r = M.parse(latex, kind, macros=mm)
        dt = time.perf_counter() - t0
        try:
            M.to_sympy(r)
            sym = "ok"
        except Exception as e:  # noqa: BLE001
            sym = type(e).__name__
        can, oldc = M.canonical(r), old(latex, page_macros)
        rows.append({"unit": unit, "kind": kind, "latex": latex, "status": r.status, "detected": r.kind or "",
                     "category": (r.reason or {}).get("category", ""), "at": (r.reason or {}).get("at", ""),
                     "sympy": sym, "notes": "; ".join(r.notes), "canonical": can, "canonical_9223fb3": oldc,
                     "canonical_same": can == oldc, "ms": round(dt * 1000, 1)})
    _write("values.tsv", rows)
    vs = {
        "n": len(rows),
        "distinct_latex": len({r["latex"] for r in rows}),
        "status_by_kind": {k: dict(Counter(r["status"] for r in rows if r["kind"] == k)) for k in ("formula", "set_expr")},
        "failed_by_category": dict(Counter(r["category"] for r in rows if r["status"] == "failed")),
        "sympy": dict(Counter(r["sympy"] for r in rows if r["status"] in ("ok", "partial"))),
        "canonical_same_as_9223fb3": dict(Counter(str(r["canonical_same"]) for r in rows)),
        "canonical_differences": sorted({(r["latex"], r["canonical"], r["canonical_9223fb3"]) for r in rows if not r["canonical_same"]})[:30],
        "ms_max": max(r["ms"] for r in rows),
    }
    print("values", json.dumps({k: v for k, v in vs.items() if k != "canonical_differences"}, ensure_ascii=False))

    # ---- 2. corpus spans
    rng = random.Random(SEED)
    srows = []
    pages = first_pass_pages()
    for page in pages:
        spans, macros = page_spans(page)
        mm = merged_macros(macros)
        for mk in ("math_inline", "math_display"):
            pool = [s for k, s in spans if k == mk]
            for s in rng.sample(pool, min(a.per_page, len(pool))):
                t0 = time.perf_counter()
                r = M.parse(s, "any_value", macros=mm)
                dt = time.perf_counter() - t0
                srows.append({"page": page, "math": mk, "latex": strip_delimiters(s), "status": r.status,
                              "detected": r.kind or "", "category": (r.reason or {}).get("category", ""),
                              "at": (r.reason or {}).get("at", ""), "notes": "; ".join(r.notes), "ms": round(dt * 1000, 1)})
    _write("spans.tsv", srows)
    ss = {
        "pages": len(pages),
        "n": len(srows),
        "per_page_and_kind": a.per_page,
        "status": dict(Counter(r["status"] for r in srows)),
        "status_by_math_kind": {k: dict(Counter(r["status"] for r in srows if r["math"] == k)) for k in ("math_inline", "math_display")},
        "detected": dict(Counter(r["detected"] for r in srows if r["status"] != "failed")),
        "failed_by_category": dict(Counter(r["category"] for r in srows if r["status"] == "failed").most_common()),
        "failed_commands": Counter(r["at"].split("{")[0].split("(")[0].strip()[:14] for r in srows
                                   if r["category"] == "unknown-command").most_common(25),
        "ambiguous_notes": Counter(n.split("(")[0].strip() for r in srows if r["status"] == "ambiguous"
                                   for n in r["notes"].split("; ")).most_common(),
        "ms_median": sorted(r["ms"] for r in srows)[len(srows) // 2],
        "ms_max": max(r["ms"] for r in srows),
    }
    print("spans", json.dumps(ss, ensure_ascii=False)[:2500])
    (OUT / "summary.json").write_text(json.dumps({"seed": SEED, "values": vs, "spans": ss}, indent=1, ensure_ascii=False) + "\n")
    return 0


def _write(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", encoding="utf-8") as fh:
        fh.write("\t".join(rows[0]) + "\n")
        for r in rows:
            fh.write("\t".join(str(v).replace("\t", " ").replace("\n", " ") for v in r.values()) + "\n")


if __name__ == "__main__":
    sys.exit(main())
