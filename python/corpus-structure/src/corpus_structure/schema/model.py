"""The model: loading, the declaration check, enum expansion and the model revision.

Model and projections §3.1; D2 §3, §3.4; TM §2, §4. The model is LinkML in two code-release
modules here (`model/core.yaml`, `model/system.yaml`, which imports core); packs are the third
module and are S1's. Everything here is a pure function of the model files.

**The declaration check** refuses, with the element's path:
- an annotation outside the vocabulary below (D2 §3.1 to §3.4, with the four relational declarations
  probe Q-3 added: `ci:on_delete`, `ci:generated`, `ci:sql_type` and the `iff_absent` template);
- an annotation whose declaration has no consumer (`ci:record` and `ci:anchor` are reserved);
- a value outside its declaration's admitted values, an invariant that does not parse or names an
  unknown field, a `ci:key_role_when` that is not a member property of `ClaimModality`;
- member properties used wrongly. Member properties are native `in_subset` on permissible values
  (probe Q-2, `p0q.member-properties`), and they share the schema's subset namespace with element
  subsets (`structural`, `meta`, …), so a subset counts as a member property by being used on
  members. One must be used by the members of one enum only and on no element, and must be in the
  generated `core/vocab.py`'s `MEMBER_PROPERTIES`.

**Enum expressions** (`expand_enum`): own members, then each `inherits` enum in order, then each
`include` expression, then `minus` removes members by text; a member's properties come from the
enum that defines it; repeated members are kept once; an own member that collides with an
inherited or included one is refused (a pack member colliding with a core member). linkml-runtime
1.12.1's `induced_enum` does not expand these (model and projections §3.1).

**The model revision** (TM §2) is the LinkML `version`, the SHA-256 of the canonical JSON (D1 §10.1)
of the parsed core and system files, the compiler versions and the key scheme. The checked-in
log `model/revisions.yaml` is the authority; its last entry must be the current revision.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml
from linkml_runtime.linkml_model.meta import SlotDefinition
from linkml_runtime.utils.schemaview import SchemaView

from corpus_structure.core.canonical import canonical_json

MODEL_DIR = Path(__file__).resolve().parents[1] / "model"
CORE = MODEL_DIR / "core.yaml"
SYSTEM = MODEL_DIR / "system.yaml"
REVISIONS = MODEL_DIR / "revisions.yaml"

# The Stage A generator's version: bump on any change to what it writes for the same model.
GENERATOR_VERSION = "1"
GENERATOR = "corpus_structure.schema.generate"

# The vocabulary of the template invariants (D2 §3.4; iff_absent and only_when from probe Q-3).
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


# --- The declaration vocabulary ----------------------------------------------------------------


@dataclass(frozen=True)
class Declaration:
    """One project annotation: where it may stand, what values it admits (members of a model
    enum, a fixed set, or a pattern) and who reads it. No consumer: reserved, refused."""

    on: frozenset[str]
    consumers: tuple[str, ...]
    enum: str | None = None
    values: frozenset[str] | None = None
    pattern: str | None = None


def _d(on: str, consumers: str, **kw: Any) -> Declaration:
    values = kw.pop("values", None)
    return Declaration(
        frozenset(on.split()),
        tuple(c.strip() for c in consumers.split(";") if c.strip()),
        values=frozenset(values.split()) if values else None,
        **kw,
    )


_NAME = r"^[A-Za-z_][A-Za-z0-9_]*$"
VOCABULARY: Mapping[str, Declaration] = {
    # D2 §3.1 to §3.3: pack semantics (S1's compilers read them; core uses some)
    "ci:scope": _d("class", "S1 schema tables; keys (entity scope)", enum="EntityScope"),
    "ci:extract": _d(
        "class slot enum",
        "S1 GLiNER2 and prompt compilers",
        values="mention none relation llm record attribute classification",
    ),
    "ci:reify": _d("class", "S1 schema tables; consolidation (D1 §5.4)", values="true"),
    "ci:threshold": _d("class", "S1 GLiNER2 compiler (M06)", pattern=r"^0?\.[0-9]+$"),
    "ci:parameter_class": _d("class", "S1; consolidation bindings (D1 §6.1)", pattern=_NAME),
    "ci:role": _d("slot", "S1 schema tables; Stage A specs", values="predicate qualifier"),
    "ci:qualifiers": _d("slot", "S1 schema tables and batch models"),
    "ci:identity_qualifiers": _d("slot", "S1 KeySchema compiler"),
    "ci:functional": _d("slot", "consolidation slots (D5 §5.4)", values="true"),
    "ci:param_map": _d("slot", "S1 rule view; consolidation bindings", pattern=_NAME),
    "ci:applies_to": _d("enum", "S1 GLiNER2 compiler", pattern=_NAME),
    "ci:target": _d("enum", "S1 GLiNER2 compiler", pattern=r"^[a-z_]+( [a-z_]+)*$"),
    "ci:arity": _d("member", "S1 side table (D2 §5)", values="1 2 2+"),
    "ci:args": _d("member", "S1 side table (D2 §5)", pattern=_NAME),
    "ci:symmetric": _d("member", "keys (D1 §7 argument order)", values="true"),
    "ci:z3": _d("member", "verifiers (M20)", pattern=_NAME),
    "ci:record": _d("slot", ""),  # reserved (D2 §3.2): no v0 consumer
    "ci:anchor": _d("slot", ""),  # reserved (D2 §3.2): no v0 consumer
    # D2 §3.4: the model's declarations
    "ci:lifecycle": _d("enum", "Stage A vocab.py; M2 CHECKs and member rows", enum="Lifecycle"),
    "ci:key_role": _d("slot", "Stage A qualifier specs; KeySchema (F2d)", enum="KeyRole"),
    "ci:key_role_when": _d("slot", "Stage A qualifier specs; KeySchema (F2d)", pattern=_NAME),
    "ci:case": _d("slot attribute class", "Stage A qualifier specs; KeySchema", enum="CaseRule"),
    "ci:form": _d("attribute", "interim mirror guard; Stage B", values="model stored consolidated"),
    "ci:required_in": _d("attribute", "interim mirror guard; Stage B", values="model stored"),
    "ci:stored_range": _d("slot", "Stage A qualifier specs; interim mirror guard", pattern=_NAME),
    "ci:invariant": _d("class", "Stage A validators; M2 CHECKs"),
    "ci:store": _d("class slot attribute", "Stage A specs; M2; M3", values="table nested edge"),
    "ci:payload": _d("class", "M4 payload-schema registry", pattern=r"^[a-z_]+$"),
    "ci:sql_visible": _d("class", "M4 change classifier; M2 overlay check"),
    "ci:null": _d("attribute slot", "M3 Arrow compiler", values="never json"),
    "ci:key_scheme": _d("schema", "Stage A revision; runs (O1); E1", pattern=r"^[1-9][0-9]*$"),
    # probe Q-3's relational declarations
    "ci:on_delete": _d("attribute slot", "M2 MetaData", values="cascade set_null restrict"),
    "ci:generated": _d("attribute slot", "M2 MetaData compiler", values="insert_time"),
    "ci:sql_type": _d("type", "M2 MetaData compiler", pattern=r"^[a-z][a-z0-9_]*$"),
}  # fmt: skip


# --- Loading -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Member:
    """One member of an expanded enum, with the enum that defines it."""

    text: str
    description: str | None
    properties: tuple[str, ...]
    defined_in: str


@dataclass
class Model:
    """The loaded model: the core module, and the system module with core imported."""

    core: View
    system: View
    paths: tuple[Path, Path] = (CORE, SYSTEM)
    _expanded: dict[str, list[Member]] = field(default_factory=dict)

    def modules(self) -> Iterator[tuple[str, View]]:
        yield "core", self.core
        yield "system", self.system

    def enums(self) -> Iterator[tuple[str, Any]]:
        """Every enum of core then system, in file order, with its module."""
        for module, view in self.modules():
            for enum in view.schema.enums.values():
                yield module, enum

    def view_of(self, module: str) -> View:
        return self.core if module == "core" else self.system

    def expanded(self, name: str) -> list[Member]:
        if name not in self._expanded:
            self._expanded[name] = expand_enum(self.system, name)
        return self._expanded[name]

    @cached_property
    def member_properties(self) -> dict[str, str]:
        """Member property -> the enum whose members use it (first use)."""
        out: dict[str, str] = {}
        for _, enum in self.enums():
            for pv in enum.permissible_values.values():
                for prop in pv.in_subset or ():
                    out.setdefault(str(prop), str(enum.name))
        return out


def load(core: Path = CORE, system: Path = SYSTEM) -> Model:
    """Both modules through `SchemaView`; system resolves its `core` import beside itself."""
    return Model(SchemaView(str(core)), SchemaView(str(system)), (core, system))


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
        Member(str(text), pv.description, tuple(str(p) for p in pv.in_subset or ()), enum_name)
        for text, pv in pvs.items()
    ]


def _expression(view: View, owner: str, expr: Any, seen: tuple[str, ...]) -> list[Member]:
    for unsupported in ("reachable_from", "matches", "concepts"):
        if getattr(expr, unsupported, None):
            raise EnumExpansionError(f"{owner}: {unsupported} is not expanded")
    out = _members_of(owner, expr.permissible_values or {})
    for parent in expr.inherits or ():
        out += _expand(view, str(parent), seen)
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
    own = _members_of(name, enum.permissible_values or {})
    brought: list[Member] = []
    for parent in enum.inherits or ():
        brought += _expand(view, str(parent), seen)
    for expr in enum.include or ():
        brought += _expression(view, name, expr, seen)
    own_texts = {m.text for m in own}
    for member in brought:
        if member.text in own_texts:
            raise EnumExpansionError(
                f"{name}: member {member.text!r} collides with {member.defined_in}'s member"
            )
    removed: set[str] = set()
    for expr in enum.minus or ():
        removed |= {m.text for m in _expression(view, name, expr, seen)}
    out: list[Member] = []
    kept: set[str] = set()
    for member in (*own, *brought):
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


def _elements(model: Model) -> Iterator[tuple[str, str, Any, Any]]:
    """(path, kind, element, owning class) for every annotatable element of both modules."""
    for module, view in model.modules():
        schema = view.schema
        yield f"{module}", "schema", schema, None
        for name, typ in (schema.types or {}).items():
            yield f"{module}.types.{name}", "type", typ, None
        for name, cls in (schema.classes or {}).items():
            yield f"{module}.classes.{name}", "class", cls, None
            for attr_name, attr in (cls.attributes or {}).items():
                yield f"{module}.classes.{name}.{attr_name}", "attribute", attr, cls
            for usage_name, usage in (cls.slot_usage or {}).items():
                yield f"{module}.classes.{name}.slot_usage.{usage_name}", "attribute", usage, cls
        for name, slot in (schema.slots or {}).items():
            yield f"{module}.slots.{name}", "slot", slot, None
        for name, enum in (schema.enums or {}).items():
            yield f"{module}.enums.{name}", "enum", enum, None
            for text, pv in (enum.permissible_values or {}).items():
                yield f"{module}.enums.{name}.{text}", "member", pv, None


def _admitted(model: Model, decl: Declaration, value: Any) -> bool:
    text = str(value).lower() if isinstance(value, bool) else str(value)
    if decl.enum is not None:
        return text in {m.text for m in model.expanded(decl.enum)}
    if decl.values is not None:
        return text in decl.values
    if decl.pattern is not None:
        return re.match(decl.pattern, text) is not None
    return bool(text.strip())


def check(model: Model, generated_properties: Mapping[str, object] | None = None) -> list[str]:
    """Every problem of the model's declarations (module doc); empty when it passes.
    `generated_properties` is the generated vocabulary's `MEMBER_PROPERTIES`, checked if given."""
    problems: list[str] = []
    for path, kind, element, _ in _elements(model):
        for tag, value in ci_annotations(element).items():
            decl = VOCABULARY.get(tag)
            if decl is None:
                problems.append(f"{path}: {tag} is not in the declaration vocabulary")
                continue
            if not decl.consumers:
                problems.append(f"{path}: {tag} has no consumer (reserved)")
                continue
            if kind not in decl.on:
                problems.append(f"{path}: {tag} is not declared on a {kind}")
                continue
            if not _admitted(model, decl, value):
                problems.append(f"{path}: {tag} value {value!r} is not admitted")
            problems += _check_value(model, path, tag, str(value), element)
    problems += _check_member_properties(model, generated_properties)
    for module, enum in model.enums():
        try:
            model.expanded(str(enum.name))
        except EnumExpansionError as error:
            problems.append(f"{module}.enums.{enum.name}: {error}")
        if "ci:lifecycle" not in ci_annotations(enum):
            problems.append(f"{module}.enums.{enum.name}: a closed set declares its ci:lifecycle")
    return problems


