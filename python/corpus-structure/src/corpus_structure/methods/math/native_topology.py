"""Prepared native containment and section scope, shared by mathematical consumers.

The retained native graph supplies identity and parentage; projection pieces supply text
coordinates. No parsing, source rewriting or inferred sibling relationship is performed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Any

from corpus_structure.caches import declare, retained_size
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_source_view import thaw_native


@dataclass(frozen=True)
class NativeTopology:
    root: str
    order: Mapping[str, int]
    chains: Mapping[str, tuple[str, ...]]
    section_parents: Mapping[str, str | None]
    ends: Mapping[str, int]
    bounds: Mapping[str, tuple[int, int]]
    projected: Mapping[str, tuple[int, int]]

    def section(self, pointer: str) -> str:
        return self.chains[pointer][0]

    def scope_chain(self, pointer: str, source: str) -> tuple[str, ...]:
        return tuple(f"{source}:section:{section}" for section in self.chains[pointer])


def prepare_native_topology(view: Any) -> NativeTopology:
    return prepare_native_topology_columns(
        root=view.ref.section_pointer,
        text=view.text,
        items=view.items,
        ancestors=view.ancestors,
        pieces=view.pieces,
    )


def _topology_key(*, root: str, text: str, items, ancestors, pieces) -> bytes:
    return sha256(
        canonical_bytes(
            thaw_native(
                dict(
                    root=root,
                    text=text,
                    items=items,
                    ancestors=ancestors,
                    pieces=pieces,
                )
            )
        )
    ).digest()


@declare(
    "native-topology-columns",
    "runtime_bytes",
    key=_topology_key,
    weight=lambda value: retained_size(value),
)
def prepare_native_topology_columns(
    *, root: str, text: str, items, ancestors, pieces
) -> NativeTopology:
    """Use actual native columns and their original root, without a source-view identity."""
    nodes = {item["self_ref"]: item for item in (*ancestors, *items)}
    sections = {
        ref for ref, item in nodes.items() if item.get("label") in {"section", "chapter"}
    } | {root}
    order = {item["self_ref"]: index for index, item in enumerate(items)}
    chains = {}
    for pointer in order:
        cursor = pointer
        seen = set()
        chain = []
        while True:
            if cursor in seen:
                raise ValueError("native section topology contains a parent cycle")
            seen.add(cursor)
            if cursor in sections:
                chain.append(cursor)
            if cursor == root:
                break
            parent = (nodes.get(cursor, {}).get("parent") or {}).get("$ref")
            if parent is None:
                # A direct projection may omit external container nodes. Its admitted view
                # membership still supplies the root section; do not invent inner sections.
                cursor = root
            elif parent not in nodes and parent != root:
                raise ValueError("native section topology has an unavailable parent: " + parent)
            else:
                cursor = parent
        chains[pointer] = tuple(chain)
    chains.setdefault(root, (root,))
    selected_sections = {section for chain in chains.values() for section in chain}
    parents = {
        section: (chains[section][1] if len(chains.get(section, ())) > 1 else None)
        for section in selected_sections
    }
    ends = {
        section: max(
            (index + 1 for pointer, index in order.items() if section in chains[pointer]),
            default=len(order),
        )
        for section in selected_sections
    }
    bounds = {root: (0, len(text))}
    projected = {}
    for piece in pieces:
        pointer = piece.get("item_ref")
        if pointer not in chains or piece["start"] >= piece["end"]:
            continue
        previous = projected.get(pointer)
        projected[pointer] = (
            (piece["start"], piece["end"])
            if previous is None
            else (min(previous[0], piece["start"]), max(previous[1], piece["end"]))
        )
        for section in chains[pointer]:
            previous = bounds.get(section)
            bounds[section] = (
                (piece["start"], piece["end"])
                if previous is None
                else (min(previous[0], piece["start"]), max(previous[1], piece["end"]))
            )
    return NativeTopology(
        root,
        MappingProxyType(order),
        MappingProxyType(chains),
        MappingProxyType(parents),
        MappingProxyType(ends),
        MappingProxyType(bounds),
        MappingProxyType(projected),
    )


def native_topology(view: Any) -> NativeTopology:
    prepared = getattr(view, "topology", None)
    return prepared if prepared is not None else prepare_native_topology(view)
