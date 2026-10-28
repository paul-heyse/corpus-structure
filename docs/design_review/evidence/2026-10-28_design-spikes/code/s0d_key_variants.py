"""S0-D: key-stability variants (D1 §10.1, OPEN-D3-4). Writes normalized copies of stored batches.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0d_key_variants.py SRC_DIR DST_DIR [--anchors] [--labels]

--anchors: a statement anchor that exactly covers one segment (e.g. all sentences of a unit) is
           replaced by that segment's key, so "the unit" and "its sentences" key alike.
--labels:  a global entity whose identity attributes are all filled keeps a label derived from its
           identity (type + identity values) instead of the annotator's wording.
Then run code/s0d_compare.py on the copies; only the keys can differ from the unnormalized run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
S1 = EVIDENCE / "results" / "s1"
SAMPLE = json.loads((EVIDENCE / "sample.json").read_text())
COVER_KINDS = {"unit", "paragraph", "details", "list_item"}


def _name(page: str) -> str:
    return page.replace("/", "__").removesuffix(".html")


def normalize(unit: str, b: dict, anchors: bool, labels: bool) -> dict:
    meta = SAMPLE["units"][unit]
    segs = [json.loads(x) for x in (S1 / "segments" / f"{_name(meta['page'])}.jsonl").read_text().splitlines()]
    span = {s["key"]: (s["start"], s["end"]) for s in segs}
    for p in meta["parts"]:
        for s in p["sentences"]:
            span[s["key"]] = (s["start"], s["end"])
    if anchors:
        for st in b.get("statements", []):
            keys = [k for k in st.get("anchor") or [] if k in span]
            if not keys:
                continue
            lo, hi = min(span[k][0] for k in keys), max(span[k][1] for k in keys)
            # the anchor must tile [lo, hi]: no gap between its pieces beyond whitespace
            cover = [s for s in segs if s["kind"] in COVER_KINDS and s["start"] == lo and s["end"] == hi]
            if cover:
                st["anchor"] = [min(cover, key=lambda s: s["key"])["key"]]
            elif len(keys) > 1:
                # several parts (T1: paragraph + unit): replace each run of sentences by its part
                parts = [p["segment_key"] for p in meta["parts"]
                         if any(p["start"] <= span[k][0] < p["end"] for k in keys)]
                if all(any(p["segment_key"] == q and p["start"] >= lo and p["end"] <= hi for p in meta["parts"]) for q in parts):
                    st["anchor"] = sorted(parts)
    if labels:
        refs = {e["local_ref"] for e in b.get("entities", [])}
        for e in b.get("entities", []):
            ident = e.get("identity") or {}
            if e.get("scope") == "global" and ident and all(v not in (None, "") for v in ident.values()):
                # ref-valued slots (the family) are already resolved to keys in the identity part
                e["label"] = e["type"] + ":" + ",".join(f"{k}={ident[k]}" for k in sorted(ident) if ident[k] not in refs)
    return b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--anchors", action="store_true")
    ap.add_argument("--labels", action="store_true")
    a = ap.parse_args()
    a.dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(a.src.glob("*.json")):
        if f.stem not in SAMPLE["units"]:
            continue
        b = normalize(f.stem, json.loads(f.read_text()), a.anchors, a.labels)
        (a.dst / f.name).write_text(json.dumps(b, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
