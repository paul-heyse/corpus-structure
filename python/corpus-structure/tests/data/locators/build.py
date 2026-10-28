"""Write the locator test fixture from the frozen S1 renditions of the four spike pages.

    python3 python/corpus-structure/tests/data/locators/build.py

Reads, as data only (no spike code is imported), the S1 spike's canonical texts
(`results/s1/canonical/<page>.txt`) and flat segment lists with parent keys
(`results/s1/segments/<page>.jsonl`), and `results/s1/renditions.json` for each page's source URI.
For each page it removes the diagnostic attributes production segments do not carry (D1 §3.2:
`tag`, `sid`, `sourceline`, `roles`), drops the spike's segment keys, rebuilds the segment tree from
the parent keys and writes `<page>.json`: `{"page", "source_uri", "canonical_text", "document"}`,
where `document` is the nested `Segment` tree that `RenditionContent` validates. Stdlib only; the
output is committed and is the fixture's authority, this script its provenance.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
S1 = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/results/s1"
PAGES = (
    "special/LocationScale.html",
    "special/Normal.html",
    "special/LogNormal.html",
    "special/Gamma.html",
)
DIAGNOSTIC = frozenset({"tag", "sid", "sourceline", "roles"})


def stem(page: str) -> str:
    return page.removesuffix(".html").replace("/", "__")


def tree(rows: list[dict]) -> dict:
    nodes: dict[str, dict] = {}
    for row in rows:
        node = {
            "kind": row["kind"],
            "start": row["start"],
            "end": row["end"],
            "parse_status": row["parse_status"],
            "attrs": {k: v for k, v in row["attrs"].items() if k not in DIAGNOSTIC},
            "children": [],
        }
        if row.get("parse_reason") is not None:
            node["parse_reason"] = row["parse_reason"]
        nodes[row["key"]] = node
    roots = []
    for row in rows:
        parent = row["parent"]
        (roots if parent is None else nodes[parent]["children"]).append(nodes[row["key"]])
    (root,) = roots
    return root


def main() -> None:
    renditions = json.loads((S1 / "renditions.json").read_text(encoding="utf-8"))
    for page in PAGES:
        text = (S1 / "canonical" / f"{stem(page)}.txt").read_text(encoding="utf-8")
        lines = (S1 / "segments" / f"{stem(page)}.jsonl").read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line]
        fixture = {
            "page": page,
            "source_uri": renditions[page]["source_uri"],
            "canonical_text": text,
            "document": tree(rows),
        }
        out = HERE / f"{stem(page)}.json"
        body = json.dumps(fixture, ensure_ascii=False, separators=(",", ":"))
        out.write_text(body + "\n", encoding="utf-8")
        print(f"{out.relative_to(REPO)}: {len(rows)} segments, {len(text)} characters")


if __name__ == "__main__":
    main()
