"""Normalize independent GS120 source inventories without inventing semantic agreement.

This is an evidence adapter, not a producer, reference author or protected native importer.
Every original author case and author packet remains the cited authority for its judgment.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
JUDGMENTS = {"supported", "unsupported", "ambiguous", "unassessed"}
SOURCE_STATES = {"stated", "unstated", "unresolved", "uninspected"}
AUTHOR_PATTERNS = {
    "a": "physical*-*.json",
    "b": "packet-*-*.json",
    "c": "grinstead-snell-physical*-*.json",
}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def retain(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def load_source_packets(base: Path):
    packets, views = {}, {}
    for path in sorted((base / "source-packets").glob("grinstead-snell-physical*-*.json")):
        packet = json.loads(path.read_bytes())
        packets[digest(path)] = (path, packet)
        for view in packet["views"]:
            native = view["native_context"]
            native = json.loads(native) if isinstance(native, str) else native
            identifier = view["source"]["source_view_id"]
            if identifier in views:
                raise ValueError(f"source view {identifier} appears in several input packets")
            views[identifier] = {**view, "native_context": native, "packet": packet,
                                 "packet_file": str(path.relative_to(base)),
                                 "packet_sha256": digest(path)}
    if len(packets) != 12:
        raise ValueError("the frozen shared source selection must contain twelve ten-page packets")
    return packets, views


def pointer_for_piece(piece):
    pointer = piece["item_ref"]
    if piece.get("cell_index") is not None:
        pointer += "/data/table_cells/" + str(piece["cell_index"])
    return pointer


def native_segments(view, start: int, end: int, text: str):
    """Map exact projected text onto unchanged native pieces; separators remain explicit."""
    passage = view["passage"]
    if type(start) is not int or type(end) is not int or not passage["start"] <= start < end <= passage["end"]:
        raise ValueError("authored source extent lies outside the frozen original passage")
    if passage["text"][start - passage["start"]:end - passage["start"]] != text:
        raise ValueError("authored quotation differs from its exact frozen source slice")
    nodes = {node["self_ref"]: node for node in view["native_context"]["items"]}
    page_map = {row["excerpt_physical_page"]: row["parent_physical_page"]
                for row in view["packet"]["page_map"]}
    source = view["source"]
    result, separators, covered = [], [], []
    for piece in view["native_context"]["pieces"]:
        low, high = max(start, piece["start"]), min(end, piece["end"])
        if low >= high:
            continue
        covered.append((low, high))
        if piece["kind"] == "synthetic_separator":
            separators.append({"start": low, "end": high,
                               "text": passage["text"][low-passage["start"]:high-passage["start"]]})
            continue
        if piece["kind"] != "native_text":
            raise ValueError("unsupported authored source-piece coordinate kind")
        node = nodes[piece["item_ref"]]
        provenance = node.get("prov", ())
        local_start, local_end = low-piece["start"], high-piece["start"]
        native_node = node
        if piece.get("cell_index") is not None:
            field = "table_cells" if piece.get("source_field") == "cell_text" else "chart_data"
            if field == "table_cells":
                native_node = node["data"]["table_cells"][piece["cell_index"]]
        native_text = native_node.get("text")
        if piece.get("source_field") == "orig":
            native_text = native_node.get("orig")
        quote = passage["text"][low-passage["start"]:high-passage["start"]]
        # Native text and orig are ordinary exact bridges. Unsupported rich/chart fields
        # remain cited under the original projection instead of being silently repaired.
        bridge = isinstance(native_text, str) and native_text[local_start:local_end] == quote
        parent_pages = sorted({page_map[p["page_no"]] for p in provenance
                               if p.get("page_no") in page_map})
        result.append({
            "source_view_id": source["source_view_id"],
            "source_ref": passage["source_ref"],
            "native_product_key": source["native_product_key"],
            "native_content_digest": source["native_content_digest"],
            "native_task_id": source["native_task_id"],
            "source_pointer": pointer_for_piece(piece),
            "source_field": piece.get("source_field"),
            "projection_start": low, "projection_end": high,
            "native_start": local_start, "native_end": local_end,
            "text": quote, "exact_native_text_bridge": bridge,
            "parent_physical_pages": parent_pages,
            "native_provenance": provenance,
        })
    if not covered or min(a for a, _ in covered) != start or max(b for _, b in covered) != end:
        raise ValueError("quoted source range has no complete native projection-piece coverage")
    ordered = sorted(covered)
    if any(a[1] != b[0] for a, b in zip(ordered, ordered[1:])):
        raise ValueError("quoted source range has overlapping or missing projection pieces")
    return result, separators


def authored_spans(author, case):
    if author == "a":
        return [(span["source_view_id"], span["start"], span["end"], span["text"],
                 span.get("role"), span.get("pointer")) for span in case["evidence_spans"]]
    if author == "b":
        return [(span["view_id"], span["start"], span["end"], span["quote"],
                 None, span.get("pointer")) for span in case["evidence"]]
    return [(case["view"], *case["span"], case["quote"], None, case.get("pointer"))]


def normalize_case(author, case, author_path, author_sha, views):
    state, judgment = case["source_state"], case["judgment"]
    if state not in SOURCE_STATES or judgment not in JUDGMENTS:
        raise ValueError(f"unknown authored state or judgment: {case['id']}")
    if state == "uninspected" and judgment != "unassessed":
        raise ValueError("uninspected source cannot acquire a truth label")
    spans = []
    for view_id, start, end, text, role, declared_pointer in authored_spans(author, case):
        view = views[view_id]
        segments, separators = native_segments(view, start, end, text)
        spans.append({"source_view_id": view_id, "source_ref": view["passage"]["source_ref"],
                      "passage_id": view["passage"]["passage_id"], "start": start, "end": end,
                      "text": text, "authored_role": role, "declared_pointer": declared_pointer,
                      "source_packet": view["packet_file"],
                      "source_packet_sha256": view["packet_sha256"],
                      "native_segments": segments, "synthetic_separators": separators})
    pages = sorted({page for span in spans for segment in span["native_segments"]
                    for page in segment["parent_physical_pages"]})
    # Textual descriptions do not become exact machine alternatives by normalization.
    return {
        "case_key": author.upper() + ":" + case["id"],
        "author": author.upper(), "author_case_id": case["id"],
        "author_file": str(author_path.relative_to(BASE)), "author_sha256": author_sha,
        "facet": case.get("facet", "/".join(case.get("roles", ()))),
        "expected_description": case.get("semantic_distinction"),
        "expected_roles_relationships": case.get("expected_roles_relationships", case.get("roles", [])),
        "expected_relation": case.get("proposed_relation", case.get("relationship")),
        "source_state": state, "source_judgment": judgment,
        "reason": case.get("reason", case.get("uncertainty")),
        "missing_facets": case.get("missing_facets", []),
        "parent_physical_pages": pages,
        "authored_parent_physical_pages": case.get("parent_physical_pages", case.get("pages")),
        "spans": spans,
        "semantic_capture": "unassessed",
        "normalization_claim": "exact source quotation and native-piece mapping only",
    }


def build(base=BASE, *, authors=("a", "b", "c"), allow_partial=False):
    packets, views = load_source_packets(base)
    cases, author_receipts, gaps = [], [], []
    for author in authors:
        paths = sorted((base / "authors" / author).glob(AUTHOR_PATTERNS[author]))
        if len(paths) != 12 and not allow_partial:
            raise ValueError(f"author {author.upper()} has {len(paths)} packets; expected12")
        author_count = 0
        for path in paths:
            document = json.loads(path.read_bytes())
            if document.get("protocol") != "gs120-source-author-1" or document.get("author") != author.upper():
                raise ValueError("unexpected source-author protocol or identity")
            input_hash = document["input_sha256"]
            if input_hash not in packets:
                raise ValueError("authored packet does not bind any exact selected source packet")
            _, source = packets[input_hash]
            file_hash = digest(path)
            for case in document["cases"]:
                normalized = normalize_case(author, case, path, file_hash, views)
                if any(span["source_packet_sha256"] != input_hash for span in normalized["spans"]):
                    raise ValueError("case source view escapes its author packet's frozen input")
                cases.append(normalized)
                author_count += 1
            gaps.append({"author": author.upper(), "author_file": str(path.relative_to(base)),
                         "input_sha256": input_hash, "physical_pages": source["parent_physical_pages"],
                         "authored_coverage": document["coverage"],
                         "remaining_gaps": document.get("remaining_gaps", [])})
        author_receipts.append({"author": author.upper(), "packet_count": len(paths),
                                "case_count": author_count, "complete_packet_set": len(paths) == 12})
    if len({case["case_key"] for case in cases}) != len(cases):
        raise ValueError("author-scoped case identity repeats")
    pages = []
    for page in range(191, 311):
        available = []
        for view_id, view in views.items():
            nodes = {item["self_ref"]: item for item in view["native_context"]["items"]}
            page_map = {r["excerpt_physical_page"]: r["parent_physical_page"]
                        for r in view["packet"]["page_map"]}
            native_pages = {page_map[p["page_no"]] for piece in view["native_context"]["pieces"]
                            if piece.get("kind") == "native_text"
                            for p in nodes[piece["item_ref"]].get("prov", ())
                            if p.get("page_no") in page_map}
            if page in native_pages:
                available.append(view_id)
        page_cases = [case for case in cases if page in case["parent_physical_pages"]]
        pages.append({"parent_physical_page": page, "available_projection_view_ids": available,
                      "projection_availability": "present" if available else "absent",
                      "case_count_by_author": dict(sorted(Counter(c["author"] for c in page_cases).items())),
                      "case_keys": [c["case_key"] for c in page_cases],
                      "semantic_capture": "unassessed", "inventory_kind": "selective_not_census"})
    summary = {
        "protocol": "gs120-normalized-source-inventory-1", "authors": author_receipts,
        "case_count": len(cases), "source_view_count": len(views), "physical_page_count": 120,
        "projection_present_pages": [p["parent_physical_page"] for p in pages if p["projection_availability"] == "present"],
        "projection_absent_pages": [p["parent_physical_page"] for p in pages if p["projection_availability"] == "absent"],
        "source_state_counts": dict(Counter(c["source_state"] for c in cases)),
        "source_judgment_counts": dict(Counter(c["source_judgment"] for c in cases)),
        "semantic_capture_counts": {"unassessed": len(cases)},
        "overlap_credit_policy": "Physical overlap is a location intersection, never semantic capture or independent corroboration.",
        "population": "same120pages; selective independently authored source inventories; no held-out claim",
        "cases_are_distinct_independent_facts": False,
        "assessment_completeness": "normalization only; semantic correctness/completeness and author disagreements remain unassessed",
    }
    return summary, cases, pages, gaps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors", nargs="+", choices=tuple(AUTHOR_PATTERNS), default=list(AUTHOR_PATTERNS))
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--out", default=".", help="New result directory under assessment; existing results are never overwritten")
    args = parser.parse_args()
    output = (HERE / args.out).resolve()
    if output != HERE and HERE not in output.parents:
        raise ValueError("normalization output must stay within the assessment assignment")
    if output != HERE:
        output.mkdir(exist_ok=False)
    summary, cases, pages, gaps = build(authors=tuple(args.authors), allow_partial=args.allow_partial)
    retain(output / "source-summary.json", summary)
    retain(output / "source-cases.json", cases)
    retain(output / "source-pages.json", pages)
    retain(output / "author-coverage-and-gaps.json", gaps)
    report = ["# Shared GS120 source inventory", "", "Normalized2026-11-06. Exact quotations and native-piece mappings are verified; semantic capture remains unassessed.", "", "This is a selective source inventory, not a census. Author cases remain separate and are not counts of distinct facts. No output predictions enter this source normalization.", "", "| Author | Packets | Cases |", "|---|---:|---:|"]
    report += [f"| {r['author']} | {r['packet_count']} | {r['case_count']} |" for r in summary["authors"]]
    report += ["", "All120 physical pages have explicit entries. Projected native pieces are present on" + str(len(summary["projection_present_pages"])) + " pages and absent on" + str(len(summary["projection_absent_pages"])) + ". Original visual regions and unsampled semantic distinctions remain uninspected.", "", "Projection-absent pages: " + ", ".join(map(str, summary["projection_absent_pages"])) + ".", "", "| Physical page | Native views | Author case counts | Capture |", "|---:|---|---|---|"]
    report += [f"| {p['parent_physical_page']} | {','.join(map(str,p['available_projection_view_ids'])) or 'absent'} | " + ", ".join(f"{a}:{n}" for a,n in p["case_count_by_author"].items()) + " | unassessed |" for p in pages]
    report += ["", "`source-cases.json` retains exact evidence, author prose, expected roles/relationships and source states. `author-coverage-and-gaps.json` retains every author's original inspection boundary. No automatic agreement or supported semantic capture is inferred.", ""]
    with (output / "source-inventory.md").open("x") as stream:
        stream.write("\n".join(report))
    print(json.dumps({"outcome": "passed", "authors": summary["authors"], "cases": len(cases), "projection_absent_pages": summary["projection_absent_pages"]}))


if __name__ == "__main__":
    main()