def _check_value(model: Model, path: str, tag: str, value: str, element: Any) -> list[str]:
    view = model.system
    if tag == "ci:invariant":
        try:
            parsed = parse_invariants(value)
        except ValueError as error:
            return [f"{path}: {error}"]
        slots = {str(s.name) for s in view.class_induced_slots(str(element.name))}
        out = []
        for inv in parsed:
            for name in (*inv.fields, *((inv.condition,) if inv.condition else ())):
                if name not in slots:
                    out.append(f"{path}: invariant {inv} names unknown field {name!r}")
            if inv.condition and inv.condition in slots:
                rng = view.induced_slot(inv.condition, str(element.name)).range
                if rng and view.get_enum(rng) is not None:
                    members = {m.text for m in model.expanded(rng)}
                    out += [f"{path}: invariant {inv}: {v!r} is not a {rng} member"
                            for v in inv.values if v not in members]  # fmt: skip
        return out
    if tag == "ci:key_role_when":
        props = {p for p, e in model.member_properties.items() if e == "ClaimModality"}
        if value not in props:
            return [f"{path}: ci:key_role_when {value!r} is not a ClaimModality member property"]
    if tag == "ci:stored_range" and view.get_class(value) is None:
        return [f"{path}: ci:stored_range {value!r} is not a class"]
    if tag == "ci:required_in" and isinstance(element, SlotDefinition):
        form = ci_annotations(element).get("ci:form")
        if form is not None and form != value:
            return [f"{path}: required in {value} but present only in {form}"]
    return []


