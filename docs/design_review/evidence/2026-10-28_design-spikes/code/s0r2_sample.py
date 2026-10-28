"""S0-R2: the revisit sample — the twelve core units, six units from pages S0 did not use (held out
from rule writing) and three worked-example units — with standing context assembled by query.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0r2_sample.py

Standing context (guideline v1 §10.2) is a query, not a position rule: for every symbol the unit
mentions, the binding site M13 assigns it (code/s0e_m13_probe.py, spaCy patterns, paragraph
statements) when that site lies outside the unit, plus the site a "Suppose again" reopens. Each
context sentence keeps its segment key and offsets, so a batch may cite it (`cN`).

Writes results/s0r2/sample.json; renditions of the new pages under results/s0r2/s1/ (the same
adapter configuration and sentence variant as S1, so offsets and keys are comparable).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
from s0e_m13_probe import assign, probe_page_patterns  # noqa: E402
from s1_adapter import DEFAULT_CONFIG, adapt  # noqa: E402
from s1_sentences import sentences  # noqa: E402
from s1b_sample import resolve, ws  # noqa: E402

EVIDENCE = CODE.parent
OUT = EVIDENCE / "results" / "s0r2"
CORE = json.loads((EVIDENCE / "sample.json").read_text())
# id -> (page, start offset of the unit segment); chosen by kind from pages S0 did not use
HELD_OUT = {"H1": ("special/Pareto.html", 235), "H2": ("special/Pareto.html", 9161),
            "H3": ("special/Pareto.html", 11780), "H4": ("special/ChiSquare.html", 6836),
            "H5": ("special/ChiSquare.html", 8200), "H6": ("special/Pareto.html", 17189)}
EXAMPLES = {"E1": ("special/Weibull.html", 10158), "E2": ("special/Weibull.html", 15721),
            "E3": ("special/Weibull.html", 22349)}
MAX_CONTEXT = 6


def name_of(page: str) -> str:
    return page.replace("/", "__").removesuffix(".html")


def persist(page: str, r: dict, sents: list[dict]) -> None:
    n = name_of(page)
    for sub in ("canonical", "segments", "sentences"):
        (OUT / "s1" / sub).mkdir(parents=True, exist_ok=True)
    (OUT / "s1" / "canonical" / f"{n}.txt").write_text(r["text"], encoding="utf-8")
    (OUT / "s1" / "segments" / f"{n}.jsonl").write_text(
        "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in r["segments"]))
    (OUT / "s1" / "sentences" / f"{n}.provisional.jsonl").write_text(
        "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in sents))


def unit_entry(page: str, start: int, r: dict, sents: list[dict]) -> dict:
    seg = next(s for s in r["segments"] if s["kind"] == "unit" and s["start"] == start)
    text = r["text"][seg["start"]:seg["end"]]
    prefix = ws(text)[:48]
    loc = f"{page}@u:{prefix}"
    hits = resolve(loc, r)
    assert len(hits) == 1 and hits[0]["key"] == seg["key"], (loc, len(hits))
    sids = [s for s in sents if seg["start"] <= s["start"] and s["end"] <= seg["end"]]
    part = {"locator": loc, "found_by": "@u", "segment_key": seg["key"], "kind": "unit",
            "start": seg["start"], "end": seg["end"], "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "sentences": [{"id": f"s{i + 1}", "key": s["key"], "start": s["start"], "end": s["end"]}
                          for i, s in enumerate(sids)], "first_80": text[:80]}
    return {"page": page, "document_key": r["rendition"]["document_key"],
            "rendition_key": r["rendition"]["rendition_key"], "parts": [part]}


def context_for(meta: dict, pg: dict, sents: list[dict], text: str) -> list[dict]:
    """Binding sentences outside the unit for every symbol the unit mentions, in page order."""
    ranges = [(p["start"], p["end"]) for p in meta["parts"]]
    inside = lambda a: any(s <= a < e for s, e in ranges)  # noqa: E731
    syms = sorted({m["symbol"] for m in pg["mentions"] if inside(m["pos"])})
    spans = set()
    for sym in syms:
        got = assign(pg, sym, ranges)
        if got["binding"] == "unresolved":
            continue
        site = next((s for s in pg["sites"] if s["symbol"] == sym and s["sentence"] == got["site"]), None)
        if site is None:
            continue
        for span in (site["sent_span"], site.get("reopens_span")):
            if span and not inside(span[0]):
                spans.add(tuple(span))
    out = []
    unit_texts = {text[s["start"]:s["end"]] for p in meta["parts"] for s in p["sentences"]}
    for a, e in sorted(spans)[-MAX_CONTEXT:]:
        s = next((x for x in sents if x["start"] <= a < x["end"]), None)
        if s and text[s["start"]:s["end"]] not in unit_texts:  # the page may restate a unit's own supposition
            out.append({"key": s["key"], "start": s["start"], "end": s["end"]})
    uniq = {c["key"]: c for c in out}
    return [{"id": f"c{i + 1}", **c} for i, c in enumerate(sorted(uniq.values(), key=lambda c: c["start"]))]


def main() -> int:
    units: dict[str, dict] = {}
    renditions: dict[str, dict] = {}
    new_pages = sorted({p for p, _ in [*HELD_OUT.values(), *EXAMPLES.values()]})
    adapted = {}
    for page in new_pages:
        r = adapt(page, DEFAULT_CONFIG)
        s = sentences(r, "P1", "bp+c")
        persist(page, r, s)
        adapted[page] = (r, s)
        renditions[page] = r["rendition"]
    for uid, meta in CORE["units"].items():
        units[uid] = {**meta, "set": "core", "rendition_dir": "results/s1"}
    for group, table in (("held_out", HELD_OUT), ("example", EXAMPLES)):
        for uid, (page, start) in table.items():
            r, s = adapted[page]
            units[uid] = {**unit_entry(page, start, r, s), "set": group, "rendition_dir": "results/s0r2/s1"}
    by_page: dict[str, list[str]] = {}
    for uid, meta in units.items():
        by_page.setdefault(meta["page"], []).append(uid)
    for page, uids in by_page.items():
        parts = [{"start": p["start"], "end": p["end"], "key": p["segment_key"]} for u in uids for p in units[u]["parts"]]
        pg = probe_page_patterns(page, "h3h4", paragraph_statements=True, sample_parts=parts)
        rdir = EVIDENCE / units[uids[0]]["rendition_dir"]
        canonical = (rdir / "canonical" / f"{name_of(page)}.txt").read_text(encoding="utf-8")
        assert pg["text"] == canonical, f"{page}: probe text differs from the stored rendition"
        sents = [json.loads(x) for x in (rdir / "sentences" / f"{name_of(page)}.provisional.jsonl").read_text().splitlines()]
        for u in uids:
            units[u]["context"] = context_for(units[u], pg, sents, canonical)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "s1" / "renditions.json").write_text(json.dumps(renditions, indent=1, ensure_ascii=False) + "\n")
    sample = {"created": "2026-10-28", "sentence_variant": CORE["sentence_variant"],
              "adapter_config": DEFAULT_CONFIG, "context_rule": "M13 binding sites outside the unit (s0r2_sample.py)",
              "units": units}
    (OUT / "sample.json").write_text(json.dumps(sample, indent=1, ensure_ascii=False) + "\n")
    for uid, m in units.items():
        print(uid, m["set"], m["page"], "context", len(m["context"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
