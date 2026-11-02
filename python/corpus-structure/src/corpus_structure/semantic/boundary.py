"""Boundary adapters built from immutable effective recipes, without source compilation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from functools import cache, reduce
from operator import or_
from typing import Annotated, Any, ForwardRef, Literal

from pydantic import (
    MISSING,
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationInfo,
    create_model,
    model_validator,
)

from .conditional_rules import conditional_model_namespace
from .types import ClassDefinition, VocabularySnapshot

_LITERAL: Any = Literal
_ANNOTATED: Any = Annotated
_TUPLE: Any = tuple
_DICT: Any = dict


def _numeric_bound(
    value: str, representation: type | None, *, lower: bool
) -> int | float | Decimal:
    number = Decimal(value)
    if representation is int:
        return int(number.to_integral_value(rounding=ROUND_CEILING if lower else ROUND_FLOOR))
    if representation is float:
        # Match the float boundary's own representation. Decimal metadata is
        # otherwise emitted as a string by JSON-mode schema encoders.
        return float(number)
    return number


def _keyed_members(key: str):
    def validate(value: dict[str, Any]) -> dict[str, Any]:
        for name, member in value.items():
            if getattr(member, key) != name:
                raise ValueError("inlined collection key differs from its member identifier")
        return value

    return validate


def _pattern_validator(patterns: tuple[str, ...]):
    compiled = tuple(re.compile(pattern) for pattern in patterns)

    def validate(value: Any) -> Any:
        if not isinstance(value, str) or any(pattern.search(value) is None for pattern in compiled):
            raise ValueError("value violates declared patterns")
        return value

    return validate


def _projection_namespace(definition: ClassDefinition) -> dict[str, Any]:
    properties = tuple(p for p in definition.properties if p.constraint_scope == "accepted_value")
    if not properties:
        return {}

    def validate_projection(model: Any, info: ValidationInfo) -> Any:
        if (info.context or {}).get("validation_purpose") != "accepted_value":
            return model
        for prop in properties:
            present = prop.name in model.model_fields_set
            if not present:
                if prop.required:
                    raise ValueError(f"accepted projection requires {definition.name}/{prop.name}")
                continue
            value = getattr(model, prop.name)
            values = (
                tuple(value.values())
                if prop.collection_key
                else tuple(value)
                if prop.multivalued
                else (value,)
            )
            if prop.multivalued:
                if prop.minimum_cardinality is not None and len(values) < prop.minimum_cardinality:
                    raise ValueError(f"accepted projection cardinality below minimum: {prop.name}")
                if prop.maximum_cardinality is not None and len(values) > prop.maximum_cardinality:
                    raise ValueError(f"accepted projection cardinality above maximum: {prop.name}")
            for item in values:
                if prop.minimum is not None and item < Decimal(prop.minimum):
                    raise ValueError(f"accepted projection value below minimum: {prop.name}")
                if prop.maximum is not None and item > Decimal(prop.maximum):
                    raise ValueError(f"accepted projection value above maximum: {prop.name}")
                if prop.patterns:
                    _pattern_validator(prop.patterns)(item)
        return model

    return {"_validate_projection_constraints": model_validator(mode="after")(validate_projection)}


def build_boundary_adapters(
    definitions: tuple[ClassDefinition, ...],
    vocabularies: tuple[VocabularySnapshot, ...],
    *,
    primitive_types: Mapping[str, Any],
    aliases: Mapping[tuple[str, str], str],
    conditional_fragments: Mapping[str, dict[str, Any]],
    conditional_scope: str = "shape",
    finite_fields: bool = True,
    class_names: tuple[str, ...] | None = None,
    descendant_order: Mapping[str, tuple[str, ...]] | None = None,
    models_out: dict[str, type[BaseModel]] | None = None,
) -> tuple[tuple[str, TypeAdapter[BaseModel]], ...]:
    """Reuse exactly the same model construction for preparation and archive opening.

    Callers select structural or accepted-value validation through their owned entry point.
    """
    classes = {definition.name: definition for definition in definitions}
    enums = {v.enum: _LITERAL[tuple(m.value for m in v.members)] for v in vocabularies}
    models: dict[str, Any] = dict(models_out or {})
    added: list[type[BaseModel]] = []

    def concrete(name: str) -> tuple[str, ...]:
        if descendant_order is not None and name in descendant_order:
            return descendant_order[name]
        return tuple(d.name for d in definitions if name in d.ancestors and not d.abstract)

    @cache
    def discriminator(name: str) -> str | None:
        members = concrete(name)
        if not members:
            return None
        constants = [
            {
                prop.name: prop.equals_string
                for prop in classes[member].properties
                if prop.equals_string is not None
            }
            for member in members
        ]
        candidates = set.intersection(*(set(row) for row in constants))
        candidates = {
            key for key in candidates if len({row[key] for row in constants}) == len(members)
        }
        for preferred in ("kind", "universe", "type"):
            if preferred in candidates:
                return preferred
        return min(candidates) if candidates else None

    selected = set(classes) if class_names is None else set(class_names)
    pending = list(selected)
    while pending:
        name = pending.pop()
        definition = classes[name]
        required = set(concrete(name)) if definition.abstract else set()
        required.update(p.range for p in definition.properties if p.inlined and p.range in classes)
        for dependency in required - selected:
            selected.add(dependency)
            pending.append(dependency)
    for definition in definitions:
        if definition.name not in selected or definition.name in models:
            continue
        fields: dict[str, Any] = {}
        for prop in definition.properties:
            if prop.range in classes:
                if prop.inlined and classes[prop.range].abstract:
                    members = concrete(prop.range)
                    if not members:
                        raise ValueError(f"abstract range {prop.range} has no concrete members")
                    selector = discriminator(prop.range)
                    if selector is None:
                        raise ValueError(
                            f"abstract range {prop.range} lacks a unique declared discriminator"
                        )
                    annotation = _ANNOTATED[
                        reduce(or_, (ForwardRef(name) for name in members)),
                        Field(discriminator=selector),
                    ]
                else:
                    annotation = ForwardRef(prop.range) if prop.inlined else str
            elif prop.range in enums:
                annotation = enums[prop.range]
            else:
                annotation = primitive_types[prop.range]
                if annotation is float and finite_fields:
                    annotation = _ANNOTATED[annotation, Field(allow_inf_nan=False)]
            if prop.equals_string is not None:
                annotation = _LITERAL[prop.equals_string]
            limits: dict[str, Any] = {}
            if prop.constraint_scope == "shape":
                representation = primitive_types.get(prop.range)

                if prop.minimum is not None:
                    limits["ge"] = _numeric_bound(prop.minimum, representation, lower=True)
                if prop.maximum is not None:
                    limits["le"] = _numeric_bound(prop.maximum, representation, lower=False)
                if prop.patterns:
                    annotation = _ANNOTATED[
                        annotation, AfterValidator(_pattern_validator(prop.patterns))
                    ]
                    limits["json_schema_extra"] = {"allOf": [{"pattern": p} for p in prop.patterns]}
            if limits:
                annotation = _ANNOTATED[annotation, Field(**limits)]
            if prop.multivalued:
                annotation = (
                    _DICT[str, annotation] if prop.collection_key else _TUPLE[annotation, ...]
                )
                if prop.collection_key:
                    annotation = _ANNOTATED[
                        annotation, AfterValidator(_keyed_members(prop.collection_key))
                    ]
                cardinality: dict[str, int] = {}
                if prop.constraint_scope == "shape":
                    if prop.minimum_cardinality is not None:
                        cardinality["min_length"] = prop.minimum_cardinality
                    if prop.maximum_cardinality is not None:
                        cardinality["max_length"] = prop.maximum_cardinality
                if cardinality:
                    annotation = _ANNOTATED[annotation, Field(**cardinality)]
            required = prop.name in definition.identity_slots or (
                prop.constraint_scope == "shape" and prop.required
            )
            fields[prop.name] = (
                annotation,
                Field(
                    default=... if required else MISSING,
                    alias=aliases.get((definition.name, prop.name), prop.name),
                ),
            )
        namespace = conditional_model_namespace(
            conditional_fragments.get(definition.name, {}),
            scope=conditional_scope,
        )
        namespace.update(_projection_namespace(definition))
        models[definition.name] = create_model(
            definition.name,
            __namespace__=namespace,
            __config__=ConfigDict(
                frozen=True, extra="forbid", strict=True, allow_inf_nan=False, defer_build=True
            ),
            **fields,
        )
        added.append(models[definition.name])
    for model in added:
        model.model_rebuild(_types_namespace=models)
    adapters = []
    for name in sorted(selected if class_names is None else class_names):
        model = models[name]
        if classes[name].abstract and (selector := discriminator(name)) is not None:
            members = concrete(name)
            if not members:
                raise ValueError(f"abstract boundary {name} has no concrete members")
            adapters.append(
                (
                    name,
                    TypeAdapter(
                        _ANNOTATED[
                            reduce(or_, (models[n] for n in members)), Field(discriminator=selector)
                        ]
                    ),
                )
            )
        else:
            adapters.append((name, TypeAdapter(model)))
    for _, adapter in adapters:
        adapter.rebuild(_types_namespace=models)
    if models_out is not None:
        models_out.update(models)
    return tuple(adapters)
