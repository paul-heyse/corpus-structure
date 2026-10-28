"""Per-predicate rules from the LinkML schema v0 (instruments §2.2).

Loads the verbatim copies of D2 §9 (``code/schema/statistics.yaml``) and D2 §6
(``code/schema/core.yaml``) with ``SchemaView``. The statistics schema imports
``../../core/schema/core`` (the D2 §2 pack layout); the flat spike layout resolves it with
SchemaView's ``importmap`` instead of editing the file (S4 observation, recorded).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from linkml_runtime.utils.schemaview import SchemaView

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"

# Core qualifiers are allowed on every predicate and never listed in ci:qualifiers (D2 §4).
CORE_QUALIFIERS = ("modality", "polarity", "hedge", "attribution", "conditions", "scope", "valid_time")
# Value `t` accepted for each ci:object (D1 §6).
OBJECT_T = {
    "formula": {"formula"},
    "set": {"set"},
    "text": {"text"},
    "number": {"number"},
    "bool": {"bool"},
    "enum": {"enum"},
    "date": {"date"},
    "interval": {"interval"},
    "phrase": {"phrase"},
}


def _ann(element) -> dict:
    anns = getattr(element, "annotations", None) or {}
    return {k: getattr(v, "value", v) for k, v in anns.items()}


@dataclass(frozen=True)
class PredicateRule:
    name: str
    prefixed: str
    domain: str | None
    range: str | None
    object_kind: str  # ci:object
    qualifiers: tuple[str, ...]
    identity_qualifiers: tuple[str, ...]
    functional: bool
    symmetric: bool


@dataclass
class SchemaLookup:
    schema_path: Path = field(default_factory=lambda: SCHEMA_DIR / "statistics.yaml")
    core_path: Path = field(default_factory=lambda: SCHEMA_DIR / "core.yaml")

    @cached_property
    def sv(self) -> SchemaView:
        importmap = {"../../core/schema/core": os.path.splitext(str(self.core_path))[0]}
        return SchemaView(str(self.schema_path), importmap=importmap)

    # ----- names and prefixes

    @cached_property
    def _slot_prefix(self) -> dict[str, str]:
        out = {}
        for name, slot in self.sv.all_slots().items():
            src = slot.from_schema or ""
            out[name] = "core" if src.rstrip("/").endswith("/core") else "stat"
        return out

    def bare(self, name: str) -> str:
        """Strip a ``stat:``/``core:`` prefix."""
        return name.split(":", 1)[1] if ":" in name else name

    def prefixed(self, name: str) -> str:
        b = self.bare(name)
        return f"{self._slot_prefix.get(b, 'stat')}:{b}"

    # ----- classes

    @cached_property
    def entity_classes(self) -> dict[str, dict]:
        return {
            n: _ann(c)
            for n, c in self.sv.all_classes().items()
            if _ann(c).get("ci:kind") == "entity"
        }

    def is_entity_class(self, name: str) -> bool:
        return self.bare(name) in self.entity_classes

    def class_scope(self, name: str) -> str | None:
        return self.entity_classes.get(self.bare(name), {}).get("ci:scope")

    def identity_keys(self, name: str) -> list[str]:
        return list(self.entity_classes.get(self.bare(name), {}).get("ci:identity_keys", []) or [])

    def is_a(self, cls: str, target: str) -> bool:
        """True when ``target`` is ``cls`` or one of its ancestors (mixins included)."""
        cls, target = self.bare(cls), self.bare(target)
        if cls not in self.sv.all_classes():
            return False
        return target in self.sv.class_ancestors(cls)

    # ----- predicates and qualifiers

    @cached_property
    def predicates(self) -> dict[str, PredicateRule]:
        out = {}
        for name in self.sv.all_slots():
            a = _ann(self.sv.get_slot(name))
            if a.get("ci:role") != "predicate":
                continue
            s = self.sv.induced_slot(name)
            out[name] = PredicateRule(
                name=name,
                prefixed=self.prefixed(name),
                domain=s.domain,
                range=s.range,
                object_kind=a.get("ci:object", "entity"),
                qualifiers=tuple(a.get("ci:qualifiers", []) or []),
                identity_qualifiers=tuple(a.get("ci:identity_qualifiers", []) or []),
                functional=bool(a.get("ci:functional", False)),
                symmetric=bool(a.get("ci:symmetric", False)),
            )
        return out

    def predicate(self, name: str) -> PredicateRule | None:
        return self.predicates.get(self.bare(name))

    def qualifier(self, name: str) -> tuple[str, str | None] | None:
        """(ci:object, range) of a qualifier slot, or None if not a qualifier."""
        name = self.bare(name)
        if name not in self.sv.all_slots():
            return None
        a = _ann(self.sv.get_slot(name))
        if a.get("ci:role") != "qualifier":
            return None
        return a.get("ci:object"), self.sv.induced_slot(name).range

    def map_value_kind(self, range_class: str) -> str | None:
        """For a ``ci:object: map`` qualifier: the ci-kind of its ``value`` attribute."""
        cls = self.sv.get_class(range_class)
        if cls is None or "value" not in (cls.attributes or {}):
            return None
        rng = cls.attributes["value"].range
        if rng in ("Formula",):
            return "formula"
        if rng in ("SetExpr",):
            return "set"
        return "text"  # plain string (ParamMapping: a canonical parameter name)

    # ----- enums

    def enum_values(self, enum: str) -> set[str]:
        e = self.sv.get_enum(enum)
        return set(e.permissible_values) if e is not None else set()

    def has_enum(self, enum: str) -> bool:
        return self.sv.get_enum(enum) is not None

    def condition_predicate(self, name: str) -> dict | None:
        e = self.sv.get_enum("ConditionPredicate")
        if e is None or name not in e.permissible_values:
            return None
        return _ann(e.permissible_values[name])

    # ----- S4 byproduct observations

    def observations(self) -> list[str]:
        obs = [
            "statistics.yaml imports '../../core/schema/core' (D2 §2 pack layout); loaded unedited "
            "from the flat code/schema/ copy through SchemaView(importmap=...).",
        ]
        q = _ann(self.sv.get_slot("has_distribution")).get("ci:qualifiers")
        obs.append(
            f"OPEN-D2-6: list-valued annotation ci:qualifiers on has_distribution reads back as "
            f"{type(q).__name__} {q!r}"
        )
        ex = self.entity_classes.get("FamilyParameter", {}).get("ci:examples")
        obs.append(f"OPEN-D2-6: ci:examples on FamilyParameter reads back as {type(ex).__name__} {ex!r}")
        obs.append(
            f"classes={len(self.sv.all_classes())} slots={len(self.sv.all_slots())} "
            f"enums={len(self.sv.all_enums())} predicates={len(self.predicates)}"
        )
        return obs
