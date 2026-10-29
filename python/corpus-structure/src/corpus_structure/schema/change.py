"""The schema-change model (model and projections §3.6; ADR-0022; TM §9): diff, record, classifier.

**The diff** (`diff(old, new)`; LinkML 1.12.1 has none) compares two models element by element:
the schema's `version` and `ci:key_scheme`; each type, class, slot of a class (as induced) and free
slot, enum and enum member, by prefixed path (`sys:Claim`, `sys:Claim.predicate`, `core:modality`,
`core:SegmentKind`, `core:SegmentKind#paragraph`). An element is `added`, `removed` or `changed`,
a change named by its aspect (`range`, `required`, `description`, `ci:key_role`, `properties`, …).
The children of an added or removed element are not listed separately. A rename is a removal and an
addition: the diff cannot tell, so the change record declares it in its name map.

**The change record** (`ChangeRecord`, `ElementChange`) is the `system` module's class of the same
name; the shapes here are its hand-written mirror until Stage B (a test keeps their fields equal).

**The classifier** (`check(record, old, new)`) derives each change's class from the diff and the two
models and refuses a record that does not declare exactly that class for exactly the changes found.
The derivation, first match:
- `description`, `title`, `comments`, `examples` or the schema `version`: `descriptive`;
- the key scheme, `ci:key_role`, `ci:key_role_when`, `ci:case`, `ci:stored_range`, an added
  slot that declares a key role, or a member property whose subset's `ci:consumer` names keys:
  `key-bearing`;
- a removal; a change of range, cardinality, identifier, lifecycle, placement, payload kind or type;
  an added pattern, invariant or unique key, or a slot made required; an added required slot without
  a default: `breaking` (narrowing or loss);
- a schema-version closed set's member or property: `version-scoped-additive`;
- anything a table, a CHECK or the overlay reads: a table class's slot or invariant, a static closed
  set that a table column uses (its CHECK), a static set's member property (the SQL constants), a
  newly `sql_visible` path, a nested slot on an `sql_visible` path, `ci:on_delete`, `ci:generated`,
  `ci:same`: `relational-additive`;
- otherwise (an optional field, a member no CHECK lists, a widening of a nested class):
  `nested-additive`.

A removal and an addition that the name map pairs are `mapped`. A `breaking` change passes only
with a recorded `decision` (DP-24). A `nested-additive` change names its upcaster (`absent`: the
older payload reads as it is), `relational-additive` needs the record's Alembic revision and
`key-bearing` its key consequences. `route(class)` is the class's route (§3.6's table).
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from corpus_structure.core.vocab import ChangeKind, CompatibilityClass
from corpus_structure.schema.model import Model, ci_annotations, expand_enum

C = CompatibilityClass
DESCRIPTIVE_ASPECTS = frozenset({"description", "title", "comments", "examples", "version"})
KEY_ASPECTS = frozenset(
    {"ci:key_role", "ci:key_role_when", "ci:case", "ci:stored_range", "ci:key_scheme"}
)
RELATIONAL_ASPECTS = frozenset({"ci:on_delete", "ci:generated", "ci:same"})
ROUTES: Mapping[CompatibilityClass, str] = {
    C.INITIAL: "a first payload-schema version: no parent, no route",
    C.DESCRIPTIVE: "new revision; no DDL",
    C.NESTED_ADDITIVE: "registry row with its upcast; no DDL, no rewrite",
    C.RELATIONAL_ADDITIVE: "generated Alembic revision",
    C.VERSION_SCOPED_ADDITIVE: "new schema version",
    C.MAPPED: "name map applied when items are derived or payloads read; authored artifacts never "
    "rewritten",
    C.KEY_BEARING: "new key scheme with carry-over and new conformance vectors",
    C.BREAKING: "refused unless an explicit decision is recorded (DP-24)",
}


def route(compatibility_class: CompatibilityClass | str) -> str:
    return ROUTES[CompatibilityClass(compatibility_class)]


# --- The change record (the system classes ChangeRecord and ElementChange) ---------------------


class ElementChange(BaseModel):
    """One element change of a step, with its declared class and why it is allowed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    element: str
    change: ChangeKind
    aspect: str | None = None
    compatibility_class: CompatibilityClass
    reason: str = Field(min_length=1)
    authorized_by: str = Field(min_length=1)
    decision: str | None = None
    upcaster: str | None = None


