"""Immutable publication batches and one SERIALIZABLE transaction/retry owner.

SQLAlchemy owns every transaction, including COPY. The native routine independently
checks identities, exact batch bytes and semantic constraints; these Python rows are input.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import asdict, astuple, dataclass, field, fields, replace
from decimal import Decimal
from hashlib import sha256
from typing import Any, Protocol

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from sqlalchemy import Connection, Engine, text
from sqlalchemy.dialects import postgresql

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.db.store import (
    RETRYABLE,
    DatabaseCause,
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    record_operation_failure,
)

from .identity import canonical_bytes
from .metadata import table
from .outcomes import ScientificOutcome, SemanticCoverageOutcome
from .record_projection import (
    RECORD_ROW_TYPES,
    RecordAdmissionRow,
    RecordAlternativeEvidenceRow,
    RecordAlternativePieceRow,
    RecordAlternativeRow,
    RecordAnchorRow,
    RecordAssertionRow,
    RecordDependencyRow,
    RecordEvidenceMemberRow,
    RecordEvidenceSetRow,
    RecordFieldEvidenceRow,
    RecordFieldPieceRow,
    RecordFieldRow,
    RecordOccurrenceAnchorRow,
    RecordPremiseRow,
    RecordPrivateAssertionRow,
    RecordReportMemberRow,
    RecordReportRow,
    SourceRecordRow,
)
from .types import PreparedRelease


@dataclass(frozen=True)
class EntityRow:
    entity_id: str


@dataclass(frozen=True)
class EntitySourceRow:
    entity_id: str
    observation_id: int
    local_id: str


@dataclass(frozen=True)
class IdentityExclusionRow:
    exclusion_id: str
    observation_id: int
    local_id: str
    left_kind: str
    left_ref: str
    right_kind: str
    right_ref: str
    left_entity_id: str
    right_entity_id: str
    reason: str
    operation_id: str
    operation_version: str


@dataclass(frozen=True)
class IdentityExclusionEvidenceRow:
    exclusion_id: str
    evidence_id: str


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
    report_object_value_id: str
    report_qualification_value_id: str | None = None


@dataclass(frozen=True)
class SupportRow:
    fact_id: str
    occurrence_id: str


@dataclass(frozen=True)
class SelectionRow:
    fact_id: str
    selected: bool = True


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
class OccurrenceContextRow:
    occurrence_id: str
    statement_entity_id: str | None = None
    statement_role: str | None = None


@dataclass(frozen=True)
class OccurrenceEvidenceRoleRow:
    occurrence_id: str
    evidence_id: str
    role: str


@dataclass(frozen=True)
class MembershipSupportRow:
    entity_id: str
    class_id: str
    evidence_id: str


@dataclass(frozen=True)
class OccurrenceEstablishmentRow:
    occurrence_id: str
    establishment: str


@dataclass(frozen=True)
class EvidenceSourceRow:
    evidence_id: str
    observation_id: int
    rendition_id: int | None
    span_id: int | None = None
    source_view_id: int | None = None
    native_address: str | None = None


@dataclass(frozen=True)
class EntityInputRow:
    entity_id: str
    input_realization_id: str
    input_data_revision: int
    input_entity_id: str
    run_id: int


@dataclass(frozen=True)
class FactInputRow:
    fact_id: str
    input_realization_id: str
    input_data_revision: int
    input_fact_id: str
    run_id: int


@dataclass(frozen=True)
class AlternativeGroupRow:
    group_id: str
    reason: str
    operation_id: str
    operation_version: str


@dataclass(frozen=True)
class AlternativeMemberRow:
    group_id: str
    fact_id: str


@dataclass(frozen=True)
class AssessmentRow:
    assessment_id: str
    operation_id: str
    operation_version: str
    outcome: ScientificOutcome
    fact_id: str | None = None
    occurrence_id: str | None = None
    confidence: Decimal | None = None
    reason: str | None = None
    uncertainty: str | None = None
    counterpart_fact_id: str | None = None
    counterpart_occurrence_id: str | None = None
    context_value_id: str | None = None
    comparison_tier: str | None = None


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
    outcome: SemanticCoverageOutcome
    reason: str | None = None
    source_outcome: str | None = None
    required_capability: str | None = None


# The fixed transport schema is shared with the narrow native DDL companion.
_ROW_TYPES = {
    **RECORD_ROW_TYPES,
    "entity": EntityRow,
    "entity_source": EntitySourceRow,
    "identity_exclusion": IdentityExclusionRow,
    "identity_exclusion_evidence": IdentityExclusionEvidenceRow,
    "membership": MembershipRow,
    "typed_value": ValueRow,
    "value_role": RoleRow,
    "fact": FactRow,
    "occurrence": OccurrenceRow,
    "support": SupportRow,
    "selection": SelectionRow,
    "evidence": EvidenceRow,
    "occurrence_evidence": OccurrenceEvidenceRow,
    "occurrence_context": OccurrenceContextRow,
    "occurrence_evidence_role": OccurrenceEvidenceRoleRow,
    "membership_support": MembershipSupportRow,
    "derivation": DerivationRow,
    "derivation_premise": DerivationPremiseRow,
    "coverage": CoverageRow,
    "occurrence_establishment": OccurrenceEstablishmentRow,
    "evidence_source": EvidenceSourceRow,
    "assessment": AssessmentRow,
    "entity_input": EntityInputRow,
    "fact_input": FactInputRow,
    "alternative_group": AlternativeGroupRow,
    "alternative_member": AlternativeMemberRow,
}
_DIALECT = postgresql.dialect()
STAGE_TYPES: dict[str, tuple[type, tuple[str, ...]]] = {
    name: (
        row_type,
        tuple(
            "boolean"
            if name == "selection" and field.name == "selected"
            else table("data." + name).c[field.name].type.compile(dialect=_DIALECT).lower()
            for field in fields(row_type)
        ),
    )
    for name, row_type in _ROW_TYPES.items()
}


@dataclass(frozen=True)
class PublicationBatch:
    release_id: str
    realization_id: str
    batch_id: str
    entity: tuple[EntityRow, ...] = ()
    entity_source: tuple[EntitySourceRow, ...] = ()
    identity_exclusion: tuple[IdentityExclusionRow, ...] = ()
    identity_exclusion_evidence: tuple[IdentityExclusionEvidenceRow, ...] = ()
    membership: tuple[MembershipRow, ...] = ()
    typed_value: tuple[ValueRow, ...] = ()
    value_role: tuple[RoleRow, ...] = ()
    fact: tuple[FactRow, ...] = ()
    occurrence: tuple[OccurrenceRow, ...] = ()
    support: tuple[SupportRow, ...] = ()
    selection: tuple[SelectionRow, ...] = ()
    evidence: tuple[EvidenceRow, ...] = ()
    occurrence_evidence: tuple[OccurrenceEvidenceRow, ...] = ()
    occurrence_context: tuple[OccurrenceContextRow, ...] = ()
    occurrence_evidence_role: tuple[OccurrenceEvidenceRoleRow, ...] = ()
    membership_support: tuple[MembershipSupportRow, ...] = ()
    derivation: tuple[DerivationRow, ...] = ()
    derivation_premise: tuple[DerivationPremiseRow, ...] = ()
    coverage: tuple[CoverageRow, ...] = ()
    occurrence_establishment: tuple[OccurrenceEstablishmentRow, ...] = ()
    evidence_source: tuple[EvidenceSourceRow, ...] = ()
    assessment: tuple[AssessmentRow, ...] = ()
    alternative_group: tuple[AlternativeGroupRow, ...] = ()
    alternative_member: tuple[AlternativeMemberRow, ...] = ()
    entity_input: tuple[EntityInputRow, ...] = ()
    fact_input: tuple[FactInputRow, ...] = ()

    record_report: tuple[RecordReportRow, ...] = ()
    source_record: tuple[SourceRecordRow, ...] = ()
    record_report_member: tuple[RecordReportMemberRow, ...] = ()
    record_field: tuple[RecordFieldRow, ...] = ()
    record_field_piece: tuple[RecordFieldPieceRow, ...] = ()
    record_alternative: tuple[RecordAlternativeRow, ...] = ()
    record_alternative_piece: tuple[RecordAlternativePieceRow, ...] = ()
    record_anchor: tuple[RecordAnchorRow, ...] = ()
    record_occurrence_anchor: tuple[RecordOccurrenceAnchorRow, ...] = ()
    record_evidence_set: tuple[RecordEvidenceSetRow, ...] = ()
    record_evidence_member: tuple[RecordEvidenceMemberRow, ...] = ()
    record_field_evidence: tuple[RecordFieldEvidenceRow, ...] = ()
    record_alternative_evidence: tuple[RecordAlternativeEvidenceRow, ...] = ()
    record_premise: tuple[RecordPremiseRow, ...] = ()
    record_dependency: tuple[RecordDependencyRow, ...] = ()
    record_private_assertion: tuple[RecordPrivateAssertionRow, ...] = ()
    record_admission: tuple[RecordAdmissionRow, ...] = ()
    record_assertion: tuple[RecordAssertionRow, ...] = ()

    _analysis_input: Any = field(default=None, repr=False, compare=False)

    def bind_preparation(
        self, prepared: PreparedRelease, *, snapshot: Any = None
    ) -> PublicationBatch:
        from dataclasses import replace
        from hashlib import sha256

        from .analysis_contracts import bind_analysis_family
        from .contracts import EXECUTION_COMPILER_VERSION, execution_payload

        payload = execution_payload(prepared)
        if (
            payload is None
            or json.loads(payload)["inputs"]["compiler_version"] != EXECUTION_COMPILER_VERSION
        ):
            return self
        owned = bind_analysis_family(prepared, "publication").prepare(
            release=self.release_id,
            snapshot=snapshot
            if snapshot is not None
            else {"kind": "append_target", "realization": self.realization_id},
            content=sha256(self.content).hexdigest(),
        )
        return replace(self, _analysis_input=owned)

    def validate_preparation(self) -> None:
        from hashlib import sha256

        if self._analysis_input is None:
            return  # Explicit base/retained row producer; native admission still applies.
        owned = self._analysis_input
        dependencies = dict(owned.dependencies)
        if (
            owned.family != "publication"
            or owned.release_id != self.release_id
            or dependencies.get("release") != canonical_bytes(self.release_id)
            or dependencies.get("content") != canonical_bytes(sha256(self.content).hexdigest())
        ):
            raise ValueError("publication preparation differs from its actual owned rows")

    def __post_init__(self) -> None:
        if any(
            type(value) is not str or not value
            for value in (self.release_id, self.realization_id, self.batch_id)
        ):
            raise ValueError("publication requires release, realization and batch identity")
        for name, (row_type, _) in STAGE_TYPES.items():
            rows = getattr(self, name)
            if not isinstance(rows, tuple) or any(type(row) is not row_type for row in rows):
                raise TypeError(f"{name} must be an immutable tuple of {row_type.__name__}")
            for row in rows:
                for column in fields(row):
                    value = getattr(row, column.name)
                    if type(value) not in {str, int, bool, Decimal, type(None)}:
                        raise TypeError(f"{name}.{column.name} must be an immutable scalar")
                    if isinstance(value, Decimal) and not value.is_finite():
                        raise ValueError("non-finite decimal projection")
                    if column.name == "opaque_payload" and value is not None:
                        raise ValueError("opaque payload has no admitted semantic lowering")

    @property
    def content(self) -> bytes:
        body = {}
        for name in STAGE_TYPES:
            rows = [list(astuple(row)) for row in getattr(self, name)]
            # Native receipt encoding uses exact textual numeric representations.
            for row in rows:
                for index, typ in enumerate(STAGE_TYPES[name][1]):
                    if typ == "numeric" and row[index] is not None:
                        value = row[index]
                        if isinstance(value, Decimal):
                            row[index] = format(value.copy_abs() if value.is_zero() else value, "f")
                        else:
                            row[index] = str(value)
            body[name] = sorted(rows, key=canonical_bytes)
        return canonical_bytes([self.release_id, self.realization_id, body])


@dataclass(frozen=True)
class PublicationReceipt:
    batch_id: str
    data_revision: int
    content_digest: str


class PublicationConflict(ValueError):
    """An existing batch identity has different exact contents."""


class PublicationInput(Protocol):
    """Exact replay identity shared by row and Arrow transport."""

    @property
    def release_id(self) -> str: ...
    @property
    def realization_id(self) -> str: ...
    @property
    def batch_id(self) -> str: ...
    @property
    def content(self) -> bytes: ...


def native_constraints(prepared: PreparedRelease) -> dict[tuple[str, str], dict[str, Any]]:
    """Prepare native datatype and exact bound lowerings once per release projection."""
    primitives = {
        "string",
        "integer",
        "decimal",
        "boolean",
        "date",
        "datetime",
        "float",
        "double",
        "uri",
        "uriorcurie",
    }
    classes = {d.name for d in prepared.definitions}
    enums = {v.enum for v in prepared.vocabularies}
    definitions = {
        row.name: json.loads(row.body) for row in prepared.registry_rows if row.kind == "type"
    }
    resolved = {name: name for name in primitives | classes | enums}

    def resolve(name: str, path: frozenset[str] = frozenset()) -> str:
        if name in resolved:
            return resolved[name]
        if name in path or name not in definitions:
            raise ValueError(f"unsupported native range {name}")
        definition = definitions[name]
        parent = definition.get("typeof") or definition.get("base") or "string"
        parent = {"str": "string", "int": "integer", "bool": "boolean", "Decimal": "decimal"}.get(
            parent, parent
        )
        resolved[name] = resolve(parent, path | {name})
        return resolved[name]

    result = {}
    for definition in prepared.definitions:
        for prop in definition.properties:
            constraints = asdict(prop)
            constraints["native_range"] = resolve(prop.range)
            if constraints["native_range"] in {"float", "double"} and (
                prop.minimum is not None or prop.maximum is not None
            ):
                raise ValueError("exact float bounds have no admitted native lowering")
            for bound in ("minimum", "maximum"):
                raw = getattr(prop, bound)
                if raw is not None:
                    value = Decimal(raw)
                    if not value.is_finite():
                        raise ValueError("non-finite native bound")
                    lexical = format(value, "f") if value else "0"
                    if "." in lexical:
                        lexical = lexical.rstrip("0").rstrip(".")
                    constraints["native_" + bound] = lexical
            result[definition.iri, prop.iri] = constraints
    return result


def _admit_inference(prepared: PreparedRelease) -> None:
    """Admit only the finite binary profile implemented by protected inference validation."""
    classes = {d.name: d for d in prepared.definitions}
    applications = {}
    for definition in prepared.definitions:
        for prop in definition.properties:
            applications.setdefault(prop.iri, []).append((definition, prop))
    rules = [json.loads(row.body) for row in prepared.registry_rows if row.kind == "inference_rule"]
    signatures = set()

    def subtype(child, parent):
        return child.iri == parent.iri or parent.name in child.ancestors

    for rule in rules:
        kind, predicate = rule["kind"], rule["predicate"]
        if kind not in {"inverse", "symmetric", "transitive", "subproperty"}:
            raise ValueError("unsupported inference rule kind")
        target = rule.get("target") or predicate
        if predicate not in applications or target not in applications:
            raise ValueError("inference rule references undeclared property")
        signatures.add((kind, predicate, target))
        for domain, prop in applications[predicate]:
            if prop.inlined or prop.range not in classes:
                raise ValueError("inference requires binary entity relations")
            range_class = classes[prop.range]
            # Inversion changes the domain; subproperty lifting retains it.
            target_domain = domain if kind == "subproperty" else range_class
            matching = [p for p in target_domain.properties if p.iri == target]
            if not matching:
                raise ValueError("inference target is not applicable to transformed subject")
            for result in matching:
                if result.inlined or result.range not in classes:
                    raise ValueError("inference target requires binary entity range")
                expected_object = range_class if kind in {"subproperty", "transitive"} else domain
                if not subtype(expected_object, classes[result.range]):
                    raise ValueError("inference transformed object violates target range")
    for definition in prepared.definitions:
        for prop in definition.properties:
            for flag in ("symmetric", "transitive"):
                if getattr(prop, flag) and (flag, prop.iri, prop.iri) not in signatures:
                    raise ValueError("required graph characteristic has no compiled rule")
            if prop.inverse:
                targets = {
                    p.iri
                    for d in prepared.definitions
                    for p in d.properties
                    if prop.inverse in {p.name, p.iri}
                }
                if (
                    len(targets) != 1
                    or ("inverse", prop.iri, next(iter(targets))) not in signatures
                ):
                    raise ValueError("required inverse has no compiled target rule")


def admit_release(prepared: PreparedRelease, *, connection: Connection | None = None) -> None:
    """Refuse required semantics outside the currently implemented native lowering."""
    from .execution_admission import admit_execution_release
    from .record_contracts import record_product_classes

    admit_execution_release(prepared, connection=connection)
    native_constraints(prepared)
    _admit_inference(prepared)
    products = record_product_classes(prepared.definitions)
    for definition in prepared.definitions:
        if definition.name in products:
            continue
        for prop in definition.properties:
            if prop.constraint_scope not in {"shape", "accepted_value"}:
                raise ValueError(f"unsupported native constraint scope {prop.constraint_scope}")
            if prop.pattern or prop.patterns:
                raise ValueError("Python regular expressions have no admitted native equivalence")
    if any(
        d.outcome in {"unsupported", "unresolved"}
        or (
            d.outcome == "unchecked"
            and not (d.code == "unchecked_term" and d.message == "not4curation:unchecked")
        )
        for d in prepared.diagnostics
    ):
        raise ValueError("release contains unresolved or unchecked required semantics")


def stage_batch(
    connection: Connection,
    batch: PublicationBatch,
    *,
    cancellation: BorrowerCancellation | None = None,
) -> None:
    """COPY fixed typed rows on the driver's *same* SQLAlchemy-owned connection."""
    from ._operation_calls import begin_stage

    begin_stage(connection)
    driver = connection.connection.driver_connection
    if not isinstance(driver, psycopg.Connection):
        raise TypeError("publication requires the existing psycopg-backed SQLAlchemy engine")
    with driver.cursor() as cursor:
        for name, (row_type, types) in STAGE_TYPES.items():
            if cancellation is not None:
                cancellation.check_active()
            columns = tuple(f.name for f in fields(row_type))
            statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
                sql.Identifier("pg_temp", "sp_" + name),
                sql.SQL(",").join(map(sql.Identifier, columns)),
            )
            with cursor.copy(statement) as copy:
                copy.set_types(types)
                for row in getattr(batch, name):
                    if cancellation is not None:
                        cancellation.check_active()
                    values = astuple(row)
                    if name == "typed_value" and values[-1] is not None:
                        values = (*values[:-1], Jsonb(values[-1]))
                    copy.write_row(values)


