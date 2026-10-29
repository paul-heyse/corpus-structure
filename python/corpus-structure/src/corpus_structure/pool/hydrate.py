"""T3 hydration (target model §7; pool and interchange §3.1): the pool's candidate relations as one
keyed candidate set per `claim_proposal` observation, its support.

`hydrate(pool)` is the reference path for Python steps (keying, resolution, the view builder). Each
`Hydrated` holds the observation id (the candidates' support, D5 §2) and a `KeyedCandidateSet` on
the batch's rendition, in stored form, ids the batch's local refs and keys `UNKEYED` until keying;
an `ExternalReference` candidate is `AWAITING`. It reads each candidate's stored item (`item`), so
nothing a relation lifts can disagree with what hydrates. Items come in the relations' canonical
order (by local ref; alternatives by their ordinal in the batch).

`T3` declares the translation with T2's class maps (`core/translations.py`): the pool's items are a
stored batch's items, regrouped by relation, and the support is what T3 adds. A `claim_proposal`
observation with no items hydrates to an empty set on its rendition.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pyarrow as pa

from corpus_structure.core import candidates as C
from corpus_structure.core.batch import (
    AlternativeItem,
    StoredClaim,
    StoredEntity,
    StoredOutside,
    StoredStatement,
    StoredUnsupported,
)
from corpus_structure.core.translations import T2, Translation
from corpus_structure.pool.contract import (
    ALTERNATIVES,
    BATCHES,
    CLAIMS,
    ENTITIES,
    REFERENCES,
    STATEMENTS,
    UNSUPPORTED,
    Pool,
)

T3 = Translation(
    id="T3",
    name="pool -> keyed candidate set",
    owner="pool and interchange (P0-P-1), for consolidate",
    source_form="stored",
    classes=T2.classes,
)


@dataclass(frozen=True)
class Hydrated:
    observation_id: int  # the support of every candidate in the set
    candidates: C.KeyedCandidateSet


def _entity(e: StoredEntity) -> C.CandidateEntity:
    return C.CandidateEntity(
        id=e.local_ref,
        type=e.type,
        label=e.label,
        scope=e.scope,
        extent=e.extent,
        scope_segment=e.scope_segment,
        symbol=e.symbol,
        aliases=e.aliases,
        identity=e.identity,
    )


def _statement(s: StoredStatement) -> C.CandidateStatement:
    return C.CandidateStatement(id=s.local_ref, kind=s.kind, anchor=s.anchor)


def _reference(o: StoredOutside) -> C.CandidateReference:
    return C.CandidateReference(id=o.local_ref, descriptor=o.descriptor)


def _claim(c: StoredClaim) -> C.CandidateClaim:
    return C.CandidateClaim(
        id=c.local_ref,
        predicate=c.predicate,
        subject=c.subject,
        object=c.object,
        qualifiers=c.qualifiers,
        statement=c.statement,
        statement_role=c.statement_role,
        establishment=c.establishment,
        derived_from=c.derived_from,
        rule=c.rule,
        evidence=c.evidence,
    )


def _alternative(a: AlternativeItem) -> C.CandidateAlternative:
    return C.CandidateAlternative(refs=a.refs, reason=a.reason)


def _unsupported(u: StoredUnsupported) -> C.CandidateUnsupported:
    return C.CandidateUnsupported(
        id=u.local_ref, start=u.start, end=u.end, reason=u.reason, coarse=u.coarse
    )


_RELATIONS: dict[str, tuple[str, Any, Any]] = {
    ENTITIES: ("entities", StoredEntity, _entity),
    STATEMENTS: ("statements", StoredStatement, _statement),
    REFERENCES: ("references", StoredOutside, _reference),
    CLAIMS: ("claims", StoredClaim, _claim),
    ALTERNATIVES: ("alternatives", AlternativeItem, _alternative),
    UNSUPPORTED: ("unsupported", StoredUnsupported, _unsupported),
}


def _items(table: pa.Table) -> list[tuple[int, Any]]:
    ids = table.column("observation_id").to_pylist()
    items = table.column("item").to_pylist()
    return [(oid, json.loads(text)) for oid, text in zip(ids, items, strict=True)]


def hydrate(pool: Pool) -> tuple[Hydrated, ...]:
    """One keyed candidate set per `claim_proposal` observation, by observation id (module doc)."""
    batches = pool[BATCHES]
    fields: dict[int, dict[str, list[Any]]] = {
        oid: {name: [] for name, _, _ in _RELATIONS.values()}
        for oid in batches.column("observation_id").to_pylist()
    }
    for relation, (name, stored, translate) in _RELATIONS.items():
        for oid, item in _items(pool[relation]):
            fields[oid][name].append(translate(stored.model_validate(item)))
    renditions = batches.column("rendition").to_pylist()
    return tuple(
        Hydrated(oid, C.KeyedCandidateSet(rendition=rendition, **fields[oid]))
        for oid, rendition in zip(fields, renditions, strict=True)
    )
