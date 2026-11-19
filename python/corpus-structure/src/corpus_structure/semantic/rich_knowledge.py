"""Current rich knowledge kernels over explicit semantic sources and closed universes.

Source proposal addresses remain separate from resolved domain identity. These pure
values grant no accepted standing; native admission owns that effect.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

from .data_operation_model import SubjectContext
from .data_operation_values import semantic_value
from .identity import canonical_bytes
from .reference_positions import LocatedReference
from .types import ClassDefinition, PreparedRelease, PropertyDefinition


@dataclass(frozen=True)
class RichEntitySource:
    """One actually selected source proposal product, prepared inside an invocation."""

    reference: str
    context: SubjectContext
    entities: tuple[dict, ...]
    exclusions: tuple[dict, ...]
    macros: Mapping[str, Any]

    def __post_init__(self):
        address = json.loads(self.reference)
        if (
            not isinstance(address, list)
            or len(address) != 2
            or not isinstance(address[0], str)
            or not address[0]
            or (address[1] is not None and (not isinstance(address[1], str) or not address[1]))
            or canonical_bytes(address).decode() != self.reference
        ):
            raise ValueError("rich source requires its exact semantic product/member address")


@dataclass(frozen=True)
class RichKnownEntityIdentity:
    """One actual class's key/label basis, without merging property namespaces."""

    class_iri: str
    fields: Mapping[str, Any]
    source_context: SubjectContext | None
    label: str | None = None


@dataclass(frozen=True)
class RichKnownEntity:
    identities: tuple[RichKnownEntityIdentity, ...]


@dataclass(frozen=True)
class RichEntityResolution:
    source_reference: str
    local_id: str
    entity_id: str
    basis: Literal["declared_key", "global_label", "source_local"]
    outcome: Literal["resolved", "incomplete_key", "ambiguous_anchor", "ungrounded_cycle"]
    candidate_identity_keys: tuple[str, ...]
    matched_entity_ids: tuple[str, ...]
    dependencies: tuple[str, ...]


class RichIdentityConflict(ValueError):
    def __init__(self, source_reference, exclusion_id, left, right, entity_id):
        self.source_reference, self.exclusion_id = source_reference, exclusion_id
        self.left, self.right, self.entity_id = left, right, entity_id
        super().__init__(
            f"identity exclusion {exclusion_id} contradicts mandatory identity {entity_id}"
        )


def _identity(tag, value):
    return tag + ":" + sha256(canonical_bytes(semantic_value(value))).hexdigest()


def _range(prepared: PreparedRelease, name: str) -> str:
    primitives = {
        "string",
        "integer",
        "decimal",
        "boolean",
        "date",
        "datetime",
        "float",
        "double",
        "uri",
        "uriorcurie",
    }
    definitions = {
        row.name: json.loads(row.body) for row in prepared.registry_rows if row.kind == "type"
    }
    path = set()
    while name not in primitives:
        if name in path or name not in definitions:
            raise ValueError(f"rich property has an unsupported primitive range {name}")
        path.add(name)
        current = definitions[name]
        name = current.get("typeof") or current.get("base") or "string"
        name = {"str": "string", "int": "integer", "bool": "boolean", "Decimal": "decimal"}.get(
            name, name
        )
    return name


def rich_property_value(
    prepared: PreparedRelease,
    definition: ClassDefinition,
    prop: PropertyDefinition,
    value: Mapping[str, Any],
    entities: Mapping[str, str] | Callable[[LocatedReference], str],
    claims: Mapping[str, str] | None = None,
) -> Any:
    """Use the actual declared property boundary and compiled reference positions."""
    from .proposals import _property_value
    from .reference_positions import class_reference_value, rewrite_references

    classes = prepared.index.definitions
    if prop.range in classes:
        if not prop.inlined:
            reference = class_reference_value(prepared, value)
            raw = (
                entities(
                    LocatedReference("class", reference, prop.range, (definition.name, prop.name))
                )
                if callable(entities)
                else entities.get(reference, reference)
            )
        else:
            raw = rewrite_references(
                prepared, prop.range, value, classes=entities, facts=claims, collision="equal"
            )
    else:
        native_range = (
            "string"
            if prop.range in {v.enum for v in prepared.vocabularies}
            else _range(prepared, prop.range)
        )
        raw = _property_value(value, native_range)
        if prop.reference_role == "fact" and claims is not None:
            if raw not in claims:
                raise ValueError("rich property names an unavailable source claim")
            raw = claims[raw]
    return prepared.property_adapter(
        definition.name, prop.name, item=prop.multivalued
    ).validate_python(raw, strict=True)


