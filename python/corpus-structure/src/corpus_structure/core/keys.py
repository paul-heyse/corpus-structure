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
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import Any, Literal, Self, assert_never

import regex
from pydantic import (
    MISSING,
    Field,
    JsonValue,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from corpus_structure.core.batch import CORE_PREFIX, PrefixedName, StoredQualifiers, StoredScope
from corpus_structure.core.candidates import (
    CandidateClaim,
    CandidateEntity,
    CandidateStatement,
    KeyedCandidateSet,
)
from corpus_structure.core.canonical import canonical_json, make_key
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
    AuthoredAnd,
    AuthoredCondition,
    AuthoredForall,
    AuthoredNot,
    AuthoredOr,
    AuthoredPhrase,
    AuthoredPhraseNode,
    AuthoredValue,
    BoolValue,
    ClaimNode,
    CmpNode,
    CoreModel,
    DateValue,
    EntityRef,
    EnumValue,
    Formula,
    IntervalValue,
    MemberNode,
    NumberValue,
    PredNode,
    SetValue,
    StoredAnd,
    StoredCondition,
    StoredForall,
    StoredNot,
    StoredOr,
    StoredPhrase,
    StoredPhraseNode,
    StoredValue,
    SymbolBinding,
    TextValue,
)
from corpus_structure.core.vocab import DropReason, EntityScope

Json = Any

# Core qualifier names as the stored form (and so every key) writes them.
MODALITY, POLARITY, ATTRIBUTION = "core:modality", "core:polarity", "core:attribution"
CONDITIONS, SCOPE, VALID_TIME = "core:conditions", "core:scope", "core:valid_time"
Resolve = Callable[[str], str]  # a reference (entity, statement or claim id) to its key

type Value = AuthoredValue | StoredValue
type Condition = AuthoredCondition | StoredCondition
# A qualifier's typed value: a core qualifier's field, or a schema qualifier's raw JSON made typed.
type QualifierValue = (
    EntityRef | StoredValue | StoredCondition | str | int | bool
    | dict[str, QualifierValue] | tuple[QualifierValue, ...] | None
)  # fmt: skip


# --- Text and label forms ----------------------------------------------------------------------


