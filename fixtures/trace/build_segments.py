"""Write `fixtures/trace/<unit>.segments.json` for the five trace annotation units.

    uv run python fixtures/trace/build_segments.py

Provenance only (foundations §3.7, P0-F-3): the committed JSON files are the authority. Kinds,
counts and attributes are what `docs/design/trace.md` states, asserted below (`TRACE_MD`); offsets,
texts, attributes and parse statuses come from the frozen S1 renditions (read as data, no spike code
imported), and locators from the product generator (`corpus_structure.core.locators`). I1a's
acceptance compares production segments with these files, which also makes them a
rendition-identity check against S1.

The S1 rendition is rebuilt as in `fixtures/s0/build.py` (diagnostic attributes `tag`, `sid`,
`sourceline` and `roles` dropped, provisional sentence segments added under their parent keys).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from corpus_structure.core.evidence import RenditionContent, Segment, SegmentKind
from corpus_structure.core.locators import LocatorIndex

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
S1 = Path("docs/design_review/evidence/2026-10-28_design-spikes/results/s1")
DIAGNOSTIC = frozenset({"tag", "sid", "sourceline", "roles"})

# Each trace annotation unit: its page, a locator selecting it (D2 §12.2's trace slice), and what
# trace.md states about it (the T sections' "Segments" and the M01/M09 rows of "Expected
# observations"). `statement_math_inline` counts the inline math outside a `details` block.
UNITS: dict[str, dict[str, Any]] = {
    "T1-leadin": {
        "trace": "T1",
        "page": "special/LocationScale.html",
        "select": "special/LocationScale.html@p:As usual, our starting point",
        "trace_md": {"kind": "paragraph", "counts": {"math_inline": 7}},
    },
    "T1-dfn1": {
        "trace": "T1",
        "page": "special/LocationScale.html",
        "select": "special/LocationScale.html#dfn1",
        "trace_md": {
            "kind": "unit",
            "id": "dfn1",
            "counts": {"paragraph": 1, "math_inline": 7, "sentence": 3},
            "paragraph_classes": ["dfn"],
            "dfn_markup": ["location-scale family"],
        },
    },
    "T2": {
        "trace": "T2",
        "page": "special/Normal.html",
        "select": "special/Normal.html@p:Suppose again that \\( X \\) has the normal distribution "
        "with location parameter",
        "trace_md": {"kind": "paragraph", "counts": {"math_inline": 3}},
    },
    "T3": {
        "trace": "T3",
        "page": "special/Normal.html",
        "select": "special/Normal.html#rel1",
        "trace_md": {
            "kind": "unit",
            "id": "rel1",
            "counts": {"math_inline": 11, "math_display": 1, "details": 1},
            "statement_math_inline": 8,
            "paragraph_classes": ["math"],
        },
    },
    "T4": {
        "trace": "T4",
        "page": "special/LogNormal.html",
        "select": "special/LogNormal.html#dfn",
        "trace_md": {
            "kind": "unit",
            "id": "dfn",
            "counts": {"math_inline": 10, "list_item": 2, "paragraph": 2},
        },
    },
}


def stem(page: str) -> str:
    return page.removesuffix(".html").replace("/", "__")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_rendition(page: str) -> tuple[RenditionContent, list[dict[str, Any]]]:
    text = (REPO / S1 / "canonical" / f"{stem(page)}.txt").read_text(encoding="utf-8")
    rows = read_jsonl(REPO / S1 / "segments" / f"{stem(page)}.jsonl")
    rows += read_jsonl(REPO / S1 / "sentences" / f"{stem(page)}.provisional.jsonl")
    nodes: dict[str, dict[str, Any]] = {}
    for row in rows:
        node: dict[str, Any] = {
            "kind": row["kind"],
            "start": row["start"],
            "end": row["end"],
            "parse_status": row.get("parse_status", "ok"),
            "attrs": {k: v for k, v in row.get("attrs", {}).items() if k not in DIAGNOSTIC},
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
    content = RenditionContent.model_validate({"canonical_text": text, "document": root})
    markup = read_jsonl(REPO / S1 / "markup" / f"{stem(page)}.jsonl")
    return content, markup


def row(index: LocatorIndex, segment: Segment) -> dict[str, Any]:
    out: dict[str, Any] = {
        "kind": segment.kind.value,
        "locator": str(index.generate(segment)),
        "start": segment.start,
        "end": segment.end,
        "attrs": segment.attrs,
        "parse_status": segment.parse_status,
    }
    if segment.parse_reason is not None:
        out["parse_reason"] = segment.parse_reason
    return out


def ancestors(root: Segment, target: Segment) -> list[Segment]:
    path: list[Segment] = []

    def visit(node: Segment) -> bool:
        if node is target:
            return True
        for child in node.children:
            if child.start <= target.start and target.end <= child.end and visit(child):
                path.append(node)
                return True
        return False

    visit(root)
    return list(reversed(path))


def check(name: str, unit: Segment, stated: dict[str, Any], markup: list[dict]) -> None:
    faults = []
    if unit.kind.value != stated["kind"]:
        faults.append(f"kind {unit.kind.value} != {stated['kind']}")
    if "id" in stated and unit.attrs.get("id") != stated["id"]:
        faults.append(f"id {unit.attrs.get('id')} != {stated['id']}")
    counts = Counter(s.kind.value for s in unit.walk())
    for kind, n in stated["counts"].items():
        if counts[kind] != n:
            faults.append(f"{kind} count {counts[kind]} != {n}")
    if "statement_math_inline" in stated:
        details = [s for s in unit.walk() if s.kind is SegmentKind.DETAILS]
        inside = {
            (s.start, s.end) for d in details for s in d.walk() if s.kind is SegmentKind.MATH_INLINE
        }
        outside = sum(
            1
            for s in unit.walk()
            if s.kind is SegmentKind.MATH_INLINE and (s.start, s.end) not in inside
        )
        if outside != stated["statement_math_inline"]:
            faults.append(f"statement math_inline {outside} != {stated['statement_math_inline']}")
    if "paragraph_classes" in stated:
        first = next(s for s in unit.walk() if s.kind is SegmentKind.PARAGRAPH)
        if first.attrs.get("classes") != stated["paragraph_classes"]:
            faults.append(f"paragraph classes {first.attrs.get('classes')}")
    for term in stated.get("dfn_markup", ()):
        if not any(m["markup"] == "dfn" and m["text"] == term for m in markup):
            faults.append(f"no dfn markup {term!r}")
    if faults:
        raise SystemExit(f"{name}: S1 differs from trace.md: {'; '.join(faults)}")


def main() -> None:
    renditions = json.loads((REPO / S1 / "renditions.json").read_text(encoding="utf-8"))
    loaded: dict[str, tuple[RenditionContent, LocatorIndex, list[dict]]] = {}
    for name, spec in UNITS.items():
        page = spec["page"]
        if page not in loaded:
            content, markup = load_rendition(page)
            loaded[page] = (content, LocatorIndex(content, page), markup)
        content, index, page_markup = loaded[page]
        unit = index.resolve(spec["select"])
        unit_key = index.unit_key(unit)
        if unit_key not in {u.key for u in index.annotation_units().units}:
            raise SystemExit(f"{name}: {unit_key} is not an annotation unit")
        markup = [
            {k: m[k] for k in ("markup", "start", "end", "text")}
            for m in page_markup
            if unit.start <= m["start"] and m["end"] <= unit.end
        ]
        check(name, unit, spec["trace_md"], markup)
        segments = [row(index, s) for s in unit.walk()]
        record = {
            "trace_unit": spec["trace"],
            "page": page,
            "source_uri": renditions[page]["source_uri"],
            "unit_key": unit_key,
            "ancestors": [row(index, s) for s in ancestors(content.document, unit)],
            "segments": segments,
            "counts": dict(sorted(Counter(s["kind"] for s in segments).items())),
            "markup": markup,
            "trace_md": spec["trace_md"],
            "provenance": {
                "kinds_counts_attributes": "docs/design/trace.md (asserted in build_segments.py)",
                "offsets_texts_attributes": f"{S1} (canonical, segments, sentences "
                "provisional, markup); diagnostic attributes tag, sid, sourceline, roles dropped",
                "spike_rendition_key": renditions[page]["rendition_key"],
                "locators": "corpus_structure.core.locators.LocatorIndex.generate",
            },
        }
        out = HERE / f"{name}.segments.json"
        out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{out.relative_to(REPO)}: {unit_key}, {record['counts']}")


if __name__ == "__main__":
    main()