def _check_member_properties(model: Model, generated: Mapping[str, object] | None) -> list[str]:
    problems: list[str] = []
    users: dict[str, set[str]] = {}
    for _, enum in model.enums():
        for pv in enum.permissible_values.values():
            for prop in pv.in_subset or ():
                users.setdefault(str(prop), set()).add(str(enum.name))
    on_elements: set[str] = set()
    for _, view in model.modules():
        for collection in (view.schema.classes, view.schema.slots, view.schema.enums):
            for element in (collection or {}).values():
                on_elements |= {str(s) for s in element.in_subset or ()}
    for prop, enums in sorted(users.items()):
        if len(enums) > 1:
            problems.append(f"member property {prop} is used by {sorted(enums)}; one enum only")
        if prop in on_elements:
            problems.append(f"member property {prop} is also an element subset")
        if generated is not None and prop not in generated:
            problems.append(f"member property {prop} is not in the generated vocabulary")
    return problems


# --- The model revision ------------------------------------------------------------------------


@dataclass(frozen=True)
class Revision:
    """A model revision (TM §2)."""

    label: str
    content_hash: str
    key_scheme: int
    compilers: Mapping[str, str]

    def entry(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "content_hash": self.content_hash,
            "key_scheme": self.key_scheme,
            "compilers": dict(sorted(self.compilers.items())),
        }