class ChangeRecord(BaseModel):
    """One revision step: its element changes, the migration mapping and the consequences."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    from_revision: str
    to_revision: str
    changes: tuple[ElementChange, ...] = ()
    name_map: dict[str, str] = Field(default_factory=dict)
    alembic_revision: str | None = None
    key_consequences: JsonValue = None
    judgment_carry_over: JsonValue = None
    compiled_artifacts: tuple[str, ...] = ()
    source_profiles: tuple[str, ...] = ()


# --- The diff ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Change:
    """One difference between two models."""

    element: str
    change: ChangeKind
    aspect: str | None = None
    old: Any = None
    new: Any = None


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list | tuple):
        return tuple(_plain(v) for v in value)
    if isinstance(value, Mapping) or hasattr(value, "items"):
        return tuple(sorted((str(k), _plain(v)) for k, v in value.items()))
    return str(value)


def _prefix(model: Model, name: str, kind: str) -> str:
    collection = getattr(model.core.schema, kind) or {}
    return f"core:{name}" if name in collection else f"sys:{name}"


_SLOT_FACTS = (
    "range",
    "required",
    "multivalued",
    "identifier",
    "inlined",
    "inlined_as_list",
    "ifabsent",
    "pattern",
    "description",
)


def _slot_facts(slot: Any) -> dict[str, Any]:
    facts = {f: _plain(getattr(slot, f, None)) for f in _SLOT_FACTS}
    facts.update({k: _plain(v) for k, v in ci_annotations(slot).items()})
    return facts


def elements(model: Model) -> dict[str, dict[str, Any]]:
    """Every element of the model by path (module doc), with its compared facts."""
    out: dict[str, dict[str, Any]] = {}
    view = model.system
    core = model.core.schema
    out["core"] = {"version": str(core.version), **ci_annotations(core)}
    for _, module_view in model.modules():
        schema = module_view.schema
        for name, typ in (schema.types or {}).items():
            out[_prefix(model, str(name), "types")] = {
                "typeof": typ.typeof,
                "uri": typ.uri,
                "pattern": typ.pattern,
                "description": typ.description,
                **ci_annotations(typ),
            }
        for name, cls in (schema.classes or {}).items():
            path = _prefix(model, str(name), "classes")
            out[path] = {
                "is_a": cls.is_a,
                "abstract": cls.abstract,
                "description": cls.description,
                "subsets": _plain(sorted(str(s) for s in cls.in_subset or ())),
                "unique_keys": _plain(
                    sorted(
                        tuple(map(str, uk.unique_key_slots))
                        for uk in (cls.unique_keys or {}).values()
                    )
                ),
                "local_names": _plain(
                    {k: v.local_name_value for k, v in (cls.local_names or {}).items()}
                ),
                **{k: _plain(v) for k, v in ci_annotations(cls).items()},
            }
            for slot in view.class_induced_slots(str(name)):
                out[f"{path}.{slot.name}"] = _slot_facts(slot)
        for name, slot in (schema.slots or {}).items():
            out[_prefix(model, str(name), "slots")] = _slot_facts(slot)
        for name, enum in (schema.enums or {}).items():
            path = _prefix(model, str(name), "enums")
            out[path] = {
                "description": enum.description,
                **ci_annotations(enum),
                "inherits": _plain(sorted(map(str, enum.inherits or ()))),
            }
            for member in expand_enum(view, str(name)):
                out[f"{path}#{member.text}"] = {
                    "description": member.description,
                    "properties": tuple(sorted(member.properties)),
                }
    return out


def _parent(path: str) -> str | None:
    if "#" in path:
        return path.split("#", 1)[0]
    head, _, _ = path.rpartition(".")
    return head if ":" in head and "." not in head.split(":", 1)[1] else None


def diff(old: Model, new: Model) -> list[Change]:
    """The element changes from `old` to `new` (module doc), in path order."""
    a, b = elements(old), elements(new)
    out: list[Change] = []
    for path in sorted(set(a) | set(b)):
        parent = _parent(path)
        if parent is not None and ((parent in a) != (parent in b)):
            continue  # inside an added or removed element
        if path not in a:
            out.append(Change(path, ChangeKind.ADDED, new=b[path]))
        elif path not in b:
            out.append(Change(path, ChangeKind.REMOVED, old=a[path]))
        else:
            for aspect in sorted(set(a[path]) | set(b[path])):
                if a[path].get(aspect) != b[path].get(aspect):
                    out.append(
                        Change(
                            path,
                            ChangeKind.CHANGED,
                            aspect,
                            a[path].get(aspect),
                            b[path].get(aspect),
                        )
                    )
    return out


# --- Deriving the class ------------------------------------------------------------------------


@dataclass(frozen=True)
class _Context:
    model: Model

    def class_of(self, path: str) -> tuple[str, str | None]:
        """(class name, slot name or None) of a class or slot path."""
        local = path.split(":", 1)[1]
        cls, _, slot = local.partition(".")
        return cls, slot or None

    def is_table(self, cls: str) -> bool:
        element = self.model.system.get_class(cls)
        if element is None:
            return False
        subsets = {str(s) for s in element.in_subset or ()}
        store = ci_annotations(element).get("ci:store")
        return bool(subsets & {"meta", "ops", "kb", "eval"}) and store in (None, "table")

    def sql_visible(self, cls: str) -> set[str]:
        element = self.model.system.get_class(cls)
        text = ci_annotations(element).get("ci:sql_visible") if element is not None else None
        return set(str(text).split()) if text else set()

    def table_enums(self) -> set[str]:
        """The static closed sets a table column uses (their CHECKs)."""
        view = self.model.system
        out = set()
        for cls in view.all_classes():
            if self.is_table(str(cls)):
                for slot in view.class_induced_slots(str(cls)):
                    if slot.range and view.get_enum(slot.range) is not None:
                        out.add(str(slot.range))
        return out

    def lifecycle(self, enum: str) -> str | None:
        element = self.model.system.get_enum(enum)
        return None if element is None else ci_annotations(element).get("ci:lifecycle")

    def key_properties(self) -> set[str]:
        """Member properties whose subset's `ci:consumer` names keys."""
        out = set()
        for _, view in self.model.modules():
            for name, subset in (view.schema.subsets or {}).items():
                consumer = str(ci_annotations(subset).get("ci:consumer", ""))
                if re.search(r"\bkey(s|Schema)?\b", consumer, re.I):
                    out.add(str(name))
        return out


