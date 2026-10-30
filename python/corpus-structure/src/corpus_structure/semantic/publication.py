"""Immutable publication batches and one SERIALIZABLE transaction/retry owner.

SQLAlchemy owns every transaction, including COPY. The native routine independently
checks identities, exact batch bytes and semantic constraints; these Python rows are input.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, astuple, dataclass, field, fields
from decimal import Decimal
from hashlib import sha256
from typing import Any, Protocol

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from sqlalchemy import Connection, Engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import DBAPIError

from .identity import canonical_bytes
from .metadata import table
from .outcomes import ScientificOutcome, SemanticCoverageOutcome
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
    rendition_id: int
    span_id: int | None = None


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

    _analysis_input: Any = field(default=None, repr=False, compare=False)

    def bind_preparation(
        self, prepared: PreparedRelease, *, snapshot: Any = None
    ) -> PublicationBatch:
        from dataclasses import replace
        from hashlib import sha256

        from .analysis_contracts import bind_analysis_family
        from .contracts import execution_payload

        payload = execution_payload(prepared)
        if payload is None or json.loads(payload)["inputs"]["compiler_version"] != "7":
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

    admit_execution_release(prepared, connection=connection)
    native_constraints(prepared)
    _admit_inference(prepared)
    for definition in prepared.definitions:
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
    from .contracts import require_database_operation

    require_database_operation(connection, batch.release_id, "publish")
    stage_batch(connection, batch)
    revision = connection.execute(
        text("SELECT data.publish_batch(:release,:realization,:batch,:content)"),
        {
            "release": batch.release_id,
            "realization": batch.realization_id,
            "batch": batch.batch_id,
            "content": batch.content,
        },
    ).scalar_one()
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
    engine: Engine, batch: PublicationBatch, *, attempts: int = 3
) -> PublicationReceipt:
    """Retry a whole immutable batch; resolve ambiguous commits using the same identity."""
    return _publish(engine, batch, publish_on_connection, attempts=attempts)


def _publish(
    engine: Engine,
    batch: PublicationInput,
    publish: Callable[[Connection, Any], PublicationReceipt],
    *,
    attempts: int,
) -> PublicationReceipt:
    """Single retry owner for both transports; source fencing stays inside publication."""
    if isinstance(batch, PublicationBatch):
        batch.validate_preparation()
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(attempts):
        try:
            with (
                engine.connect().execution_options(isolation_level="SERIALIZABLE") as connection,
                connection.begin(),
            ):
                receipt = publish(connection, batch)
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
