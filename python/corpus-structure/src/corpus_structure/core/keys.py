"""Canonical forms, label normalization and the entity, statement, claim and group keys.

D1 §6.2, §7, §10.1; D5 §3.3, §5.2, §5.3; foundations §3.6.

Every function here is pure. Schema facts (`KeySchema`) and label rules (`LabelRules`) arrive as
data from S1 and the pack, and the rendition (`KeyContext`) from the caller; nothing reads the
database or a pack file. Which claims are alternatives, and on what they disagree, is C1's
decision, passed to `key_claims` as `members`.

Canonical forms consume the typed model (R03): they pattern-match on the value and condition
unions with `typing.assert_never`, so an unknown value kind or operator is unrepresentable after
validation. A condition tree has one traversal (`condition_nodes`), which feeds `claim_refs`,
`canonical_condition` and binding collection. Canonical JSON serializes only the final key parts
(and orders `and`/`or` arguments and symmetric operands, as D1 §7 defines). Phrase text enters by
its text form alone, so authored and stored inputs give the same parts. Schema qualifiers arrive as
raw JSON until S1 types them; `qualifier_value` turns one into typed values first (by shape until
F2d's canonical form by range), refusing what is no typed value.

A candidate that cannot be keyed is dropped with a `DropReason` code (`Drop`); its message is a
projection of the code, never the reason itself.

**References resolve by kind** (F2e; R04, DA-006): a `Resolver` has one lookup per kind
(`entity`, `statement`, `claim`, and `subject` for an entity or a statement), and a reference
naming a candidate of another kind is dropped as `WRONG_KIND_REFERENCE`, never keyed as the kind it
names. An `ExternalReference` (D1 §4.4) is keyed `xrf` by its citing statement's key, its quote's
text form and its link target, and stands where it is cited (an entity, or a claim in a `claim`
condition or binding); once consolidation has resolved it, the resolved statement's key stands in
its place (a stated stability limit, D1 §10.3), and an unresolved one is never a dropped claim.
The candidate set names its rendition, and keying refuses a context of another rendition.

**Key scheme 1 is frozen** (F2e, after `s5.keys-property` froze `core/tex.py`): conformance vector
v1 (`tests/core/test_conformance.py`) pins each output by hand-written parts. A change to any output
is M4's `key-bearing` class: a new scheme, a carry-over map (`carry_over`) and a new vector.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import Any, Literal, Self, assert_never

import regex
from pydantic import (
    MISSING,
    ConfigDict,
    Field,
    InstanceOf,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from corpus_structure.core._model import names
from corpus_structure.core._model.qualifiers import CORE_QUALIFIERS, QualifierSpec
from corpus_structure.core._model.revision import KEY_SCHEME
from corpus_structure.core.batch import CORE_PREFIX, PrefixedName, StoredQualifiers, StoredScope
from corpus_structure.core.candidates import (
    AWAITING,
    UNKEYED,
    CandidateClaim,
    CandidateEntity,
    CandidateReference,
    CandidateStatement,
    KeyedCandidateSet,
)
from corpus_structure.core.canonical import CanonicalJsonError, canonical_json, make_key
from corpus_structure.core.evidence import (
    MacroDef,
    RenditionContent,
    Segment,
    SegmentKind,
    content_digest,
    rendition_key,
    segment_key,
)
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.tex import token_form
from corpus_structure.core.values import (
    CONDITION_ADAPTERS,
    AuthoredAnd,
    AuthoredCondition,
    AuthoredEnumValue,
    AuthoredForall,
    AuthoredNot,
    AuthoredOr,
    AuthoredPhrase,
    AuthoredPhraseNode,
    AuthoredUnsupportedNode,
    AuthoredValue,
    BoolValue,
    ClaimNode,
    CmpNode,
    CoreModel,
    DateValue,
    EntityRef,
    Formula,
    IntervalValue,
    MemberNode,
    NumberValue,
    PredNode,
    RefKind,
    SetValue,
    StoredAnd,
    StoredCondition,
    StoredEnumValue,
    StoredForall,
    StoredNot,
    StoredOr,
    StoredPhrase,
    StoredPhraseNode,
    StoredUnsupportedNode,
    StoredValue,
    SymbolBinding,
    TextValue,
)
from corpus_structure.core.vocab import (
    CITABLE_SENTENCE,
    CONVERSE_REWRITTEN,
    MEMBER_PROPERTIES,
    PROPERTY_OF,
    SECTION_LIKE,
    STATEMENT_ANCHOR,
    SYMMETRIC_RELATION,
    CanonicalForm,
    CaseRule,
    ClaimModality,
    DropReason,
    EntityScope,
    KeyRole,
    Relation,
)

Json = Any

# Core qualifier names as the stored form (and so every key) writes them (the model's, generated).
MODALITY, POLARITY, ATTRIBUTION = names.MODALITY, names.POLARITY, names.ATTRIBUTION
CONDITIONS, SCOPE, VALID_TIME = names.CONDITIONS, names.SCOPE, names.VALID_TIME

type Value = AuthoredValue | StoredValue
type Condition = AuthoredCondition | StoredCondition


# --- Text and label forms ----------------------------------------------------------------------


def collapse(text: str) -> str:
    """NFC with whitespace runs collapsed to one space and the ends trimmed."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def text_form(text: str, case: CaseRule = CaseRule.FOLD) -> str:
    """The D1 §6.2 text form: NFC, whitespace collapsed, and casefolded under the `fold` case
    policy (the default); `preserve` keeps case (math-bearing text, ADR-0023). It is also a string
    identifier's canonical form under its declared case."""
    nfc = unicodedata.normalize("NFC", text)
    return " ".join((nfc.casefold() if case is CaseRule.FOLD else nfc).split())


class Rewrite(CoreModel):
    """One pack rewrite (`match`/`replace`, applied with `regex.sub`) of the `aliases:` section.

    The pattern is compiled on validation, so a malformed one is a pack error, never a keying
    failure."""

    match: str
    replace: str

    @field_validator("match")
    @classmethod
    def _compiles(cls, pattern: str) -> str:
        try:
            regex.compile(pattern)
        except regex.error as error:
            raise ValueError(f"rewrite pattern {pattern!r} does not compile: {error}") from None
        return pattern


class LabelRules(CoreModel):
    """Label-normalization data from the pack's `aliases:` section; core holds no word list."""

    articles: tuple[str, ...] = ()
    head_words: dict[str, tuple[str, ...]] = Field(default_factory=dict)  # prefixed class -> words
    rewrites: tuple[Rewrite, ...] = ()


def normalize_label(
    text: str, type_: str, rules: LabelRules, case: CaseRule = CaseRule.FOLD
) -> str:
    """Text form under the class's case policy; one leading article removed; the rewrites in
    order; the class's head words removed as trailing whole words; whitespace collapsed again.
    Articles and head words match regardless of case. Never empties a label."""
    label = text_form(text, case)
    words = label.split(" ")
    articles = {text_form(a) for a in rules.articles}
    if len(words) > 1 and words[0].casefold() in articles:
        label = " ".join(words[1:])
    for rewrite in rules.rewrites:
        label = regex.sub(rewrite.match, rewrite.replace, label)
    label = text_form(label, case)
    heads = {text_form(w) for w in rules.head_words.get(type_, ())}
    words = label.split(" ") if label else []
    while len(words) > 1 and words[-1].casefold() in heads:
        words.pop()
    return text_form(" ".join(words), case)


