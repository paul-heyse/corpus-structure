"""Compile input reads from the owned product and partition declarations."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from typing import Literal, cast

from .data_operation_identity import SemanticGraph, canonical_identity
from .data_operation_model import (
    EffectiveKind,
    InputReadProjection,
    PartitionHalo,
    ProjectedCollection,
)
from .data_operation_rules import observed_body_path

_Scope = Literal["whole", "partition", "halo"]


def compile_read_projection(
    raw: dict,
    kind: str,
    kinds: dict[str, EffectiveKind],
    graph: SemanticGraph,
) -> tuple[InputReadProjection, tuple[tuple[str, str], ...]]:
    """Return the compiled specification and its direct observed model references."""
    scope = cast(_Scope, raw["scope"])
    if kinds[kind].category != "class":
        raise ValueError("a read projection requires a declared class")
    layouts = json.loads(kinds[kind].facts).get("collections", {})
    header = tuple(sorted(raw.get("header", ())))
    if len(set(header)) != len(header):
        raise ValueError("read projection header paths must be distinct")
    if any(path.startswith(("$", "/")) or path.partition(".")[0] in layouts for path in header):
        raise ValueError("read projection header paths must name nonpartition fields")

    references: set[tuple[str, str]] = set()
    field_contracts: dict[str, dict] = {}

    def observe(owner: str, paths: tuple[str, ...], role: str) -> None:
        for path in paths:
            *properties, leaf = observed_body_path(kinds, owner, path)
            if any(not kinds[node].complete for node in properties):
                raise ValueError("read projection observes an incomplete property: " + path)
            references.update((role, node) for node in properties)
            references.add((role, leaf))
            for node in properties:
                field_contracts[node] = json.loads(kinds[node].facts)
            # A read of an inline object observes its complete leaf shape. The
            # intermediate traversed records alone contribute no sibling fields.
            if leaf not in field_contracts:
                closure = graph.rooted_record(leaf)
                if any(not kinds[node["id"]].complete for node in closure["nodes"]):
                    raise ValueError("read projection observes an incomplete range: " + path)
                field_contracts[leaf] = {"contract": canonical_identity("kind", closure).key}

    observe(kind, header, "header")
    selections = []
    collection_contracts = {}
    for entry in sorted(raw.get("collections", ()), key=lambda row: row["name"]):
        name = entry["name"]
        if name in collection_contracts:
            raise ValueError("read projection collection names must be distinct")
        layout = layouts.get(name)
        if layout is None or layout["unit"] != "partitioned":
            raise ValueError("read projection requires a declared partition collection: " + name)
        groups = tuple(sorted(entry.get("groups", ())))
        if len(set(groups)) != len(groups) or not set(groups) <= layout["field_groups"].keys():
            raise ValueError("read projection groups must be distinct declared groups: " + name)
        selection = ProjectedCollection(
            name,
            groups,
            entry.get("membership", False),
            entry.get("order", False),
            entry.get("placement", False),
        )
        if not any((groups, selection.membership, selection.order, selection.placement)):
            raise ValueError(
                "read projection collection must observe at least one premise: " + name
            )
        selections.append(selection)

        property_id = kind + "/property/" + name
        property_facts = json.loads(kinds[property_id].facts)
        item_kind = property_facts["range"]
        references.add((name, property_id))
        selected_paths = {group: tuple(layout["field_groups"][group]) for group in groups}
        for group, paths in selected_paths.items():
            observe(item_kind, paths, name + "/" + group)
        contract = {
            "property": {
                key: value for key, value in property_facts.items() if key != "collection"
            },
            "partition_key": layout["partition_key"],
            "groups": selected_paths,
        }
        if groups or selection.order:
            # Field-group digests commit to rows in canonical item order.
            contract["item_order"] = layout["item_order"]
            observe(item_kind, tuple(layout["item_order"]), name + "/item-order")
        if selection.membership:
            contract["address"] = layout["address"]
            observe(item_kind, tuple(layout["address"]), name + "/membership")
        collection_contracts[name] = contract

    if not (header or selections):
        raise ValueError("read projection must observe at least one premise")
    if scope != "whole" and not selections:
        raise ValueError("partition or halo read projection requires a partition collection")
    halo = None
    if scope == "halo":
        neighbourhood = raw.get("halo")
        if neighbourhood is None or not any(neighbourhood.values()):
            raise ValueError("halo read projection requires a nonempty adjacent partition window")
        if not all(selection.order for selection in selections):
            raise ValueError("halo read projection must observe partition order")
        halo = PartitionHalo(neighbourhood["before"], neighbourhood["after"])
    elif "halo" in raw:
        raise ValueError("a partition window requires halo scope")

    projection = InputReadProjection(1, scope, header, tuple(selections), halo, "")
    specification = asdict(projection)
    specification.pop("fingerprint")
    identity = canonical_identity(
        "input-read-projection",
        {
            "input_kind": kind,
            "specification": specification,
            "collections": collection_contracts,
            "fields": field_contracts,
        },
    )
    return replace(projection, fingerprint=identity.key), tuple(sorted(references))
