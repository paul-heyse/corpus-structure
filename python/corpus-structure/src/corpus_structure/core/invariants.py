"""The `ci:invariant` templates (D2 §3.4): the behaviour behind each declared cross-field invariant.

The model declares which template holds on which fields of a class; `core/_model/validators.py`
is generated from those declarations and calls these functions, and M2 compiles the same
declarations into CHECKs (F01). A field is absent when it is `MISSING` (or not a field of the
object's form) or None. A violation raises `ValueError`, so a Pydantic validator that calls a
generated validator reports it as a validation error.

The templates:
- `ordered(a, b)`: a < b, when both are present;
- `ordered_eq(a, b)`: a <= b, when both are present;
- `iff_present(x, y = v)`: x is present exactly when y is one of the values;
- `iff_absent(x, y = v)`: x is absent exactly when y is one of the values;
- `only_when(x, y = v)`: x is present only when y is one of the values;
- `together(a, b, …)`: all present or all absent;
- `exactly_one(a, b, …)`: exactly one present.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from pydantic import MISSING


def _value(obj: object, name: str) -> Any:
    return getattr(obj, name, MISSING)


def absent(value: object) -> bool:
    return value is MISSING or value is None


def _names(names: tuple[str, ...]) -> str:
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _values(values: Collection[object]) -> str:
    return " or ".join(str(v) for v in values)


def ordered(obj: object, a: str, b: str) -> None:
    lo, hi = _value(obj, a), _value(obj, b)
    if not absent(lo) and not absent(hi) and not lo < hi:
        raise ValueError(f"[{a}, {b}) = [{lo}, {hi}) is empty or reversed")


def ordered_eq(obj: object, a: str, b: str) -> None:
    lo, hi = _value(obj, a), _value(obj, b)
    if not absent(lo) and not absent(hi) and not lo <= hi:
        raise ValueError(f"{a} {lo} > {b} {hi}")


def iff_present(obj: object, x: str, y: str, values: Collection[object]) -> None:
    if absent(_value(obj, x)) == (_value(obj, y) in values):
        raise ValueError(f"{x} is given exactly when {y} is {_values(values)}")


def iff_absent(obj: object, x: str, y: str, values: Collection[object]) -> None:
    if absent(_value(obj, x)) != (_value(obj, y) in values):
        raise ValueError(f"{x} is absent exactly when {y} is {_values(values)}")


def only_when(obj: object, x: str, y: str, values: Collection[object]) -> None:
    if not absent(_value(obj, x)) and _value(obj, y) not in values:
        raise ValueError(f"{x} is given only when {y} is {_values(values)}")


def together(obj: object, *names: str) -> None:
    present = {absent(_value(obj, name)) for name in names}
    if len(present) > 1:
        raise ValueError(f"{_names(names)} are present together or not at all")


def exactly_one(obj: object, *names: str) -> None:
    if sum(not absent(_value(obj, name)) for name in names) != 1:
        raise ValueError(f"exactly one of {_names(names)} is given")