def symbol_form(symbol: str, macros: Mapping[str, MacroDef]) -> str:
    """A symbol as keys and symbol maps write it: token form, a lone control word unescaped."""
    form = token_form(symbol, macros)
    if regex.fullmatch(r"\\[A-Za-z]+", form):
        return form[1:]
    return form


# --- Outcomes ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Drop:
    """Why a candidate or member was not keyed: its code, the reference, segment key, predicate
    or qualifier the failure names, and a cycle's path or a malformed value's position."""

    code: DropReason
    ref: str
    path: tuple[str, ...] = ()

    @property
    def message(self) -> str:
        """The code's message: a projection of the code and its fields."""
        ref = repr(self.ref)
        match self.code:
            case DropReason.UNKNOWN_PREDICATE:
                return f"predicate {ref} is not in the schema"
            case DropReason.SEGMENT_NOT_ON_RENDITION:
                return f"segment key {self.ref} is not on this rendition"
            case DropReason.UNKNOWN_REFERENCE:
                return f"unknown item {ref}"
            case DropReason.WRONG_KIND_REFERENCE:
                expected, actual = self.path
                return f"{ref} names {actual}; its position takes: {expected}"
            case DropReason.UNCITED_REFERENCE:
                return f"external reference {ref}'s descriptor lies in no statement of the set"
            case DropReason.UNLOCATED_QUOTE:  # parse's (A0), never keying's
                return f"{ref}: a quote that has no span on the rendition"
            case DropReason.UNRESOLVED_EXTENT:  # parse's (A0), and keying's for a local entity
                return f"{ref}: an extent that resolves to no segment on the rendition"
            case DropReason.DROPPED_DEPENDENCY:
                return f"depends on dropped item {ref}"
            case DropReason.UNKNOWN_CLAIM_REF:
                return f"references unknown claim {ref}"
            case DropReason.UNKNOWN_IDENTITY_ENTITY:
                return f"identity names unknown entity {ref}"
            case DropReason.IDENTITY_CYCLE:
                return f"entity identity cycle through {ref}"
            case DropReason.CONDITION_CYCLE:
                return "condition reference cycle: " + " -> ".join(self.path)
            case DropReason.MALFORMED_QUALIFIER:
                at = "/".join(self.path) or "its top"
                return f"qualifier {ref} holds no typed value at {at}"
            case DropReason.MALFORMED_VALUE:
                return f"{ref} holds a value with no canonical JSON at {'/'.join(self.path)}"
            case DropReason.ORPHANED_PREMISE:  # consolidation's, after keying
                return f"supposed claim {ref}: every claim it is a premise of was dropped"
            case DropReason.MALFORMED_EVIDENCE:  # consolidation's, after keying
                return f"stated claim {ref} has no primary evidence"
            case _:
                assert_never(self.code)


class KeyingError(LookupError):
    """A candidate that cannot be keyed, with its `Drop`; counted, never raised past
    `key_claims`."""

    def __init__(self, code: DropReason, ref: str, path: Iterable[str] = ()) -> None:
        self.drop = Drop(code, ref, tuple(path))
        super().__init__(self.drop.message)

    @property
    def code(self) -> DropReason:
        return self.drop.code


# --- References by kind ------------------------------------------------------------------------

# What each position kind accepts. A statement and an ExternalReference are entities (D1 §4.1,
# §4.4: `Statement` and `ExternalReference` are Entity classes), so an entity position takes them
# (`proves` names a statement as its object); an ExternalReference also stands where it is cited as
# a claim (a `claim` condition, a binding's claim). A claim is never an entity (D1 §5.5: relations
# between claims are links).
_ACCEPTS: Mapping[RefKind | Literal["subject"], frozenset[str]] = {
    RefKind.ENTITY: frozenset({"entity", "reference", "statement"}),
    RefKind.STATEMENT: frozenset({"statement"}),
    RefKind.CLAIM: frozenset({"claim", "reference"}),
    "subject": frozenset({"entity", "reference", "statement"}),
}
_EXPECTED: Mapping[RefKind | Literal["subject"], str] = {
    RefKind.ENTITY: "entity", RefKind.STATEMENT: "statement", RefKind.CLAIM: "claim",
    "subject": "entity or statement",
}  # fmt: skip
_UNKNOWN: Mapping[RefKind | Literal["subject"], DropReason] = {
    RefKind.CLAIM: DropReason.UNKNOWN_CLAIM_REF,
}


class Resolver:
    """A reference's key by the kind its position declares (`values.ref_kinds`): `entity`,
    `statement`, `claim` and `subject` (an entity or a statement). A reference naming a candidate
    of another kind is `WRONG_KIND_REFERENCE`, one naming no candidate `UNKNOWN_REFERENCE`
    (`UNKNOWN_CLAIM_REF` for a claim), one naming a dropped candidate `DROPPED_DEPENDENCY`."""

    def __init__(
        self,
        kinds: Mapping[str, str],
        keys: Mapping[str, Mapping[str, str]],
        dropped: Mapping[str, Drop],
    ) -> None:
        self._kinds = kinds  # candidate id -> "entity" | "reference" | "statement" | "claim"
        self._keys = keys  # kind -> id -> the key it resolves to
        self._dropped = dropped

    def _lookup(self, ref: str, position: RefKind | Literal["subject"]) -> str:
        kind = self._kinds.get(ref)
        if kind is None:
            raise KeyingError(_UNKNOWN.get(position, DropReason.UNKNOWN_REFERENCE), ref)
        if kind not in _ACCEPTS[position]:
            article = "an" if kind[0] in "aeiou" else "a"
            raise KeyingError(DropReason.WRONG_KIND_REFERENCE, ref,
                              (_EXPECTED[position], f"{article} {kind}"))  # fmt: skip
        key = self._keys[kind].get(ref)
        if key is None:
            raise KeyingError(DropReason.DROPPED_DEPENDENCY, ref)
        return key

    def entity(self, ref: str) -> str:
        return self._lookup(ref, RefKind.ENTITY)

    def statement(self, ref: str) -> str:
        return self._lookup(ref, RefKind.STATEMENT)

    def claim(self, ref: str) -> str:
        return self._lookup(ref, RefKind.CLAIM)

    def subject(self, ref: str) -> str:
        return self._lookup(ref, "subject")


class Uniform(Resolver):
    """A resolver that maps every reference alike, whatever its kind (a caller that has already
    checked kinds, or a test)."""

    def __init__(self, resolve: Callable[[str], str]) -> None:
        super().__init__({}, {}, {})
        self._resolve = resolve

    def _lookup(self, ref: str, position: RefKind | Literal["subject"]) -> str:
        return self._resolve(ref)


# --- Canonical values and conditions -----------------------------------------------------------


