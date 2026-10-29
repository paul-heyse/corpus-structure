"""Core qualifiers, generic batch items and envelopes in both forms, and the citation frame.

D1 §5.2, §10.3; D2 §7.3; foundations §3.5.

These are the schema-free shapes A0, the fixtures and the `claim_proposal` payload use; S1's
compiled envelope over the same bases is the full validation (predicate names, entity types,
statement kinds and schema qualifiers typed per predicate). The authored form cites evidence by
sentence id and quote and anchors statements by sentence ids, `"unit"`, or `"outside"` for a
statement the unit refers to but that lies outside it (S4 V2); the stored form has
offsets and segment keys on one rendition, which the record holding it names.

`CoreQualifiers` keeps `modality` and `polarity` with defaults that dumps leave out (equal meaning,
equal JSON) and that rule views see filled in; the other core qualifiers are absent by `MISSING`.
The closed sets, the defaults, the core qualifier names and the span invariants come from the
model (`vocab.py`, `_model/`; ADR-0020); the shape structure stays here until Stage B (P0-M-5).
It accepts schema qualifiers as raw JSON; S1's per-predicate models subclass it with
`extra="forbid"` and typed fields.
"""

from __future__ import annotations

import functools
import re
import types
import typing
from collections.abc import Callable, Iterator
from typing import Annotated, Any, Literal, Self

from pydantic import MISSING, BaseModel, ConfigDict, Field, JsonValue, RootModel, model_validator

from corpus_structure.core._model import names, validators
from corpus_structure.core._model.qualifiers import BY_NAME
from corpus_structure.core.values import (
    CITATION,
    SENTENCE_ID,
    AuthoredCondition,
    AuthoredObject,
    AuthoredPhrase,
    CoreModel,
    EntityRef,
    IntervalValue,
    Offset,
    SentenceId,
    StoredCondition,
    StoredObject,
    StoredPhrase,
    refuse_m11_fields,
)
from corpus_structure.core.vocab import (
    ClaimModality,
    EntityExtent,
    EntityScope,
    EvidenceRole,
    Polarity,
    ScopeExtent,
    StatementRole,
)

LocalRef = Annotated[str, Field(min_length=1)]

# The stored form names every schema element (class, predicate, qualifier, identity slot) by its
# prefixed name; the authored form keeps local names (coordinator ruling, 2026-10-28, from X2).
PREFIXED_NAME = r"^[a-z][a-z0-9_]*:[A-Za-z_][A-Za-z0-9_]*$"
PrefixedName = Annotated[str, Field(pattern=PREFIXED_NAME)]
CORE_PREFIX = names.PREFIX
_PREFIXED = re.compile(PREFIXED_NAME)

DEFAULT_MODALITY: ClaimModality = BY_NAME[names.MODALITY].default
DEFAULT_POLARITY: Polarity = BY_NAME[names.POLARITY].default


def _is_default_modality(value: object) -> bool:
    return value == DEFAULT_MODALITY


def _is_default_polarity(value: object) -> bool:
    return value == DEFAULT_POLARITY


# --- Core qualifiers ---------------------------------------------------------------------------


class _Qualifiers(CoreModel):
    model_config = ConfigDict(frozen=True, extra="allow")
    # schema qualifiers, raw JSON until S1 types them (Pydantic's typed-extras declaration)
    __pydantic_extra__: dict[str, JsonValue]  # type: ignore[bad-override]

    modality: ClaimModality = Field(DEFAULT_MODALITY, exclude_if=_is_default_modality)
    polarity: Polarity = Field(DEFAULT_POLARITY, exclude_if=_is_default_polarity)
    attribution: EntityRef | MISSING = MISSING  # type: ignore[valid-type]
    valid_time: IntervalValue | MISSING = MISSING  # type: ignore[valid-type]


class StoredScope(CoreModel):
    """The stored scope qualifier: the extent and the segment it resolves to on the rendition."""

    extent: ScopeExtent
    segment: str = Field(min_length=1)


class AuthoredQualifiers(_Qualifiers):
    hedge: AuthoredPhrase | MISSING = MISSING  # type: ignore[valid-type]
    conditions: AuthoredCondition | MISSING = MISSING  # type: ignore[valid-type]
    scope: ScopeExtent | MISSING = MISSING  # type: ignore[valid-type]


CORE_QUALIFIERS = names.QUALIFIERS
STORED_CORE_QUALIFIERS = names.STORED_QUALIFIERS


def _core(name: str) -> str:
    return f"{CORE_PREFIX}:{name}"


