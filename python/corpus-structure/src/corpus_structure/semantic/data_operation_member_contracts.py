"""Derive typed product-member contracts from the effective nominal property graph."""

from __future__ import annotations

import json
from typing import Never

from .data_operation_kind_refinements import MissingNominalEndpoint, nominal_inheritance_graph
from .data_operation_model import EffectiveDataOperationModel, EffectiveKind
from .graph_topology import rooted_closure
from .types import Diagnostic, PreparationError


def derive_member_kinds(
    model: EffectiveDataOperationModel, container_kind_id: str
) -> tuple[str, ...]:
    """Resolve Container.members -> Packet.body and declared concrete subtypes.

    An ordinary collection property is not automatically a native member packet.
    Captured closed JSON records have the same nominal packet-body authority as
    LinkML records. Generic JSON and ambiguous/open unions establish no authority.
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
        if "json_schema" in json.loads(root.facts):
            return json_family(root)
        try:
            graph = nominal_inheritance_graph(model)
        except MissingNominalEndpoint as error:
            refuse(
                root.semantic_id,
                "member projection requires a complete nominal kind: " + str(error),
            )
        except ValueError as error:
            refuse(root.semantic_id, str(error))
        found = rooted_closure(graph, (root.semantic_id,))
        for kind_id in found:
            owned(kind_id)
        return tuple(
            owned(kind_id)
            for kind_id in sorted(found)
            if not json.loads(owned(kind_id).facts).get("abstract", False)
        )

    def closed_record(kind: EffectiveKind) -> None:
        facts = json.loads(kind.facts)
        schema = facts.get("json_schema", {})
        if (
            not facts.get("nominal_namespace")
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
            or any(key in schema for key in ("allOf", "anyOf", "oneOf", "$ref"))
        ):
            refuse(kind.semantic_id, "member projection requires a captured closed nominal record")

    def json_family(root: EffectiveKind, active: frozenset[str] = frozenset()) -> tuple[EffectiveKind, ...]:
        from .data_operation_wire import schema_closure

        if root.semantic_id in active:
            refuse(root.semantic_id, "recursive member body union has no finite nominal variants")
        facts = json.loads(root.facts)
        schema = facts["json_schema"]
        alternatives = schema.get("oneOf", schema.get("anyOf"))
        if alternatives is None:
            closed_record(root)
            return (root,)
        if (
            not isinstance(alternatives, list) or not alternatives
            or not facts.get("nominal_namespace")
            or set(schema) - {"$schema", "$id", "title", "description", "definitions", "anyOf", "oneOf"}
            or ("oneOf" in schema and "anyOf" in schema)
        ):
            refuse(root.semantic_id, "member union requires explicit finite nominal alternatives")
        namespace = facts["nominal_namespace"]
        source_owners = {origin.source for origin in root.origins}
        if len(source_owners) != 1:
            refuse(root.semantic_id, "member union requires one captured source owner")
        definitions = schema.get("definitions", {})
        variants = {}
        for alternative in alternatives:
            if not isinstance(alternative, dict) or set(alternative) != {"$ref"}:
                refuse(root.semantic_id, "member union alternatives require captured nominal references")
            reference = alternative["$ref"]
            if not isinstance(reference, str) or not reference.startswith("#/definitions/"):
                refuse(root.semantic_id, "member union reference is not a closed local definition")
            name = reference.removeprefix("#/definitions/")
            target = owned(namespace + name)
            target_facts = json.loads(target.facts)
            if (
                name not in definitions
                or target_facts.get("nominal_namespace") != namespace
                or source_owners != {origin.source for origin in target.origins}
                or target_facts.get("json_schema") != schema_closure(definitions[name], definitions)
            ):
                refuse(root.semantic_id, "member union reference differs from its captured nominal owner")
            for leaf in json_family(target, active | {root.semantic_id}):
                if leaf.semantic_id in variants:
                    refuse(root.semantic_id, "member union repeats a nominal alternative")
                variants[leaf.semantic_id] = leaf
        result = tuple(variants[key] for key in sorted(variants))
        if len(result) > 1:
            schemas = [json.loads(kind.facts)["json_schema"] for kind in result]
            required = set.intersection(*(set(schema.get("required", ())) for schema in schemas))

            def disjoint(name):
                values = []
                for schema in schemas:
                    prop = schema["properties"][name]
                    literals = prop.get("enum", [prop["const"]] if "const" in prop else [])
                    if not isinstance(literals, list) or not literals:
                        return False
                    if any(value == other for previous in values for value in previous for other in literals):
                        return False
                    values.append(literals)
                return True

            if not any(disjoint(name) for name in required):
                refuse(root.semantic_id, "member union requires disjoint required literal discriminators")
        return result

    container = owned(container_kind_id)
    members = property_kind(container_kind_id, "members")
    if members is None or json.loads(members.facts).get("multivalued") is not True:
        return ()
    if "json_schema" in json.loads(container.facts):
        if not json.loads(container.facts).get("nominal_namespace"):
            return ()
        closed_record(container)
    packet = range_kind(members)
    if packet.category != "class":
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
        if nominal.semantic_id == "primitive:json":
            refuse(body.semantic_id, "generic JSON body cannot establish a nominal member contract")
        variants = concrete_family(nominal)
        if not variants:
            refuse(nominal.semantic_id, "member body has no declared concrete variants")
        member_ids.update(variant.semantic_id for variant in variants)
    return tuple(sorted(member_ids))