def canonical_value(
    value: EntityRef | Value,
    macros: Mapping[str, MacroDef],
    resolve: Resolver,
    case: CaseRule = CaseRule.FOLD,
) -> Json:
    """The key form of a value or entity reference (JSON), per D1 §6.2; text and phrases under
    the declared case policy."""
    match value:
        case EntityRef(ref=ref):
            return {"key": resolve.entity(ref)}
        case TextValue(v=v):
            return {"t": "text", "v": text_form(v, case)}
        case NumberValue():
            out: Json = {"t": "number", "v": value.v}
            if value.unit is not MISSING:
                out["unit"] = collapse(value.unit)
            if value.basis is not MISSING:
                out["basis"] = collapse(value.basis)
            return out
        case Formula(latex=latex) | SetValue(latex=latex):
            return {"t": value.t, "latex": token_form(latex, macros)}
        case IntervalValue():
            interval: Json = {"t": "interval"}
            if value.start is not MISSING:
                interval["start"] = canonical_value(value.start, macros, resolve)
            if value.end is not MISSING:
                interval["end"] = canonical_value(value.end, macros, resolve)
            if value.start_incl is not MISSING:
                interval["start_incl"] = value.start_incl
            if value.end_incl is not MISSING:
                interval["end_incl"] = value.end_incl
            return interval
        case AuthoredPhrase(text=text) | StoredPhrase(text=text):
            return {"t": "phrase", "text": text_form(text, case)}
        case BoolValue(v=v):
            return {"t": "bool", "v": v}
        case StoredEnumValue(enum=enum, v=v):
            return {"t": "enum", "enum": enum, "v": v}
        case AuthoredEnumValue():
            raise TypeError(
                f"the authored enum value {value.enum}.{value.v} names its enum locally; keys read "
                "the stored form, which names it prefixed (X2-01)"
            )
        case DateValue(v=v):
            return {"t": "date", "v": v}
        case _:
            assert_never(value)


def _parts(node: Condition) -> tuple[tuple[Condition, ...], tuple[EntityRef | Value, ...]]:
    """A node's child conditions and its value positions: the one structural dispatch."""
    match node:
        case (
            AuthoredAnd(args=args)
            | StoredAnd(args=args)
            | AuthoredOr(args=args)
            | StoredOr(args=args)
        ):
            return args, ()
        case AuthoredNot(arg=arg) | StoredNot(arg=arg):
            return (arg,), ()
        case AuthoredForall(set=set_, body=body) | StoredForall(set=set_, body=body):
            return (body,), (set_,)
        case ClaimNode():
            return (), ()
        case MemberNode(x=x, set=set_):
            return (), (x, set_)
        case CmpNode(lhs=lhs, rhs=rhs):
            return (), (lhs, rhs)
        case PredNode(args=pred_args):
            return (), pred_args
        case (
            AuthoredPhraseNode()
            | StoredPhraseNode()
            | AuthoredUnsupportedNode()
            | StoredUnsupportedNode()
        ):
            return (), ()
        case _:
            assert_never(node)


def condition_nodes(node: Condition) -> Iterator[Condition]:
    """Every node of a condition tree, children before their parent, left to right."""
    children, _ = _parts(node)
    for child in children:
        yield from condition_nodes(child)
    yield node


def claim_refs(node: Condition) -> list[str]:
    """The claim refs a condition tree references, in tree order."""
    return [n.ref for n in condition_nodes(node) if isinstance(n, ClaimNode)]


def _sort(items: Iterable[Json]) -> list[Json]:
    return sorted(items, key=canonical_json)


def canonical_condition(
    node: Condition,
    macros: Mapping[str, MacroDef],
    resolve: Resolver,
    symmetric: frozenset[str] = frozenset(),
) -> Json | None:
    """The D1 §7 canonical form of a condition tree, bottom-up; `None` is no condition."""
    done: dict[int, Json | None] = {}

    def value(v: EntityRef | Value) -> Json:
        return canonical_value(v, macros, resolve)

    for n in condition_nodes(node):  # children first, so each child's form is ready
        done[id(n)] = _canonical_node(n, done, value, resolve, symmetric, macros)
    return done[id(node)]


def _canonical_node(
    n: Condition,
    done: Mapping[int, Json | None],
    value: Callable[[EntityRef | Value], Json],
    resolve: Resolver,
    symmetric: frozenset[str],
    macros: Mapping[str, MacroDef],
) -> Json | None:
    match n:
        case (
            AuthoredAnd(op=op, args=args)
            | StoredAnd(op=op, args=args)
            | AuthoredOr(op=op, args=args)
            | StoredOr(op=op, args=args)
        ):
            flat: list[Json] = []
            for child in args:
                c = done[id(child)]
                if c is None:
                    continue
                flat.extend(c["args"] if c["op"] == op else [c])
            unique = {canonical_json(a): a for a in flat}  # identical args once
            if not unique:
                return None
            if len(unique) == 1:
                return next(iter(unique.values()))
            return {"op": op, "args": [unique[k] for k in sorted(unique)]}
        case AuthoredNot(arg=arg) | StoredNot(arg=arg):
            inner = done[id(arg)]
            return None if inner is None else {"op": "not", "arg": inner}
        case ClaimNode(ref=ref):
            return {"op": "claim", "ref": resolve.claim(ref)}
        case MemberNode(x=x, set=set_):
            return {"op": "member", "x": value(x), "set": value(set_)}
        case CmpNode(rel=rel, lhs=lhs, rhs=rhs):
            if rel in CONVERSE_REWRITTEN:  # > as <, >= as <=, the sides swapped
                rel, lhs, rhs = Relation(rel.replace(">", "<")), rhs, lhs
            sides = [value(lhs), value(rhs)]
            if rel in SYMMETRIC_RELATION:  # operands in canonical order
                sides = _sort(sides)
            return {"op": "cmp", "rel": rel, "lhs": sides[0], "rhs": sides[1]}
        case PredNode(name=name, args=pred_args):
            canonical_args = [value(a) for a in pred_args]
            if name in symmetric:
                canonical_args = _sort(canonical_args)
            return {"op": "pred", "name": name, "args": canonical_args}
        case (
            AuthoredForall(var=var, set=set_, body=body)
            | StoredForall(var=var, set=set_, body=body)
        ):
            inner = done[id(body)]
            if inner is None:
                return None
            return {"op": "forall", "var": symbol_form(var, macros), "set": value(set_),
                    "body": inner}  # fmt: skip
        case (
            AuthoredPhraseNode(op=op, text=text)
            | StoredPhraseNode(op=op, text=text)
            | AuthoredUnsupportedNode(op=op, text=text)
            | StoredUnsupportedNode(op=op, text=text)
        ):
            return {"op": op, "text": text_form(text)}
        case _:
            assert_never(n)


def canonical_binding(
    symbol: str, binding: SymbolBinding, macros: Mapping[str, MacroDef], resolve: Resolver
) -> Json:
    """The key form of one symbol binding (used only in alternative member keys)."""
    out: Json = {"symbol": symbol_form(symbol, macros), "bind": binding.bind}
    if binding.entity is not MISSING:
        out["entity"] = resolve.entity(binding.entity)
    if binding.claim is not MISSING:
        out["claim"] = resolve.claim(binding.claim)
    if binding.param is not MISSING:
        out["param"] = binding.param
    return out


def expressions(value: EntityRef | Value | Condition) -> Iterator[Formula | SetValue]:
    """Every formula and set inside a value or a condition tree (through `condition_nodes`)."""
    match value:
        case Formula() | SetValue():
            yield value
        case IntervalValue():
            for bound in (value.start, value.end):
                if isinstance(bound, Formula):
                    yield bound
        case (
            TextValue() | NumberValue() | BoolValue() | AuthoredEnumValue() | StoredEnumValue()
            | DateValue()
            | AuthoredPhrase() | StoredPhrase() | EntityRef()
        ):  # fmt: skip
            return
        case (
            AuthoredAnd() | AuthoredOr() | AuthoredNot() | AuthoredForall() | StoredAnd()
            | StoredOr() | StoredNot() | StoredForall() | ClaimNode() | MemberNode() | CmpNode()
            | PredNode() | AuthoredPhraseNode() | StoredPhraseNode() | AuthoredUnsupportedNode() | StoredUnsupportedNode()
        ):  # fmt: skip
            for node in condition_nodes(value):
                for v in _parts(node)[1]:
                    yield from expressions(v)
        case _:
            assert_never(value)


