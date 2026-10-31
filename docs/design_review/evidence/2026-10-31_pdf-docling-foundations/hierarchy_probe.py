"""I04 native section-group derivation over a pinned converted document, no inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from docling_core.types.doc import ContentLayer, DocItemLabel, DoclingDocument, GroupLabel

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "raw/heron-20-45.document.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def nodes(doc):
    return [(node.self_ref, node) for name in ("texts", "groups", "tables", "pictures",
        "key_value_items", "form_items", "field_regions", "field_items")
        for node in getattr(doc, name) if hasattr(node, "self_ref")]


def content_order(doc):
    return [node.self_ref for node, _ in doc.iterate_items(traverse_pictures=True, included_content_layers=set(ContentLayer))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path, default=SOURCE)
    args = parser.parse_args()
    original_bytes = args.document.read_bytes()
    (HERE / "raw/hierarchy-input.document.json").write_bytes(original_bytes)
    original_hash = digest(original_bytes)
    source = DoclingDocument.model_validate_json(original_bytes)
    source.validate_document()
    source_order = content_order(source)
    source_nodes = dict(nodes(source))
    source_export = source.export_to_dict()
    original_root_refs = [ref.cref for ref in source.body.children]
    headings = [node for node in source_nodes.values() if node.label == DocItemLabel.SECTION_HEADER]
    section_groups_before = [node for node in source.groups if node.label == GroupLabel.SECTION]
    derived = DoclingDocument.model_validate_json(original_bytes)
    derived.body.children = []
    stack = []
    section_basis = []
    for ref in original_root_refs:
        node = source_nodes[ref]
        target = node.get_ref().resolve(derived)
        if target.label == DocItemLabel.SECTION_HEADER:
            level = target.level
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1] if stack else derived.body
            group = derived.add_group(label=GroupLabel.SECTION, name=target.text, parent=parent)
            stack.append((level, group))
            section_basis.append({"group": group.self_ref, "source_heading": ref,
                                  "heading_level": level, "name": target.text,
                                  "parent": group.parent.cref,
                                  "basis": "inferred native heading level; organizational container, not new source text"})
        parent = stack[-1][1] if stack else derived.body
        target.parent = parent.get_ref()
        parent.children.append(target.get_ref())
    derived.validate_document()
    after_order = content_order(derived)
    assert after_order == source_order
    after_nodes = dict(nodes(derived))
    assert set(source_nodes) <= set(after_nodes)
    assert set(source.pages) == set(derived.pages)
    assert source_export["pages"] == derived.export_to_dict()["pages"]
    assert len(source.texts) == len(derived.texts)
    assert len(source.tables) == len(derived.tables)
    assert len(source.pictures) == len(derived.pictures)
    assert source.body.self_ref == derived.body.self_ref
    for ref, node in source_nodes.items():
        before = node.model_dump(mode="json")
        after = after_nodes[ref].model_dump(mode="json")
        before.pop("parent", None)
        after.pop("parent", None)
        assert before == after, ref
    root_sections = [s for s in section_basis if s["heading_level"] == 1]
    assert [s["name"] for s in root_sections] == ["1.1: Sets", "1.2: Functions"]
    assert all(s["parent"] == "#/body" for s in root_sections)
    derived_bytes = json.dumps(derived.export_to_dict(), ensure_ascii=False, indent=2).encode()
    dest = HERE / "raw/hierarchy-derived.document.json"
    dest.write_bytes(derived_bytes)
    restored = DoclingDocument.model_validate_json(derived_bytes)
    restored.validate_document()
    assert content_order(restored) == source_order
    assert args.document.read_bytes() == original_bytes
    mappings = [{"source_document_sha256": original_hash, "source_ref": ref,
                 "target_document_sha256": digest(derived_bytes), "target_ref": ref}
                for ref in source_nodes]
    result = {"outcome": "passed", "scope": "actual Heron conversion of physical pages 20-45; organizational hierarchy, no source-fidelity or whole-book claim",
              "source": str(args.document), "source_sha256": original_hash,
              "derived_sha256": digest(derived_bytes),
              "native_page_numbers": sorted(source.pages),
              "native_heading_count": len(headings),
              "native_section_group_count": len(section_groups_before),
              "native_root_heading_count": sum(node.parent is not None and node.parent.cref == "#/body" for node in headings),
              "derived_section_group_count": len(section_basis),
              "original_node_count": len(source_nodes),
              "original_content_order_preserved": True,
              "original_source_file_unchanged": True,
              "original_page_geometry_preserved": True,
              "root_sections": root_sections,
              "section_basis": section_basis,
              "old_to_derived_references": mappings,
              "selection_semantics": {"direct": "direct child content or pre-existing native groups owned by the selected section, excluding newly derived child sections",
                                      "descendant": "ordered traversal including child sections; caller explicitly selects this policy",
                                      "rule": "section-level extraction uses non-overlapping selected units; ancestor context is not an additional extraction pass"}}
    (HERE / "raw/hierarchy-results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in {"section_basis", "old_to_derived_references"}}, indent=2))


if __name__ == "__main__":
    main()
