"""Native PDF access and region projections shared by certifiers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ITEM_REPORT_KINDS = ("cell_reports", "derivation_mappings", "inline_alignment_reports")


def project_pdf_access(document: Mapping[str, Any]):
    """Derive item and region values for pre-staging semantic validators."""
    # Source access is a derived, per-item projection, never the content authority.
    nodes = {}
    for key in ("body", "furniture"):
        node = document.get(key)
        if node:
            nodes[node["self_ref"]] = node
    for key in ("groups", "texts", "pictures", "tables", "key_value_items", "form_items"):
        for node in document.get(key, []):
            nodes[node["self_ref"]] = node
    order = []
    seen = set()

    def walk(pointer):
        if pointer in seen:
            raise ValueError("native containment repeats an item")
        seen.add(pointer)
        order.append(pointer)
        for child in nodes[pointer].get("children", []):
            walk(child["$ref"])

    walk(document["body"]["self_ref"])
    walk(document["furniture"]["self_ref"])
    order.extend(sorted(set(nodes) - seen))
    sections = {p for p, n in nodes.items() if n.get("label") in ("section", "chapter")}
    owners: dict[str, str | None] = {}

    def section_owner(pointer: str) -> str | None:
        path = []
        visited = set()
        current = pointer
        while current not in owners:
            if current in visited:
                raise ValueError("cyclic source section ancestry")
            visited.add(current)
            path.append(current)
            if current in sections:
                owner = current
                break
            parent = nodes[current].get("parent", {}).get("$ref")
            if parent is None:
                owner = None
                break
            current = parent
        else:
            owner = owners[current]
        for node_pointer in path:
            owners[node_pointer] = owner
        return owner

    items, regions = [], []
    for ordinal, pointer in enumerate(order):
        node = nodes[pointer]
        items.append(
            dict(
                pointer=pointer,
                ordinal=ordinal,
                label=node.get("label", "unspecified"),
                parent_pointer=node.get("parent", {}).get("$ref"),
                section_pointer=section_owner(pointer),
                content_layer=node.get("content_layer", "body"),
                text=node.get("text"),
                native_json=node,
            )
        )
        for index, prov in enumerate(node.get("prov", [])):
            page = document["pages"][str(prov["page_no"])]
            box = prov["bbox"]
            regions.append(
                dict(
                    pointer=pointer,
                    region_index=index,
                    page_no=prov["page_no"],
                    page_width=page["size"]["width"],
                    page_height=page["size"]["height"],
                    left=box["l"],
                    top=box["t"],
                    right=box["r"],
                    bottom=box["b"],
                    origin="top_left" if box["coord_origin"] == "TOPLEFT" else "bottom_left",
                )
            )
    return items, regions


def write_pdf_access_projection(document: Mapping[str, Any], projection: Path, *, items) -> None:
    """Stage the native JSON copies. Publication derives their access columns."""
    referenced_pages = {
        prov["page_no"] for row in items for prov in row["native_json"].get("prov", ())
    }
    with projection.open("w", encoding="utf-8") as out:
        for item in items:
            row = {"family": "access", "body": {"native_json": item["native_json"]}}
            out.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        for page_no in sorted(referenced_pages):
            row = {
                "family": "page",
                "body": {"page_no": page_no, "size": document["pages"][str(page_no)]["size"]},
            }
            out.write(json.dumps(row, allow_nan=False) + "\n")


def staged_pdf_access_row(row):
    """Project an authenticated legacy envelope without rewriting the original spool."""
    family, body = row["family"], row["body"]
    if family == "access":
        return {"family": "access", "body": {"native_json": body["native_json"]}}
    if family == "page":
        return row
    if family == "region":
        return {
            "family": "page",
            "body": {
                "page_no": body["page_no"],
                "size": {"width": body["page_width"], "height": body["page_height"]},
            },
        }
    raise ValueError("unsupported legacy PDF access projection family")