# --- Qualifiers and the key schema ------------------------------------------------------------


class _Unset(Enum):
    UNSET = "unset"


UNSET: Literal[_Unset.UNSET] = _Unset.UNSET

# stored core qualifier name (`core:hedge`) -> its `StoredQualifiers` field
_CORE_FIELDS: dict[str, str] = {
    info.alias: name for name, info in StoredQualifiers.model_fields.items() if info.alias
}
_STORED_VALUE: TypeAdapter[Any] = TypeAdapter(StoredValue)
_STORED_CONDITION: TypeAdapter[Any] = CONDITION_ADAPTERS["stored"]
_PREFIXED = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*$")

# The value classes each canonical form takes (a schema qualifier's raw JSON is validated into
# one of them by its declared range, never chosen by its shape).
_KINDS: Mapping[CanonicalForm, tuple[type, ...]] = {
    CanonicalForm.TOKEN_FORM: (Formula, SetValue),
    CanonicalForm.TEXT_FORM: (TextValue, StoredPhrase),
    CanonicalForm.ENUM: (StoredEnumValue,),
    CanonicalForm.INTERVAL: (IntervalValue,),
    CanonicalForm.NUMBER: (NumberValue,),
    CanonicalForm.VERBATIM: (DateValue, BoolValue),
}


@dataclass(frozen=True, slots=True)
class ValueSpec:
    """A declared range's canonical form and case: a map entry's value range (S1 compiles one per
    map qualifier range from its `MapEntry` subclass)."""

    range: str
    canonical: CanonicalForm
    case: CaseRule = CaseRule.FOLD


def qualifier_value(qualifiers: StoredQualifiers, name: str) -> Any:
    """A qualifier's value by its stored name: a core qualifier's typed field, or a schema
    qualifier's raw JSON; `UNSET` when it is absent or (`modality`, `polarity`) the default,
    which equal JSON leaves out."""
    attr = _CORE_FIELDS.get(name)
    if attr is None:
        extras = qualifiers.__pydantic_extra__ or {}
        return extras.get(name, UNSET)
    value = getattr(qualifiers, attr)
    exclude = StoredQualifiers.model_fields[attr].exclude_if
    if value is MISSING or (exclude is not None and exclude(value)):
        return UNSET
    return value


def _typed(value: Any, kinds: tuple[type, ...], name: str, path: tuple[str, ...]) -> Any:
    """`value` as one of the value classes its declared range takes, validating raw JSON."""
    if isinstance(value, kinds):
        return value
    if isinstance(value, dict):
        try:
            typed = _STORED_VALUE.validate_python(value)
        except ValidationError:
            raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path) from None
        if isinstance(typed, kinds):
            return typed
    raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path)


def _condition(value: Any, name: str, path: tuple[str, ...]) -> Condition:
    if isinstance(value, dict):
        try:
            return _STORED_CONDITION.validate_python(value)
        except ValidationError:
            raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path) from None
    if isinstance(value, StoredScope | str | int | bool | list | tuple) or value is None:
        raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path)
    return value


def canonical_qualifier(
    value: Any,
    spec: QualifierSpec | ValueSpec,
    schema: KeySchema,
    macros: Mapping[str, MacroDef],
    resolve: Resolver,
    name: str,
    path: tuple[str, ...] = (),
    locate: Callable[[str], Json] | None = None,
) -> Json | None:
    """A qualifier's canonical form, chosen by its declared range's `CanonicalForm` (TM §8; D1
    §6.2), never by the value's shape: core values arrive typed, schema qualifiers as raw JSON
    validated into the range's class. `None` is an empty condition tree. A stored scope needs
    `locate` (member keys only). A value outside its range is `MALFORMED_QUALIFIER`."""
    form = spec.canonical
    match form:
        case (
            CanonicalForm.TOKEN_FORM | CanonicalForm.TEXT_FORM | CanonicalForm.ENUM
            | CanonicalForm.INTERVAL | CanonicalForm.NUMBER
        ):  # fmt: skip
            typed = _typed(value, _KINDS[form], name, path)
            return canonical_value(typed, macros, resolve, spec.case)
        case CanonicalForm.VERBATIM:
            if isinstance(value, bool | int | str):
                return value
            return canonical_value(_typed(value, _KINDS[form], name, path), macros, resolve)
        case CanonicalForm.IDENTIFIER:
            if not isinstance(value, str):
                raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path)
            return text_form(value, spec.case)
        case CanonicalForm.MEMBER:
            if not isinstance(value, str):
                raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path)
            return str.__str__(value)  # normalize member string subclasses
        case CanonicalForm.ENTITY_KEY:
            if isinstance(value, dict):
                try:
                    value = EntityRef.model_validate(value)
                except ValidationError:
                    raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path) from None
            if not isinstance(value, EntityRef):
                raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path)
            return resolve.entity(value.ref)  # the resolved key, bare
        case CanonicalForm.MAP:
            entry = schema.map_values.get(spec.range)
            if not isinstance(value, dict) or entry is None:
                raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path)
            # keys stay as written: canonical JSON NFC-normalizes them, and refuses two that
            # collide after NFC (mapped to this qualifier by `_key`)
            return {
                k: canonical_qualifier(v, entry, schema, macros, resolve, name, (*path, k), locate)
                for k, v in value.items()
            }
        case CanonicalForm.CONDITION:
            tree = _condition(value, name, path)
            return canonical_condition(tree, macros, resolve, schema.symmetric_predicates)
        case CanonicalForm.SCOPE:
            if locate is None:
                raise ValueError(f"{name}: a scope is canonical only with its rendition")
            if isinstance(value, dict):
                try:
                    value = StoredScope.model_validate(value)
                except ValidationError:
                    raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path) from None
            if not isinstance(value, StoredScope):
                raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path)
            return {"extent": value.extent, "segment": locate(value.segment)}
        case _:
            assert_never(form)


def _canonical_expressions(
    tree: Condition,
    macros: Mapping[str, MacroDef],
    resolve: Resolver,
    symmetric: frozenset[str],
) -> list[Formula | SetValue]:
    """The formulas and sets of a condition tree's canonical form, over the one traversal: an
    `and`/`or` keeps each canonically distinct argument once, flattened as its canonical form is,
    and a node canonicalization drops (an empty `and`/`or`, a `not` or `forall` of one)
    contributes nothing. So `or(M, M)` and `M` give the same expressions."""
    done: dict[int, Json | None] = {}
    found: dict[int, list[Formula | SetValue]] = {}
    args: dict[int, list[tuple[bytes, list[Formula | SetValue]]]] = {}  # and/or: flattened

    def value(v: EntityRef | Value) -> Json:
        return canonical_value(v, macros, resolve)

    for node in condition_nodes(tree):  # children first
        done[id(node)] = form = _canonical_node(node, done, value, resolve, symmetric, macros)
        children, values = _parts(node)
        own = [e for v in values for e in expressions(v)]
        match node:
            case AuthoredAnd(op=op) | StoredAnd(op=op) | AuthoredOr(op=op) | StoredOr(op=op):
                flat: list[tuple[bytes, list[Formula | SetValue]]] = []
                for child in children:
                    child_form = done[id(child)]
                    if child_form is None:
                        continue
                    if id(child) in args and child_form["op"] == op:
                        flat.extend(args[id(child)])  # flattened into this node
                    else:
                        flat.append((canonical_json(child_form), found[id(child)]))
                unique = dict(flat[::-1])  # the first of each canonically equal argument wins
                args[id(node)] = [(k, unique[k]) for k in dict.fromkeys(k for k, _ in flat)]
                found[id(node)] = [e for _, es in args[id(node)] for e in es]
            case _:
                inner = [e for c in children if done[id(c)] is not None for e in found[id(c)]]
                found[id(node)] = [*own, *inner] if form is not None else []
    return found[id(tree)] if done[id(tree)] is not None else []