def publish_on_connection(
    connection: Connection,
    batch: PublicationBatch,
    *,
    cancellation: BorrowerCancellation | None = None,
) -> PublicationReceipt:
    """Stage and validate inside an already SERIALIZABLE transaction; never commit it."""
    from .contracts import require_database_operation

    require_database_operation(connection, batch.release_id, "publish")
    if cancellation is None:
        stage_batch(connection, batch)
    else:
        stage_batch(connection, batch, cancellation=cancellation)
    from ._operation_calls import publish_batch as invoke_publish_batch
    from ._operation_ids import RealizationId, ReleaseId

    revision = invoke_publish_batch(
        connection,
        release_id=ReleaseId(batch.release_id),
        realization_id=RealizationId(batch.realization_id),
        batch_id=batch.batch_id,
        content=batch.content,
    )
    return PublicationReceipt(batch.batch_id, revision, sha256(batch.content).hexdigest())


def lookup_receipt(engine: Engine, batch: PublicationInput) -> PublicationReceipt | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT content,content_digest,data_revision FROM data.batch "
                "WHERE release_id=:r AND realization_id=:z AND batch_id=:b"
            ),
            {"r": batch.release_id, "z": batch.realization_id, "b": batch.batch_id},
        ).one_or_none()
    if row is None:
        return None
    if bytes(row.content) != batch.content:
        raise PublicationConflict("batch identity already names different exact contents")
    return PublicationReceipt(batch.batch_id, row.data_revision, row.content_digest)


