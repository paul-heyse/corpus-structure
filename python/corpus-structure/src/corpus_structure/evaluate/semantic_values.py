"""Evaluation adapters over the archived semantic boundary and reference visitor."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ValidationError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.reference_positions import collect_references
from corpus_structure.semantic.reference_positions import rewrite_references as rewrite_positions
from corpus_structure.semantic.types import ClassDefinition, PreparedRelease, PropertyDefinition


def _validated_record(prepared: PreparedRelease, range_name: str, value: Any) -> BaseModel:
    candidates = []
    for definition in prepared.definitions:
        if definition.abstract or not (
            definition.name == range_name or range_name in definition.ancestors
        ):
            continue
        try:
            validated = prepared.adapter(definition.name).validate_json(
                canonical_bytes(value),
                strict=True,
                by_name=True,
                context={"validation_purpose": "structural"},
            )
        except ValidationError:
            continue
        candidates.append((definition, validated))
    if not candidates:
        raise ValueError(f"no archived {range_name} boundary accepts the value")
    depth = max(len(d.ancestors) for d, _ in candidates)
    selected = [record for definition, record in candidates if len(definition.ancestors) == depth]
    if len(selected) != 1:
        raise ValueError(f"ambiguous archived record type for {range_name}")
    return selected[0]


def record_definition(
    prepared: PreparedRelease, range_name: str | None, value: Mapping[str, Any]
) -> ClassDefinition | None:
    if range_name is None or not any(d.name == range_name for d in prepared.definitions):
        return None
    model = _validated_record(prepared, range_name, value)
    return next(d for d in prepared.definitions if d.name == type(model).__name__)


def entity_reference(definitions: Sequence[ClassDefinition], prop: PropertyDefinition) -> bool:
    """Class-ranged references include non-Entity concepts; literals remain literals."""
    return (
        not prop.inlined
        and prop.reference_role != "fact"
        and any(d.name == prop.range for d in definitions)
    )


def rewrite_references(
    prepared: PreparedRelease,
    range_name: str,
    value: Any,
    entities: Mapping[str, str],
    claims: Mapping[str, str] | None = None,
) -> Any:
    if not isinstance(value, Mapping):
        return value
    model = _validated_record(prepared, range_name, value)
    rewritten = rewrite_positions(
        prepared, type(model).__name__, model, classes=entities, facts=claims, collision="reject"
    )

    # The visitor returns schema-native Python records (dates, Decimals and tuples included).
    # Evaluation combines and reopens these records at the producer JSON boundary, so cross
    # that boundary through its canonical Pydantic model rather than an identity encoder or
    # generic string conversion. Field-specific serializers retain exact lexical values.
    boundary = prepared.adapter(type(model).__name__).validate_python(
        rewritten, strict=True, by_name=True, context={"validation_purpose": "structural"}
    )
    return boundary.model_dump(mode="json", by_alias=False, exclude_unset=True)


def entity_references(prepared: PreparedRelease, range_name: str, value: Any) -> frozenset[str]:
    if not isinstance(value, Mapping):
        return frozenset()
    model = _validated_record(prepared, range_name, value)
    return frozenset(
        ref.target
        for ref in collect_references(prepared, type(model).__name__, model)
        if ref.kind == "class"
    )