def _qualifier_expressions(
    value: Any,
    spec: QualifierSpec | ValueSpec,
    schema: KeySchema,
    macros: Mapping[str, MacroDef],
    resolve: Resolver,
    name: str,
    path: tuple[str, ...],
) -> Iterator[Formula | SetValue]:
    """The formulas and sets a qualifier's value holds, read by its declared range."""
    match spec.canonical:
        case CanonicalForm.TOKEN_FORM | CanonicalForm.INTERVAL:
            yield from expressions(_typed(value, _KINDS[spec.canonical], name, path))
        case CanonicalForm.CONDITION:
            tree = _condition(value, name, path)
            yield from _canonical_expressions(tree, macros, resolve, schema.symmetric_predicates)
        case CanonicalForm.MAP:
            entry = schema.map_values.get(spec.range)
            if not isinstance(value, dict) or entry is None:
                raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path)
            for k, v in value.items():
                at = (*path, k)
                yield from _qualifier_expressions(v, entry, schema, macros, resolve, name, at)
        case _:
            return


_CORE_MODALITY_PROPERTIES: dict[str, frozenset[str]] = {
    prop: frozenset(str(m) for m in members)
    for prop, members in MEMBER_PROPERTIES.items()
    if PROPERTY_OF[prop] is ClaimModality
}


class KeySchema(CoreModel):
    """The schema facts keys need, compiled into one lookup (ADR-0023; foundations §3.6): every
    name prefixed as the stored form writes it. The core qualifier specifications come from the
    model (`_model/qualifiers.py`); S1 compiles a schema version's half:

    - `qualifiers`: each predicate's schema qualifier specifications (`ci:key_role`, or the
      `ci:identity_qualifiers` list compiled into the same specs);
    - `map_values`: each map range's entry value range (`MapEntry` subclasses);
    - `modality_properties`: each `ClaimModality` member property's members, core and pack;
    - `label_case`, `slot_case`: the case policy of a class's label and of a string-ranged
      identity slot (`ci:case`; `fold` when absent);
    - `identity_keys`, `entity_identity`, `predicates`, `symmetric_predicates`, as before;
    - `key_scheme`: the scheme the keys are of, recorded beside them and never hashed (RC08).

    Keys, consolidation's slots and conflicts, and the rule view read it (`specs`, `role`,
    `meaning_qualifiers`, `has_property`) and restate nothing. A malformed schema is refused on
    construction (`ValueError`): an input error, not a keying outcome."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    identity_keys: dict[PrefixedName, tuple[PrefixedName, ...]] = Field(default_factory=dict)
    entity_identity: dict[PrefixedName, tuple[PrefixedName, ...]] = Field(default_factory=dict)
    predicates: frozenset[PrefixedName] = frozenset()
    qualifiers: dict[PrefixedName, tuple[InstanceOf[QualifierSpec], ...]] = Field(
        default_factory=dict
    )
    map_values: dict[str, InstanceOf[ValueSpec]] = Field(default_factory=dict)
    modality_properties: dict[str, frozenset[str]] = Field(
        default_factory=lambda: dict(_CORE_MODALITY_PROPERTIES)
    )
    label_case: dict[PrefixedName, CaseRule] = Field(default_factory=dict)
    slot_case: dict[PrefixedName, CaseRule] = Field(default_factory=dict)
    # condition predicates, named as condition trees name them
    symmetric_predicates: frozenset[str] = frozenset()
    key_scheme: int = Field(KEY_SCHEME, ge=1)

    @model_validator(mode="after")
    def _specs_well_formed(self) -> Self:
        for prop, members in _CORE_MODALITY_PROPERTIES.items():
            if not members <= self.modality_properties.get(prop, frozenset()):
                raise ValueError(f"modality property {prop!r} drops core members")
        for spec in CORE_QUALIFIERS:
            self._check(spec, "core")
        for predicate, specs in self.qualifiers.items():
            if predicate not in self.predicates:
                raise ValueError(f"qualifiers names {predicate!r}, not a known predicate")
            seen: set[str] = set()
            for spec in specs:
                if spec.name.startswith(f"{CORE_PREFIX}:"):
                    raise ValueError(f"{predicate}: {spec.name!r} is core; its role is fixed")
                if not _PREFIXED.match(spec.name) or spec.name in seen:
                    raise ValueError(f"{predicate}: {spec.name!r} is malformed or repeated")
                seen.add(spec.name)
                self._check(spec, predicate)
        return self

    def _check(self, spec: QualifierSpec, owner: str) -> None:
        if spec.key_role_when is not None and spec.key_role_when not in self.modality_properties:
            raise ValueError(f"{owner}: {spec.name}'s condition {spec.key_role_when!r} is unknown")
        if spec.canonical is CanonicalForm.MAP and spec.range not in self.map_values:
            raise ValueError(f"{owner}: {spec.name}'s map range {spec.range!r} has no value range")
        if spec.canonical is CanonicalForm.SCOPE and owner != "core":
            raise ValueError(f"{owner}: {spec.name}: only the core scope is a scope")

    def predicate(self, name: str) -> str:
        """`name` when the schema knows the predicate; otherwise refused."""
        if name in self.predicates:
            return name
        raise KeyingError(DropReason.UNKNOWN_PREDICATE, name)

    def specs(self, predicate: str) -> tuple[QualifierSpec, ...]:
        """The qualifier specifications that apply to the predicate's claims: core, then pack."""
        return (*CORE_QUALIFIERS, *self.qualifiers.get(predicate, ()))

    def spec(self, predicate: str, name: str) -> QualifierSpec | None:
        return next((s for s in self.specs(predicate) if s.name == name), None)

    def has_property(self, modality: str, prop: str) -> bool:
        return modality in self.modality_properties.get(prop, frozenset())

    def role(self, spec: QualifierSpec, modality: str) -> KeyRole:
        """The qualifier's key role for a claim of that modality: `identity` when its role
        condition holds (attribution under an `attribution_identifying` modality), else its
        declared role."""
        if spec.key_role_when is not None and self.has_property(modality, spec.key_role_when):
            return KeyRole.IDENTITY
        return spec.key_role

    def meaning_qualifiers(self, predicate: str, modality: str) -> tuple[str, ...]:
        """The qualifiers whose disagreement makes alternatives (C1, D5 §5.3)."""
        return tuple(
            s.name for s in self.specs(predicate) if self.role(s, modality) is KeyRole.MEANING
        )