def collapse(text: str) -> str:
    """NFC with whitespace runs collapsed to one space and the ends trimmed."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def text_form(text: str) -> str:
    """The D1 §6.2 text form: NFC, casefolded, whitespace collapsed."""
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


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


def normalize_label(text: str, type_: str, rules: LabelRules) -> str:
    """Text form; one leading article removed; the rewrites in order; the class's head words
    removed as trailing whole words; whitespace collapsed again. Never empties a label."""
    label = text_form(text)
    words = label.split(" ")
    articles = {text_form(a) for a in rules.articles}
    if len(words) > 1 and words[0] in articles:
        label = " ".join(words[1:])
    for rewrite in rules.rewrites:
        label = regex.sub(rewrite.match, rewrite.replace, label)
    label = text_form(label)
    heads = {text_form(w) for w in rules.head_words.get(type_, ())}
    words = label.split(" ") if label else []
    while len(words) > 1 and words[-1] in heads:
        words.pop()
    return text_form(" ".join(words))


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
            case DropReason.OUTSIDE_UNRESOLVED:
                return f"statement {ref} lies outside the unit and is unresolved"
            case DropReason.UNKNOWN_REFERENCE:
                return f"unknown item {ref}"
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


# --- Canonical values and conditions -----------------------------------------------------------


def canonical_value(
    value: EntityRef | Value, macros: Mapping[str, MacroDef], resolve: Resolve
) -> Json:
    """The key form of a value or entity reference (JSON), per D1 §6.2."""
    match value:
        case EntityRef(ref=ref):
            return {"key": resolve(ref)}
        case TextValue(v=v):
            return {"t": "text", "v": text_form(v)}
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
            return {"t": "phrase", "text": text_form(text)}
        case BoolValue(v=v):
            return {"t": "bool", "v": v}
        case EnumValue(enum=enum, v=v):
            return {"t": "enum", "enum": enum, "v": v}
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
        case AuthoredPhraseNode() | StoredPhraseNode():  # `unsupported` leaves included
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
    resolve: Resolve,
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
    resolve: Resolve,
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
            return {"op": "claim", "ref": resolve(ref)}
        case MemberNode(x=x, set=set_):
            return {"op": "member", "x": value(x), "set": value(set_)}
        case CmpNode(rel=rel, lhs=lhs, rhs=rhs):
            if rel in (">", ">="):
                rel, lhs, rhs = {">": "<", ">=": "<="}[rel], rhs, lhs
            sides = [value(lhs), value(rhs)]
            if rel in ("=", "!="):  # symmetric relations: operands in canonical order
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
        case AuthoredPhraseNode(op=op, text=text) | StoredPhraseNode(op=op, text=text):
            return {"op": op, "text": text_form(text)}
        case _:
            assert_never(n)


def canonical_binding(
    symbol: str, binding: SymbolBinding, macros: Mapping[str, MacroDef], resolve: Resolve
) -> Json:
    """The key form of one symbol binding (used only in alternative member keys)."""
    out: Json = {"symbol": symbol_form(symbol, macros), "bind": binding.bind}
    if binding.entity is not MISSING:
        out["entity"] = resolve(binding.entity)
    if binding.claim is not MISSING:
        out["claim"] = resolve(binding.claim)
    if binding.param is not MISSING:
        out["param"] = binding.param
    return out


def expressions(
    value: QualifierValue | StoredScope | EntityRef | Value,
) -> Iterator[Formula | SetValue]:
    """Every formula and set inside a value, a condition tree (through `condition_nodes`), or a
    typed qualifier value."""
    match value:
        case Formula() | SetValue():
            yield value
        case IntervalValue():
            for bound in (value.start, value.end):
                if isinstance(bound, Formula):
                    yield bound
        case (
            TextValue() | NumberValue() | BoolValue() | EnumValue() | DateValue()
            | AuthoredPhrase() | StoredPhrase() | EntityRef() | StoredScope()
        ):  # fmt: skip
            return
        case (
            AuthoredAnd() | AuthoredOr() | AuthoredNot() | AuthoredForall() | StoredAnd()
            | StoredOr() | StoredNot() | StoredForall() | ClaimNode() | MemberNode() | CmpNode()
            | PredNode() | AuthoredPhraseNode() | StoredPhraseNode()
        ):  # fmt: skip
            for node in condition_nodes(value):
                for v in _parts(node)[1]:
                    yield from expressions(v)
        case dict():
            for item in value.values():
                yield from expressions(item)
        case tuple():
            for item in value:
                yield from expressions(item)
        case str() | int() | bool() | None:
            return
        case _:
            assert_never(value)


# --- Qualifiers --------------------------------------------------------------------------------


class _Unset(Enum):
    UNSET = "unset"


UNSET: Literal[_Unset.UNSET] = _Unset.UNSET

# stored core qualifier name (`core:hedge`) -> its `StoredQualifiers` field
_CORE_FIELDS: dict[str, str] = {
    info.alias: name for name, info in StoredQualifiers.model_fields.items() if info.alias
}
_STORED_VALUE: TypeAdapter[Any] = TypeAdapter(StoredValue)


def _typed_json(raw: JsonValue, name: str, path: tuple[str, ...]) -> QualifierValue:
    """A schema qualifier's raw JSON as typed values: an object with `t` is a stored value, one
    whose only key is `ref` an entity reference (by shape until F2d's canonical form by range);
    maps and lists keep their structure. Anything else (a float, a malformed value) is refused."""
    match raw:
        case dict() if "t" in raw or set(raw) == {"ref"}:
            try:
                if "t" in raw:
                    return _STORED_VALUE.validate_python(raw)
                return EntityRef.model_validate(raw)
            except ValidationError:
                raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path) from None
        case dict():
            return {k: _typed_json(v, name, (*path, k)) for k, v in raw.items()}
        case list() | tuple():
            return tuple(_typed_json(v, name, (*path, str(i))) for i, v in enumerate(raw))
        case bool() | int() | str() | None:
            return raw
        case _:  # a float: no canonical JSON (D1 §6.2 writes numbers as decimals)
            raise KeyingError(DropReason.MALFORMED_QUALIFIER, name, path)


def qualifier_value(
    qualifiers: StoredQualifiers, name: str
) -> QualifierValue | StoredScope | Literal[_Unset.UNSET]:
    """The typed value of a qualifier by its stored name, or `UNSET` when it is absent or (for
    `modality` and `polarity`) the default, which equal JSON leaves out."""
    attr = _CORE_FIELDS.get(name)
    if attr is None:
        extras = qualifiers.__pydantic_extra__ or {}
        return _typed_json(extras[name], name, ()) if name in extras else UNSET
    value = getattr(qualifiers, attr)
    exclude = StoredQualifiers.model_fields[attr].exclude_if
    if value is MISSING or (exclude is not None and exclude(value)):
        return UNSET
    return value


def canonical_qualifier(
    value: QualifierValue, macros: Mapping[str, MacroDef], resolve: Resolve
) -> Json:
    """A qualifier's canonical form: a value, an entity reference, a condition tree, a literal
    (text form) or a map/list of them."""
    match value:
        case (
            EntityRef() | TextValue() | NumberValue() | BoolValue() | EnumValue() | Formula()
            | SetValue() | DateValue() | IntervalValue() | StoredPhrase()
        ):  # fmt: skip
            return canonical_value(value, macros, resolve)
        case (
            StoredAnd() | StoredOr() | StoredNot() | StoredForall() | ClaimNode() | MemberNode()
            | CmpNode() | PredNode() | StoredPhraseNode()
        ):  # fmt: skip
            return canonical_condition(value, macros, resolve)
        case dict():
            return {k: canonical_qualifier(v, macros, resolve) for k, v in value.items()}
        case tuple():
            return [canonical_qualifier(v, macros, resolve) for v in value]
        case str():
            return text_form(value)
        case bool() | int() | None:
            return value
        case _:
            assert_never(value)


# --- Schema facts and the rendition ------------------------------------------------------------


class KeySchema(CoreModel):
    """The schema facts keys need (from S1's compiled lookup), every name prefixed as the stored
    form writes it: classes, slots, predicates and qualifiers. `predicates` lists every predicate
    the schema knows; a claim with another is refused.

    A malformed schema is refused on construction (`ValueError`): that is an input error, not a
    keying outcome, so it carries no `DropReason`."""

    identity_keys: dict[PrefixedName, tuple[PrefixedName, ...]] = Field(default_factory=dict)
    entity_identity: dict[PrefixedName, tuple[PrefixedName, ...]] = Field(default_factory=dict)
    predicates: frozenset[PrefixedName] = frozenset()
    identity_qualifiers: dict[PrefixedName, tuple[PrefixedName, ...]] = Field(
        default_factory=dict
    )  # predicate -> its schema identity qualifiers
    # condition predicates, named as condition trees name them
    symmetric_predicates: frozenset[str] = frozenset()

    @model_validator(mode="after")
    def _qualifiers_of_known_predicates(self) -> Self:
        for name, qualifiers in self.identity_qualifiers.items():
            if name not in self.predicates:
                raise ValueError(f"identity_qualifiers names {name!r}, not a known predicate")
            for qualifier in qualifiers:
                if qualifier.startswith(f"{CORE_PREFIX}:"):
                    raise ValueError(
                        f"identity_qualifiers names {qualifier!r}: a core qualifier's key role "
                        "is fixed"
                    )
        return self

    def predicate(self, name: str) -> str:
        """`name` when the schema knows the predicate; otherwise refused."""
        if name in self.predicates:
            return name
        raise KeyingError(DropReason.UNKNOWN_PREDICATE, name)


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
    def segments(self) -> dict[str, Segment]:
        """Segment key -> segment on this rendition."""
        ren = rendition_key(self.document_key, content_digest(self.content))
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
    entity: CandidateEntity, schema: KeySchema, rules: LabelRules, resolve: Resolve
) -> str:
    """`ent`: type and identity attributes; the normalized label when identity is incomplete."""
    declared = schema.identity_keys.get(entity.type, ())
    entity_slots = set(schema.entity_identity.get(entity.type, ()))
    identity: Json = {}
    for slot in declared:
        if slot in entity.identity:
            value = entity.identity[slot]
            identity[slot] = resolve(value) if slot in entity_slots else text_form(value)
    parts: Json = {"type": entity.type, "identity": identity}
    if not declared or len(identity) < len(declared):
        parts["label"] = normalize_label(entity.label, entity.type, rules)
    return make_key("ent", parts)


def local_entity_key(entity: CandidateEntity, ctx: KeyContext, rules: LabelRules) -> str:
    """`ent`: type, the scope segment's locator (structured), and the symbol or normalized label."""
    assert entity.scope_segment is not None
    parts: Json = {"type": entity.type, "scope": ctx.locator_key(ctx.segment(entity.scope_segment))}
    if entity.symbol:
        parts["symbol"] = symbol_form(entity.symbol, ctx.macros)
    else:
        parts["label"] = normalize_label(entity.label, entity.type, rules)
    return make_key("ent", parts)


def statement_anchor(statement: CandidateStatement, ctx: KeyContext) -> tuple[Segment, int]:
    """The statement's anchor segment and the 1-based ordinal of its first sentence there.

    The anchor is the innermost `details` or `unit` containing the first anchor segment, else the
    annotation unit containing it, else the top-level block outside every unit that contains it (a
    list, table, figure, …: an `uncovered` block of `annotation_units`), else the outermost
    block below sections and the document; never the document unless that is the segment itself.
    """
    if statement.anchor == "outside":
        raise KeyingError(DropReason.OUTSIDE_UNRESOLVED, statement.id)
    first = min((ctx.segment(k) for k in statement.anchor), key=lambda s: (s.start, -s.end))
    chain = [first, *ctx.ancestors(first)]
    anchor = next((s for s in chain if s.kind in (SegmentKind.DETAILS, SegmentKind.UNIT)), None)
    if anchor is None:
        tops = ctx.top_blocks
        anchor = next((s for s in chain if (s.kind, s.start, s.end) in tops), None)
    if anchor is None:
        blocks = [s for s in chain if s.kind not in (SegmentKind.SECTION, SegmentKind.DOCUMENT)]
        anchor = blocks[-1] if blocks else first
    before = sum(
        1 for s in anchor.walk() if s.kind is SegmentKind.SENTENCE and s.start < first.start
    )
    return anchor, before + 1


def statement_key(statement: CandidateStatement, ctx: KeyContext) -> str:
    """`stm`: the anchor's generated locator (structured) and the first sentence's ordinal."""
    anchor, ordinal = statement_anchor(statement, ctx)
    return make_key("stm", {"anchor": ctx.locator_key(anchor), "ordinal": ordinal})


# --- Claim keys --------------------------------------------------------------------------------


def _object_part(
    obj: EntityRef | StoredValue, macros: Mapping[str, MacroDef], resolve: Resolve
) -> Json:
    match obj:
        case EntityRef(ref=ref):
            return {"key": resolve(ref)}
        case _:
            return {"value": canonical_value(obj, macros, resolve)}


def claim_parts(
    claim: CandidateClaim,
    schema: KeySchema,
    macros: Mapping[str, MacroDef],
    resolve: Resolve,
) -> Json:
    """The parts of a claim key: subject, predicate, object, statement and the identity
    qualifiers, all named as the stored form names them (`core:modality`, `stat:param_values`)."""
    predicate = schema.predicate(claim.predicate)
    q = claim.qualifiers
    parts: Json = {
        "subject": resolve(claim.subject),
        "predicate": predicate,
        "object": _object_part(claim.object, macros, resolve),
    }
    if claim.statement is not None:
        parts["statement"] = resolve(claim.statement)
    identity: Json = {}
    for name in (MODALITY, POLARITY):
        value = qualifier_value(q, name)
        if value is not UNSET:  # present only when not the default
            identity[name] = value
    if q.conditions is not MISSING:
        tree = canonical_condition(q.conditions, macros, resolve, schema.symmetric_predicates)
        if tree is not None:
            identity[CONDITIONS] = tree
    if q.valid_time is not MISSING:
        identity[VALID_TIME] = canonical_value(q.valid_time, macros, resolve)
    if q.modality == "cited" and q.attribution is not MISSING:
        identity[ATTRIBUTION] = resolve(q.attribution.ref)
    for name in schema.identity_qualifiers.get(predicate, ()):
        value = qualifier_value(q, name)
        if value is not UNSET and not isinstance(value, StoredScope):
            identity[name] = canonical_qualifier(value, macros, resolve)
    parts["qualifiers"] = identity
    return parts


def claim_bindings(claim: CandidateClaim, macros: Mapping[str, MacroDef], resolve: Resolve) -> Json:
    """Every formula's or set's canonical bindings beside its canonical value, over the object and
    every qualifier, sorted by canonical JSON, so neither argument order nor a rewritten comparison
    moves them."""
    q = claim.qualifiers
    names = (*_CORE_FIELDS, *(q.__pydantic_extra__ or {}))
    found = [*expressions(claim.object)]
    for name in names:
        value = qualifier_value(q, name)
        if value is not UNSET:
            found.extend(expressions(value))
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
    claim: CandidateClaim, member: Member, base: Json, ctx: KeyContext, resolve: Resolve
) -> Json:
    """A member's key parts: the claim's parts (`base`, from `claim_parts`) plus its canonical
    disagreeing qualifiers (null when it leaves one unset) and, when bindings disagree, its
    canonical bindings. A stored `scope` enters by its extent and its segment's locator, never by
    the physical segment key."""
    own: Json = {}
    for name in sorted(member.qualifiers):
        value = qualifier_value(claim.qualifiers, name)
        match value:
            case _Unset.UNSET:
                own[name] = None
            case StoredScope(extent=extent, segment=segment):
                own[name] = {"extent": extent, "segment": ctx.locator_key(ctx.segment(segment))}
            case _:
                own[name] = canonical_qualifier(value, ctx.macros, resolve)
    extra: Json = {"qualifiers": own}
    if member.bindings:
        extra["bindings"] = claim_bindings(claim, ctx.macros, resolve)
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
    """Keys by candidate id, alternatives' member keys, and the dropped items with their codes."""

    entities: dict[str, str] = field(default_factory=dict)
    statements: dict[str, str] = field(default_factory=dict)
    claims: dict[str, str] = field(default_factory=dict)
    members: dict[str, str] = field(default_factory=dict)
    dropped: dict[str, Drop] = field(default_factory=dict)
    dropped_members: dict[str, Drop] = field(default_factory=dict)
    outside: set[str] = field(default_factory=set)  # unresolved "outside" statements

    def of(self, ref: str) -> str:
        for table in (self.entities, self.statements, self.claims):
            if ref in table:
                return table[ref]
        if ref in self.outside:
            raise KeyingError(DropReason.OUTSIDE_UNRESOLVED, ref)
        if ref in self.dropped:
            raise KeyingError(DropReason.DROPPED_DEPENDENCY, ref)
        raise KeyingError(DropReason.UNKNOWN_REFERENCE, ref)


def _entity_keys(
    candidates: KeyedCandidateSet,
    ctx: KeyContext,
    schema: KeySchema,
    rules: LabelRules,
    keys: Keys,
) -> None:
    by_id = {e.id: e for e in candidates.entities}
    visiting: set[str] = set()

    def key_of(entity_id: str) -> str:
        if entity_id in keys.entities:
            return keys.entities[entity_id]
        entity = by_id.get(entity_id)
        if entity is None:
            raise KeyingError(DropReason.UNKNOWN_IDENTITY_ENTITY, entity_id)
        if entity_id in visiting:
            raise KeyingError(DropReason.IDENTITY_CYCLE, entity_id)
        visiting.add(entity_id)
        if entity.key is not None:
            key = entity.key
        elif entity.scope is EntityScope.LOCAL:
            key = local_entity_key(entity, ctx, rules)
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
    """Key every candidate: entities, statements, then claims in a topological order of their
    condition `claim` references. A candidate that cannot be keyed (on or behind a reference
    cycle, naming an unknown or dropped item, an unknown predicate, an unresolved `outside`
    statement, a malformed schema qualifier) is dropped with its `Drop` (D5 §5.2), never raised.
    `members` (C1's) adds member keys, reusing each claim's parts; a member that cannot be keyed is
    in `dropped_members` with its `Drop`."""
    keys = Keys()
    _entity_keys(candidates, ctx, schema, rules, keys)
    for statement in candidates.statements:
        if statement.key is not None:
            keys.statements[statement.id] = statement.key
        elif statement.anchor == "outside":
            keys.outside.add(statement.id)  # consolidation resolves it to the statement it names
        else:
            try:
                keys.statements[statement.id] = statement_key(statement, ctx)
            except KeyingError as error:
                keys.dropped[statement.id] = error.drop

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
            if ref not in claims:
                drop(claim_id, Drop(DropReason.UNKNOWN_CLAIM_REF, ref))
                ok = False
            elif not visit(ref):
                drop(claim_id, Drop(DropReason.DROPPED_DEPENDENCY, ref))
                ok = False
        stack.pop()
        if not ok or state.get(claim_id) == "dropped":
            state[claim_id] = "dropped"
            return False
        claim = claims[claim_id]
        try:
            if claim.key is not None:
                keys.claims[claim_id] = claim.key
            else:
                parts[claim_id] = claim_parts(claim, schema, ctx.macros, keys.of)
                keys.claims[claim_id] = make_key("clm", parts[claim_id])
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
                parts[claim_id] = claim_parts(claim, schema, ctx.macros, keys.of)
            member_key = make_key("clm", member_parts(claim, member, parts[claim_id], ctx, keys.of))
        except KeyingError as error:
            keys.dropped_members[claim_id] = error.drop
            continue
        keys.members[claim_id] = member_key
    return keys