class StoredQualifiers(CoreModel):
    """The stored qualifiers: the core ones as `core:<name>`, schema qualifiers by prefixed name.

    Attributes keep the local names (`q.modality`); validation and dumps use the prefixed ones."""

    model_config = ConfigDict(
        frozen=True,
        extra="allow",
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
    )
    # schema qualifiers, raw JSON until S1 types them (Pydantic's typed-extras declaration)
    __pydantic_extra__: dict[str, JsonValue]  # type: ignore[bad-override]

    modality: ClaimModality = Field(
        DEFAULT_MODALITY, alias=_core("modality"), exclude_if=_is_default_modality
    )
    polarity: Polarity = Field(
        DEFAULT_POLARITY, alias=_core("polarity"), exclude_if=_is_default_polarity
    )
    hedge: StoredPhrase | MISSING = Field(MISSING, alias=_core("hedge"))  # type: ignore[valid-type]
    attribution: EntityRef | MISSING = Field(MISSING, alias=_core("attribution"))  # type: ignore[valid-type]
    conditions: StoredCondition | MISSING = Field(MISSING, alias=_core("conditions"))  # type: ignore[valid-type]
    scope: StoredScope | MISSING = Field(MISSING, alias=_core("scope"))  # type: ignore[valid-type]
    valid_time: IntervalValue | MISSING = Field(MISSING, alias=_core("valid_time"))  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _schema_qualifiers_prefixed(self) -> Self:
        for name in self.__pydantic_extra__ or {}:
            if not _PREFIXED.match(name):
                raise ValueError(f"stored qualifier {name!r} is not a prefixed name")
            if name.startswith(f"{CORE_PREFIX}:"):
                raise ValueError(f"{name!r} is not a core qualifier")
        return self


# --- Evidence ----------------------------------------------------------------------------------


class _Span(CoreModel):
    start: Offset
    end: Offset


class AuthoredEvidence(CoreModel):
    sentence: SentenceId
    quote: str = Field(min_length=1)
    role: EvidenceRole


class StoredEvidence(_Span):
    role: EvidenceRole
    coarse: bool | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        validators.evidence(self)
        return self


# --- Items -------------------------------------------------------------------------------------


class _Entity(CoreModel):
    local_ref: LocalRef
    type: str
    label: str
    scope: EntityScope
    extent: EntityExtent | MISSING = MISSING  # type: ignore[valid-type]
    symbol: str | MISSING = MISSING  # type: ignore[valid-type]
    aliases: tuple[str, ...] = ()
    identity: dict[str, str] = Field(default_factory=dict)  # slot -> local ref or literal

    @model_validator(mode="after")
    def _extent_only_local(self) -> Self:
        if self.scope is EntityScope.GLOBAL and self.extent is not MISSING:
            raise ValueError("only a local entity has an extent")
        return self


class AuthoredEntity(_Entity):
    pass


class StoredEntity(_Entity):
    type: PrefixedName  # type: ignore[assignment]
    identity: dict[PrefixedName, str] = Field(default_factory=dict)  # type: ignore[assignment]
    scope_segment: str | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _segment_iff_local(self) -> Self:
        if (self.scope is EntityScope.LOCAL) != (self.scope_segment is not MISSING):
            raise ValueError("a stored entity has a scope_segment exactly when it is local")
        return self


class AuthoredStatement(CoreModel):
    local_ref: LocalRef
    kind: str
    # "outside": a statement the unit refers to that lies outside it ("the last result"; S4 V2)
    anchor: Literal["unit", "outside"] | Annotated[tuple[SentenceId, ...], Field(min_length=1)]


class StoredStatement(CoreModel):
    local_ref: LocalRef
    kind: str
    # segment keys, or "outside": the cascade has no segment to anchor such a statement to
    anchor: Literal["outside"] | Annotated[tuple[str, ...], Field(min_length=1)]


class _Claim(CoreModel):
    local_ref: LocalRef
    predicate: str
    subject: LocalRef
    statement: str | MISSING = MISSING  # type: ignore[valid-type]
    statement_role: StatementRole | MISSING = MISSING  # type: ignore[valid-type]


class AuthoredClaim(_Claim):
    object: AuthoredObject
    qualifiers: AuthoredQualifiers = Field(default_factory=AuthoredQualifiers)
    evidence: Annotated[tuple[AuthoredEvidence, ...], Field(min_length=1)]


class StoredClaim(_Claim):
    predicate: PrefixedName  # type: ignore[assignment]
    object: StoredObject
    qualifiers: StoredQualifiers = Field(default_factory=StoredQualifiers)
    evidence: Annotated[tuple[StoredEvidence, ...], Field(min_length=1)]


class AlternativeItem(CoreModel):
    refs: Annotated[tuple[LocalRef, ...], Field(min_length=2)]
    reason: str


class AuthoredUnsupported(CoreModel):
    local_ref: LocalRef
    sentence: SentenceId
    quote: str = Field(min_length=1)
    reason: str


class StoredUnsupported(_Span):
    local_ref: LocalRef
    reason: str
    coarse: bool | MISSING = MISSING  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        validators.unsupported_item(self)
        return self


# The item unions of each form: what a batch's item lists hold.
type AuthoredItem = (
    AuthoredEntity | AuthoredStatement | AuthoredClaim | AlternativeItem | AuthoredUnsupported
)
type StoredItem = StoredEntity | StoredStatement | StoredClaim | AlternativeItem | StoredUnsupported


# --- Envelopes ---------------------------------------------------------------------------------