def required_class(change: Change, old: Model, new: Model) -> CompatibilityClass:
    """The class the diff gives a change (module doc)."""
    ctx = _Context(new if change.change != ChangeKind.REMOVED else old)
    path, aspect = change.element, change.aspect
    if aspect in DESCRIPTIVE_ASPECTS:
        return C.DESCRIPTIVE
    if aspect in KEY_ASPECTS:
        return C.KEY_BEARING
    if change.change == ChangeKind.REMOVED:
        return C.BREAKING
    if path == "core":
        return C.BREAKING
    if "#" in path:  # an enum member
        enum = path.split("#", 1)[0].split(":", 1)[1]
        moved = set(change.old or ()) ^ set(change.new or ())
        if aspect == "properties" and moved & (
            _Context(old).key_properties() | ctx.key_properties()
        ):
            return C.KEY_BEARING
        if ctx.lifecycle(enum) == "schema_version":
            return C.VERSION_SCOPED_ADDITIVE
        if aspect == "properties" or enum in ctx.table_enums():
            return C.RELATIONAL_ADDITIVE
        return C.NESTED_ADDITIVE
    local = path.split(":", 1)[1]
    if ctx.model.system.get_enum(local) is not None:  # an enum
        if change.change == ChangeKind.ADDED:
            if ctx.lifecycle(local) == "schema_version":
                return C.VERSION_SCOPED_ADDITIVE
            return C.NESTED_ADDITIVE
        return C.BREAKING  # lifecycle, inheritance
    if ctx.model.system.get_type(local) is not None and "." not in local:
        return C.NESTED_ADDITIVE if change.change == ChangeKind.ADDED else C.BREAKING
    cls, slot = ctx.class_of(path)
    if ctx.model.system.get_class(cls) is None:  # a free slot (core qualifiers, predicates)
        facts = change.new or {}
        if change.change == ChangeKind.ADDED:
            return C.KEY_BEARING if dict(facts).get("ci:key_role") else C.NESTED_ADDITIVE
        return _slot_change(change, table=False, visible=False)
    table = ctx.is_table(cls)
    if slot is None:  # a class
        if change.change == ChangeKind.ADDED:
            return C.RELATIONAL_ADDITIVE if table else C.NESTED_ADDITIVE
        if aspect == "ci:sql_visible":
            return C.RELATIONAL_ADDITIVE
        if aspect == "ci:invariant":
            return _widening(change, table)
        if aspect == "unique_keys":
            return (
                C.RELATIONAL_ADDITIVE
                if set(change.new or ()) <= set(change.old or ())
                else (C.BREAKING)
            )
        return C.BREAKING
    visible = slot in ctx.sql_visible(cls) or slot in _Context(old).sql_visible(cls)
    if change.change == ChangeKind.ADDED:
        facts = dict(change.new or {})
        if facts.get("ci:key_role"):
            return C.KEY_BEARING
        defaulted = facts.get("ifabsent") or facts.get("ci:generated") or facts.get("multivalued")
        if facts.get("required") and not defaulted:
            return C.BREAKING
        return C.RELATIONAL_ADDITIVE if table or visible else C.NESTED_ADDITIVE
    return _slot_change(change, table=table, visible=visible)


