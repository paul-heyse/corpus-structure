"""S1-C: stratified sample of text blocks for the sentence-boundary gold, and the marking worksheet.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s1c_gold_sample.py

Sample: 60 blocks from the four spike pages, stratified by inline-math density (none / low / high),
display math, list item, inside details, and known traps; plus every splittable block of the
twelve core units. Writes results/s1/gold/sample.json and results/s1/gold/worksheet.md.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s1_adapter import EVIDENCE, adapt  # noqa: E402
from s1_sentences import blocks_of  # noqa: E402

PAGES = ["special/LocationScale.html", "special/Normal.html", "special/LogNormal.html", "special/Gamma.html"]
OUT = EVIDENCE / "results" / "s1" / "gold"
SEED = 20261028
TRAP = re.compile(r"\bi\.e\.|\be\.g\.|\bcf\.|\\\]\s*(Then|where|so)\b|\\\)\.\s*$|\\\]\.?\s*$")


def strata(b: dict, by_key: dict) -> list[str]:
    inline = [m for m in b["math"] if not m["display"]]
    share = sum(m["end"] - m["start"] for m in inline) / max(1, len(b["text"]))
    tags = ["math_none" if not inline else "math_low" if share < 0.3 else "math_high"]
    if any(m["display"] for m in b["math"]):
        tags.append("display")
    if b["kind"] == "list_item":
        tags.append("list_item")
    s = by_key[b["key"]]
    while s.get("parent"):
        s = by_key[s["parent"]]
        if s["kind"] == "details":
            tags.append("details")
            break
    if TRAP.search(b["text"]):
        tags.append("trap")
    return tags


def main() -> int:
    sample = json.loads((EVIDENCE / "sample.json").read_text())
    core_ranges = {(u["page"], p["start"], p["end"]) for u in sample["units"].values() for p in u["parts"]}
    rng = random.Random(SEED)
    pool, core = [], []
    for page in PAGES:
        r = adapt(page)
        by_key = {s["key"]: s for s in r["segments"]}
        for b in blocks_of(r):
            if len(b["text"]) < 20:
                continue
            item = {"page": page, "rendition": r["rendition"]["rendition_key"], "key": b["key"], "kind": b["kind"],
                    "start": b["start"], "end": b["start"] + len(b["text"]), "text": b["text"],
                    "strata": strata(b, by_key)}
            in_core = any(pg == page and a <= item["start"] and item["end"] <= e for pg, a, e in core_ranges)
            (core if in_core else pool).append(item)
    # stratified: draw round-robin over the primary strata so each is represented
    order = ["math_none", "math_low", "math_high", "display", "list_item", "details", "trap"]
    chosen, seen = [], set()
    rng.shuffle(pool)
    while len(chosen) < 60:
        progressed = False
        for tag in order:
            cand = next((x for x in pool if tag in x["strata"] and x["key"] not in seen), None)
            if cand and len(chosen) < 60:
                chosen.append(cand)
                seen.add(cand["key"])
                progressed = True
        if not progressed:
            break
    for x in core:
        x["core"] = True
    blocks = [*chosen, *core]
    for i, b in enumerate(blocks):
        b["id"] = f"B{i + 1:03d}"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sample.json").write_text(json.dumps({"seed": SEED, "blocks": blocks}, indent=2, ensure_ascii=False) + "\n")
    lines = ["# Sentence-boundary worksheet", "",
             "Each block below is one paragraph, list item, table cell or caption of canonical text.", ""]
    for b in blocks:
        lines += [f"## {b['id']}", "", "```text", b["text"], "```", ""]
    (OUT / "worksheet.md").write_text("\n".join(lines))
    from collections import Counter
    print(len(chosen), "sampled +", len(core), "core blocks;", Counter(t for b in chosen for t in b["strata"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
