"""Immutable snapshots of exact, inert JSON values used by selected projections."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import isfinite

from .data_operation_json import DdoJsonValue

type JsonScalar = bool | int | float | Decimal | str | None
type FrozenJson = JsonScalar | FrozenArray | FrozenObject


@dataclass(frozen=True, slots=True)
class FrozenArray:
    values: tuple[FrozenJson, ...]


@dataclass(frozen=True, slots=True)
class FrozenObject:
    fields: tuple[tuple[str, FrozenJson], ...]


def _scalar(value: object) -> JsonScalar:
    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if type(value) is float:
        if not isfinite(value):
            raise ValueError("snapshot requires finite JSON numbers")
        return value
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("snapshot requires finite JSON numbers")
        return value
    raise TypeError("snapshot requires exact inert JSON values")


def freeze_json(value: object) -> FrozenJson:
    """Detach a tree without invoking methods on caller-provided containers."""
    if type(value) is list:
        return FrozenArray(tuple(freeze_json(item) for item in value))
    if type(value) is dict:
        fields = []
        for key in value:
            if type(key) is not str:
                raise TypeError("snapshot requires exact string keys")
            fields.append((key, freeze_json(value[key])))
        return FrozenObject(tuple(fields))
    return _scalar(value)


def thaw_json(value: FrozenJson) -> DdoJsonValue:
    """Return an owned projection value, checking the representation at ingress."""
    if type(value) is FrozenArray:
        if type(value.values) is not tuple:
            raise TypeError("snapshot requires immutable array values")
        return [thaw_json(item) for item in value.values]
    if type(value) is FrozenObject:
        if type(value.fields) is not tuple:
            raise TypeError("snapshot requires immutable object fields")
        fields = {}
        for entry in value.fields:
            if type(entry) is not tuple or len(entry) != 2:
                raise TypeError("snapshot requires immutable field pairs")
            key, item = entry
            if type(key) is not str or key in fields:
                raise TypeError("snapshot requires unique exact string keys")
            fields[key] = thaw_json(item)
        return fields
    return _scalar(value)