def content_hash(core: Path = CORE, system: Path = SYSTEM) -> str:
    """SHA-256 of the canonical JSON of the parsed core and system files (D2 §2's rule)."""
    parsed = {
        "core": yaml.safe_load(core.read_text(encoding="utf-8")),
        "system": yaml.safe_load(system.read_text(encoding="utf-8")),
    }
    return hashlib.sha256(canonical_json(parsed)).hexdigest()


def compilers() -> dict[str, str]:
    """The compiler versions a revision records: linkml-runtime and each generator's own."""
    return {"linkml-runtime": importlib.metadata.version("linkml-runtime"),
            GENERATOR: GENERATOR_VERSION}  # fmt: skip


def revision(model: Model) -> Revision:
    core, system = model.core.schema, model.system.schema
    if core.version != system.version:
        raise ModelError([f"core is version {core.version} but system {system.version}"])
    scheme = ci_annotations(core).get("ci:key_scheme")
    if not isinstance(scheme, int):
        raise ModelError(["core declares no integer ci:key_scheme"])
    return Revision(str(core.version), content_hash(*model.paths), scheme, compilers())


def read_log(path: Path = REVISIONS) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return list(yaml.safe_load(path.read_text(encoding="utf-8")) or [])


def check_log(current: Revision, log: list[dict[str, Any]]) -> list[str]:
    """The log's shape, and that its last entry is the current revision."""
    if not log:
        return ["the revision log is empty"]
    problems: list[str] = []
    keys = {"label", "content_hash", "key_scheme", "compilers", "parent", "change_record"}
    for i, entry in enumerate(log):
        if set(entry) != keys:
            problems.append(f"revision {i}: fields {sorted(entry)} are not {sorted(keys)}")
            continue
        if i == 0 and (entry["parent"] is not None or entry["change_record"] is not None):
            problems.append("the first revision has no parent and no change record")
        if i > 0 and (entry["parent"] != log[i - 1]["content_hash"] or not entry["change_record"]):
            problems.append(f"revision {i}: names its parent's content hash and a change record")
    last = {k: log[-1].get(k) for k in ("label", "content_hash", "key_scheme", "compilers")}
    if last != current.entry():
        problems.append(
            f"the model is not its logged revision: logged {last}, now {current.entry()}"
        )
    return problems


def render_log(log: list[dict[str, Any]]) -> str:
    """The log's YAML text, written deterministically."""
    header = (
        "# The model-revision log (model and projections §3.1; ADR-0022): the authority that\n"
        "# meta.model_revision projects. Each entry is a revision of model/core.yaml and\n"
        "# model/system.yaml; a revision after the first names its parent and its change record.\n"
    )
    return header + yaml.safe_dump(log, sort_keys=False, allow_unicode=True, width=100)


def record_root(current: Revision, log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The log with its root entry set to the current revision, while the root is the only
    entry (before the first release; a later revision needs a change record, P0-M-4)."""
    if len(log) > 1:
        if check_log(current, log):
            raise ModelError(["the model changed after its first revision: add a revision with "
                              "its change record (P0-M-4)"])  # fmt: skip
        return log
    return [{**current.entry(), "parent": None, "change_record": None}]
