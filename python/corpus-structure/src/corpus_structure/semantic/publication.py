"""Immutable publication batches and one SERIALIZABLE transaction/retry owner.

SQLAlchemy owns every transaction, including COPY. The native routine independently
checks identities, exact batch bytes and semantic constraints; these Python rows are input.
"""
from __future__ import annotations

from dataclasses import astuple, dataclass, fields
from decimal import Decimal
from hashlib import sha256
from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from .identity import canonical_bytes
from .types import PreparedRelease


@dataclass(frozen=True)
class EntityRow:
    entity_id: str


@dataclass(frozen=True)
class MembershipRow:
    entity_id: str
    class_id: str
    establishment: str


@dataclass(frozen=True)
class ValueRow:
    value_id: str
    kind: str
    text_value: str | None = None
    integer_value: Decimal | int | None = None
    numeric_value: Decimal | None = None
    decimal_lexical: str | None = None
    boolean_value: bool | None = None
    entity_id: str | None = None
    language: str | None = None
    datatype: str | None = None
    opaque_payload: None = None


@dataclass(frozen=True)
class RoleRow:
    parent_value_id: str
    role: str
    position: int
    child_value_id: str


@dataclass(frozen=True)
class FactRow:
    fact_id: str
    subject_id: str
    property_id: str
    object_value_id: str
    qualification_value_id: str | None = None


@dataclass(frozen=True)
class OccurrenceRow:
    occurrence_id: str
    fact_id: str
    source: str
    item: str


@dataclass(frozen=True)
class SupportRow:
    fact_id: str
    occurrence_id: str


@dataclass(frozen=True)
class SelectionRow:
    fact_id: str


@dataclass(frozen=True)
class EvidenceRow:
    evidence_id: str
    source_uri: str
    locator: str
    provider: str
    operation_version: str


@dataclass(frozen=True)
class OccurrenceEvidenceRow:
    occurrence_id: str
    evidence_id: str


@dataclass(frozen=True)
class MembershipSupportRow:
    entity_id: str
    class_id: str
    evidence_id: str


@dataclass(frozen=True)
class DerivationRow:
    derivation_id: str
    conclusion_fact_id: str
    rule: str
    rule_version: str


@dataclass(frozen=True)
class DerivationPremiseRow:
    derivation_id: str
    position: int
    premise_fact_id: str


@dataclass(frozen=True)
class CoverageRow:
    coverage_id: str
    family: str
    scope: str
    outcome: str
    reason: str | None = None


# The fixed transport schema is shared with the narrow native DDL companion.
STAGE_TYPES: dict[str, tuple[type, tuple[str, ...]]] = {
    "entity": (EntityRow, ("text",)),
    "membership": (MembershipRow, ("text", "text", "text")),
    "typed_value": (ValueRow, ("text", "text", "text", "numeric", "numeric", "text", "boolean", "text", "text", "text", "jsonb")),
    "value_role": (RoleRow, ("text", "text", "integer", "text")),
    "fact": (FactRow, ("text", "text", "text", "text", "text")),
    "occurrence": (OccurrenceRow, ("text", "text", "text", "text")),
    "support": (SupportRow, ("text", "text")),
    "selection": (SelectionRow, ("text",)),
    "evidence": (EvidenceRow, ("text", "text", "text", "text", "text")),
    "occurrence_evidence": (OccurrenceEvidenceRow, ("text", "text")),
    "membership_support": (MembershipSupportRow, ("text", "text", "text")),
    "derivation": (DerivationRow, ("text", "text", "text", "text")),
    "derivation_premise": (DerivationPremiseRow, ("text", "integer", "text")),
    "coverage": (CoverageRow, ("text", "text", "text", "text", "text")),
}


@dataclass(frozen=True)
class PublicationBatch:
    release_id: str
    realization_id: str
    batch_id: str
    entity: tuple[EntityRow, ...] = ()
    membership: tuple[MembershipRow, ...] = ()
    typed_value: tuple[ValueRow, ...] = ()
    value_role: tuple[RoleRow, ...] = ()
    fact: tuple[FactRow, ...] = ()
    occurrence: tuple[OccurrenceRow, ...] = ()
    support: tuple[SupportRow, ...] = ()
    selection: tuple[SelectionRow, ...] = ()
    evidence: tuple[EvidenceRow, ...] = ()
    occurrence_evidence: tuple[OccurrenceEvidenceRow, ...] = ()
    membership_support: tuple[MembershipSupportRow, ...] = ()
    derivation: tuple[DerivationRow, ...] = ()
    derivation_premise: tuple[DerivationPremiseRow, ...] = ()
    coverage: tuple[CoverageRow, ...] = ()

    def __post_init__(self) -> None:
        if not all((self.release_id, self.realization_id, self.batch_id)):
            raise ValueError("publication requires release, realization and batch identity")
        for name, (row_type, _) in STAGE_TYPES.items():
            rows = getattr(self, name)
            if not isinstance(rows, tuple) or any(type(row) is not row_type for row in rows):
                raise TypeError(f"{name} must be an immutable tuple of {row_type.__name__}")

    @property
    def content(self) -> bytes:
        body = {}
        for name in STAGE_TYPES:
            rows = [list(astuple(row)) for row in getattr(self, name)]
            # Native receipt encoding uses exact textual numeric representations.
            if name == "typed_value":
                for row in rows:
                    for index in (3, 4):
                        if row[index] is not None:
                            row[index] = format(row[index], "f") if isinstance(row[index], Decimal) else str(row[index])
            body[name] = sorted(rows, key=canonical_bytes)
        return canonical_bytes([self.release_id, self.realization_id, body])