def _widening(change: Change, table: bool) -> CompatibilityClass:
    old = {p.strip() for p in str(change.old or "").split(";") if p.strip()}
    new = {p.strip() for p in str(change.new or "").split(";") if p.strip()}
    if new <= old:
        return C.RELATIONAL_ADDITIVE if table else C.NESTED_ADDITIVE
    return C.BREAKING


def _slot_change(change: Change, *, table: bool, visible: bool) -> CompatibilityClass:
    aspect = change.aspect
    additive = C.RELATIONAL_ADDITIVE if table or visible else C.NESTED_ADDITIVE
    if aspect in RELATIONAL_ASPECTS:
        return C.RELATIONAL_ADDITIVE
    if aspect == "required":
        return additive if not change.new else C.BREAKING
    if aspect == "pattern":
        return additive if change.new is None else C.BREAKING
    if aspect in ("ifabsent", "ci:null"):
        return additive
    return C.BREAKING  # range, multivalued, identifier, inlining, placement, other declarations


# --- Checking a record -------------------------------------------------------------------------


def _key(element: str, change: ChangeKind | str, aspect: str | None) -> tuple[str, str, str]:
    return element, str(change), aspect or ""


def derived(old: Model, new: Model, name_map: Mapping[str, str]) -> dict[tuple, CompatibilityClass]:
    """Each diff change's required class, with the name map's pairs as `mapped`."""
    changes = diff(old, new)
    out = {_key(c.element, c.change, c.aspect): required_class(c, old, new) for c in changes}
    for before, after in name_map.items():
        for key in (_key(before, ChangeKind.REMOVED, None), _key(after, ChangeKind.ADDED, None)):
            if key in out:
                out[key] = C.MAPPED
    return out


