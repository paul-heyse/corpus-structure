"""The loaded pack: SchemaView facts the compilers read, and the rules files (D2 §2, §3, §7).

Everything domain-specific comes from the schema files: no predicate, class or subset is named here.
``ci:kind`` and ``ci:object`` are derived (D2 §3): a class is an entity class when ``Entity`` is an
ancestor and it is not abstract or a mixin; a value class when ``Value`` is an ancestor; a slot's object
kind follows its range (entity class, value class tag, enum, map entry class, ``Condition``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Literal

import yaml
from linkml_runtime.utils.schemaview import SchemaView
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import paths

LIST_ANNOTATIONS = ("ci:qualifiers", "ci:identity_qualifiers", "ci:target")
VALUE_ROOT, ENTITY_ROOT, CONDITION, MAP_ENTRY, ENTITY_REF = "Value", "Entity", "Condition", "MapEntry", "EntityRef"


def annotations(element) -> dict[str, Any]:
    """ci: annotations of an element as plain Python scalars (lists split from space-separated strings)."""
    out = {}
    anns = getattr(element, "annotations", None) or {}
    if not isinstance(anns, dict):  # induced slots carry a JsonObj
        anns = {k: v for k, v in vars(anns).items() if not k.startswith("_")}
    for k, v in anns.items():
        val = getattr(v, "value", v.get("value") if isinstance(v, dict) else v)
        if isinstance(val, str):
            val = str(val)
        if k in LIST_ANNOTATIONS:
            val = tuple(str(val).split())
        out[k] = val
    return out


@dataclass(frozen=True)
class Predicate:
    name: str
    prefixed: str
    domain: str
    range: str
    object_kind: str
    qualifiers: tuple[str, ...]
    identity_qualifiers: tuple[str, ...]
    subsets: tuple[str, ...]
    extract: str | None
    functional: bool
    symmetric: bool
    transitive: bool
    param_map: str | None
    description: str
    annotations: dict = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class Qualifier:
    name: str
    prefixed: str
    range: str
    object_kind: str
    map_value_kind: str | None  # for object kind map: formula | set | text
    core: bool
    description: str


class Pack:
    """One schema version: the pack schema with its core import, and both rules files."""

    def __init__(self, schema: Path = paths.PACK_YAML, rules: tuple[Path, ...] = (paths.CORE_RULES, paths.PACK_RULES)):
        self.schema_path = schema
        self.rules_paths = rules
        self.sv = SchemaView(str(schema))

    # ------------------------------------------------------------------ classes

    def ancestors(self, cls: str) -> list[str]:
        return self.sv.class_ancestors(cls) if cls in self.sv.all_classes() else []

    def is_a(self, cls: str, target: str) -> bool:
        return target in self.ancestors(cls)

    @cached_property
    def entity_classes(self) -> dict[str, dict]:
        out = {}
        for n, c in self.sv.all_classes().items():
            if n != ENTITY_ROOT and ENTITY_ROOT in self.ancestors(n) and not c.abstract and not c.mixin:
                out[n] = annotations(c)
        return dict(sorted(out.items()))

    @cached_property
    def value_classes(self) -> dict[str, str]:
        """Value class -> its tag t (equals_string)."""
        out = {}
        for n in sorted(self.sv.all_classes()):
            if n != VALUE_ROOT and VALUE_ROOT in self.ancestors(n):
                out[n] = str(self.sv.induced_slot("t", n).equals_string)
        return out

    def class_kind(self, n: str) -> str:
        c = self.sv.get_class(n)
        if n in self.entity_classes:
            return "entity"
        if c.abstract or c.mixin:
            return "abstract"
        return "value"

    def scope(self, cls: str) -> str | None:
        return self.entity_classes.get(cls, {}).get("ci:scope")

    def identity_keys(self, cls: str) -> tuple[str, ...]:
        uk = self.sv.get_class(cls).unique_keys or {}
        for name in sorted(uk):
            return tuple(uk[name].unique_key_slots)
        for a in self.ancestors(cls)[1:]:
            k = self.identity_keys(a) if a in self.sv.all_classes() else ()
            if k:
                return k
        return ()

    def mention_classes(self) -> list[str]:
        return [n for n, a in self.entity_classes.items() if a.get("ci:extract") == "mention"]

    def batch_entity_types(self) -> list[str]:
        """Entity classes an entities[] item may name: every entity class except Statement (V2b)."""
        return [n for n in self.entity_classes if n != "Statement"]

    # ------------------------------------------------------------------ slots

    def prefixed(self, name: str) -> str:
        return self.sv.get_uri(self.sv.get_slot(name), expand=False)

    def object_kind(self, rng: str, multivalued: bool = False) -> tuple[str, str | None]:
        """(ci:object, map value kind) derived from a slot range."""
        if rng in self.value_classes:
            return self.value_classes[rng], None
        if rng == CONDITION:
            return "condition", None
        if rng in self.sv.all_enums():
            return "enum", None
        if rng in self.sv.all_classes() and MAP_ENTRY in self.ancestors(rng):
            vr = self.sv.induced_slot("value", rng).range
            return "map", self.value_classes.get(vr, "text")
        if rng in self.sv.all_classes() and (rng == ENTITY_ROOT or ENTITY_ROOT in self.ancestors(rng)):
            return "entity", None
        if rng in self.sv.all_classes() and self.sv.get_class(rng).mixin:
            return "entity", None
        return {"string": "text", "integer": "number", "boolean": "bool"}.get(rng, "text"), None

    @cached_property
    def predicates(self) -> dict[str, Predicate]:
        out = {}
        for name in sorted(self.sv.all_slots()):
            s = self.sv.get_slot(name)
            a = annotations(s)
            if a.get("ci:role") != "predicate":
                continue
            ind = self.sv.induced_slot(name)
            kind, _ = self.object_kind(ind.range)
            out[name] = Predicate(
                name=name,
                prefixed=str(self.prefixed(name)),
                domain=str(ind.domain),
                range=str(ind.range),
                object_kind=str(a.get("ci:object", kind)),
                qualifiers=a.get("ci:qualifiers", ()),
                identity_qualifiers=a.get("ci:identity_qualifiers", ()),
                subsets=tuple(sorted(str(x) for x in (s.in_subset or ()))),
                extract=a.get("ci:extract"),
                functional=bool(a.get("ci:functional", False)),
                symmetric=bool(s.symmetric),
                transitive=bool(s.transitive),
                param_map=a.get("ci:param_map"),
                description=" ".join(str(s.description or "").split()),
                annotations=a,
            )
        return out

    @cached_property
    def qualifiers(self) -> dict[str, Qualifier]:
        out = {}
        for name in sorted(self.sv.all_slots()):
            s = self.sv.get_slot(name)
            if annotations(s).get("ci:role") != "qualifier":
                continue
            ind = self.sv.induced_slot(name)
            kind, mvk = self.object_kind(ind.range, bool(ind.multivalued))
            out[name] = Qualifier(
                name=name,
                prefixed=str(self.prefixed(name)),
                range=str(ind.range),
                object_kind=kind,
                map_value_kind=mvk,
                core=self.prefixed(name).startswith("core:"),
                description=" ".join(str(s.description or "").split()),
            )
        return out

    @cached_property
    def core_qualifiers(self) -> list[str]:
        return [q for q, i in self.qualifiers.items() if i.core]

    def predicate_qualifiers(self, p: str) -> list[str]:
        return self.core_qualifiers + [q for q in self.predicates[p].qualifiers if q not in self.core_qualifiers]

    def applicable_predicates(self, cls: str) -> list[str]:
        """Predicates whose domain is the class or an ancestor (mixins included), L-08."""
        anc = set(self.ancestors(cls))
        return [p for p, i in self.predicates.items() if i.domain in anc]

    # ------------------------------------------------------------------ enums and subsets

    def enum_values(self, enum: str) -> list[str]:
        e = self.sv.get_enum(enum)
        return list(e.permissible_values) if e is not None else []

    @cached_property
    def enums(self) -> dict[str, list[str]]:
        return {n: self.enum_values(n) for n in sorted(self.sv.all_enums())}

    def pv_annotations(self, enum: str) -> dict[str, dict]:
        return {k: annotations(v) for k, v in self.sv.get_enum(enum).permissible_values.items()}

    @cached_property
    def subsets(self) -> dict[str, list[str]]:
        out = {n: [] for n in sorted(self.sv.all_subsets())}
        for p, i in self.predicates.items():
            for s in i.subsets:
                out[s].append(p)
        return out

    def subset_description(self, name: str) -> str:
        return " ".join(str(self.sv.get_subset(name).description or "").split())

    # ------------------------------------------------------------------ rules files

    @cached_property
    def rules(self) -> "RulesFile":
        merged: dict[str, Any] = {"views": {}, "rules": [], "guideline": [], "tables": {}, "derive": []}
        for p in self.rules_paths:
            d = RulesFile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
            merged["views"].update(d.views)
            merged["rules"] += d.rules
            merged["guideline"] += d.guideline
            merged["tables"].update(d.tables)
            merged["derive"] += d.derive
        return RulesFile.model_construct(**merged)

    def expand_applies_to(self, applies_to: str | list[str]) -> list[str]:
        """Predicate set (bare names) of an applies_to; an unknown name raises (D2 §7.4)."""
        items = [applies_to] if isinstance(applies_to, str) else list(applies_to)
        out: list[str] = []
        by_prefixed = {i.prefixed: p for p, i in self.predicates.items()}
        for it in items:
            if it == "any":
                out += list(self.predicates)
            elif it.startswith("subset:"):
                s = it.split(":", 1)[1]
                if s not in self.subsets:
                    raise KeyError(f"applies_to names unknown subset {s!r}")
                out += self.subsets[s]
            elif it in by_prefixed:
                out.append(by_prefixed[it])
            else:
                raise KeyError(f"applies_to names unknown predicate {it!r}")
        return sorted(set(out))


# ---------------------------------------------------------------------- the rules file (its lint)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ViewDecl(_Strict):
    description: str
    applies_to: str | list[str]
    source: str
    match: dict[Literal["source", "claim"], Literal["subject", "object"]]
    project: str


class RuleDecl(_Strict):
    id: str
    applies_to: str | list[str]
    severity: Literal["warning", "error"]
    at: tuple[Literal["batch", "finalize"], ...] = Field(min_length=1)
    description: str
    when: str = "true"
    check: str

    @field_validator("check", "when")
    @classmethod
    def _one_line(cls, v: str) -> str:
        return " ".join(v.split())


class GuidelineDecl(_Strict):
    id: str
    applies_to: str | list[str]
    description: str
    when: str = "true"
    check: str

    @field_validator("check", "when")
    @classmethod
    def _one_line(cls, v: str) -> str:
        return " ".join(v.split())


class RulesFile(_Strict):
    views: dict[str, ViewDecl] = {}
    rules: list[RuleDecl] = []
    guideline: list[GuidelineDecl] = []
    tables: dict[str, dict[str, Any]] = {}
    derive: list[dict] = []
