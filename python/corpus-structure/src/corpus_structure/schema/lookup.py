"""The typed schema lookup, the compiled `KeySchema` and the pack name map (P0-S-1).

Schema and rules §3.2; D2 §3, §7.1; ADR-0023; X2-01. `SchemaView` is read only here, while
compiling; `SchemaLookup` is frozen (dataclasses and tuples), so request-time code never touches
SchemaView's caches. Object kinds, class kinds and slot roles are derived from the schema (D2 §3),
never written.

**Names.** Outside the pack files and the model-facing batch every element carries its schema's
prefix (`stat:has_distribution`, `core:proves`), from `get_uri(expand=False)`. A pack member of a
version-scoped core set is written `<prefix>:<name>` (`toy:clause`), while core members stay bare
(`theorem`): one spelling for the stored form, the compiled rows and source profiles alike. The
name map holds local <-> prefixed for every class, slot, enum and pack member of the version, and a
local name that maps to two prefixed names is a compile error naming both.

**The compiled `KeySchema`** (foundations' type, F2d) gets its pack half here: per predicate, a
`QualifierSpec` for each listed schema qualifier, with its role from `ci:key_role` or, else, from
the predicate's `ci:identity_qualifiers` (identity when listed, meaning otherwise) and its
canonical form by declared range; each map range's entry value spec; the version's
`ClaimModality` member properties (core and pack members, each from its own enum); the case policy
of class labels and identity slots; identity keys, entity identity slots, symmetric condition
predicates and the prefixed predicates. The core half is the model's.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from corpus_structure.core._model import names as core_names
from corpus_structure.core._model.qualifiers import MISSING, QualifierSpec
from corpus_structure.core.keys import KeySchema, ValueSpec
from corpus_structure.core.vocab import CanonicalForm, CaseRule, KeyRole, QualifierStore
from corpus_structure.schema.model import Member, ci_annotations, expand_enum
from corpus_structure.schema.pack import Pack, PackError, version_members

VALUE_ROOT, ENTITY_ROOT, CONDITION, MAP_ENTRY = "Value", "Entity", "Condition", "MapEntry"
# Value class -> its D1 tag, for the classes the model declares (read by `t` equals_string).
SCALARS = {"string": "text", "integer": "number", "boolean": "bool"}
CANONICAL_BY_KIND: Mapping[str, CanonicalForm] = {
    "formula": CanonicalForm.TOKEN_FORM,
    "set": CanonicalForm.TOKEN_FORM,
    "text": CanonicalForm.TEXT_FORM,
    "phrase": CanonicalForm.TEXT_FORM,
    "enum": CanonicalForm.ENUM,
    "entity": CanonicalForm.ENTITY_KEY,
    "interval": CanonicalForm.INTERVAL,
    "number": CanonicalForm.NUMBER,
    "date": CanonicalForm.VERBATIM,
    "bool": CanonicalForm.VERBATIM,
    "map": CanonicalForm.MAP,
    "condition": CanonicalForm.CONDITION,
}


def _one(text: Any) -> str:
    return " ".join(str(text or "").split())


@dataclass(frozen=True)
class EntityClass:
    name: str
    prefixed: str
    scope: str | None
    identity_keys: tuple[str, ...]  # prefixed identity slots (unique_keys)
    entity_identity: tuple[str, ...]  # those of them that hold entities
    label_case: CaseRule
    identity_case: Mapping[str, CaseRule]  # prefixed identity slot -> its ci:case
    extract: str | None
    parameter_class: str | None
    title: str | None
    examples: tuple[str, ...]
    description: str
    ancestors: tuple[str, ...]


@dataclass(frozen=True)
class Predicate:
    name: str
    prefixed: str
    domain: str
    range: str
    object_kind: str
    qualifiers: tuple[str, ...]  # local names of its schema qualifiers
    identity_qualifiers: tuple[str, ...]
    subsets: tuple[str, ...]
    functional: bool
    symmetric: bool  # native: inference declarations a recursive-SQL compiler reads
    transitive: bool
    inverse: str | None
    param_map: str | None
    extract: str | None
    description: str


@dataclass(frozen=True)
class Qualifier:
    name: str
    prefixed: str
    range: str
    object_kind: str
    map_value_range: str | None
    map_value_kind: str | None
    key_role: str | None  # declared ci:key_role, or None
    key_role_when: str | None
    case: CaseRule
    core: bool
    multivalued: bool
    description: str


@dataclass(frozen=True)
class EnumMember:
    text: str  # local (model-facing) name
    stored: str  # as stored: bare for a core member, <prefix>:<text> for a pack one
    description: str
    properties: tuple[str, ...]
    defined_in: str
    annotations: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnumSet:
    name: str
    prefixed: str
    lifecycle: str
    members: tuple[EnumMember, ...]
    annotations: Mapping[str, Any] = field(default_factory=dict)
    description: str = ""

    def property(self, prop: str) -> frozenset[str]:
        return frozenset(m.stored for m in self.members if prop in m.properties)


@dataclass(frozen=True)
class ConditionPredicate:
    name: str
    arity: str | None
    args: str | None
    symmetric: bool
    z3: str | None


@dataclass(frozen=True)
class SchemaLookup:
    """The frozen facts of one schema version's packs (schema and rules §3.2)."""

    packs: tuple[str, ...]
    prefixes: Mapping[str, str]  # pack -> its prefix
    entity_classes: Mapping[str, EntityClass]
    value_classes: Mapping[str, str]  # value class -> tag
    predicates: Mapping[str, Predicate]
    qualifiers: Mapping[str, Qualifier]
    enums: Mapping[str, EnumSet]  # the packs' enums
    version_sets: Mapping[str, EnumSet]  # StatementKind, ClaimModality: core and pack members
    condition_predicates: Mapping[str, ConditionPredicate]
    subsets: Mapping[str, tuple[str, tuple[str, ...]]]  # name -> (description, predicates)
    ancestors: Mapping[str, tuple[str, ...]]
    class_names: Mapping[str, str]  # every class (core and pack) -> its prefixed name

    def applicable_predicates(self, cls: str) -> tuple[str, ...]:
        """Predicates whose domain is the class or an ancestor (mixins included; L-08)."""
        anc = set(self.ancestors.get(cls, ()))
        return tuple(p for p, i in self.predicates.items() if i.domain in anc)

    def batch_entity_types(self) -> tuple[str, ...]:
        """The classes an `entities[]` item may name: every entity class but `Statement` and
        `ExternalReference`, which have items of their own (S4 V2)."""
        return tuple(n for n in self.entity_classes if n not in ("Statement", "ExternalReference"))