@dataclass(frozen=True)
class PublicationReceipt:
    batch_id: str
    data_revision: int
    content_digest: str


class PublicationConflict(ValueError):
    """An existing batch identity has different exact contents."""


def admit_release(prepared: PreparedRelease) -> None:
    """Refuse required semantics outside the currently implemented native lowering."""
    primitives = {"string", "integer", "decimal", "boolean", "date", "datetime", "float", "double", "uri", "uriorcurie"}
    classes = {d.name for d in prepared.definitions}
    enums = {v.enum for v in prepared.vocabularies}
    for definition in prepared.definitions:
        for prop in definition.properties:
            if prop.range not in primitives | classes | enums:
                raise ValueError(f"unsupported native range {definition.name}/{prop.name}: {prop.range}")
            if prop.constraint_scope not in {"shape", "accepted_value"}:
                raise ValueError(f"unsupported native constraint scope {prop.constraint_scope}")
            if prop.pattern or prop.patterns:
                raise ValueError("Python regular expressions have no admitted native equivalence")
            if prop.inverse or prop.symmetric or prop.transitive:
                raise ValueError("required graph integrity has no admitted native lowering")
    if any(d.outcome in {"unsupported", "unresolved", "unchecked"} for d in prepared.diagnostics):
        raise ValueError("release contains unresolved or unchecked required semantics")


def stage_batch(connection: Connection, batch: PublicationBatch) -> None:
    """COPY fixed typed rows on the driver's *same* SQLAlchemy-owned connection."""
    connection.execute(text("SELECT data.begin_stage()"))
    driver = connection.connection.driver_connection
    if not isinstance(driver, psycopg.Connection):
        raise TypeError("publication requires the existing psycopg-backed SQLAlchemy engine")
    with driver.cursor() as cursor:
        for name, (row_type, types) in STAGE_TYPES.items():
            columns = tuple(f.name for f in fields(row_type))
            statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
                sql.Identifier("pg_temp", "sp_" + name),
                sql.SQL(",").join(map(sql.Identifier, columns)),
            )
            with cursor.copy(statement) as copy:
                copy.set_types(types)
                for row in getattr(batch, name):
                    values = astuple(row)
                    if name == "typed_value" and values[-1] is not None:
                        values = (*values[:-1], Jsonb(values[-1]))
                    copy.write_row(values)


def publish_on_connection(connection: Connection, batch: PublicationBatch) -> PublicationReceipt:
    """Stage and validate inside an already SERIALIZABLE transaction; never commit it."""
    stage_batch(connection, batch)
    revision = connection.execute(
        text("SELECT data.publish_batch(:release,:realization,:batch,:content)"),
        {"release": batch.release_id, "realization": batch.realization_id,
         "batch": batch.batch_id, "content": batch.content},
    ).scalar_one()
    return PublicationReceipt(batch.batch_id, revision, sha256(batch.content).hexdigest())


def lookup_receipt(engine: Engine, batch: PublicationBatch) -> PublicationReceipt | None:
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT content,content_digest,data_revision FROM data.batch WHERE release_id=:r AND realization_id=:z AND batch_id=:b"),
            {"r": batch.release_id, "z": batch.realization_id, "b": batch.batch_id},
        ).one_or_none()
    if row is None:
        return None
    if bytes(row.content) != batch.content:
        raise PublicationConflict("batch identity already names different exact contents")
    return PublicationReceipt(batch.batch_id, row.data_revision, row.content_digest)


def publish_batch(engine: Engine, batch: PublicationBatch, *, attempts: int = 3) -> PublicationReceipt:
    """Retry a whole immutable batch; resolve ambiguous commits using the same identity."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(attempts):
        try:
            with engine.connect().execution_options(isolation_level="SERIALIZABLE") as connection:
                with connection.begin():
                    receipt = publish_on_connection(connection, batch)
            return receipt
        except (DBAPIError, psycopg.Error) as exc:
            original: Any = exc.orig if isinstance(exc, DBAPIError) else exc
            state = getattr(original, "sqlstate", None)
            lost = (isinstance(exc, DBAPIError) and exc.connection_invalidated) or (
                isinstance(original, psycopg.OperationalError) and state is None
            )
            if lost:
                receipt = lookup_receipt(engine, batch)
                if receipt is not None:
                    return receipt
            if (state not in {"40001", "40P01"} and not lost) or attempt + 1 == attempts:
                raise
    raise AssertionError("unreachable")
