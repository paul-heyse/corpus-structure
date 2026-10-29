"""Core qualifiers, generic batch items and envelopes in both forms, and the citation frame.

D1 §5.2, §10.3; D2 §7.3; foundations §3.5.

These are the schema-free shapes A0, the fixtures and the `claim_proposal` payload use; S1's
compiled envelope over the same bases is the full validation (predicate names, entity types,
statement kinds and schema qualifiers typed per predicate). The authored form cites evidence by
sentence id and quote and anchors statements by sentence ids or `"unit"`; the stored form has
offsets and segment keys on one rendition, which it names by its `ren` key (`StoredBatch.rendition`;
F2e, R04), beside the row-level column of the record that holds it.

A statement the unit refers to but that lies outside it ("the last result", an author `[n]` link;
S4 V2) is an `outside` item in `statements[]` (`AuthoredOutside`, `StoredOutside`): a typed
`ExternalReference` node with its descriptor (the citing sentence and quote when authored, the
quote's span when stored, and the author's link target) and no kind (D1 §4.4, D2 §7.3).

Claims carry their `establishment` (`stated` by default, left out of dumps like `modality`) and,
exactly when derived, `derived_from` and `rule` (the model's `ClaimItem` invariant). References are
typed by kind (`values.EntityId`, `StatementId`, `ClaimId`, `SubjectId`); `validate` (S2) checks
them against a batch's items (RC19).

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

from pydantic import (
    MISSING,
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    JsonValue,
    RootModel,
    Tag,
    model_validator,
)

from corpus_structure.core._model import names, validators
from corpus_structure.core._model.qualifiers import BY_NAME
from corpus_structure.core.canonical import KEY_HEX_DIGITS
from corpus_structure.core.values import (
    CITATION,
    PREFIXED_NAME,
    SENTENCE_ID,
    AuthoredCondition,
    AuthoredObject,
    AuthoredPhrase,
    ClaimId,
    CoreModel,
    EntityRef,
    IntervalValue,
    Offset,
    PrefixedName,
    SentenceId,
    StatementId,
    StoredCondition,
    StoredObject,
    StoredPhrase,
    SubjectId,
    refuse_m11_fields,
)
from corpus_structure.core.vocab import (
    ClaimModality,
    EntityExtent,
    EntityScope,
    Establishment,
    EvidenceRole,
    Polarity,
    ScopeExtent,
    StatementRole,
)

LocalRef = Annotated[str, Field(min_length=1)]
# A rendition by its `ren` key (D1 §10.1): the typed reference a stored batch and a keyed candidate
# set carry (R04).
RENDITION_KEY = rf"^ren:[0-9a-f]{{{KEY_HEX_DIGITS}}}$"
RenditionKey = Annotated[str, Field(pattern=RENDITION_KEY)]

CORE_PREFIX = names.PREFIX
_PREFIXED = re.compile(PREFIXED_NAME)

DEFAULT_MODALITY: ClaimModality = BY_NAME[names.MODALITY].default
# `ClaimModality` is schema-version-scoped: the generic shapes admit a pack's members (a local
# name, or a prefixed one), and S1's per-version models and S2's checks refuse what the run's
# schema version lacks; `ClaimModality` lists the core members.
ModalityName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*(:[a-z][a-z0-9_]*)?$")]
DEFAULT_POLARITY: Polarity = BY_NAME[names.POLARITY].default


def _is_default_modality(value: object) -> bool:
    return value == DEFAULT_MODALITY


def _is_default_polarity(value: object) -> bool:
    return value == DEFAULT_POLARITY


def _is_stated(value: object) -> bool:
    return value == Establishment.STATED


# --- Core qualifiers ---------------------------------------------------------------------------


class _Qualifiers(CoreModel):
    model_config = ConfigDict(frozen=True, extra="allow")
    # schema qualifiers, raw JSON until S1 types them (Pydantic's typed-extras declaration)
    __pydantic_extra__: dict[str, JsonValue]  # type: ignore[bad-override]

    modality: ModalityName = Field(DEFAULT_MODALITY, exclude_if=_is_default_modality)
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

    modality: ModalityName = Field(
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
    def _only_local(self) -> Self:
        validators.entity_item(self)  # extent, scope_segment: only on a local entity
        return self


class AuthoredEntity(_Entity):
    pass


class StoredEntity(_Entity):
    type: PrefixedName  # type: ignore[assignment]
    identity: dict[PrefixedName, str] = Field(default_factory=dict)  # type: ignore[assignment]
    # absent on a local entity whose extent resolves to no segment (reported, never guessed)
    scope_segment: str | MISSING = MISSING  # type: ignore[valid-type]


class AuthoredStatement(CoreModel):
    local_ref: LocalRef
    kind: str
    anchor: Literal["unit"] | Annotated[tuple[SentenceId, ...], Field(min_length=1)]


class StoredStatement(CoreModel):
    local_ref: LocalRef
    kind: str
    anchor: Annotated[tuple[str, ...], Field(min_length=1)]  # segment keys


class AuthoredDescriptor(CoreModel):
    """An authored external reference's citing text: the sentence and the quote that makes the
    reference, and the author's link target when the text gives one (a D1 §3.4 locator or author
    link target, as written)."""

    sentence: SentenceId
    quote: str = Field(min_length=1)
    target: str | MISSING = Field(MISSING, min_length=1)  # type: ignore[valid-type]


class StoredDescriptor(CoreModel):
    """A stored external reference's citing text: the quote's located span (`coarse` when only its
    sentence was located) and the link target."""

    start: Offset
    end: Offset
    coarse: bool | MISSING = MISSING  # type: ignore[valid-type]
    target: str | MISSING = Field(MISSING, min_length=1)  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        validators.reference_descriptor(self)
        return self


class AuthoredOutside(CoreModel):
    """A statement outside the unit (S4 V2): an `ExternalReference` node, with no kind."""

    local_ref: LocalRef
    anchor: Literal["outside"]
    descriptor: AuthoredDescriptor


class StoredOutside(CoreModel):
    local_ref: LocalRef
    anchor: Literal["outside"]
    descriptor: StoredDescriptor


def _statement_or_outside(raw: Any) -> str:
    anchor = raw.get("anchor") if isinstance(raw, dict) else getattr(raw, "anchor", None)
    return "outside" if anchor == "outside" else "statement"


type AuthoredStatementItem = Annotated[
    Annotated[AuthoredStatement, Tag("statement")] | Annotated[AuthoredOutside, Tag("outside")],
    Discriminator(_statement_or_outside),
]
type StoredStatementItem = Annotated[
    Annotated[StoredStatement, Tag("statement")] | Annotated[StoredOutside, Tag("outside")],
    Discriminator(_statement_or_outside),
]


class _Claim(CoreModel):
    local_ref: LocalRef
    predicate: str
    subject: SubjectId
    statement: StatementId | MISSING = MISSING  # type: ignore[valid-type]
    statement_role: StatementRole | MISSING = MISSING  # type: ignore[valid-type]
    establishment: Establishment = Field(Establishment.STATED, exclude_if=_is_stated)
    derived_from: Annotated[tuple[ClaimId, ...], Field(min_length=1)] | MISSING = MISSING  # type: ignore[valid-type]
    rule: str | MISSING = Field(MISSING, min_length=1)  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _derivation(self) -> Self:
        validators.claim_item(self)  # derived_from and rule exactly when derived
        return self


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
    refs: Annotated[tuple[ClaimId, ...], Field(min_length=2)]
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
    AuthoredEntity | AuthoredStatement | AuthoredOutside | AuthoredClaim | AlternativeItem
    | AuthoredUnsupported
)
type StoredItem = (
    StoredEntity | StoredStatement | StoredOutside | StoredClaim | AlternativeItem
    | StoredUnsupported
)


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
    statements: tuple[AuthoredStatementItem, ...] = ()
    claims: tuple[AuthoredClaim, ...] = ()
    alternatives: tuple[AlternativeItem, ...] = ()
    unsupported: tuple[AuthoredUnsupported, ...] = ()


class StoredBatch(_Batch):
    rendition: RenditionKey
    entities: tuple[StoredEntity, ...] = ()
    statements: tuple[StoredStatementItem, ...] = ()
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