def _key(prefix: str, parts: Json, ref: str) -> str:
    """`make_key`, with a value that has no canonical JSON (a lone surrogate, keys equal after
    NFC) dropped by code: inside a qualifier as `MALFORMED_QUALIFIER`, else `MALFORMED_VALUE`."""
    try:
        return make_key(prefix, parts)
    except CanonicalJsonError as error:
        m = re.match(r"^\$(?:\.member)?\.qualifiers\.([a-z][a-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*)(.*)$",
                     error.path)  # fmt: skip
        if m:
            rest = tuple(p for p in re.split(r"[.\[\]]", m.group(2)) if p)
            raise KeyingError(DropReason.MALFORMED_QUALIFIER, m.group(1), rest) from None
        raise KeyingError(DropReason.MALFORMED_VALUE, ref, (error.path,)) from None


# --- Schema facts and the rendition ------------------------------------------------------------


@dataclass
class KeyContext:
    """One rendition: the document key, its content and page, and the effective macro table.

    Rendition-wide work (the locator index, the segment keys, the parent map and the annotation
    units' top-level blocks) is prepared once per context, on first use."""

    document_key: str
    content: RenditionContent
    page: str
    macros: Mapping[str, MacroDef] = field(default_factory=dict)

    @cached_property
    def index(self) -> LocatorIndex:
        return LocatorIndex(self.content, self.page)

    @cached_property
    def rendition_key(self) -> str:
        """The rendition's `ren` key, which a candidate set keyed here must name."""
        return rendition_key(self.document_key, content_digest(self.content))

    @cached_property
    def segments(self) -> dict[str, Segment]:
        """Segment key -> segment on this rendition."""
        ren = self.rendition_key
        return {segment_key(ren, s.kind, s.start, s.end): s for s in self.content.document.walk()}

    @cached_property
    def parents(self) -> dict[tuple[str, int, int], Segment]:
        out: dict[tuple[str, int, int], Segment] = {}
        for segment in self.content.document.walk():
            for child in segment.children:
                out[(child.kind.value, child.start, child.end)] = segment
        return out

    @cached_property
    def top_blocks(self) -> frozenset[tuple[SegmentKind, int, int]]:
        """The annotation units and the `uncovered` top-level blocks, by kind and range."""
        found = self.index.annotation_units()
        blocks = (*(u.segment for u in found.units), *found.uncovered)
        return frozenset((s.kind, s.start, s.end) for s in blocks)

    def segment(self, key: str) -> Segment:
        try:
            return self.segments[key]
        except KeyError:
            raise KeyingError(DropReason.SEGMENT_NOT_ON_RENDITION, key) from None

    def ancestors(self, segment: Segment) -> list[Segment]:
        """The segment's ancestors, innermost first."""
        out = []
        current = self.parents.get((segment.kind.value, segment.start, segment.end))
        while current is not None:
            out.append(current)
            current = self.parents.get((current.kind.value, current.start, current.end))
        return out

    def locator_key(self, segment: Segment) -> Json:
        return self.index.generate(segment).key_form(self.document_key)


# --- Entity and statement keys -----------------------------------------------------------------


def global_entity_key(
    entity: CandidateEntity, schema: KeySchema, rules: LabelRules, resolve: Callable[[str], str]
) -> str:
    """`ent`: type and identity attributes; the normalized label when identity is incomplete.
    `resolve` is the entity lookup of an entity-ranged identity slot."""
    declared = schema.identity_keys.get(entity.type, ())
    entity_slots = set(schema.entity_identity.get(entity.type, ()))
    identity: Json = {}
    for slot in declared:
        if slot in entity.identity:
            value = entity.identity[slot]
            case = schema.slot_case.get(slot, CaseRule.FOLD)
            identity[slot] = resolve(value) if slot in entity_slots else text_form(value, case)
    parts: Json = {"type": entity.type, "identity": identity}
    if not declared or len(identity) < len(declared):
        case = schema.label_case.get(entity.type, CaseRule.FOLD)
        parts["label"] = normalize_label(entity.label, entity.type, rules, case)
    return _key("ent", parts, entity.id)


def local_entity_key(
    entity: CandidateEntity, ctx: KeyContext, rules: LabelRules, schema: KeySchema
) -> str:
    """`ent`: type, the scope segment's locator (structured), and the symbol or normalized label
    (under the class's label case policy). A local entity whose extent resolved to no segment has
    no scope to key by: `UNRESOLVED_EXTENT`."""
    if entity.scope_segment is MISSING:
        raise KeyingError(DropReason.UNRESOLVED_EXTENT, entity.id)
    parts: Json = {"type": entity.type, "scope": ctx.locator_key(ctx.segment(entity.scope_segment))}
    if entity.symbol is not MISSING and entity.symbol:
        parts["symbol"] = symbol_form(entity.symbol, ctx.macros)
    else:
        case = schema.label_case.get(entity.type, CaseRule.FOLD)
        parts["label"] = normalize_label(entity.label, entity.type, rules, case)
    return _key("ent", parts, entity.id)


def statement_anchor(statement: CandidateStatement, ctx: KeyContext) -> tuple[Segment, int]:
    """The statement's anchor segment and the 1-based ordinal of its first sentence there.

    The anchor is the innermost segment of a `statement_anchor` kind (`details`, `unit`) containing
    the first anchor segment, else the annotation unit containing it, else the top-level block
    outside every unit that contains it (a list, table, figure, …: an `uncovered` block of
    `annotation_units`), else the outermost block below the `section_like` segments; never the
    document unless that is the segment itself. Kinds are read by member property (DA-003).
    """
    first = min((ctx.segment(k) for k in statement.anchor), key=lambda s: (s.start, -s.end))
    chain = [first, *ctx.ancestors(first)]
    anchor = next((s for s in chain if s.kind in STATEMENT_ANCHOR), None)
    if anchor is None:
        tops = ctx.top_blocks
        anchor = next((s for s in chain if (s.kind, s.start, s.end) in tops), None)
    if anchor is None:
        blocks = [s for s in chain if s.kind not in SECTION_LIKE]
        anchor = blocks[-1] if blocks else first
    before = sum(1 for s in anchor.walk() if s.kind in CITABLE_SENTENCE and s.start < first.start)
    return anchor, before + 1


def statement_key(statement: CandidateStatement, ctx: KeyContext) -> str:
    """`stm`: the anchor's generated locator (structured) and the first sentence's ordinal."""
    anchor, ordinal = statement_anchor(statement, ctx)
    return _key("stm", {"anchor": ctx.locator_key(anchor), "ordinal": ordinal}, statement.id)


def citing_statement(
    reference: CandidateReference, statements: Iterable[CandidateStatement], ctx: KeyContext
) -> CandidateStatement:
    """The statement that cites an external reference: of the statements one of whose anchor
    segments contains the descriptor's span, the one with the innermost such segment (ties by id).
    None: `UNCITED_REFERENCE`."""
    d = reference.descriptor
    best: tuple[int, str, CandidateStatement] | None = None
    for statement in statements:
        for k in statement.anchor:
            segment = ctx.segments.get(k)
            if segment is not None and segment.start <= d.start and d.end <= segment.end:
                found = (segment.end - segment.start, statement.id, statement)
                if best is None or found[:2] < best[:2]:
                    best = found
    if best is None:
        raise KeyingError(DropReason.UNCITED_REFERENCE, reference.id)
    return best[2]


