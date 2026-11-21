"""Native PDF access and region projections shared by certifiers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def write_pdf_access_projection(document: Mapping[str, Any], projection: Path) -> None:
    """Derive access and regions from the actual certified native document."""
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

    # Organized section groups use section/chapter labels; keep the native labels.
    with Path(projection).open("w") as out:
        for ordinal, pointer in enumerate(order):
            node = nodes[pointer]
            parent = node.get("parent", {}).get("$ref")
            row = dict(
                pointer=pointer,
                ordinal=ordinal,
                label=node.get("label", "unspecified"),
                parent_pointer=parent,
                section_pointer=section_owner(pointer),
                content_layer=node.get("content_layer", "body"),
                text=node.get("text"),
                native_json=node,
            )
            out.write(
                json.dumps({"family": "access", "body": row}, ensure_ascii=False, allow_nan=False)
                + "\n"
            )
            for index, prov in enumerate(node.get("prov", [])):
                page = document["pages"][str(prov["page_no"])]
                box = prov["bbox"]
                region = dict(
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
                out.write(json.dumps({"family": "region", "body": region}) + "\n")
