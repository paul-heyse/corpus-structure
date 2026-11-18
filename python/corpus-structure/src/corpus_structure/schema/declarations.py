"""Shared typed declaration access over a captured LinkML view."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

TEMPLATES: Mapping[str, str] = {
    "ordered": "pair",
    "ordered_eq": "pair",
    "together": "fields",
    "exactly_one": "fields",
    "iff_present": "condition",
    "iff_absent": "condition",
    "only_when": "condition",
}


class ModelError(ValueError):
    """The model fails its declaration check or its revision log; `problems` lists each."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("model check failed:\n  " + "\n  ".join(problems))


# linkml-runtime's metamodel classes and `SchemaView` carry types pyrefly cannot follow (decorated
# accessors, optional containers), so the model code reads them as `Any`.
type View = Any


@dataclass(frozen=True)
class Member:
    """One member of an expanded enum, with the enum that defines it."""

    text: str
    description: str | None
    properties: tuple[str, ...]
    defined_in: str
    title: str | None = None  # the native title, which names the generated member when given


def ci_annotations(element: Any) -> dict[str, Any]:
    """An element's annotations as tag -> plain value (scalar; `extended_str` cast to str)."""
    raw = getattr(element, "annotations", None) or {}
    items = raw.items() if hasattr(raw, "items") else vars(raw).items()
    out: dict[str, Any] = {}
    for tag, ann in items:
        value = getattr(ann, "value", ann)
        out[str(tag)] = value if isinstance(value, bool | int) else str(value)
    return out


# --- Enum expansion ----------------------------------------------------------------------------


class EnumExpansionError(ValueError):
    pass


def _members_of(enum_name: str, pvs: Mapping[str, Any]) -> list[Member]:
    return [
        Member(
            str.__str__(text),
            pv.description,
            tuple(str(p) for p in pv.in_subset or ()),
            enum_name,
            str(pv.title) if getattr(pv, "title", None) else None,
        )
        for text, pv in pvs.items()
    ]


def _expression(
    view: View, owner: str, expr: Any, seen: tuple[str, ...]
) -> list[tuple[Member, bool]]:
    """An expression's members in order, each with whether `owner` defines it (an inline
    member) rather than brings it from a parent (`inherits`)."""
    for unsupported in ("reachable_from", "matches", "concepts"):
        if getattr(expr, unsupported, None):
            raise EnumExpansionError(f"{owner}: {unsupported} is not expanded")
    out = [(m, True) for m in _members_of(owner, expr.permissible_values or {})]
    for parent in expr.inherits or ():
        out += [(m, False) for m in _expand(view, str(parent), seen)]
    return out


def _expand(view: View, name: str, seen: tuple[str, ...]) -> list[Member]:
    if name in seen:
        raise EnumExpansionError(f"enum inheritance cycle: {' -> '.join((*seen, name))}")
    enum = view.get_enum(name)
    if enum is None:
        raise EnumExpansionError(f"unknown enum {name!r}")
    seen = (*seen, name)
    for unsupported in ("reachable_from", "matches", "concepts"):
        if getattr(enum, unsupported, None):
            raise EnumExpansionError(f"{name}: {unsupported} is not expanded")
    # own members, each inherits enum, each include expression; True: defined by this enum
    members = [(m, True) for m in _members_of(name, enum.permissible_values or {})]
    for parent in enum.inherits or ():
        members += [(m, False) for m in _expand(view, str(parent), seen)]
    for expr in enum.include or ():
        members += _expression(view, name, expr, seen)
    defined: dict[str, Member] = {}
    for member, own in members:
        if own and member.text in defined:
            raise EnumExpansionError(f"{name}: member {member.text!r} is defined twice")
        if own:
            defined[member.text] = member
    first: dict[str, Member] = {}
    for member, own in members:
        if own:
            continue
        if member.text in defined:
            raise EnumExpansionError(
                f"{name}: member {member.text!r} collides with {member.defined_in}'s member"
            )
        earlier = first.setdefault(member.text, member)
        if set(earlier.properties) != set(member.properties):
            raise EnumExpansionError(
                f"{name}: member {member.text!r} comes from {earlier.defined_in} with properties "
                f"{sorted(earlier.properties)} and from {member.defined_in} with "
                f"{sorted(member.properties)}"
            )
    removed: set[str] = set()
    for expr in enum.minus or ():
        removed |= {m.text for m, _ in _expression(view, name, expr, seen)}
    out: list[Member] = []
    kept: set[str] = set()
    for member, _ in members:
        if member.text in kept or member.text in removed:
            continue
        kept.add(member.text)
        out.append(member)
    return out


def expand_enum(view: View, name: str) -> list[Member]:
    """The members of an enum with its `inherits`, `include` and `minus` expanded (module doc)."""
    return _expand(view, name, ())


# --- The declaration check ---------------------------------------------------------------------


_INVARIANT = re.compile(r"^\s*([a-z_]+)\s*\((.*)\)\s*$")


@dataclass(frozen=True)
class Invariant:
    """One parsed `ci:invariant` entry: the template, its fields and, for a condition, the
    field and the values it compares with (as written)."""

    template: str
    fields: tuple[str, ...]
    condition: str | None = None
    values: tuple[str, ...] = ()

    def __str__(self) -> str:
        if self.condition is None:
            return f"{self.template}({', '.join(self.fields)})"
        return f"{self.template}({self.fields[0]}, {self.condition} = {'|'.join(self.values)})"


def parse_invariants(text: str) -> list[Invariant]:
    """`ordered(a, b); iff_present(x, y = v1|v2)` as `Invariant`s; refused if malformed."""
    out: list[Invariant] = []
    for part in (p for p in text.split(";") if p.strip()):
        m = _INVARIANT.match(part)
        if not m or m.group(1) not in TEMPLATES:
            raise ValueError(f"not an invariant template: {part.strip()!r}")
        template, args = m.group(1), [a.strip() for a in m.group(2).split(",")]
        kind = TEMPLATES[template]
        if kind == "condition":
            if len(args) != 2 or "=" not in args[1]:
                raise ValueError(f"{template} takes (x, y = v): {part.strip()!r}")
            y, values = (s.strip() for s in args[1].split("=", 1))
            out.append(Invariant(template, (args[0],), y, tuple(values.split("|"))))
        else:
            if (kind == "pair" and len(args) != 2) or len(args) < 2 or not all(args):
                raise ValueError(f"{template} takes two or more fields: {part.strip()!r}")
            out.append(Invariant(template, tuple(args)))
    return out


def invariants_of(view: View, cls: str) -> list[Invariant]:
    """A class's own and inherited invariants, ancestors first."""
    out: list[Invariant] = []
    for name in reversed(view.class_ancestors(cls)):
        text = ci_annotations(view.get_class(name)).get("ci:invariant")
        if text:
            out += parse_invariants(str(text))
    return out