# --- Building the lookup -----------------------------------------------------------------------


class _Builder:
    def __init__(self, pack: Pack) -> None:
        self.pack = pack
        self.view = pack.view
        self.classes = {str(n): c for n, c in self.view.all_classes().items()}

    def ancestors(self, cls: str) -> tuple[str, ...]:
        return tuple(self.view.class_ancestors(cls)) if cls in self.classes else ()

    def prefixed(self, element: Any) -> str:
        return str(self.view.get_uri(element, expand=False))

    def value_classes(self) -> dict[str, str]:
        out = {}
        for n in sorted(self.classes):
            if n != VALUE_ROOT and VALUE_ROOT in self.ancestors(n):
                out[n] = str(self.view.induced_slot("t", n).equals_string)
        return out

    def object_kind(self, rng: str | None) -> tuple[str, str | None, str | None]:
        """(object kind, map value range, map value kind) derived from a slot range (D2 §3)."""
        rng = rng or "string"
        values = self.value_classes()
        if rng in values:
            return values[rng], None, None
        if rng == CONDITION:
            return "condition", None, None
        if self.view.get_enum(rng) is not None:
            return "enum", None, None
        if rng in self.classes and MAP_ENTRY in self.ancestors(rng):
            vr = str(self.view.induced_slot("value", rng).range or "string")
            return "map", vr, values.get(vr) or SCALARS.get(vr, "text")
        if rng in self.classes and (ENTITY_ROOT in self.ancestors(rng) or self.classes[rng].mixin):
            return "entity", None, None
        return SCALARS.get(rng, "text"), None, None

    def identity_keys(self, cls: str) -> tuple[str, ...]:
        for name in self.ancestors(cls):
            keys = self.classes[name].unique_keys or {}
            for key in sorted(keys):
                return tuple(str(s) for s in keys[key].unique_key_slots)
        return ()

    def entity_classes(self) -> dict[str, EntityClass]:
        out = {}
        for n in sorted(self.classes):
            c = self.classes[n]
            if n == ENTITY_ROOT or ENTITY_ROOT not in self.ancestors(n) or c.abstract or c.mixin:
                continue
            ann = ci_annotations(c)
            keys = self.identity_keys(n)
            entity_slots = tuple(
                s
                for s in keys
                if self.object_kind(self.view.induced_slot(s, n).range)[0] == "entity"
            )
            out[n] = EntityClass(
                name=n,
                prefixed=self.prefixed(c),
                scope=ann.get("ci:scope"),
                identity_keys=tuple(self.prefixed(self.view.get_slot(s)) for s in keys),
                entity_identity=tuple(self.prefixed(self.view.get_slot(s)) for s in entity_slots),
                label_case=CaseRule(ann.get("ci:case", "fold")),
                identity_case={
                    self.prefixed(self.view.get_slot(s)): CaseRule(
                        ci_annotations(self.view.get_slot(s)).get("ci:case", "fold")
                    )
                    for s in keys
                },
                extract=ann.get("ci:extract"),
                parameter_class=ann.get("ci:parameter_class"),
                title=str(c.title) if c.title else None,
                examples=tuple(str(e.value) for e in c.examples or ()),
                description=_one(c.description),
                ancestors=self.ancestors(n),
            )
        return out

    def predicates(self) -> dict[str, Predicate]:
        out = {}
        for name in sorted(self.view.all_slots()):
            s = self.view.get_slot(name)
            a = ci_annotations(s)
            if a.get("ci:role") != "predicate":
                continue
            ind = self.view.induced_slot(name)
            out[str(name)] = Predicate(
                name=str(name),
                prefixed=self.prefixed(s),
                domain=str(ind.domain),
                range=str(ind.range),
                object_kind=self.object_kind(ind.range)[0],
                qualifiers=tuple(str(a.get("ci:qualifiers", "")).split()),
                identity_qualifiers=tuple(str(a.get("ci:identity_qualifiers", "")).split()),
                subsets=tuple(sorted(str(x) for x in s.in_subset or ())),
                functional=bool(a.get("ci:functional", False)),
                symmetric=bool(s.symmetric),
                transitive=bool(s.transitive),
                inverse=str(s.inverse) if s.inverse else None,
                param_map=a.get("ci:param_map"),
                extract=a.get("ci:extract"),
                description=_one(s.description),
            )
        return out

    def qualifiers(self) -> dict[str, Qualifier]:
        out = {}
        for name in sorted(self.view.all_slots()):
            s = self.view.get_slot(name)
            a = ci_annotations(s)
            if a.get("ci:role") != "qualifier":
                continue
            ind = self.view.induced_slot(name)
            kind, mvr, mvk = self.object_kind(ind.range)
            prefixed = self.prefixed(s)
            out[str(name)] = Qualifier(
                name=str(name),
                prefixed=prefixed,
                range=str(ind.range),
                object_kind=kind,
                map_value_range=mvr,
                map_value_kind=mvk,
                key_role=a.get("ci:key_role"),
                key_role_when=a.get("ci:key_role_when"),
                case=CaseRule(a.get("ci:case", "fold")),
                core=prefixed.startswith(f"{core_names.PREFIX}:"),
                multivalued=bool(ind.multivalued),
                description=_one(s.description),
            )
        return out

    def enum_set(self, name: str, members: Sequence[Member]) -> EnumSet:
        enum = self.view.get_enum(name)
        own_prefix = self.pack.prefix
        out = []
        for m in members:
            defining = self.view.get_enum(m.defined_in)
            core = self.prefixed(defining).startswith(f"{core_names.PREFIX}:")
            pv = defining.permissible_values[m.text]
            out.append(
                EnumMember(
                    text=m.text,
                    stored=m.text if core else f"{own_prefix}:{m.text}",
                    description=_one(m.description),
                    properties=m.properties,
                    defined_in=m.defined_in,
                    annotations=ci_annotations(pv),
                )
            )
        ann = ci_annotations(enum)
        return EnumSet(
            name=name,
            prefixed=self.prefixed(enum),
            lifecycle=str(ann.get("ci:lifecycle", "schema_version")),
            members=tuple(out),
            annotations=ann,
            description=_one(enum.description),
        )