class _Batch(CoreModel):
    unit_ref: str = Field(min_length=1)

    def local_refs(self) -> Iterator[tuple[str, str]]:
        """Each item's (kind, local ref), in batch order."""
        for kind in ("entities", "statements", "claims", "unsupported"):
            for item in getattr(self, kind):
                yield kind, item.local_ref

    @model_validator(mode="after")
    def _well_formed(self) -> Self:
        seen: dict[str, str] = {}
        for kind, ref in self.local_refs():
            if ref in seen:
                raise ValueError(f"local ref {ref!r} is used by {seen[ref]} and {kind}")
            seen[ref] = kind
        m11 = refuse_m11_fields(self)
        if m11:
            raise ValueError(f"sympy and parse are set by M11 only, never in a batch: {m11}")
        return self


class AuthoredBatch(_Batch):
    entities: tuple[AuthoredEntity, ...] = ()
    statements: tuple[AuthoredStatement, ...] = ()
    claims: tuple[AuthoredClaim, ...] = ()
    alternatives: tuple[AlternativeItem, ...] = ()
    unsupported: tuple[AuthoredUnsupported, ...] = ()


class StoredBatch(_Batch):
    entities: tuple[StoredEntity, ...] = ()
    statements: tuple[StoredStatement, ...] = ()
    claims: tuple[StoredClaim, ...] = ()
    alternatives: tuple[AlternativeItem, ...] = ()
    unsupported: tuple[StoredUnsupported, ...] = ()


# --- The citation frame ------------------------------------------------------------------------


class FrameEntry(CoreModel):
    """One cited sentence: its locator (D1 §3.4) and its canonical text."""

    locator: str = Field(min_length=1)
    text: str


class CitationFrame(RootModel[dict[Annotated[str, Field(pattern=SENTENCE_ID)], FrameEntry]]):
    """Maps each cited sentence id (`sN`, or `cN` of the standing context) to locator and text."""

    model_config = ConfigDict(frozen=True, json_schema_extra={"additionalProperties": False})

    def __getitem__(self, sentence: str) -> FrameEntry:
        return self.root[sentence]

    def __contains__(self, sentence: object) -> bool:
        return sentence in self.root

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        return iter(self.root)


# --- Citation positions -----------------------------------------------------------------------


@functools.cache
def _citation_fields(model: type[BaseModel]) -> dict[str, frozenset[str]]:
    """The model's declared fields that cite sentences: "one" when the field is a `SentenceId`
    (`sentence`), "many" when it is a tuple of them (`anchor`), found by the `CITATION` marker in
    the field's annotation, never by its name. Undeclared extras (schema qualifiers) cite
    nothing."""
    out: dict[str, frozenset[str]] = {}
    for name, info in model.model_fields.items():
        kinds = (
            frozenset({"one"}) if CITATION in info.metadata else _citation_kinds(info.annotation)
        )
        if kinds:
            out[name] = kinds
    return out


def _citation_kinds(annotation: object) -> frozenset[str]:
    if typing.get_origin(annotation) is Annotated:
        base, *metadata = typing.get_args(annotation)
        return frozenset({"one"}) if CITATION in metadata else _citation_kinds(base)
    origin = typing.get_origin(annotation)
    if origin is tuple:
        items = [a for a in typing.get_args(annotation) if a is not Ellipsis]
        return (
            frozenset({"many"}) if any("one" in _citation_kinds(a) for a in items) else frozenset()
        )
    if origin is typing.Union or origin is types.UnionType:
        found: frozenset[str] = frozenset()
        for member in typing.get_args(annotation):
            found |= _citation_kinds(member)
        return found
    return frozenset()


def _rewrite(node: Any, cite: Callable[[str], str]) -> Any:
    if isinstance(node, BaseModel):
        cites = _citation_fields(type(node))
        update: dict[str, Any] = {}
        for name in type(node).model_fields:
            value = getattr(node, name)
            kinds = cites.get(name, frozenset())
            if isinstance(value, str) and "one" in kinds:
                moved: Any = cite(value)
            elif isinstance(value, tuple) and "many" in kinds:
                moved = tuple(cite(s) for s in value)
            else:
                moved = _rewrite(value, cite)
            if moved is not value and moved != value:
                update[name] = moved
        return node.model_copy(update=update) if update else node
    if isinstance(node, tuple):
        items = tuple(_rewrite(item, cite) for item in node)
        return node if all(a is b for a, b in zip(items, node, strict=True)) else items
    if isinstance(node, dict):
        mapped = {key: _rewrite(item, cite) for key, item in node.items()}
        return node if all(mapped[k] is node[k] for k in node) else mapped
    return node


def rewrite_citations[M: BaseModel](model: M, cite: Callable[[str], str]) -> M:
    """`model` with every sentence id at a citation position replaced by `cite(id)`, visited in
    field order. Citation positions are found by their declared `SentenceId` type through nested
    models, tuples and dicts; raw schema-qualifier JSON is never one, so a pack qualifier named
    `sentence` is not a citation (R03)."""
    return _rewrite(model, cite)


def cited_sentences(batch: AuthoredBatch) -> list[str]:
    """Every sentence id an authored batch cites, in first-use order (values and nodes included)."""
    seen: dict[str, None] = {}

    def record(sentence: str) -> str:
        seen.setdefault(sentence)
        return sentence

    rewrite_citations(batch, record)
    return list(seen)
