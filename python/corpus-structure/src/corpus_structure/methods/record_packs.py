"""Private native packs derived from the actual released family declarations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from corpus_structure.semantic.types import ClassDefinition, PreparedRelease, PropertyDefinition

from .gliner import GlinerPack, GlinerRefused

INSPECTION_POLICY = "source-role-inspection-1"
SOURCE_STATES = ("present", "unstated", "inapplicable", "unresolved")


def inspection_fields(prepared: PreparedRelease, roles) -> tuple[dict[str, Any], ...]:
    """Native proposal fields, kept outside the released domain role vocabulary."""
    fields = []
    for role in roles:
        if field_kind(prepared, role) not in {"literal", "classified"}:
            continue
        fields.append(
            dict(
                name=role.name + "__state",
                dtype="str",
                cardinality="optional_one",
                choices=list(SOURCE_STATES),
                description=(
                    f"Inspect the entire supplied source context for this record's {role.name}. "
                    "Choose present only when stated and attached to this reading; unstated only "
                    "after inspecting an applicable scope that does not state it; "
                    "inapplicable only "
                    "when this role cannot apply to this reading; unresolved for ambiguous meaning "
                    "or attachment. Missing extraction output never means unstated."
                ),
            )
        )
        if field_kind(prepared, role) == "classified":
            fields.append(
                dict(
                    name=role.name + "__cue",
                    dtype="str",
                    cardinality="optional_one",
                    description=(
                        f"Exact source phrase or grammatical cue that supports the {role.name} "
                        "classification for this same reading. Extract its actual source words; "
                        "do not copy the classification label unless those words are stated."
                    ),
                )
            )
    return tuple(fields)


def family_roles(
    prepared: PreparedRelease, contract: str
) -> tuple[ClassDefinition, tuple[PropertyDefinition, ...]]:
    definition = prepared.index.definitions[contract]
    if "SemanticRecordFields" not in definition.ancestors:
        raise GlinerRefused("contract is not a released record family")
    roles = tuple(
        prop for prop in definition.properties if prop.name not in {"family", "occurrence_recipe"}
    )
    return definition, roles


def field_kind(prepared: PreparedRelease, role: PropertyDefinition) -> str:
    properties = prepared.index.properties_by_class[role.range]
    kind = properties["kind"].equals_string
    # Transformed fields require a separate explicit operation, never native extraction.
    if kind is None and properties["kind"].range == "RecordTransformationKind":
        return "normalized"
    if kind not in {"literal", "classified", "native"}:
        raise GlinerRefused("unsupported released record field kind")
    return kind


def classification(
    prepared: PreparedRelease, role: PropertyDefinition
) -> tuple[str, tuple[str, ...]]:
    value_type = prepared.index.properties_by_class[role.range]["value"].range
    properties = prepared.index.properties_by_class[value_type]
    kind = properties["kind"].equals_string
    if not kind:
        raise GlinerRefused("classification requires a released value kind")
    choices = tuple(sorted(prepared.enum_members(properties["label"].range)))
    if not choices:
        raise GlinerRefused("classification requires a released closed label vocabulary")
    return kind, choices


def family_pack(
    prepared: PreparedRelease,
    *,
    contract: str,
    anchor_role: str,
    descriptions: Mapping[str, str] | None = None,
    source_inspection: bool = False,
) -> GlinerPack:
    """Choose natural grouping explicitly; optional native fields never decide source absence.

    Native locations and transformed fields come from their owners, not model strings.
    Description/anchor choices are extraction policy; family roles and choices are released.
    """
    definition, roles = family_roles(prepared, contract)
    descriptions = descriptions or {}
    if set(descriptions) - {role.name for role in roles}:
        raise GlinerRefused("description names an unreleased family role")
    fields = []
    for role in roles:
        kind = field_kind(prepared, role)
        if kind not in {"literal", "classified"}:
            continue
        field: dict[str, Any] = dict(name=role.name, dtype="str", cardinality="optional_one")
        if kind == "classified":
            field["choices"] = list(classification(prepared, role)[1])
        if role.name in descriptions:
            field["description"] = descriptions[role.name]
        fields.append(field)
    if source_inspection:
        fields.extend(inspection_fields(prepared, roles))
    if anchor_role not in {field["name"] for field in fields} or next(
        field for field in fields if field["name"] == anchor_role
    ).get("choices"):
        raise GlinerRefused("native natural grouping requires an explicit literal anchor role")
    family = next(prop.equals_string for prop in definition.properties if prop.name == "family")
    return GlinerPack.from_declaration(
        prepared.release_id,
        {"structures": {family: dict(mode="natural", anchor=anchor_role, fields=fields)}},
    )