def publish_batch(
    engine: Engine,
    batch: PublicationBatch,
    *,
    attempts: int = 3,
    cancellation: BorrowerCancellation | None = None,
) -> PublicationReceipt:
    """Retry a whole immutable batch; resolve ambiguous commits using the same identity."""

    def publish(connection, candidate):
        return publish_on_connection(connection, candidate, cancellation=cancellation)

    return _publish(engine, batch, publish, attempts=attempts, cancellation=cancellation)


def _publish(
    engine: Engine,
    batch: PublicationInput,
    publish: Callable[[Connection, Any], PublicationReceipt],
    *,
    attempts: int,
    cancellation: BorrowerCancellation | None = None,
) -> PublicationReceipt:
    """Own phases and settled whole-transaction retry for both publication transports."""
    if isinstance(batch, PublicationBatch):
        batch.validate_preparation()
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(attempts):
        phase = DatabasePhase.ACQUIRING
        effects = EffectKnowledge.NONE
        broken = False
        try:
            if cancellation is not None:
                cancellation.check_active()
            with engine.connect().execution_options(isolation_level="SERIALIZABLE") as connection:
                scope = (
                    cancellation.borrow(connection) if cancellation is not None else nullcontext()
                )
                with scope:
                    driver = connection.connection.driver_connection
                    transaction = connection.begin()
                    try:
                        phase = DatabasePhase.EXECUTING
                        effects = EffectKnowledge.UNCERTAIN
                        receipt = publish(connection, batch)
                        if cancellation is not None:
                            cancellation.check_active()
                        phase = DatabasePhase.COMMITTING
                        transaction.commit()
                        effects = EffectKnowledge.COMMITTED
                    except BaseException as original:
                        broken = connection.invalidated or bool(getattr(driver, "broken", False))
                        try:
                            transaction.rollback()
                            # After commit was attempted, rollback cannot establish whether
                            # the server committed before acknowledgement was lost.
                            if not broken and (
                                phase != DatabasePhase.COMMITTING
                                or classify_error(original).sqlstate in RETRYABLE
                            ):
                                effects = EffectKnowledge.ROLLED_BACK
                        except BaseException as cleanup:
                            original.add_note("database rollback failed: " + type(cleanup).__name__)
                            try:
                                connection.invalidate()
                            except BaseException as invalidation:
                                original.add_note(
                                    "database invalidation failed: " + type(invalidation).__name__
                                )
                        raise
            return receipt
        except BaseException as error:
            failure = classify_error(
                error,
                phase=phase,
                effects=effects,
                broken=broken,
                cancellation_requested=cancellation is not None and cancellation.requested,
            )
            record_operation_failure(
                error,
                DatabaseOperationFailure(
                    failure,
                    batch.batch_id,
                    "inspect_failure",
                    batch.release_id,
                    batch.realization_id,
                ),
            )
            # Commit-time operational loss needs identity resolution even without a native
            # code. That is phase knowledge, not evidence of transport loss.
            uncertain_commit = (
                phase == DatabasePhase.COMMITTING
                and effects == EffectKnowledge.UNCERTAIN
                and failure.cause
                in {
                    DatabaseCause.CONNECTION_UNUSABLE,
                    DatabaseCause.UNKNOWN_OPERATIONAL,
                    DatabaseCause.UNKNOWN,
                }
            )
            if uncertain_commit:
                try:
                    receipt = lookup_receipt(engine, batch)
                except PublicationConflict:
                    raise
                except BaseException as resolution:
                    unresolved = classify_error(
                        resolution,
                        phase=DatabasePhase.RESOLVING,
                        effects=EffectKnowledge.UNCERTAIN,
                        cancellation_requested=(
                            failure.cancellation_requested
                            or (cancellation is not None and cancellation.requested)
                            or isinstance(resolution, KeyboardInterrupt)
                        ),
                    )
                    context = DatabaseOperationFailure(
                        unresolved,
                        batch.batch_id,
                        "resolve_original_identity",
                        batch.release_id,
                        batch.realization_id,
                    )
                    record_operation_failure(error, context)
                    record_operation_failure(resolution, context)
                    if not isinstance(resolution, Exception):
                        raise
                    raise error from resolution
                if receipt is not None:
                    return receipt
            if cancellation is not None and cancellation.requested:
                failure = replace(failure, cancellation_requested=True)
            retryable = failure.cause in {DatabaseCause.SERIALIZATION, DatabaseCause.DEADLOCK}
            # A known broken session can be replayed only by this immutable, fenced
            # publication protocol, after the old borrow has left its owner scope.
            retryable = retryable or (
                failure.cause == DatabaseCause.CONNECTION_UNUSABLE
                and phase != DatabasePhase.ACQUIRING
            )
            # Unknown exceptions at commit may require lookup, but never authorize replay.
            if (
                not retryable
                or effects == EffectKnowledge.COMMITTED
                or failure.cancellation_requested
                or attempt + 1 == attempts
                or not isinstance(error, Exception)
            ):
                remediation = (
                    "resolve_original_identity"
                    if uncertain_commit
                    else (
                        "stop_cancelled_operation"
                        if failure.cancellation_requested
                        else "retry_transaction"
                        if retryable
                        else "inspect_failure"
                    )
                )
                record_operation_failure(
                    error,
                    DatabaseOperationFailure(
                        failure,
                        batch.batch_id,
                        remediation,
                        batch.release_id,
                        batch.realization_id,
                    ),
                )
                raise
    raise AssertionError("unreachable")
