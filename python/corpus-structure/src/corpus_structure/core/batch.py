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
The classes are generated from the model (`_model/shapes.py`, Stage B, P0-M-5; ADR-0020) with
their closed sets, defaults, core qualifier names and invariants, and re-exported here beside the
behaviour over them: the citation positions (`rewrite_citations`, `cited_sentences`). The
citation frame is hand-written (`shape_support`). The qualifier sets accept schema qualifiers as
raw JSON; S1's per-predicate models subclass them with `extra="forbid"` and typed fields.
"""

from __future__ import annotations

import functools
import types
import typing
from collections.abc import Callable
from typing import Annotated, Any

from pydantic import BaseModel

from corpus_structure.core._model import names
from corpus_structure.core._model.qualifiers import BY_NAME
from corpus_structure.core._model.shapes import (
    AlternativeItem,
    AuthoredBatch,
    AuthoredClaim,
    AuthoredDescriptor,
    AuthoredEntity,
    AuthoredEvidence,
    AuthoredOutside,
    AuthoredQualifiers,
    AuthoredStatement,
    AuthoredStatementItem,
    AuthoredUnsupported,
    StoredBatch,
    StoredClaim,
    StoredDescriptor,
    StoredEntity,
    StoredEvidence,
    StoredOutside,
    StoredQualifiers,
    StoredScope,
    StoredStatement,
    StoredStatementItem,
    StoredUnsupported,
    _statement_or_outside,
)
from corpus_structure.core._model.types import (
    CITATION,
    PREFIXED_NAME,
    SENTENCE_ID,
    NonEmpty,
    PrefixedName,
    RenditionKey,
)
from corpus_structure.core.shape_support import CitationFrame, FrameEntry
from corpus_structure.core.vocab import ClaimModality, Polarity

__all__ = [
    "CORE_PREFIX", "CORE_QUALIFIERS", "DEFAULT_MODALITY", "DEFAULT_POLARITY", "PREFIXED_NAME",
    "SENTENCE_ID", "STORED_CORE_QUALIFIERS", "AlternativeItem", "AuthoredBatch", "AuthoredClaim",
    "AuthoredDescriptor", "AuthoredEntity", "AuthoredEvidence", "AuthoredItem", "AuthoredOutside",
    "AuthoredQualifiers", "AuthoredStatement", "AuthoredStatementItem", "AuthoredUnsupported",
    "CitationFrame", "FrameEntry", "LocalRef", "PrefixedName", "RenditionKey", "StoredBatch",
    "StoredClaim", "StoredDescriptor", "StoredEntity", "StoredEvidence", "StoredItem",
    "StoredOutside", "StoredQualifiers", "StoredScope", "StoredStatement", "StoredStatementItem",
    "StoredUnsupported", "_statement_or_outside", "cited_sentences", "rewrite_citations",
]  # fmt: skip

LocalRef = NonEmpty
CORE_PREFIX = names.PREFIX
DEFAULT_MODALITY: ClaimModality = BY_NAME[names.MODALITY].default
DEFAULT_POLARITY: Polarity = BY_NAME[names.POLARITY].default
CORE_QUALIFIERS = names.QUALIFIERS
STORED_CORE_QUALIFIERS = names.STORED_QUALIFIERS

# The item unions of each form: what a batch's item lists hold.
type AuthoredItem = (
    AuthoredEntity
    | AuthoredStatement
    | AuthoredOutside
    | AuthoredClaim
    | AlternativeItem
    | AuthoredUnsupported
)
type StoredItem = (
    StoredEntity
    | StoredStatement
    | StoredOutside
    | StoredClaim
    | AlternativeItem
    | StoredUnsupported
)


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