def resolve_rich_entities(
    prepared: PreparedRelease,
    *,
    entity_contracts: Mapping[str, str],
    universe: SubjectContext,
    sources: tuple[RichEntitySource, ...],
    known: Mapping[str, RichKnownEntity],
) -> tuple[dict[str, dict[str, str]], tuple[RichEntityResolution, ...]]:
    """Resolve exact keys and explicit global labels without source/reading relabelling.

    Kind contracts and the declared knowledge subject scope identity. Local IDs are
    qualified by the actual selected product reference, independent of arrival order.
    Missing keys and ungrounded key cycles retain their source-qualified identity.
    """
    from corpus_structure.semantic.source_types import CaseRule

    from .alias_policy import label_normalizer
    from .expression_context import bind_expression_context
    from .identity_resolution import constrained_label_groups
    from .unicode_identity import identity_casefold

    if len({source.reference for source in sources}) != len(sources):
        raise ValueError("rich identity requires an explicit universe and unique selected sources")
    if any(source.context.project_id != universe.project_id for source in sources):
        raise ValueError("rich source context differs from its actual knowledge project")
    universe_meaning = universe.identity_record
    by_iri = prepared.index.by_iri
    meta = {
        row.name: json.loads(row.body)
        for row in prepared.registry_rows
        if row.kind == "operation_class"
    }
    normalize = label_normalizer(prepared)
    mappings, entries, exclusions = {}, [], []
    for source in sources:
        if len({entity["id"] for entity in source.entities}) != len(source.entities):
            raise ValueError("rich source repeats local entity identity")
        mappings[source.reference] = {
            entity["id"]: _identity(
                "entity",
                [
                    universe_meaning,
                    entity_contracts[entity["class_iri"]],
                    source.reference,
                    entity["id"],
                ],
            )
            for entity in source.entities
        }
        entries.extend((source, entity, by_iri[entity["class_iri"]]) for entity in source.entities)
        for exclusion in source.exclusions:
            if not any(
                e["role"] == "primary" and e.get("outcome") == "located"
                for e in exclusion["evidence"]
            ):
                continue

            def endpoint(value, source=source):
                return (
                    ("known", value["target"])
                    if value["kind"] == "known"
                    else (source.reference, value["target"])
                )

            exclusions.append(
                (
                    source.reference,
                    exclusion,
                    endpoint(exclusion["left"]),
                    endpoint(exclusion["right"]),
                )
            )

    def groups(definition):
        return tuple(
            group for group in definition.identity_groups if group != definition.identity_slots
        )

    def label_key(definition, label):
        case = (
            CaseRule.FOLD
            if meta.get(definition.name, {}).get("cs:case") == "casefold"
            else CaseRule.PRESERVE
        )
        return definition.iri, normalize(label, definition.iri, case)

    def global_class(definition):
        return meta.get(definition.name, {}).get("cs:scope") == "global"

    def keys(definition, values, source_context):
        properties = prepared.index.properties_by_class[definition.name]
        scope = [universe_meaning, entity_contracts[definition.iri]]
        if not global_class(definition):
            if source_context is None or source_context.original_source is None:
                raise ValueError("local rich keys require their actual source-qualified context")
            if source_context.project_id != universe.project_id:
                raise ValueError("local rich key context differs from its knowledge project")
            scope.append({"source_context": source_context.identity_record})
        return tuple(
            _identity(
                "entity",
                [
                    *scope,
                    [
                        [
                            name,
                            identity_casefold(values[name])
                            if properties[name].case_policy == "casefold"
                            and isinstance(values[name], str)
                            else values[name],
                        ]
                        for name in group
                    ],
                ],
            )
            for group in groups(definition)
        )

    soft_groups, soft_ids, soft_resolved = {}, {}, {}
    for source, entity, definition in entries:
        if (
            not groups(definition)
            and meta.get(definition.name, {}).get("cs:scope") == "global"
            and entity.get("label")
        ):
            node = source.reference, entity["id"]
            soft_groups.setdefault(label_key(definition, entity["label"]), set()).add(node)
            soft_ids[node] = mappings[source.reference][entity["id"]]
    declared_keys = {}
    for identity, entity in known.items():
        for basis in entity.identities:
            definition = by_iri[basis.class_iri]
            if global_class(definition) and basis.source_context is not None:
                raise ValueError("global rich identity cannot acquire a source-local key basis")
            if groups(definition):
                # An explicit authored local ID has no documentary key scope.
                # Preserve that ID without treating its bare key as a global anchor.
                if not global_class(definition) and basis.source_context is None:
                    continue
                if all(all(name in basis.fields for name in group) for group in groups(definition)):
                    for key in keys(definition, basis.fields, basis.source_context):
                        if key in declared_keys and declared_keys[key] != identity:
                            raise ValueError(
                                "known universe contains incompatible declared entity keys"
                            )
                        declared_keys[key] = identity
            elif meta.get(definition.name, {}).get("cs:scope") == "global" and basis.label:
                node = "known", identity
                soft_groups.setdefault(label_key(definition, basis.label), set()).add(node)
                soft_ids[node] = identity
    for (iri, label), members in soft_groups.items():
        anchors = {node for node in members if node[0] == "known"}
        forbidden = [
            (left, right)
            for _, _, left, right in exclusions
            if left in members and right in members
        ]
        if not forbidden and len(anchors) <= 1:
            canonical = (
                soft_ids[next(iter(anchors))]
                if anchors
                else _identity("entity", [universe_meaning, entity_contracts[iri], "label", label])
            )
            soft_resolved.update((node, canonical) for node in members)
        else:
            partitions = (
                constrained_label_groups(members, forbidden, anchors)
                if len(anchors) <= 1
                else tuple(frozenset((node,)) for node in sorted(members))
            )
            for group in partitions:
                anchored = group & anchors
                canonical = (
                    soft_ids[next(iter(anchored))]
                    if anchored
                    else min(soft_ids[node] for node in group)
                )
                soft_resolved.update((node, canonical) for node in group)
    pending, resolved, decisions = list(entries), set(), {}
    while pending:
        remaining, progress = [], False
        for source, entity, definition in pending:
            mapping, attrs, dependencies = mappings[source.reference], {}, []
            for attribute in entity.get("attributes", ()):
                prop = next(
                    prop for prop in definition.properties if prop.iri == attribute["predicate"]
                )
                value = bind_expression_context(attribute["value"], source.macros)
                if (
                    any(prop.name in group for group in groups(definition))
                    and value.get("kind") == "entity"
                    and value.get("target") in mapping
                ):
                    dependencies.append(value["target"])
                attrs[prop.name] = rich_property_value(prepared, definition, prop, value, mapping)
            if (
                entity.get("scope") is not None
                and "scope_locator" in prepared.index.properties_by_class[definition.name]
            ):
                attrs.setdefault("scope_locator", entity["scope"]["locator"])
            basis = (
                "declared_key"
                if groups(definition)
                else "global_label"
                if meta.get(definition.name, {}).get("cs:scope") == "global"
                else "source_local"
            )
            outcome, candidate_keys, matched_entities = "resolved", (), ()
            if groups(definition) and all(
                all(name in attrs for name in group) for group in groups(definition)
            ):
                if any(
                    (source.reference, dependency) not in resolved for dependency in dependencies
                ):
                    decisions[source.reference, entity["id"]] = RichEntityResolution(
                        source.reference,
                        entity["id"],
                        mapping[entity["id"]],
                        basis,
                        "ungrounded_cycle",
                        (),
                        (),
                        tuple(sorted(dependencies)),
                    )
                    remaining.append((source, entity, definition))
                    continue
                candidates = keys(definition, attrs, source.context)
                matches = {declared_keys[key] for key in candidates if key in declared_keys}
                if len(matches) > 1:
                    raise ValueError("declared keys bridge incompatible known identities")
                canonical = next(iter(matches)) if matches else min(candidates)
                candidate_keys, matched_entities = (
                    tuple(sorted(set(candidates))),
                    tuple(sorted(matches)),
                )
                declared_keys.update((key, canonical) for key in candidates)
                mapping[entity["id"]] = canonical
            elif not groups(definition) and basis == "global_label" and entity.get("label"):
                mapping[entity["id"]] = soft_resolved[source.reference, entity["id"]]
                matched_entities = tuple(
                    sorted(
                        soft_ids[node]
                        for node in soft_groups[label_key(definition, entity["label"])]
                        if node[0] == "known"
                    )
                )
                if len(matched_entities) > 1:
                    outcome = "ambiguous_anchor"
            elif groups(definition) or basis == "global_label":
                outcome = "incomplete_key"
            decisions[source.reference, entity["id"]] = RichEntityResolution(
                source.reference,
                entity["id"],
                mapping[entity["id"]],
                basis,
                outcome,
                candidate_keys,
                matched_entities,
                tuple(sorted(dependencies)),
            )
            resolved.add((source.reference, entity["id"]))
            progress = True
        if not progress:
            break
        pending = remaining
    for reference, exclusion, _, _ in exclusions:

        def mapped(endpoint, reference=reference):
            if endpoint["kind"] == "known":
                if endpoint["target"] not in known:
                    raise ValueError("rich identity exclusion has an unbound known endpoint")
                return endpoint["target"]
            if endpoint["target"] not in mappings[reference]:
                raise ValueError("rich identity exclusion has an undeclared local endpoint")
            return mappings[reference][endpoint["target"]]

        left, right = mapped(exclusion["left"]), mapped(exclusion["right"])
        if left == right:
            raise RichIdentityConflict(
                reference, exclusion["id"], exclusion["left"], exclusion["right"], left
            )
    return mappings, tuple(decisions[key] for key in sorted(decisions))