def build_lookup(packs: Sequence[Pack]) -> SchemaLookup:
    """The lookup of the packs compiled into one schema version; their local names must be unique
    across them (`name_map` checks it first)."""
    if not packs:
        raise PackError(["no pack to compile"])
    name_map(packs)  # refuses colliding local names before the merge
    entity_classes: dict[str, EntityClass] = {}
    values: dict[str, str] = {}
    predicates: dict[str, Predicate] = {}
    qualifiers: dict[str, Qualifier] = {}
    enums: dict[str, EnumSet] = {}
    version_sets: dict[str, list[EnumMember]] = {}
    conditions: dict[str, ConditionPredicate] = {}
    subsets: dict[str, tuple[str, list[str]]] = {}
    ancestors: dict[str, tuple[str, ...]] = {}
    class_names: dict[str, str] = {}
    for pack in packs:
        b = _Builder(pack)
        entity_classes.update(b.entity_classes())
        values.update(b.value_classes())
        predicates.update(b.predicates())
        qualifiers.update(b.qualifiers())
        ancestors.update({n: b.ancestors(n) for n in b.classes})
        class_names.update({n: b.prefixed(c) for n, c in b.classes.items()})
        for name in pack.view.schema.enums or {}:
            enums[str(name)] = b.enum_set(str(name), expand_enum(pack.view, str(name)))
        for core_set in ("StatementKind", "ClaimModality"):
            merged = version_sets.setdefault(core_set, [])
            seen = {m.stored for m in merged}
            for m in b.enum_set(core_set, version_members(pack, core_set)).members:
                if m.stored not in seen:
                    merged.append(m)
                    seen.add(m.stored)
        cp = pack.view.get_enum("ConditionPredicate")
        for text, pv in (cp.permissible_values if cp is not None else {}).items():
            a = ci_annotations(pv)
            conditions[str(text)] = ConditionPredicate(
                str(text),
                a.get("ci:arity"),
                a.get("ci:args"),
                str(a.get("ci:symmetric", "")).lower() == "true",
                a.get("ci:z3"),
            )
        for name in pack.view.all_subsets():
            sub = pack.view.get_subset(name)
            if ci_annotations(sub).get("ci:consumer") is not None:
                continue  # a member property, not a predicate subset
            _, members = subsets.setdefault(str(name), (_one(sub.description), []))
            members += [p for p, i in b.predicates().items() if name in i.subsets]
    core_view = packs[0].view
    sets = {}
    for core_set, members in version_sets.items():
        enum = core_view.get_enum(core_set)
        sets[core_set] = EnumSet(
            core_set,
            str(core_view.get_uri(enum, expand=False)),
            "schema_version",
            tuple(members),
            ci_annotations(enum),
            _one(enum.description),
        )
    return SchemaLookup(
        packs=tuple(p.name for p in packs),
        prefixes={p.name: p.prefix for p in packs},
        entity_classes=entity_classes,
        value_classes=values,
        predicates=predicates,
        qualifiers=qualifiers,
        enums=enums,
        version_sets=sets,
        condition_predicates=conditions,
        subsets={k: (d, tuple(sorted(set(m)))) for k, (d, m) in subsets.items()},
        ancestors=ancestors,
        class_names=class_names,
    )