def reference_key(reference: CandidateReference, statement: str, ctx: KeyContext) -> str:
    """`xrf` (D1 §10.1): the citing statement's key, the descriptor's quote in text form (the text
    of its located span) and the author's link target as written, when it has one. The citing
    sentence id is local to its batch and never a part."""
    d = reference.descriptor
    parts: Json = {"statement": statement,
                   "quote": text_form(ctx.content.canonical_text[d.start : d.end])}  # fmt: skip
    if d.target is not MISSING:
        parts["target"] = d.target
    return _key("xrf", parts, reference.id)


# --- Claim keys --------------------------------------------------------------------------------


def _object_part(
    obj: EntityRef | StoredValue, macros: Mapping[str, MacroDef], resolve: Resolver
) -> Json:
    match obj:
        case EntityRef(ref=ref):
            return {"key": resolve.entity(ref)}
        case _:
            return {"value": canonical_value(obj, macros, resolve)}


def claim_parts(
    claim: CandidateClaim,
    schema: KeySchema,
    macros: Mapping[str, MacroDef],
    resolve: Resolver,
) -> Json:
    """The parts of a claim key: subject, predicate, object, statement, and every qualifier whose
    key role for the claim's modality is `identity` (`KeySchema.role`), in its declared range's
    canonical form, named as the stored form names it (`core:modality`, `stat:param_values`).
    `modality` and `polarity` enter only when not the default."""
    predicate = schema.predicate(claim.predicate)
    q = claim.qualifiers
    parts: Json = {
        "subject": resolve.subject(claim.subject),
        "predicate": predicate,
        "object": _object_part(claim.object, macros, resolve),
    }
    if claim.statement is not MISSING:
        parts["statement"] = resolve.statement(claim.statement)
    identity: Json = {}
    for spec in schema.specs(predicate):
        if schema.role(spec, q.modality) is not KeyRole.IDENTITY:
            continue
        value = qualifier_value(q, spec.name)
        if value is UNSET:
            continue
        form = canonical_qualifier(value, spec, schema, macros, resolve, spec.name)
        if form is not None:  # an empty condition tree is no condition
            identity[spec.name] = form
    parts["qualifiers"] = identity
    return parts


def claim_bindings(
    claim: CandidateClaim, schema: KeySchema, macros: Mapping[str, MacroDef], resolve: Resolver
) -> Json:
    """Every formula's or set's canonical bindings beside its canonical value, over the object and
    every declared qualifier read by its range (condition trees as their canonical form keeps
    them), sorted by canonical JSON: neither argument order, a canonically repeated argument nor
    a rewritten comparison moves them."""
    q = claim.qualifiers
    found = [*expressions(claim.object)]
    for spec in schema.specs(claim.predicate):
        value = qualifier_value(q, spec.name)
        if value is not UNSET:
            found.extend(
                _qualifier_expressions(value, spec, schema, macros, resolve, spec.name, ())
            )
    out = [
        {
            "value": canonical_value(e, macros, resolve),
            "symbols": _sort(
                canonical_binding(s, b, macros, resolve) for s, b in e.symbols.items()
            ),
        }
        for e in found
    ]
    return _sort(out)


@dataclass(frozen=True)
class Member:
    """C1's decision for one alternative member: the qualifiers it disagrees on (by their stored,
    prefixed names, e.g. `core:hedge`), and whether its bindings disagree with the others'."""

    qualifiers: tuple[str, ...] = ()
    bindings: bool = False


def member_parts(
    claim: CandidateClaim,
    member: Member,
    base: Json,
    ctx: KeyContext,
    resolve: Resolver,
    schema: KeySchema,
) -> Json:
    """A member's key parts: the claim's parts (`base`, from `claim_parts`) plus its disagreeing
    qualifiers in their ranges' canonical forms (null when it leaves one unset) and, when
    bindings disagree, its canonical bindings. A stored `scope` enters by its extent and its
    segment's locator, never by the physical segment key. A qualifier the predicate does not
    declare is `MALFORMED_QUALIFIER`."""

    def locate(segment: str) -> Json:
        return ctx.locator_key(ctx.segment(segment))

    own: Json = {}
    for name in sorted(member.qualifiers):
        spec = schema.spec(claim.predicate, name)
        if spec is None:
            raise KeyingError(DropReason.MALFORMED_QUALIFIER, name)
        value = qualifier_value(claim.qualifiers, name)
        own[name] = (
            None
            if value is UNSET
            else canonical_qualifier(value, spec, schema, ctx.macros, resolve, name, (), locate)
        )
    extra: Json = {"qualifiers": own}
    if member.bindings:
        extra["bindings"] = claim_bindings(claim, schema, ctx.macros, resolve)
    return {**base, "member": extra}


def group_key(prefix: str, member_keys: Iterable[str]) -> str:
    """`alt` or `idg`: the hash of the sorted member keys."""
    if prefix not in ("alt", "idg"):
        raise ValueError(f"group prefix must be alt or idg, not {prefix!r}")
    return make_key(prefix, sorted(member_keys))


def alternative_group_key(member_keys: Iterable[str]) -> str:
    return group_key("alt", member_keys)


def identity_group_key(member_keys: Iterable[str]) -> str:
    return group_key("idg", member_keys)


# --- Batch keying ------------------------------------------------------------------------------


@dataclass
class Keys:
    """Keys by candidate id (`references`: the `ExternalReference` nodes' own `xrf` keys),
    alternatives' member keys, and the dropped items with their codes; `scheme` is the key scheme
    they are of, recorded beside them (never hashed into them)."""

    scheme: int = KEY_SCHEME
    entities: dict[str, str] = field(default_factory=dict)
    statements: dict[str, str] = field(default_factory=dict)
    references: dict[str, str] = field(default_factory=dict)
    claims: dict[str, str] = field(default_factory=dict)
    members: dict[str, str] = field(default_factory=dict)
    dropped: dict[str, Drop] = field(default_factory=dict)
    dropped_members: dict[str, Drop] = field(default_factory=dict)


def _kinds(candidates: KeyedCandidateSet) -> dict[str, str]:
    out: dict[str, str] = {}
    tables = (("entity", candidates.entities), ("statement", candidates.statements),
              ("reference", candidates.references), ("claim", candidates.claims))  # fmt: skip
    for kind, items in tables:
        for item in items:
            out[item.id] = kind
    return out


def _entity_keys(
    candidates: KeyedCandidateSet,
    ctx: KeyContext,
    schema: KeySchema,
    rules: LabelRules,
    keys: Keys,
    kinds: Mapping[str, str],
) -> None:
    by_id = {e.id: e for e in candidates.entities}
    visiting: set[str] = set()

    def key_of(entity_id: str) -> str:
        if entity_id in keys.entities:
            return keys.entities[entity_id]
        entity = by_id.get(entity_id)
        if entity is None:
            kind = kinds.get(entity_id)
            if kind is not None and kind != "entity":
                found = ("entity", f"a {kind}")
                raise KeyingError(DropReason.WRONG_KIND_REFERENCE, entity_id, found)
            raise KeyingError(DropReason.UNKNOWN_IDENTITY_ENTITY, entity_id)
        if entity_id in visiting:
            raise KeyingError(DropReason.IDENTITY_CYCLE, entity_id)
        visiting.add(entity_id)
        if entity.key is not UNKEYED:
            key = entity.key
        elif entity.scope is EntityScope.LOCAL:
            key = local_entity_key(entity, ctx, rules, schema)
        else:
            key = global_entity_key(entity, schema, rules, key_of)
        visiting.discard(entity_id)
        keys.entities[entity_id] = key
        return key

    for entity in candidates.entities:
        try:
            key_of(entity.id)
        except KeyingError as error:
            keys.dropped.setdefault(entity.id, error.drop)
            visiting.clear()


