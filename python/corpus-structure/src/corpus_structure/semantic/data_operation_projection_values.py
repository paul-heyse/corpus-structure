"""Whole-input projection materialization and digest over admitted metadata."""

from __future__ import annotations

from collections.abc import Mapping

from .data_operation_identity import canonical_identity
from .data_operation_model import InputReadProjection, ProjectedCollection
from .identity import canonical_bytes


def _path_tree(paths):
    tree = {}
    for path in sorted(set(paths)):
        *parents, field = path.split(".")
        level = tree
        for parent in parents:
            branch = level.setdefault(parent, {})
            if branch is None:
                break
            level = branch
        else:
            level[field] = None
    return tree


def _selected_fields(raw, tree, *, tagged=False):
    if tagged:
        if not isinstance(raw, list) or len(raw) != 2 or raw[0] != "mapping":
            return {}
        values = {}
        for name, value in raw[1]:
            if name in tree:
                if name in values:
                    raise ValueError("projected mapping has a repeated field: " + name)
                values[name] = value
    else:
        values = raw if isinstance(raw, Mapping) else {}
    selected = {}
    for field, children in tree.items():
        if field not in values:
            continue
        if children is None:
            selected[field] = values[field]
            continue
        nested = _selected_fields(values[field], children, tagged=tagged)
        if nested:
            selected[field] = ["mapping", _tagged_pairs(nested)] if tagged else nested
    return selected


def _tagged_pairs(values):
    return [[name, value] for name, value in sorted(values.items())]


def _select_partition_facts(packet, selection: ProjectedCollection) -> dict:
    facts = {}
    if selection.membership:
        facts["partition_key"] = packet["partition_key"]
    if selection.order:
        facts["ordinal"] = packet["ordinal"]
    if selection.placement:
        facts["placement"] = {field: packet["placement"][field] for field in ("start", "end")}
    return facts


def _whole_input(projection, header, partitions, project_partition):
    if projection.scope != "whole":
        raise ValueError("whole-input materialization requires a whole read projection")
    selection_by_name = {collection.name: collection for collection in projection.collections}
    collections = {name: [] for name in selection_by_name}
    for packet in partitions:
        name = packet["collection"]
        if name in collections:
            selection = selection_by_name[name]
            collections[name].append(
                _select_partition_facts(packet, selection) | project_partition(packet, selection)
            )

    for name, rows in collections.items():
        selection = selection_by_name[name]
        if selection.order:
            rows.sort(key=lambda item: item["ordinal"])
        elif selection.membership:
            rows.sort(key=lambda item: item["partition_key"])
        else:
            # A stable presentation must not expose undeclared keys or source order.
            rows.sort(key=canonical_bytes)
    return {
        "header": _selected_fields(header, _path_tree(projection.header)),
        "collections": collections,
    }


def materialize_whole_input_projection(
    projection: InputReadProjection, layouts, header, packets
) -> dict:
    """Expose only declared data from an already admitted whole partition envelope."""
    trees = {
        selection.name: _path_tree(
            path
            for group in selection.groups
            for path in layouts[selection.name]["field_groups"][group]
        )
        for selection in projection.collections
        if selection.groups
    }

    def project_partition(packet, selection):
        if not selection.groups:
            return {}
        body = packet["body"]
        if not isinstance(body, list) or len(body) != 2 or body[0] != "sequence":
            raise ValueError("projected partition requires its admitted item sequence")
        rows = []
        for item in body[1]:
            if not isinstance(item, list) or len(item) != 2 or item[0] != "mapping":
                raise ValueError("projected partition requires its admitted item mappings")
            fields = _selected_fields(item, trees[selection.name], tagged=True)
            rows.append(["mapping", _tagged_pairs(fields)])
        return {"body": ["sequence", rows]}

    return _whole_input(projection, header, packets, project_partition)


def input_projection_digest(projection: InputReadProjection, header, partitions) -> str:
    """Hash whole-input premises from authenticated header and stored group digests.

    Partition metadata has collection, selected address/ordinal/placement facts,
    and group digests. This helper neither needs nor consults partition bodies.
    """

    def project_partition(packet, selection):
        if not selection.groups:
            return {}
        return {"groups": {name: packet["group_digests"][name] for name in selection.groups}}

    premise = _whole_input(projection, header, partitions, project_partition)
    return canonical_identity(
        "input-projection-value", {"projection": projection.fingerprint, **premise}
    ).key