# --- The name map (X2-01, the pack half) -------------------------------------------------------


@dataclass(frozen=True)
class NameMap:
    """Local <-> prefixed names of the version's elements, core and pack."""

    to_prefixed: Mapping[str, str]
    to_local: Mapping[str, str]

    def prefixed(self, local: str) -> str:
        return self.to_prefixed[local]

    def local(self, prefixed: str) -> str:
        return self.to_local[prefixed]


def _pack_names(pack: Pack) -> Iterable[tuple[str, str, str]]:
    """(kind, local, prefixed) of a pack's own elements and its version-scoped members."""
    view, schema = pack.view, pack.view.schema
    for kind, collection in (
        ("class", schema.classes),
        ("slot", schema.slots),
        ("enum", schema.enums),
    ):
        for name, element in (collection or {}).items():
            yield kind, str(name), str(view.get_uri(element, expand=False))
    for core_set in ("StatementKind", "ClaimModality"):
        core = {m.text for m in version_members(pack, core_set) if m.defined_in == core_set}
        for m in version_members(pack, core_set):
            if m.text not in core:
                yield f"{core_set} member", m.text, f"{pack.prefix}:{m.text}"


def name_map(packs: Sequence[Pack]) -> NameMap:
    """The version's name map; a local name with two prefixed names is a `PackError` naming both."""
    seen: dict[str, set[str]] = {}
    for local, prefixed in core_names.LOCAL_TO_PREFIXED.items():
        seen.setdefault(local, set()).add(prefixed)
    for pack in packs:
        for _, local, prefixed in _pack_names(pack):
            seen.setdefault(local, set()).add(prefixed)
    problems = [
        f"local name {local!r} names {' and '.join(sorted(p))} in one schema version"
        for local, p in sorted(seen.items())
        if len(p) > 1
    ]
    if problems:
        raise PackError(problems)
    to_prefixed = {local: next(iter(p)) for local, p in seen.items()}
    return NameMap(to_prefixed, {v: k for k, v in to_prefixed.items()})