def key_claims(
    candidates: KeyedCandidateSet,
    ctx: KeyContext,
    schema: KeySchema,
    rules: LabelRules,
    members: Mapping[str, Member] | None = None,
) -> Keys:
    """Key every candidate: entities, statements, external references (by their citing statement),
    then claims in a topological order of their condition `claim` references. A candidate that
    cannot be keyed (on or behind a reference cycle, naming an unknown or dropped item or one of
    another kind, an unknown predicate, a malformed schema qualifier) is dropped with its `Drop`
    (D5 §5.2), never raised. An unresolved `ExternalReference` is keyed and stands where it is
    cited; a resolved one stands as its statement. `members` (C1's) adds member keys, reusing each
    claim's parts; a member that cannot be keyed is in `dropped_members` with its `Drop`.

    A candidate set on any rendition but exactly `ctx`'s one is refused (`ValueError`): an input
    error, not a keying outcome."""
    if candidates.renditions != (ctx.rendition_key,):
        raise ValueError(
            f"keying takes a set on exactly the context's rendition {ctx.rendition_key}; this one "
            f"is on {', '.join(candidates.renditions)}"
        )
    keys = Keys(scheme=schema.key_scheme)
    kinds = _kinds(candidates)
    _entity_keys(candidates, ctx, schema, rules, keys, kinds)
    for statement in candidates.statements:
        if statement.key is not UNKEYED:
            keys.statements[statement.id] = statement.key
            continue
        try:
            keys.statements[statement.id] = statement_key(statement, ctx)
        except KeyingError as error:
            keys.dropped[statement.id] = error.drop
    stands_for: dict[str, str] = {}  # reference id -> the key it stands as where cited
    keyed = [s for s in candidates.statements if s.id in keys.statements]
    for reference in candidates.references:
        try:
            if reference.key is not UNKEYED:
                own = reference.key
            else:
                citing = citing_statement(reference, keyed, ctx)
                own = reference_key(reference, keys.statements[citing.id], ctx)
        except KeyingError as error:
            keys.dropped[reference.id] = error.drop
            continue
        keys.references[reference.id] = own
        resolved = reference.resolved_to
        stands_for[reference.id] = own if resolved is AWAITING else str.__str__(resolved)
    resolver = Resolver(
        kinds,
        {"entity": keys.entities, "statement": keys.statements, "reference": stands_for,
         "claim": keys.claims},
        keys.dropped,
    )  # fmt: skip

    claims = {c.id: c for c in candidates.claims}
    deps: dict[str, list[str]] = {}
    for claim in candidates.claims:
        tree = claim.qualifiers.conditions
        deps[claim.id] = [] if tree is MISSING else claim_refs(tree)

    parts: dict[str, Json] = {}  # claim id -> its key parts, for member keys
    state: dict[str, str] = {}  # id -> "active" | "done" | "dropped"
    stack: list[str] = []

    def drop(claim_id: str, reason: Drop) -> None:
        state[claim_id] = "dropped"
        keys.dropped.setdefault(claim_id, reason)

    def visit(claim_id: str) -> bool:
        status = state.get(claim_id)
        if status == "done":
            return True
        if status == "dropped":
            return False
        if status == "active":
            cycle = (*stack[stack.index(claim_id) :], claim_id)
            for member in cycle[:-1]:
                drop(member, Drop(DropReason.CONDITION_CYCLE, claim_id, cycle))
            return False
        state[claim_id] = "active"
        stack.append(claim_id)
        ok = True
        for ref in deps[claim_id]:
            if ref in claims:
                if not visit(ref):
                    drop(claim_id, Drop(DropReason.DROPPED_DEPENDENCY, ref))
                    ok = False
                continue
            try:  # an external reference, or a reference of another kind or to nothing
                resolver.claim(ref)
            except KeyingError as error:
                drop(claim_id, error.drop)
                ok = False
        stack.pop()
        if not ok or state.get(claim_id) == "dropped":
            state[claim_id] = "dropped"
            return False
        claim = claims[claim_id]
        try:
            if claim.key is not UNKEYED:
                keys.claims[claim_id] = claim.key
            else:
                parts[claim_id] = claim_parts(claim, schema, ctx.macros, resolver)
                keys.claims[claim_id] = _key("clm", parts[claim_id], claim_id)
        except KeyingError as error:
            drop(claim_id, error.drop)
            return False
        state[claim_id] = "done"
        return True

    for claim in candidates.claims:
        visit(claim.id)

    for claim_id, member in (members or {}).items():
        if claim_id not in keys.claims:
            code = (
                DropReason.DROPPED_DEPENDENCY
                if claim_id in keys.dropped
                else DropReason.UNKNOWN_CLAIM_REF
            )
            keys.dropped_members[claim_id] = Drop(code, claim_id)
            continue
        claim = claims[claim_id]
        try:
            if claim_id not in parts:  # a claim that arrived keyed
                parts[claim_id] = claim_parts(claim, schema, ctx.macros, resolver)
            member = member_parts(claim, member, parts[claim_id], ctx, resolver, schema)
            member_key = _key("clm", member, claim_id)
        except KeyingError as error:
            keys.dropped_members[claim_id] = error.drop
            continue
        keys.members[claim_id] = member_key
    return keys


# --- Carry-over between key schemes (T8) -------------------------------------------------------

type Keyer = Callable[[KeyedCandidateSet, KeyContext], Keys]


@dataclass(frozen=True)
class CarryOver:
    """A carry-over map between two key schemes (ADR-0023, T8): each old key with an available
    input mapped to its new key; `missing` the asked-for old keys no input produced (reported,
    never guessed); `split` the old keys that map to more than one new key."""

    from_scheme: int
    to_scheme: int
    mapping: dict[str, str]
    missing: frozenset[str]
    split: dict[str, frozenset[str]]


def carry_over(
    old_keys: Iterable[str],
    inputs: Iterable[tuple[KeyedCandidateSet, KeyContext]],
    old: Keyer,
    new: Keyer,
) -> CarryOver:
    """Key the stored inputs under both schemes' key functions and map every old key to the new
    key of the same candidate. Which inputs and how the outgoing scheme's function stays callable
    are the caller's (probe Q-6)."""
    found: dict[str, set[str]] = {}
    schemes: tuple[int, int] | None = None
    for candidates, ctx in inputs:
        before, after = old(candidates, ctx), new(candidates, ctx)
        schemes = (before.scheme, after.scheme)
        for table in ("entities", "statements", "references", "claims", "members"):
            mine, theirs = getattr(before, table), getattr(after, table)
            for ident, key in mine.items():
                if ident in theirs:
                    found.setdefault(key, set()).add(theirs[ident])
    wanted = frozenset(old_keys)
    from_scheme, to_scheme = schemes or (0, 0)
    return CarryOver(
        from_scheme,
        to_scheme,
        {k: next(iter(v)) for k, v in found.items() if k in wanted and len(v) == 1},
        frozenset(k for k in wanted if k not in found),
        {k: frozenset(v) for k, v in found.items() if k in wanted and len(v) > 1},
    )
