"""Bulk removal over public Docling models, retaining surviving object identities.

Docling 2.105.0's public deletion scans the deletion list for every node/reference
and sums that list again while renumbering. Selection needs one document-wide
removal, so build the subtree closure and surviving collection ranks once.
Only typed references and node self references change; source text, provenance,
metadata strings and pages retain their meaning.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import Any

from docling_core.types.doc.document import DoclingDocument, GraphCell, NodeItem, RefItem
from pydantic import BaseModel


def remove_pdf_subtrees(document: DoclingDocument, nodes: Sequence[NodeItem]) -> None:
    """Remove containment subtrees and rebase surviving typed edges in place.

    List edges to removed nodes disappear. The public graph-cell optional item
    reference becomes None. Other scalar references into a removed subtree
    refuse before mutation: a required rich-cell target or surviving orphan
    cannot acquire another node's identity merely by index renumbering.
    """
    if not nodes:
        return
    collections: dict[str, list[NodeItem]] = {}
    by_ref: dict[str, NodeItem] = {}
    # Use declared Pydantic fields, excluding computed fields and private state.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        for name in type(document).model_fields:
            value = getattr(document, name)
            if isinstance(value, NodeItem):
                by_ref[value.self_ref] = value
            elif isinstance(value, list) and value and all(isinstance(n, NodeItem) for n in value):
                collections[name] = value
                for index, node in enumerate(value):
                    expected = f"#/{name}/{index}"
                    if node.self_ref != expected or expected in by_ref:
                        raise ValueError(
                            f"bulk PDF removal: inconsistent node identity {node.self_ref}, "
                            f"expected {expected}"
                        )
                    by_ref[expected] = node

    requested = {node.self_ref for node in nodes}
    if len(requested) != len(nodes):
        raise ValueError("bulk PDF removal: duplicate requested node")
    for node in nodes:
        if by_ref.get(node.self_ref) is not node or node.self_ref in {"#/body", "#/furniture"}:
            raise ValueError(
                "bulk PDF removal: requested node is not a removable document item: "
                f"{node.self_ref}"
            )

    removed: set[str] = set()
    pending = list(requested)
    while pending:
        pointer = pending.pop()
        if pointer in removed:
            continue
        item = by_ref.get(pointer)
        if item is None:
            raise ValueError(f"bulk PDF removal: missing containment target {pointer}")
        removed.add(pointer)
        pending.extend(ref.cref for ref in item.children)

    relocated = {pointer: pointer for pointer in by_ref if pointer not in removed}
    survivors: list[tuple[list[NodeItem], list[NodeItem]]] = []
    for name, items in collections.items():
        retained = [node for node in items if node.self_ref not in removed]
        survivors.append((items, retained))
        for rank, node in enumerate(retained):
            relocated[node.self_ref] = f"#/{name}/{rank}"

    # Preflight all typed edges before changing the graph. A shared RefItem can
    # occur repeatedly: record its original target once, then mutate it once.
    ref_updates: dict[int, tuple[RefItem, str]] = {}
    list_updates: list[tuple[list[Any], list[Any]]] = []
    optional_updates: list[GraphCell] = []
    visited: set[int] = set()

    def retain_reference(ref: RefItem, path: str) -> None:
        target = relocated.get(ref.cref)
        if target is None:
            # Non-node references (e.g. a page reference) retain their pointer,
            # but a dangling pointer is never silently passed through.
            try:
                ref.resolve(document)
            except (
                AttributeError,
                IndexError,
                KeyError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise ValueError(
                    f"bulk PDF removal: unresolved typed reference {path} -> {ref.cref}"
                ) from exc
            target = ref.cref
        ref_updates[id(ref)] = (ref, target)

    def visit(value: Any, path: str) -> None:
        if isinstance(value, RefItem):
            if value.cref in removed:
                raise ValueError(
                    f"bulk PDF removal: unsupported scalar reference {path} -> removed {value.cref}"
                )
            retain_reference(value, path)
            return
        if not isinstance(value, (BaseModel, list, tuple, dict)) or id(value) in visited:
            return
        visited.add(id(value))
        if isinstance(value, NodeItem) and value.self_ref in removed:
            return
        if isinstance(value, BaseModel):
            for name in type(value).model_fields:
                child = getattr(value, name)
                if isinstance(child, RefItem) and child.cref in removed:
                    if isinstance(value, GraphCell) and name == "item_ref":
                        optional_updates.append(value)
                    else:
                        raise ValueError(
                            f"bulk PDF removal: unsupported scalar reference {path}.{name} "
                            f"-> removed {child.cref}"
                        )
                else:
                    visit(child, f"{path}.{name}")
        elif isinstance(value, list):
            retained = [
                child
                for child in value
                if not (isinstance(child, RefItem) and child.cref in removed)
            ]
            if len(retained) != len(value):
                list_updates.append((value, retained))
            for index, child in enumerate(retained):
                visit(child, f"{path}[{index}]")
        elif isinstance(value, tuple):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
        else:
            for key, child in value.items():
                visit(child, f"{path}[{key!r}]")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        visit(document, "document")

    for items, retained in survivors:
        items[:] = retained
    for items, retained in list_updates:
        items[:] = retained
    for cell in optional_updates:
        cell.item_ref = None
    for ref, target in ref_updates.values():
        ref.cref = target
    for pointer, node in by_ref.items():
        if pointer not in removed:
            node.self_ref = relocated[pointer]

    validate = document.validate_document
    if not callable(validate):
        raise TypeError("native Docling document validator is not callable")
    validate()
    if not document.validate_tree(document.body):
        raise ValueError("bulk PDF removal: resulting native Docling tree is invalid")
