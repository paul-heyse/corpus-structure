"""Inspect actual Chandra products through parser replay and the current text projection."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from docling.utils.chandra_utils import parse_chandra_html
from docling_core.types.doc import DoclingDocument, Size

from corpus_structure.ingest.pdf_hierarchy import native_nodes, project_section_nodes


def trace(receipt_path):
    raw = receipt_path.read_bytes()
    document = DoclingDocument.model_validate_json(raw)
    nodes = native_nodes(document)
    body = document.body.self_ref
    projected = project_section_nodes(
        nodes,
        hashlib.sha256(raw).hexdigest(),
        body,
        "descendant",
        section_refs=frozenset({body}),
        selected_items=nodes,
    )
    table_rows = [
        {
            "ref": table.self_ref,
            "parent": table.parent.cref,
            "caption_refs": [ref.cref for ref in table.captions],
            "shape": [table.data.num_rows, table.data.num_cols],
            "cells": [cell.model_dump(mode="json") for cell in table.data.table_cells],
        }
        for table in document.tables
    ]
    pictures = [
        {
            "ref": picture.self_ref,
            "meta": picture.meta.model_dump(mode="json", exclude_none=True) if picture.meta else {},
            "caption_refs": [ref.cref for ref in picture.captions],
            "children": [ref.cref for ref in picture.children],
            "regions": [prov.model_dump(mode="json") for prov in picture.prov],
        }
        for picture in document.pictures
    ]
    text_types = {
        "formula",
        "code",
        "caption",
        "checkbox_selected",
        "checkbox_unselected",
        "fillable_field",
    }
    texts = [
        {
            "ref": item.self_ref,
            "parent": item.parent.cref,
            "label": item.label.value,
            "text": item.text,
            "orig": item.orig,
            "regions": [prov.model_dump(mode="json") for prov in item.prov],
        }
        for item in document.texts
        if item.label.value in text_types
    ]
    (page,) = document.pages.values()
    html_path = receipt_path.with_name(receipt_path.name.removesuffix(".native.json") + ".html")
    replay = parse_chandra_html(
        html_path.read_text(),
        Size(width=page.size.width, height=page.size.height),
        page.page_no,
        normalize_heading_levels=False,
    )
    replay_inventory = [item.label.value for item in native_nodes(replay).values()]
    return {
        "case": html_path.stem,
        "native_labels": dict(Counter(item.label.value for item in nodes.values())),
        "direct_replay_labels": dict(Counter(replay_inventory)),
        "page_size": [page.size.width, page.size.height],
        "stored_page_image_size": [page.image.size.width, page.image.size.height]
        if page.image
        else None,
        "tables": table_rows,
        "pictures": pictures,
        "selected_text_items": texts,
        "projection": projected.text,
        "projected_pieces": [piece.to_wire() for piece in projected.pieces],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    results = [
        trace(path)
        for path in args.inputs
        if path.with_name(path.name.replace(".native.json", ".html")).exists()
    ]
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