# --- The compiled KeySchema (pack half) --------------------------------------------------------


def _value_spec(kind: str, rng: str, case: CaseRule) -> ValueSpec:
    if kind == "text" and rng == "string":
        return ValueSpec(rng, CanonicalForm.IDENTIFIER, case)
    return ValueSpec(rng, CANONICAL_BY_KIND[kind], case)


def qualifier_spec(q: Qualifier, role: KeyRole, prefixed_range: str) -> QualifierSpec:
    """A schema qualifier's specification (model and projections §3.2)."""
    if q.object_kind == "text" and q.range == "string":
        canonical = CanonicalForm.IDENTIFIER
    else:
        canonical = CANONICAL_BY_KIND[q.object_kind]
    return QualifierSpec(
        name=q.prefixed,
        local_name=q.name,
        range=prefixed_range,
        default=MISSING,
        key_role=role,
        key_role_when=q.key_role_when,
        canonical=canonical,
        case=q.case,
        store=QualifierStore.EDGE if q.object_kind == "entity" else QualifierStore.JSON,
    )


def compile_key_schema(lookup: SchemaLookup, key_scheme: int) -> KeySchema:
    """The `KeySchema` of the version: the pack half compiled from the lookup, joined with the
    model's core half (module doc)."""
    qualifiers: dict[str, tuple[QualifierSpec, ...]] = {}
    map_values: dict[str, ValueSpec] = {}
    for p in lookup.predicates.values():
        specs = []
        for name in p.qualifiers:
            q = lookup.qualifiers[name]
            if q.key_role is not None:
                role = KeyRole(q.key_role)
            else:
                role = KeyRole.IDENTITY if name in p.identity_qualifiers else KeyRole.MEANING
            rng = q.range
            if q.object_kind == "map":
                rng = lookup.class_names[q.range]
                assert q.map_value_kind is not None and q.map_value_range is not None
                map_values[rng] = _value_spec(q.map_value_kind, q.map_value_range, q.case)
            specs.append(qualifier_spec(q, role, rng))
        if specs:
            qualifiers[p.prefixed] = tuple(specs)
    modality = lookup.version_sets["ClaimModality"]
    properties = {prop for m in modality.members for prop in m.properties}
    slot_case = {}
    for q in lookup.qualifiers.values():
        if q.case is CaseRule.PRESERVE:
            slot_case[q.prefixed] = q.case
    for e in lookup.entity_classes.values():
        slot_case.update(e.identity_case)
    return KeySchema(
        identity_keys={
            e.prefixed: e.identity_keys for e in lookup.entity_classes.values() if e.identity_keys
        },
        entity_identity={
            e.prefixed: e.entity_identity
            for e in lookup.entity_classes.values()
            if e.entity_identity
        },
        predicates=frozenset(p.prefixed for p in lookup.predicates.values()),
        qualifiers=qualifiers,
        map_values=map_values,
        modality_properties={prop: modality.property(prop) for prop in sorted(properties)},
        label_case={
            e.prefixed: e.label_case
            for e in lookup.entity_classes.values()
            if e.label_case is CaseRule.PRESERVE
        },
        slot_case={k: v for k, v in slot_case.items() if v is CaseRule.PRESERVE},
        symmetric_predicates=frozenset(
            n for n, c in lookup.condition_predicates.items() if c.symmetric
        ),
        key_scheme=key_scheme,
    )
