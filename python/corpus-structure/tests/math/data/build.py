"""Write the thin spike fixtures of `tests/math` once, from the frozen spike results (stdlib only;
run from the repository root: `python3 python/corpus-structure/tests/math/data/build.py`).

- `s0_scopes.json`: the 20 annotated symbol scopes of the S0 reference (local entities with a
  symbol that is not an expression), with the unit's parts, the annotated extent and the spike
  probe's reading without the paragraph rule (`results/s0/m13_probe.reference.patterns.h3h4.tsv`,
  record `s0.m13-probe-2`; units and parts from `sample.json`).
- `s0r2_contexts.json`: the 21 S0-R2 units with their parts and standing contexts (`id`, offsets
  and text), from `results/s0r2/sample.json` (records `s0r2.inputs`, `s0r2.scores`); texts from
  the frozen renditions (`results/s1`, `results/s0r2/s1`).
- `s5_coverage.json`: per first-pass page, S5-A's extended-grammar reading of every math span
  (`results/s5/parse.tsv`, record `s5.coverage`): the span count, the SHA-256 of the spans'
  `[start, end]` list and one status letter per span in page order (`o` ok, `a` ambiguous, `p`
  partial, `f` failed), the failure category of each failed span by its index, and the record's
  totals.

The committed JSON is the fixture's authority; this script is provenance. These are frozen
historical inputs to current component checks, not qualification of today's PDF recognition or
provider. Changes must cite the original paths/records above, state the intended semantic or
coordinate difference, adjudicate independently under the cited source and D1 §6.2, and add a new
explicitly selected reference while preserving the old witness. A current producer rerun supplies
a candidate difference, not authority to accept it.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

REPO = Path.cwd()
EVIDENCE = REPO / "docs/design_review/evidence/2026-10-28_design-spikes"
RESULTS = EVIDENCE / "results"
OUT = Path(__file__).resolve().parent
LETTER = {"ok": "o", "ambiguous": "a", "partial": "p", "failed": "f"}


def canonical(page: str, folder: str) -> str:
    name = page.replace("/", "__").removesuffix(".html")
    return (EVIDENCE / folder / "canonical" / f"{name}.txt").read_text(encoding="utf-8")


def parts(unit: dict) -> list[dict]:
    return [{"kind": p["kind"], "start": p["start"], "end": p["end"]} for p in unit["parts"]]


def scopes() -> dict:
    core = json.loads((EVIDENCE / "sample.json").read_text())["units"]
    path = RESULTS / "s0/m13_probe.reference.patterns.h3h4.tsv"
    rows = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["expression"] == "True":
                continue
            unit = core[r["unit"]]
            rows.append(
                {
                    "unit": r["unit"],
                    "page": unit["page"],
                    "parts": parts(unit),
                    "symbol": r["symbol"],
                    "annotated": r["annotated_extent"],
                    "spike": r["probe"],
                }
            )
    return {
        "records": ["s0.m13-probe-2"],
        "source": str(path.relative_to(EVIDENCE)),
        "scopes": rows,
    }


def contexts() -> dict:
    sample = json.loads((RESULTS / "s0r2/sample.json").read_text())["units"]
    units = {}
    for uid, unit in sample.items():
        folder = "results/s1" if unit["rendition_dir"] == "results/s1" else "results/s0r2/s1"
        text = canonical(unit["page"], folder)
        units[uid] = {
            "page": unit["page"],
            "set": unit["set"],
            "parts": parts(unit),
            "context": [
                {
                    "id": c["id"],
                    "start": c["start"],
                    "end": c["end"],
                    "text": text[c["start"] : c["end"]],
                }
                for c in unit["context"]
            ],
        }
    return {
        "records": ["s0r2.inputs", "s0r2.scores"],
        "source": "results/s0r2/sample.json",
        "units": units,
    }


def coverage() -> dict:
    pages: dict[str, list[tuple[int, int, str, str]]] = {}
    with (RESULTS / "s5/parse.tsv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            category = r["category_or_cause"] if r["status"] == "failed" else ""
            pages.setdefault(r["page"], []).append(
                (int(r["start"]), int(r["end"]), r["status"], category)
            )
    out = {}
    for page, spans in sorted(pages.items()):
        spans.sort()
        bounds = json.dumps([[a, b] for a, b, _, _ in spans])
        out[page] = {
            "spans": len(spans),
            "bounds_sha256": hashlib.sha256(bounds.encode()).hexdigest(),
            "status": "".join(LETTER[s] for _, _, s, _ in spans),
            "failed": {str(i): c for i, (_, _, s, c) in enumerate(spans) if s == "failed"},
        }
    record = json.loads((EVIDENCE / "records/s5.coverage.json").read_text())
    summary = json.loads((RESULTS / "s5/coverage_summary.json").read_text())
    return {
        "records": [record["id"]],
        "source": "results/s5/parse.tsv",
        "extended": summary["extended"],
        "pages": out,
    }


def main() -> None:
    for name, data in (
        ("s0_scopes", scopes()),
        ("s0r2_contexts", contexts()),
        ("s5_coverage", coverage()),
    ):
        (OUT / f"{name}.json").write_text(
            json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