def check(record: ChangeRecord, old: Model, new: Model) -> list[str]:
    """Every problem of a change record against the diff of `old` and `new` (module doc)."""
    problems: list[str] = []
    found = derived(old, new, record.name_map)
    changes = diff(old, new)
    added = {c.element for c in changes if c.change == ChangeKind.ADDED}
    removed = {c.element for c in changes if c.change == ChangeKind.REMOVED}
    for before, after in record.name_map.items():
        if before not in removed or after not in added:
            problems.append(f"name map {before} -> {after}: not a removal and an addition")
    for path in sorted(removed - set(record.name_map)):
        owner = _parent(path) or path.split(":", 1)[0]
        twins = sorted(
            a
            for a in added - set(record.name_map.values())
            if (_parent(a) or a.split(":", 1)[0]) == owner
        )
        if twins:
            problems.append(
                f"{path} is removed and {', '.join(twins)} added: a rename is declared "
                "in the name map; otherwise the removal is breaking"
            )
    declared: dict[tuple, ElementChange] = {}
    for change in record.changes:
        key = _key(change.element, change.change, change.aspect)
        if key in declared:
            problems.append(f"{change.element}: declared twice")
        declared[key] = change
    for key in sorted(set(declared) - set(found)):
        what = f"{key[0]} {key[1]}" + (f" {key[2]}" if key[2] else "")
        problems.append(f"{what}: declared but not in the diff")
    for key, required in sorted(found.items()):
        what = f"{key[0]} {key[1]}" + (f" {key[2]}" if key[2] else "")
        change = declared.get(key)
        if change is None:
            problems.append(f"{what}: not declared (the diff gives {required})")
            continue
        problems += _check_one(what, change, required, record)
    return problems


def _check_one(
    what: str, change: ElementChange, required: CompatibilityClass, record: ChangeRecord
) -> list[str]:
    declared = change.compatibility_class
    if declared == C.BREAKING:
        if not change.decision:
            return [f"{what}: breaking is refused unless a decision is recorded (DP-24)"]
        return []
    if declared != required:
        if declared == C.NESTED_ADDITIVE and required == C.RELATIONAL_ADDITIVE:
            return [
                f"{what}: nested-additive is refused: the change touches what PostgreSQL "
                "reads (an sql_visible path, a table or a CHECK); it is relational-additive"
            ]
        if declared == C.NESTED_ADDITIVE and required == C.KEY_BEARING:
            return [f"{what}: nested-additive is refused: the change touches a key-bearing path"]
        if required == C.BREAKING:
            return [
                f"{what}: declared {declared}, but the change is breaking: refused unless "
                "declared breaking with a recorded decision (DP-24)"
            ]
        return [f"{what}: declared {declared}, but the diff gives {required}"]
    if declared == C.NESTED_ADDITIVE and not change.upcaster:
        return [f"{what}: a nested-additive change names its upcaster (absent, or a named one)"]
    if declared == C.RELATIONAL_ADDITIVE and not record.alembic_revision:
        return [f"{what}: a relational-additive change needs the record's Alembic revision"]
    if declared == C.KEY_BEARING and not record.key_consequences:
        return [f"{what}: a key-bearing change needs the record's key consequences"]
    if declared == C.INITIAL:
        return [f"{what}: initial is a payload schema's first version, not a change"]
    return []


def routes(record: ChangeRecord) -> dict[CompatibilityClass, list[str]]:
    """The record's changes by the route their class takes."""
    out: dict[CompatibilityClass, list[str]] = {}
    for change in record.changes:
        out.setdefault(change.compatibility_class, []).append(change.element)
    return out


def payload_classes_changed(
    record: ChangeRecord, model: Model
) -> Iterator[tuple[str, ElementChange]]:
    """(prefixed payload class, change) for each change inside a `ci:payload` class."""
    for change in record.changes:
        cls = change.element.split("#", 1)[0].split(".", 1)[0]
        element = model.system.get_class(cls.split(":", 1)[-1])
        if element is not None and ci_annotations(element).get("ci:payload"):
            yield cls, change
