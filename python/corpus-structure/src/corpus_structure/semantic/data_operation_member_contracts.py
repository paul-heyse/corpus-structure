"""Derive typed product-member contracts from the effective nominal property graph."""

from __future__ import annotations

import json
from typing import Never

from .data_operation_model import EffectiveDataOperationModel, EffectiveKind
from .types import Diagnostic, PreparationError


def derive_member_kinds(
    model: EffectiveDataOperationModel, container_kind_id: str
) -> tuple[str, ...]:
    """Resolve Container.members -> Packet.body and declared concrete subtypes.

    An ordinary collection property is not automatically a native member packet.
    Generic JSONSchema records have no nominal packet-body authority and return
    no member contracts. Actual nonempty native member projection then refuses.
    No kind names, handwritten registries or ambient Python imports supply types.
    """
    kinds = {kind.semantic_id: kind for kind in model.kinds}

    def refuse(location: str, message: str) -> Never:
        raise PreparationError((Diagnostic("data_operation_member_contract", location, message),))

    def owned(kind_id: str) -> EffectiveKind:
        kind = kinds.get(kind_id)
        if kind is None or not kind.complete:
            refuse(kind_id, "member projection requires a complete nominal kind")
        return kind

    def property_kind(owner: str, name: str) -> EffectiveKind | None:
        matches = set()
        for edge in model.edges:
            if edge.source != owner or edge.relation != "property":
                continue
            candidate = owned(edge.target)
            facts = json.loads(candidate.facts)
            if (
                edge.role == name
                or facts.get("name") == name
                or candidate.semantic_id == owner + "/property/" + name
            ):
                if candidate.category != "property":
                    refuse(edge.target, "member field edge does not identify a property")
                matches.add(candidate.semantic_id)
        if len(matches) > 1:
            refuse(owner + "/" + name, "member field has ambiguous effective property owners")
        return owned(next(iter(matches))) if matches else None

    def range_kind(prop: EffectiveKind) -> EffectiveKind:
        target = json.loads(prop.facts).get("range")
        if not isinstance(target, str) or not target:
            refuse(prop.semantic_id, "member field has no resolved nominal range")
        ranges = {
            edge.target
            for edge in model.edges
            if edge.source == prop.semantic_id and edge.relation == "range"
        }
        if ranges != {target}:
            refuse(prop.semantic_id, "member field range differs from its effective graph")
        return owned(target)

    def concrete_family(root: EffectiveKind) -> tuple[EffectiveKind, ...]:
        found, pending = set(), [root.semantic_id]
        while pending:
            kind_id = pending.pop()
            if kind_id in found:
                continue
            kind = owned(kind_id)
            if kind.category != root.category:
                refuse(kind_id, "declared member subtype changes the nominal kind category")
            found.add(kind_id)
            pending.extend(
                edge.source
                for edge in model.edges
                if edge.relation == "inherits" and edge.target == kind_id
            )
        return tuple(
            owned(kind_id)
            for kind_id in sorted(found)
            if not json.loads(owned(kind_id).facts).get("abstract", False)
        )

    container = owned(container_kind_id)
    if "json_schema" in json.loads(container.facts):
        return ()
    members = property_kind(container_kind_id, "members")
    if members is None or json.loads(members.facts).get("multivalued") is not True:
        return ()
    packet = range_kind(members)
    if packet.category != "class" or "json_schema" in json.loads(packet.facts):
        return ()
    packets = concrete_family(packet)
    if not packets:
        refuse(packet.semantic_id, "member packet has no declared concrete variants")
    bodies = tuple(property_kind(candidate.semantic_id, "body") for candidate in packets)
    if not any(body is not None for body in bodies):
        return ()
    if any(body is None for body in bodies):
        refuse(packet.semantic_id, "a declared packet variant has no effective body property")
    member_ids = set()
    for body in bodies:
        assert body is not None
        if json.loads(body.facts).get("multivalued", False):
            refuse(body.semantic_id, "member packet body must have one nominal range")
        nominal = range_kind(body)
        if nominal.semantic_id == "primitive:json" or "json_schema" in json.loads(nominal.facts):
            refuse(body.semantic_id, "generic JSON body cannot establish a nominal member contract")
        variants = concrete_family(nominal)
        if not variants:
            refuse(nominal.semantic_id, "member body has no declared concrete variants")
        member_ids.update(variant.semantic_id for variant in variants)
    return tuple(sorted(member_ids))
