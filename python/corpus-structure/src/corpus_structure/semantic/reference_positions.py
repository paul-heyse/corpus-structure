"""Collect and rewrite references only in compiled, validated semantic positions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
from typing import Any, Literal

from pydantic import BaseModel

from .identity import canonical_bytes
from .statement_types import ReferencePosition, compile_effective_bindings
from .types import PreparedRelease


class ReferencePositionError(ValueError):
    """A validated value cannot realize its compiled reference/collection contract."""


@dataclass(frozen=True)
class LocatedReference:
    kind: Literal["class", "fact"]
    target: str
    range: str
    path: tuple[str | int, ...]


@lru_cache(maxsize=32)
def _index(content: bytes) -> Mapping[tuple[str, str], ReferencePosition]:
    product = json.loads(content)
    if product["abi"] != "effective-bindings-11":
        raise ReferencePositionError("unsupported effective reference-position ABI")
    positions = [ReferencePosition(**row) for row in product["references"]]
    index = {(position.class_name, position.property_name): position for position in positions}
    if len(index) != len(positions):
        raise ReferencePositionError("duplicate effective reference position")
    return MappingProxyType(index)


def _positions(prepared: PreparedRelease) -> Mapping[tuple[str, str], ReferencePosition]:
    artifact = next((a for a in prepared.artifacts if a.kind == "effective_bindings.json"), None)
    content = (
        artifact.content
        if artifact
        else canonical_bytes(
            compile_effective_bindings(prepared.definitions, prepared.vocabularies)
        )
    )
    return _index(content)


def reference_position(
    prepared: PreparedRelease, class_name: str, property_name: str
) -> ReferencePosition:
    try:
        return _positions(prepared)[class_name, property_name]
    except KeyError as exc:
        raise ReferencePositionError(
            f"{class_name}/{property_name}: no compiled reference position; "
            "derive a supported release"
        ) from exc


def _plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return {name: _plain(getattr(value, name)) for name in value.model_fields_set}
    if isinstance(value, tuple):
        return tuple(_plain(item) for item in value)
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, Mapping):
        return {name: _plain(item) for name, item in value.items()}
    return value


def _visit(
    prepared: PreparedRelease,
    model: BaseModel,
    found: list[LocatedReference],
    path: tuple[str | int, ...],
    classes: Mapping[str, str],
    facts: Mapping[str, str],
    collision: Literal["equal", "reject"],
    positions: Mapping[tuple[str, str], ReferencePosition],
    definitions: Mapping[str, Any],
) -> dict[str, Any]:
    class_name = type(model).__name__
    definition = definitions[class_name]
    result: dict[str, Any] = {}

    for prop in definition.properties:
        if prop.name not in model.model_fields_set:
            continue
        try:
            position = positions[class_name, prop.name]
        except KeyError as exc:
            raise ReferencePositionError(
                f"{class_name}/{prop.name}: missing compiled reference position"
            ) from exc
        value = getattr(model, prop.name)

        def lower(
            item: Any,
            item_path: tuple[str | int, ...],
            position: ReferencePosition = position,
        ) -> Any:
            if position.kind in {"class", "fact"}:
                if not isinstance(item, str):
                    raise ReferencePositionError(
                        f"{item_path}: a declared reference must be a string"
                    )
                kind: Literal["class", "fact"] = "fact" if position.kind == "fact" else "class"
                found.append(LocatedReference(kind, item, position.range, item_path))
                mapping = facts if kind == "fact" else classes
                return mapping.get(item, item)
            if position.kind == "inlined":
                if not isinstance(item, BaseModel):
                    raise ReferencePositionError(
                        f"{item_path}: an inlined position needs its validated model"
                    )
                return _visit(
                    prepared,
                    item,
                    found,
                    item_path,
                    classes,
                    facts,
                    collision,
                    positions,
                    definitions,
                )
            if position.kind != "literal":
                raise ReferencePositionError(
                    f"{item_path}: unsupported reference kind {position.kind!r}"
                )
            return _plain(item)

        field_path = (*path, prop.name)
        if position.collection == "keyed_map":
            if not prop.collection_key:
                raise ReferencePositionError(f"{field_path}: keyed position lacks its identifier")
            rewritten: dict[str, Any] = {}
            for old_key, member in value.items():
                entry = lower(member, (*field_path, old_key))
                key = entry[prop.collection_key]
                if key in rewritten and (collision == "reject" or rewritten[key] != entry):
                    raise ReferencePositionError(
                        "reference resolution collides distinct keyed members"
                    )
                rewritten[key] = entry
            result[prop.name] = rewritten
        elif position.collection == "sequence":
            result[prop.name] = tuple(
                lower(item, (*field_path, index)) for index, item in enumerate(value)
            )
        elif position.collection == "scalar":
            result[prop.name] = lower(value, field_path)
        else:
            raise ReferencePositionError(
                f"{field_path}: unsupported collection {position.collection!r}"
            )
    return result


def _validated(prepared: PreparedRelease, class_name: str, value: Any) -> BaseModel:
    # Internal schema-native records use slot names. External producer JSON has already
    # passed its separate alias-sensitive boundary before entering this visitor.
    adapter = prepared.adapter(class_name)
    return adapter.validate_python(
        value, strict=True, by_name=True, context={"validation_purpose": "structural"}
    )


def collect_references(
    prepared: PreparedRelease, class_name: str, value: Any
) -> tuple[LocatedReference, ...]:
    """Keep occurrence paths and duplicates; callers explicitly choose set semantics."""
    model = _validated(prepared, class_name, value)
    found: list[LocatedReference] = []
    _visit(
        prepared,
        model,
        found,
        (),
        {},
        {},
        "equal",
        _positions(prepared),
        {d.name: d for d in prepared.definitions},
    )
    return tuple(found)


def rewrite_references(
    prepared: PreparedRelease,
    class_name: str,
    value: Any,
    *,
    classes: Mapping[str, str],
    facts: Mapping[str, str] | None = None,
    collision: Literal["equal", "reject"] = "equal",
) -> dict[str, Any]:
    """Preserve ordered/bag positions and apply the caller's explicit keyed collision policy."""
    if collision not in {"equal", "reject"}:
        raise ReferencePositionError("unknown keyed collision policy")
    model = _validated(prepared, class_name, value)
    rewritten = _visit(
        prepared,
        model,
        [],
        (),
        classes,
        facts or {},
        collision,
        _positions(prepared),
        {d.name: d for d in prepared.definitions},
    )
    return _plain(_validated(prepared, class_name, rewritten))


def class_reference_value(prepared: PreparedRelease, value: Any) -> str:
    """Resolve a validated Value carrier with one direct compiled class-reference position.

    The receiving property owns the required target range. The carrier supplies its explicit
    reference representation; neither its discriminator spelling nor an Entity ancestry guess
    determines whether it is a reference.
    """
    references = collect_references(prepared, "Value", value)
    if len(references) != 1 or references[0].kind != "class" or len(references[0].path) != 1:
        raise ReferencePositionError(
            "class-ranged property needs one explicit direct class-reference value"
        )
    return references[0].target
