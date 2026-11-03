"""Write the thin spike fixtures of `tests/ingest` once, from the frozen S1 results (stdlib only;
run from the repository root: `python3 python/corpus-structure/tests/ingest/data/build.py`).

- `spike_renditions.json`: for the seven S0/S0-R2 pages, the canonical text's SHA-256 and length,
  every non-sentence segment as `[kind, start, end, parent kind, parent start, parent end]` and
  every provisional sentence as `[start, end, parent kind, parent start, parent end]`, sorted.
  Sources: `results/s1/{canonical,segments,sentences}` (the four spike pages) and
  `results/s0r2/s1/…` (Pareto, ChiSquare, Weibull), records `s1.adapter`, `s1.rendition-identity`
  and `s1.corpus-html5lib` (html5lib gives these renditions unchanged).
- `s1_corpus.json`: S1's 78-page figures under html5lib (`results/s1_html5lib/`, record
  `s1.corpus-html5lib`): the `partial` math spans with their reasons and opening text, the stray
  closers, the orphan runs by container, the figure count, the independent-text count, the page
  where the index counts differ, and the macro definitions with the number of pages defining each
  (the pylatexenc reader, which misses `\\renewcommand`).

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
PAGES = {
    "special/LocationScale.html": "results/s1",
    "special/Normal.html": "results/s1",
    "special/LogNormal.html": "results/s1",
    "special/Gamma.html": "results/s1",
    "special/Pareto.html": "results/s0r2/s1",
    "special/ChiSquare.html": "results/s0r2/s1",
    "special/Weibull.html": "results/s0r2/s1",
}


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def renditions() -> dict:
    pages = {}
    for page, folder in PAGES.items():
        name = page.replace("/", "__").removesuffix(".html")
        d = EVIDENCE / folder
        text = (d / "canonical" / f"{name}.txt").read_text(encoding="utf-8")
        segs = jsonl(d / "segments" / f"{name}.jsonl")
        sents = jsonl(d / "sentences" / f"{name}.provisional.jsonl")
        by_key = {s["key"]: s for s in segs}

        def parent(s: dict, by_key: dict = by_key) -> list:
            p = by_key.get(s["parent"])
            return [p["kind"], p["start"], p["end"]] if p else [None, None, None]

        pages[page] = {
            "canonical_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "chars": len(text),
            "segments": sorted([s["kind"], s["start"], s["end"], *parent(s)] for s in segs),
            "sentences": sorted([s["start"], s["end"], *parent(s)] for s in sents),
            "sources": [
                f"{folder}/{sub}/{name}{ext}"
                for sub, ext in (
                    ("canonical", ".txt"),
                    ("segments", ".jsonl"),
                    ("sentences", ".provisional.jsonl"),
                )
            ],
        }
    return {
        "records": ["s1.adapter", "s1.rendition-identity", "s1.corpus-html5lib"],
        "evidence": "docs/design_review/evidence/2026-10-28_design-spikes",
        "pages": pages,
    }


def corpus() -> dict:
    summary = json.loads((RESULTS / "s1_html5lib/corpus_summary.json").read_text())
    partial, strays = [], []
    for a in summary["math_anomalies"]:
        if "anomaly" in a:
            strays.append({"page": a["page"], "delimiter": a["anomaly"]["delim"]})
        else:
            partial.append({"page": a["page"], "reason": a["reason"], "opening": a["text"][:40]})
    with (RESULTS / "s1_html5lib/repairs.tsv").open(encoding="utf-8") as f:
        repairs = [r for r in csv.DictReader(f, delimiter="\t") if r["parser"] == "html5lib"]
    by_container: dict[str, int] = {}
    for r in repairs:
        by_container[r["container"]] = by_container.get(r["container"], 0) + 1
    with (RESULTS / "s1_html5lib/coverage.tsv").open(encoding="utf-8") as f:
        figures = sum(int(r["figure_segments"] or 0) for r in csv.DictReader(f, delimiter="\t"))
    with (RESULTS / "s1_html5lib/counts.tsv").open(encoding="utf-8") as f:
        differing = sorted(
            r["page"]
            for r in csv.DictReader(f, delimiter="\t")
            if any(r[k] != "0" for k in r if k.endswith("_delta"))
        )
    with (RESULTS / "s1_html5lib/macros.tsv").open(encoding="utf-8") as f:
        macros = {r["definition"]: int(r["pages"]) for r in csv.DictReader(f, delimiter="\t")}
    return {
        "record": "s1.corpus-html5lib",
        "sources": [
            "results/s1_html5lib/corpus_summary.json",
            "results/s1_html5lib/repairs.tsv",
            "results/s1_html5lib/coverage.tsv",
            "results/s1_html5lib/counts.tsv",
            "results/s1_html5lib/macros.tsv",
        ],
        "pages": summary["pages"],
        "independent_texts_checked": summary["invariants"]["independent_checked"],
        "partial_math": partial,
        "stray_closers": strays,
        "orphans_by_container": dict(sorted(by_container.items())),
        "figures": figures,
        "index_count_exceptions": differing,
        "macro_definitions": macros,
    }


def rows_per_line(obj: object, indent: str = "") -> str:
    """JSON with every list of scalars (a segment or sentence row) on one line."""
    inner = indent + " "
    if isinstance(obj, dict):
        items = [f"{inner}{json.dumps(k)}: {rows_per_line(v, inner)}" for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + "\n" + indent + "}"
    if isinstance(obj, list) and obj and isinstance(obj[0], (list, dict)):
        return (
            "[\n" + ",\n".join(inner + rows_per_line(v, inner) for v in obj) + "\n" + indent + "]"
        )
    return json.dumps(obj, ensure_ascii=False)


if __name__ == "__main__":
    (OUT / "spike_renditions.json").write_text(rows_per_line(renditions()) + "\n", encoding="utf-8")
    (OUT / "s1_corpus.json").write_text(
        json.dumps(corpus(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
