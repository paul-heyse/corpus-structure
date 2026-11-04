"""Release-derived Core queries inside one actual PostgreSQL read snapshot.

Continuation starts a new snapshot and refuses a changed data revision. It does not
provide historical reads. SQL selections and strict output adaptation are one operation.
"""

from __future__ import annotations

import base64
import json
from collections import defaultdict, deque
from collections.abc import Generator
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from itertools import batched
from typing import TYPE_CHECKING, Any, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, SerializeAsAny
from sqlalchemy import (
    Connection,
    Engine,
    Select,
    Text,
    and_,
    case,
    exists,
    func,
    literal,
    or_,
    select,
    tuple_,
)
from sqlalchemy.sql import CompoundSelect
from sqlalchemy.sql.elements import ColumnElement

from corpus_structure.core.db.lifetime import BorrowerCancellation

from .coverage_contract import coverage_recipe
from .identity import canonical_bytes
from .metadata import table
from .outcomes import ScientificOutcome
from .query_compatibility import QueryBindingReference
from .releases import open_release
from .scientific_evidence_schema import (
    ScientificAssessmentEvidence,
)
from .types import ClassDefinition, PreparedRelease, PropertyDefinition

if TYPE_CHECKING:
    from .ontology import QualifiedGraphProjection


from .refusals import (
    InvalidContinuation,
    SemanticReason,
    SemanticRefusal,
    WrongBinding,
    WrongRelease,
)
from .refusals import StaleSnapshot as StaleSnapshot


@dataclass(frozen=True)
class SnapshotBinding:
    release_id: str
    realization_id: str
    data_revision: int
    capture_id: str


@dataclass(frozen=True)
class ClassHandle:
    release_id: str
    iri: str


@dataclass(frozen=True)
class PropertyHandle:
    release_id: str
    class_iri: str
    iri: str


@dataclass(frozen=True)
class QuerySpec:
    class_handle: ClassHandle
    property_handle: PropertyHandle
    projection: Literal["occurrence", "fact", "accepted"] = "occurrence"
    subject_ids: tuple[str, ...] = ()
    page_size: int = 100
    arithmetic_profile: Literal["exact"] = "exact"
    coverage_scope: str = "*"
    max_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        if self.projection not in {"occurrence", "fact", "accepted"}:
            raise SemanticRefusal("unsupported projection")
        if not 1 <= self.page_size <= 10000:
            raise SemanticRefusal("page_size must be between 1 and 10000")
        if type(self.max_bytes) is not int or not 1 <= self.max_bytes <= 8 * 1024 * 1024:
            raise SemanticRefusal("max_bytes must be between 1 and 8388608")
        if self.arithmetic_profile != "exact":
            raise SemanticRefusal("unsupported arithmetic profile")
        if type(self.subject_ids) is not tuple or any(type(s) is not str for s in self.subject_ids):
            raise SemanticRefusal("subject_ids must be a tuple of strings")


class _Envelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class AnswerSelection(_Envelope):
    parameter_digest: str
    projection: Literal["occurrence", "fact", "accepted"]
    arithmetic: Literal["exact"] = "exact"


class Membership(_Envelope):
    class_iri: str
    establishment: str


class DeclaredReference(_Envelope):
    description: str
    source_uri: str | None = None
    locator: str | None = None


class EntitySourceReference(_Envelope):
    observation_id: int
    observation_key: str
    local_id: str
    reference: DeclaredReference | None = None


class EntityReference(_Envelope):
    entity_id: str
    memberships: tuple[Membership, ...]
    source_declarations: tuple[EntitySourceReference, ...] = ()


class ValueRole(_Envelope):
    role: str
    position: int
    child_value_id: str


class ValueNode(_Envelope):
    """Lossless physical receipt beside the release-validated semantic output.

    A missing optional field is absent from the record mapping. A null is an actual
    node. Missingness/quantity/interval records retain their declared kind/roles.
    """

    value_id: str
    kind: str
    lexical: str | None = None
    datatype: str | None = None
    language: str | None = None
    entity: EntityReference | None = None
    roles: tuple[ValueRole, ...] = ()


class OccurrenceContext(_Envelope):
    statement_entity_id: str | None
    statement_role: str | None


class CitationRole(_Envelope):
    evidence_id: str
    role: str


class StandingDetail(_Envelope):
    collection: str
    availability: Literal["available", "unassessed", "unavailable"] = "available"
    count: int
    references: tuple[dict[str, Any], ...] = ()
    population_complete: bool


class FactStanding(_Envelope):
    """Independent presentation of recorded relations, never an aggregate verdict."""

    release_id: str
    selection: Literal["selected", "not_selected", "undetermined"]
    selection_references: tuple[str, ...] = ()
    assessments: StandingDetail
    establishments: StandingDetail


class QueryRow(_Envelope):
    fact_id: str
    subject: EntityReference
    property_iri: str
    object_value_id: str
    object: Any
    qualification_value_id: str | None
    qualification: SerializeAsAny[BaseModel] | None
    occurrence_id: str | None = None
    source: str | None = None
    item: str | None = None
    context: OccurrenceContext | None = None
    citation_roles: tuple[CitationRole, ...] = ()
    standing: FactStanding | None = None


class Coverage(_Envelope):
    coverage_id: str
    family: str
    scope: str
    outcome: Literal["complete", "partial", "unanalysed", "failed"]
    reason: str | None
    source_outcome: Literal["complete", "partial", "unknown", "unsupported", "failed"] | None
    required_capability: str | None


class CoverageSourceCount(_Envelope):
    source_outcome: str | None
    count: int


class CoverageSummary(_Envelope):
    state: Literal["established", "not_established"]
    diagnostic: str | None = None
    family: str | None = None
    source_outcomes: tuple[CoverageSourceCount, ...] = ()


class InventoryPage(_Envelope):
    """A bounded, binding-checked selection, separate from source payloads."""

    contract_version: Literal[2] = 2
    binding: SnapshotBinding
    selection: AnswerSelection | None = None
    run_id: int | None = None
    cut_id: int | None = None
    query_binding: QueryBindingReference | None = None
    root: str
    collection: str
    items: tuple[dict[str, Any], ...]
    population_complete: bool
    next_page_token: str | None = None


class ReadLimit(SemanticRefusal):
    def __init__(self, message: str, *, reason: str):
        self.reason = reason
        super().__init__(message)


class QueryResult(_Envelope):
    contract_version: Literal[2] = 2
    binding: SnapshotBinding
    selection: AnswerSelection | None = None
    run_id: int | None = None
    cut_id: int | None = None
    projection: Literal["occurrence", "fact", "accepted"]
    rows: tuple[QueryRow, ...]
    values: tuple[ValueNode, ...]
    coverage: tuple[Coverage, ...]
    coverage_summary: CoverageSummary | None = None
    coverage_detail: InventoryPage | None = None
    knowledge: Literal["observed", "unknown", "absent"]
    continuation: str | None
    complete: bool


class SourceCustody(_Envelope):
    observation_id: int
    observation_key: str
    task_id: int
    run_id: int
    rendition_id: int | None
    span_id: int | None
    source_view_id: int | None
    native_address: str | None
    payload_definition: str
    kind: str
    input_observation_keys: tuple[str, ...]


class SourceObservationReport(_Envelope):
    binding: SnapshotBinding
    selection: AnswerSelection | None = None
    run_id: int | None = None
    cut_id: int | None = None
    query_binding: QueryBindingReference | None = None
    root_fact_id: str
    observation_id: int
    observation_key: str
    payload: dict[str, Any]


class Evidence(_Envelope):
    evidence_id: str
    source_uri: str
    locator: str
    provider: str
    operation_version: str
    source: SourceCustody | None = None


class InputEntitySupport(_Envelope):
    input_realization_id: str
    input_data_revision: int
    input_entity_id: str
    run_id: int


class IdentityEndpointReference(_Envelope):
    kind: Literal["local", "known"]
    target: str
    entity: EntityReference
    input_supports: tuple[InputEntitySupport, ...] = ()


class IdentityExclusion(_Envelope):
    exclusion_id: str
    binding: SnapshotBinding
    observation_id: int
    observation_key: str
    local_id: str
    left: IdentityEndpointReference
    right: IdentityEndpointReference
    reason: str
    operation_id: str
    operation_version: str
    evidence: tuple[Evidence, ...]


class OccurrenceSupport(_Envelope):
    occurrence_id: str
    source: str
    item: str
    report_object_value_id: str
    report_qualification_value_id: str | None
    evidence_ids: tuple[str, ...]
    context: OccurrenceContext | None = None
    citation_roles: tuple[CitationRole, ...] = ()


class Derivation(_Envelope):
    derivation_id: str
    rule: str
    rule_version: str
    premise_fact_ids: tuple[str, ...]


class InputFactSupport(_Envelope):
    input_realization_id: str
    input_data_revision: int
    input_fact_id: str
    run_id: int


class AlternativeGroup(_Envelope):
    group_id: str
    member_fact_ids: tuple[str, ...]
    reason: str
    operation_id: str
    operation_version: str


class Assessment(_Envelope):
    assessment_id: str
    operation_id: str
    operation_version: str
    outcome: ScientificOutcome
    fact_id: str | None
    occurrence_id: str | None
    confidence: Decimal | None
    reason: str | None
    uncertainty: str | None
    counterpart_fact_id: str | None
    counterpart_occurrence_id: str | None
    context_value_id: str | None
    comparison_tier: str | None
    scientific_evidence: ScientificAssessmentEvidence | None = None
    semantic_reason: SemanticReason | None = None


class Explanation(_Envelope):
    contract_version: Literal[2] = 2
    binding: SnapshotBinding
    selection: AnswerSelection | None = None
    run_id: int | None = None
    cut_id: int | None = None
    query_binding: QueryBindingReference | None = None
    fact_id: str
    standing: FactStanding
    inventories: dict[str, InventoryPage]


class _Store(Protocol):
    engine: Engine


def _scope(binding: SnapshotBinding, relation: Any) -> ColumnElement[bool]:
    return and_(
        relation.c.release_id == binding.release_id,
        relation.c.realization_id == binding.realization_id,
    )


def _same_scope(left: Any, right: Any) -> ColumnElement[bool]:
    return and_(
        left.c.release_id == right.c.release_id,
        left.c.realization_id == right.c.realization_id,
    )


# Public predicate primitives compose with explicitly scoped aliases.
scope_clause = _scope
same_scope_clause = _same_scope


@contextmanager
def read_snapshot(
    store: Engine | _Store, *, cancellation: BorrowerCancellation | None = None
) -> Generator[Connection]:
    """One read-only snapshot opener, including SQLAlchemy/psycopg reset ownership."""
    engine = store if isinstance(store, Engine) else store.engine
    with (
        engine.connect().execution_options(
            isolation_level="REPEATABLE READ", postgresql_readonly=True
        ) as conn,
        cancellation.borrow(conn) if cancellation is not None else nullcontext(),
        conn.begin(),
    ):
        yield conn
        if cancellation is not None:
            cancellation.check_active()


def _require_snapshot(conn: Connection) -> None:
    if (
        conn.get_isolation_level() != "REPEATABLE READ"
        or conn.exec_driver_sql("SHOW transaction_read_only").scalar_one() != "on"
    ):
        raise SemanticRefusal("serving requires a read-only REPEATABLE READ transaction")


def bind_realization(conn: Connection, realization_id: str, release_id: str | None = None):
    _require_snapshot(conn)
    return _bind_realization(conn, realization_id, release_id)


def _bind_realization(
    conn: Connection,
    realization_id: str,
    release_id: str | None = None,
    *,
    completed_run_id=None,
    completed_cut_id=None,
):
    realization = table("data.realization")
    row = conn.execute(
        select(realization.c.release_id, realization.c.data_revision).where(
            realization.c.realization_id == realization_id
        )
    ).one_or_none()
    if row is None:
        raise SemanticRefusal(f"unknown realization {realization_id}")
    if release_id is not None and row.release_id != release_id:
        raise WrongRelease("release selector differs from realization binding")
    binding = SnapshotBinding(row.release_id, realization_id, row.data_revision, str(uuid4()))
    return ReadSession(
        conn,
        binding,
        open_release(conn, binding.release_id),
        completed_run_id=completed_run_id,
        completed_cut_id=completed_cut_id,
    )


def bind_completed_result(conn: Connection, run_id: int):
    _require_snapshot(conn)
    completed = table("ops.completed_result")
    row = conn.execute(
        select(completed.c.release_id, completed.c.output_realization_id, completed.c.cut_id).where(
            completed.c.run_id == run_id
        )
    ).one_or_none()
    if row is None:
        raise SemanticRefusal(f"no completed semantic result for run {run_id}")
    return _bind_realization(
        conn,
        row.output_realization_id,
        row.release_id,
        completed_run_id=run_id,
        completed_cut_id=row.cut_id,
    )


@dataclass(frozen=True)
class CoverageRequirement:
    """Required modeled members, independent from the rows returned by a page."""

    family: str
    members: frozenset[str]
    global_witness: bool = True
    diagnostic: str | None = None

    def established_by(self, records: tuple[Coverage, ...]) -> bool:
        applicable = tuple(row for row in records if row.family == self.family)
        if self.global_witness and any(
            row.scope == "*" and row.outcome == "complete" for row in applicable
        ):
            # A contradictory partial witness cannot prove completeness.
            return all(row.outcome == "complete" for row in applicable)
        return bool(self.members) and all(
            any(row.scope == member and row.outcome == "complete" for row in applicable)
            and all(row.outcome == "complete" for row in applicable if row.scope == member)
            for member in self.members
        )


@contextmanager
def read_session(
    store: Engine | _Store,
    realization_id: str,
    release_id: str | None = None,
    *,
    cancellation: BorrowerCancellation | None = None,
) -> Generator[ReadSession]:
    """Own a fresh REPEATABLE READ, read-only connection, binding exactly once.

    The optional release selector must equal the realization's immutable binding;
    the project's active pointer is deliberately not consulted.
    """
    with read_snapshot(store, cancellation=cancellation) as conn:
        yield bind_realization(conn, realization_id, release_id)


_READ_TABLES = {
    name: table("data." + name) for name in ("fact", "typed_value", "value_role", "selection")
}


@dataclass(frozen=True)
class ReadSession:
    """A scoped snapshot owner. Use only within ``read_session``."""

    connection: Connection
    binding: SnapshotBinding
    prepared: PreparedRelease
    _property_adapters: dict[tuple[str, str], Any] = field(
        default_factory=dict, repr=False, compare=False
    )

    completed_run_id: int | None = field(default=None, kw_only=True)
    completed_cut_id: int | None = field(default=None, kw_only=True)
    _analysis_input: Any = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.binding.release_id != self.prepared.release_id:
            raise WrongRelease("prepared release differs from snapshot binding")
        # Retained archive ABIs keep their original read contract; new releases
        # bind the declared read input once for this actual snapshot owner.
        from .contracts import EXECUTION_COMPILER_VERSION, execution_payload

        payload = execution_payload(self.prepared)
        if (
            payload is not None
            and json.loads(payload)["inputs"]["compiler_version"] == EXECUTION_COMPILER_VERSION
        ):
            from .analysis_contracts import bind_analysis_family

            owned = bind_analysis_family(self.prepared, "read").prepare(
                release=self.binding.release_id,
                archive=self.prepared.release_id,
                boundary=asdict(self.binding),
            )
            object.__setattr__(self, "_analysis_input", owned)

    def scope(self, relation: Any) -> ColumnElement[bool]:
        return scope_clause(self.binding, relation)

    def load_values(self, roots, entity_ids):
        return self._values(roots, entity_ids)

    def load_entities(self, ids):
        return self._entities(ids)

    def load_occurrence_contexts(self, ids):
        return self._occurrence_contexts(ids)

    def hydrate_rows(self, rows, *, definition=None):
        """One strict fact/occurrence hydration boundary for primitive and named reads."""
        roots = {
            row[key]
            for row in rows
            for key in ("object_value_id", "qualification_value_id")
            if row[key] is not None
        }
        decoded, nodes, entities = self.load_values(roots, {row["subject_id"] for row in rows})
        contexts, citations = self.load_occurrence_contexts(
            tuple(row["occurrence_id"] for row in rows if row.get("occurrence_id") is not None)
        )
        standing = self.fact_standing({row["fact_id"] for row in rows})
        output = []
        for row in rows:
            memberships = {m.class_iri for m in entities[row["subject_id"]].memberships}
            cls = definition or next(
                (
                    d
                    for d in self.prepared.definitions
                    if d.iri in memberships
                    and any(p.iri == row["property_id"] for p in d.properties)
                ),
                None,
            )
            if cls is None:
                raise WrongRelease("fact property has no release-declared subject membership")
            prop = next(p for p in cls.properties if p.iri == row["property_id"])
            adapter = self.prepared.property_adapter(cls.name, prop.name, item=prop.multivalued)
            occurrence = row.get("occurrence_id")
            output.append(
                QueryRow(
                    fact_id=row["fact_id"],
                    subject=entities[row["subject_id"]],
                    property_iri=prop.iri,
                    object_value_id=row["object_value_id"],
                    object=adapter.validate_python(decoded[row["object_value_id"]], strict=True),
                    qualification_value_id=row["qualification_value_id"],
                    qualification=None
                    if row["qualification_value_id"] is None
                    else self.qualification(row["qualification_value_id"], decoded, nodes),
                    occurrence_id=occurrence,
                    source=row.get("source"),
                    item=row.get("item"),
                    context=contexts.get(occurrence),
                    citation_roles=citations.get(occurrence, ()),
                    standing=standing[row["fact_id"]],
                )
            )
        return tuple(output), nodes

    def fact_standing(self, fact_ids, *, reference_limit=8):
        """Three set-shaped reads; window limits bound references per fact before transfer."""
        if not fact_ids:
            return {}
        selected, assessment, occurrence, establishment, derivation = (
            table("data." + name)
            for name in (
                "selection",
                "assessment",
                "occurrence",
                "occurrence_establishment",
                "derivation",
            )
        )
        members = set(
            self.connection.execute(
                select(selected.c.fact_id).where(
                    self.scope(selected), selected.c.fact_id.in_(fact_ids)
                )
            ).scalars()
        )
        # A single assessment may name both fact and occurrence. UNION preserves its identity.
        direct = select(
            assessment.c.fact_id,
            assessment.c.assessment_id,
            assessment.c.operation_id,
            assessment.c.operation_version,
            assessment.c.outcome,
            assessment.c.context_value_id,
        ).where(self.scope(assessment), assessment.c.fact_id.in_(fact_ids))
        via_occurrence = select(
            occurrence.c.fact_id,
            assessment.c.assessment_id,
            assessment.c.operation_id,
            assessment.c.operation_version,
            assessment.c.outcome,
            assessment.c.context_value_id,
        ).join(
            assessment,
            and_(
                _same_scope(occurrence, assessment),
                occurrence.c.occurrence_id == assessment.c.occurrence_id,
            ),
        )
        related = direct.union(
            via_occurrence.where(self.scope(occurrence), occurrence.c.fact_id.in_(fact_ids))
        ).subquery()
        ranked = select(
            related,
            func.count().over(partition_by=related.c.fact_id).label("population"),
            func.row_number()
            .over(partition_by=related.c.fact_id, order_by=related.c.assessment_id.collate("C"))
            .label("rank"),
        ).subquery()
        assessments = defaultdict(list)
        populations = {}
        for row in self.connection.execute(
            select(ranked).where(ranked.c.rank <= reference_limit)
        ).mappings():
            populations[row["fact_id"]] = row["population"]
            assessments[row["fact_id"]].append(
                {
                    key: row[key]
                    for key in (
                        "assessment_id",
                        "operation_id",
                        "operation_version",
                        "outcome",
                        "context_value_id",
                    )
                }
            )
        sources = select(
            occurrence.c.fact_id,
            occurrence.c.occurrence_id.label("reference_id"),
            establishment.c.establishment.label("kind"),
            literal("supports").label("collection"),
        ).join(
            establishment,
            and_(
                _same_scope(occurrence, establishment),
                occurrence.c.occurrence_id == establishment.c.occurrence_id,
            ),
        )
        sources = sources.where(self.scope(occurrence), occurrence.c.fact_id.in_(fact_ids))
        inferred = select(
            derivation.c.conclusion_fact_id.label("fact_id"),
            derivation.c.derivation_id.label("reference_id"),
            literal("inference").label("kind"),
            literal("derivations").label("collection"),
        ).where(self.scope(derivation), derivation.c.conclusion_fact_id.in_(fact_ids))
        origins = sources.union_all(inferred).subquery()
        ranked_origins = select(
            origins,
            func.count().over(partition_by=origins.c.fact_id).label("population"),
            func.row_number()
            .over(
                partition_by=origins.c.fact_id,
                order_by=(origins.c.collection, origins.c.reference_id.collate("C")),
            )
            .label("rank"),
        ).subquery()
        establishments = defaultdict(list)
        origin_counts = {}
        for row in self.connection.execute(
            select(ranked_origins).where(ranked_origins.c.rank <= reference_limit)
        ).mappings():
            origin_counts[row["fact_id"]] = row["population"]
            establishments[row["fact_id"]].append(
                {key: row[key] for key in ("reference_id", "kind", "collection")}
            )
        return {
            key: FactStanding(
                release_id=self.binding.release_id,
                selection="selected" if key in members else "not_selected",
                selection_references=(key,) if key in members else (),
                assessments=StandingDetail(
                    collection="assessments",
                    availability="available" if populations.get(key, 0) else "unassessed",
                    count=populations.get(key, 0),
                    references=tuple(assessments[key]),
                    population_complete=populations.get(key, 0) <= reference_limit,
                ),
                establishments=StandingDetail(
                    collection="establishments",
                    availability="available" if origin_counts.get(key, 0) else "unavailable",
                    count=origin_counts.get(key, 0),
                    references=tuple(establishments[key]),
                    population_complete=origin_counts.get(key, 0) <= reference_limit,
                ),
            )
            for key in fact_ids
        }

    def resolve_name(self, name):
        if name.startswith(("http:", "https:", "urn:")):
            return name
        if ":" in name:
            try:
                return self.prepared.expand_name(name)
            except KeyError as error:
                raise SemanticRefusal(f"unresolved release name {name!r}") from error
        candidates = {
            p.iri for d in self.prepared.definitions for p in d.properties if p.name == name
        }
        candidates |= {d.iri for d in self.prepared.definitions if d.name == name}
        if len(candidates) != 1:
            raise SemanticRefusal(f"ambiguous or unknown release name {name!r}")
        return candidates.pop()

    def referenced_entities(self, root):
        """Correlated recursive value closure preserves nested unresolved endpoints."""
        v, role = _READ_TABLES["typed_value"], _READ_TABLES["value_role"]
        closure = (
            select(v.c.value_id)
            .where(self.scope(v), v.c.value_id == root)
            .correlate(_READ_TABLES["fact"])
            .cte(recursive=True)
        )
        closure = closure.union(
            select(role.c.child_value_id)
            .join(closure, closure.c.value_id == role.c.parent_value_id)
            .where(self.scope(role))
        )
        return select(v.c.entity_id).where(
            self.scope(v), v.c.value_id.in_(select(closure)), v.c.kind == "entity"
        )

    def qualification_matches(self, name, value):
        role, val = _READ_TABLES["value_role"].alias(), _READ_TABLES["typed_value"].alias()
        return exists(
            select(1)
            .select_from(
                role.join(
                    val, and_(same_scope_clause(role, val), role.c.child_value_id == val.c.value_id)
                )
            )
            .where(
                self.scope(role),
                role.c.parent_value_id == _READ_TABLES["fact"].c.qualification_value_id,
                role.c.role == name,
                val.c.text_value == value,
            )
        )

    def fact_statement(
        self,
        *,
        projection="accepted",
        include_candidates=False,
        include_suppositions=False,
        **filters,
    ):
        f, selected = _READ_TABLES["fact"], _READ_TABLES["selection"]
        stmt = select(f).where(self.scope(f))
        projection = (
            "fact" if include_candidates or filters.get("status") == "candidate" else projection
        )
        if projection == "accepted":
            stmt = stmt.where(
                exists(select(1).where(self.scope(selected), selected.c.fact_id == f.c.fact_id))
            )
        if not include_suppositions:
            try:
                excluded = self.prepared.enum_members("ClaimModality", subset="premise_forming")
            except StopIteration, KeyError:
                excluded = frozenset()
            for modality in excluded:
                stmt = stmt.where(~self.qualification_matches("modality", modality))
        for key, value in filters.items():
            if value is None:
                continue
            column = {
                "key": f.c.fact_id,
                "fact_id": f.c.fact_id,
                "predicate": f.c.property_id,
                "subject_id": f.c.subject_id,
            }.get(key)
            if key == "predicate":
                value = self.resolve_name(value)
            if key == "status":
                if value not in {"accepted", "candidate"}:
                    raise SemanticRefusal("semantic status must be accepted or candidate")
                criterion = exists(
                    select(1).where(self.scope(selected), selected.c.fact_id == f.c.fact_id)
                )
                stmt = stmt.where(criterion if value == "accepted" else ~criterion)
            elif key == "modality":
                stmt = stmt.where(self.qualification_matches(key, value))
            elif key == "object_entity_id":
                stmt = stmt.where(
                    value.in_(self.referenced_entities(f.c.object_value_id))
                    if hasattr(value, "in_")
                    else exists(
                        self.referenced_entities(f.c.object_value_id).where(
                            _READ_TABLES["typed_value"].c.entity_id == value
                        )
                    )
                )
            elif column is not None:
                stmt = stmt.where(
                    column.in_(value) if isinstance(value, (list, tuple, set)) else column == value
                )
            else:
                raise SemanticRefusal(f"unsupported semantic fact filter {key}")
        return stmt

    def required_coverage(self, run_id, family, scope_kind="run", scope_members=()):
        """Lift requested scopes over producer-bound units of the frozen completed cut."""
        artifact = next(
            (a for a in self.prepared.artifacts if a.kind == "query_coverage.json"), None
        )
        if artifact is not None:
            recipe = json.loads(artifact.content)
            if recipe not in (coverage_recipe(), coverage_recipe(version=3)):
                raise SemanticRefusal("unsupported archived query coverage recipe")
        else:
            raise SemanticRefusal("release lacks its query coverage recipe")

        def unknown(reason):
            return CoverageRequirement(family, frozenset(), False, reason)

        completed, cut, logical = (
            table("ops.completed_result"),
            table("ops.cut_task"),
            table("ops.task"),
        )
        run, origin = table("ops.run"), logical.alias("coverage_origin")
        config, method = table("ops.method_config"), table("ops.method")
        source_view = table("kb.source_view")
        source_query = (
            select(run.c.dependencies)
            .join(completed, completed.c.run_id == run.c.id)
            .where(
                completed.c.run_id == run_id,
                completed.c.release_id == self.binding.release_id,
                completed.c.output_realization_id == self.binding.realization_id,
            )
        )
        current_recipe = recipe["abi"] == "semantic-query-coverage-4"
        if current_recipe:
            self._admit_hydration(source_query)
        source = self.connection.execute(source_query).scalar_one_or_none()
        if source is None:
            return unknown("completed result differs from the bound coverage snapshot")
        dependencies = json.loads(bytes(source))
        operations = dependencies.get("operations", {})
        try:
            agent_property = family in self.prepared.enum_members(recipe["agent_properties"])
        except StopIteration:
            agent_property = False
        configured_agent = agent_property and current_recipe
        declarations = {}
        if configured_agent:
            from corpus_structure.methods.llm.producer import producer_binding

            from .operations import OperationConflict

            snapshot = dependencies.get("agent_configurations")
            if not isinstance(snapshot, dict) or not snapshot:
                return unknown("coverage lacks immutable configured proposal producers")
            for name, parameters in snapshot.items():
                if not isinstance(name, str) or "/" not in name or not isinstance(parameters, dict):
                    return unknown("coverage has an invalid proposal producer declaration")
                producer_name, configuration_name = name.split("/", 1)
                if producer_name not in recipe["agent_methods"] or not configuration_name:
                    return unknown("coverage has an unsupported declared proposal producer")
                try:
                    binding = producer_binding(
                        producer_name,
                        parameters,
                        unit=recipe["agent_unit"],
                        method_version=recipe["agent_protocol"],
                    )
                except OperationConflict:
                    return unknown("coverage has an incompatible declared proposal binding")
                if binding.protocol != recipe["proposal_protocol"]:
                    return unknown("coverage proposal protocol differs from its released recipe")
                declarations[name] = parameters
            producer = None
        elif agent_property:
            producer = recipe["agent_method"]
        elif family in operations:
            producer = family
        else:
            return unknown("coverage family has no archived source-operation binding")
        # Unit identity follows the recorded origin, including reused completed reports.
        member = func.coalesce(origin.c.unit_key, func.cast(origin.c.id, Text))
        document = case(
            (origin.c.unit_type == "document", origin.c.unit_id),
            (origin.c.unit_type == "source_view", source_view.c.document_id),
        )
        stmt = (
            select(
                member.label("member"),
                document.label("document"),
                method.c.version,
                config.c.config_hash,
            )
            .select_from(
                completed.join(logical, logical.c.run_id == completed.c.run_id)
                .outerjoin(
                    cut, and_(cut.c.cut_id == completed.c.cut_id, cut.c.task_id == logical.c.id)
                )
                .join(origin, origin.c.id == func.coalesce(cut.c.origin_task_id, logical.c.id))
                .join(config, config.c.id == origin.c.method_config_id)
                .join(method, method.c.id == config.c.method_id)
                .outerjoin(
                    source_view,
                    and_(origin.c.unit_type == "source_view", source_view.c.id == origin.c.unit_id),
                )
            )
            .where(
                completed.c.run_id == run_id,
                completed.c.release_id == self.binding.release_id,
                completed.c.output_realization_id == self.binding.realization_id,
                method.c.name.in_(recipe["agent_methods"])
                if configured_agent
                else method.c.name == producer,
            )
        )
        if configured_agent:
            stmt = stmt.add_columns(
                method.c.name.label("method_name"),
                method.c.unit_type.label("method_unit"),
                origin.c.unit_type.label("unit_type"),
                config.c.id.label("config_id"),
                config.c.name.label("configuration_name"),
            )
        if current_recipe:
            stmt = stmt.limit(100001)
            self._admit_hydration(stmt)
        rows = self.connection.execute(stmt).all()
        if current_recipe and len(rows) > 100000:
            raise ReadLimit("coverage required universe exceeds 100000 units", reason="work_limit")
        binding = operations.get(producer)
        if configured_agent and rows:
            configs = (
                select(config.c.id, config.c.params)
                .where(config.c.id.in_({row.config_id for row in rows}))
                .limit(10001)
            )
            self._admit_hydration(configs)
            parameters = dict(self.connection.execute(configs).all())
            if len(parameters) > 10000:
                raise ReadLimit(
                    "coverage producer configurations exceed 10000", reason="work_limit"
                )
            for row in rows:
                values = parameters[row.config_id]
                declared = declarations.get(f"{row.method_name}/{row.configuration_name}")
                expected_hash = (
                    "configuration:"
                    + sha256(canonical_bytes([row.method_name, row.version, values])).hexdigest()
                )
                if (
                    declared is None
                    or canonical_bytes(values) != canonical_bytes(declared)
                    or row.version != recipe["agent_protocol"]
                    or row.unit_type != recipe["agent_unit"]
                    or row.method_unit != recipe["agent_unit"]
                    or row.config_hash != expected_hash
                ):
                    return unknown(
                        "cut proposal producer differs from its archived configured binding"
                    )
        elif configured_agent:
            pass
        elif binding is not None:
            if any(
                row.version != binding["version"]
                or row.config_hash != binding["configuration_hash"]
                for row in rows
            ):
                return unknown("cut source method differs from its archived operation binding")
        elif not agent_property or any(row.version != recipe["agent_protocol"] for row in rows):
            return unknown("source method has no supported archived protocol binding")
        if not rows:
            return unknown("coverage family has no eligible units in this completed cut")
        if scope_kind == "run":
            members = frozenset(row.member for row in rows)
        elif scope_kind == "units":
            requested = frozenset(str(member) for member in scope_members)
            if not requested or not requested <= {row.member for row in rows}:
                return unknown("requested units are outside this family's completed-cut universe")
            members = requested
        elif scope_kind == "documents":
            requested = frozenset(str(member) for member in scope_members)
            if not requested or not requested <= {
                str(row.document) for row in rows if row.document is not None
            }:
                return unknown(
                    "requested documents have no eligible family units in this completed cut"
                )
            if any(row.document is None for row in rows):
                return unknown("an eligible source unit has no supported document binding")
            members = frozenset(row.member for row in rows if str(row.document) in requested)
        else:
            return unknown("unsupported coverage scope")
        return CoverageRequirement(family, members)

    def object_predicate(self, predicate, operand, targets=(), *, projection="fact"):
        """Lower existing equality requests through the archived property boundary."""
        from pydantic import ValidationError
        from sqlalchemy import Text, bindparam, cast
        from sqlalchemy.dialects.postgresql import ARRAY, JSONB

        from .consolidation import plain
        from .value_codec import value_meaning

        value, fact = table("data.typed_value"), table("data.fact")
        if predicate is None:
            comparison = or_(
                and_(value.c.kind == "string", value.c.text_value == operand),
                and_(value.c.kind == "entity", value.c.entity_id.in_(targets)),
            )
        else:
            iri = self.resolve_name(predicate)
            properties = [
                (d, p) for d in self.prepared.definitions for p in d.properties if p.iri == iri
            ]
            if not properties:
                raise SemanticRefusal("object predicate has no release property")
            class_names = {definition.name for definition in self.prepared.definitions}
            references = [
                not prop.inlined and prop.range in class_names and prop.reference_role != "fact"
                for _, prop in properties
            ]
            if any(references) and not all(references):
                raise SemanticRefusal(
                    "object property has incompatible reference and scalar interpretations"
                )
            if all(references):
                comparison = and_(
                    value.c.kind == "entity",
                    or_(value.c.entity_id.in_(targets), value.c.entity_id == operand),
                )
            else:
                meanings = []
                for definition, prop in properties:
                    adapter = self.prepared.property_adapter(
                        definition.name, prop.name, item=prop.multivalued
                    )
                    try:
                        try:
                            parsed = adapter.validate_json(operand, strict=True)
                        except ValidationError:
                            parsed = adapter.validate_json(json.dumps(operand), strict=True)
                        meaning = value_meaning(plain(parsed))
                    except (ValidationError, TypeError, ValueError) as error:
                        raise SemanticRefusal(
                            "unsupported exact object operand for release property"
                        ) from error
                    if meaning not in meanings:
                        meanings.append(meaning)
                if len(meanings) != 1:
                    raise SemanticRefusal(
                        "ambiguous exact object operand across property declarations"
                    )
                comparison = func.data.value_meaning(
                    self.binding.release_id,
                    self.binding.realization_id,
                    value.c.value_id,
                    cast(literal("{}"), ARRAY(Text())),
                    False,
                ) == bindparam(None, meanings[0], type_=JSONB())
        if projection not in {"fact", "accepted", "occurrence"}:
            raise SemanticRefusal("unsupported object predicate projection")
        occurrence = table("data.occurrence")
        root = (
            occurrence.c.report_object_value_id
            if projection == "occurrence"
            else fact.c.object_value_id
        )
        return exists(
            select(1).where(self.scope(value), value.c.value_id == root, comparison)
        ).correlate(fact, occurrence)

    def class_handle(self, name_or_iri: str) -> ClassHandle:
        definition = next(
            (d for d in self.prepared.definitions if name_or_iri in {d.name, d.iri}), None
        )
        if definition is None:
            raise SemanticRefusal(f"unknown release name {name_or_iri!r}")
        return ClassHandle(self.binding.release_id, definition.iri)

    def _class(self, handle: ClassHandle) -> ClassDefinition:
        if handle.release_id != self.binding.release_id:
            raise WrongRelease("class handle differs from snapshot release")
        definition = next((d for d in self.prepared.definitions if d.iri == handle.iri), None)
        if definition is None:
            raise WrongRelease(f"handle is absent from the bound release: {handle.iri}")
        return definition

    def property_handle(self, cls: ClassHandle, name_or_iri: str) -> PropertyHandle:
        definition = self._class(cls)
        prop = next((p for p in definition.properties if name_or_iri in {p.name, p.iri}), None)
        if prop is None:
            raise SemanticRefusal(f"unknown release name {name_or_iri!r}")
        return PropertyHandle(self.binding.release_id, cls.iri, prop.iri)

    def _property(self, spec: QuerySpec) -> tuple[ClassDefinition, PropertyDefinition]:
        cls = self._class(spec.class_handle)
        handle = spec.property_handle
        if handle.release_id != self.binding.release_id:
            raise WrongRelease("property handle differs from snapshot release")
        if handle.class_iri != cls.iri:
            raise WrongRelease("property handle belongs to another class")
        prop = next((p for p in cls.properties if p.iri == handle.iri), None)
        if prop is None:
            raise WrongRelease(f"handle is absent from the bound release: {handle.iri}")
        return cls, prop

    def _selection(self, spec: QuerySpec, after: str | None) -> Select:
        """Core expression construction remains visible to PostgreSQL's optimizer."""
        f, o = table("data.fact"), table("data.occurrence")
        m, h = table("data.membership"), table("sem.class_hierarchy")
        membership = exists(
            select(1).where(
                _scope(self.binding, m),
                m.c.entity_id == f.c.subject_id,
                (m.c.class_id == spec.class_handle.iri)
                | exists(
                    select(1).where(
                        h.c.release_id == self.binding.release_id,
                        h.c.class_id == m.c.class_id,
                        h.c.ancestor_id == spec.class_handle.iri,
                    )
                ),
            )
        )
        if spec.projection == "occurrence":
            source = f.join(o, and_(_same_scope(f, o), f.c.fact_id == o.c.fact_id))
            columns = [
                f.c.fact_id,
                f.c.subject_id,
                f.c.property_id,
                o.c.report_object_value_id.label("object_value_id"),
                o.c.report_qualification_value_id.label("qualification_value_id"),
                o.c.occurrence_id,
                o.c.source,
                o.c.item,
            ]
            key = o.c.occurrence_id
        else:
            source, columns, key = f, list(f.c), f.c.fact_id
        stmt = (
            select(*columns)
            .select_from(source)
            .where(_scope(self.binding, f), f.c.property_id == spec.property_handle.iri, membership)
        )
        if spec.projection == "accepted":
            selected = table("data.selection")
            stmt = stmt.where(
                exists(
                    select(1).where(
                        _scope(self.binding, selected),
                        selected.c.fact_id == f.c.fact_id,
                    )
                )
            )
        if spec.subject_ids:
            stmt = stmt.where(f.c.subject_id.in_(spec.subject_ids))
        if after is not None:
            stmt = stmt.where(key.collate("C") > after)
        return stmt.order_by(key.collate("C")).limit(spec.page_size + 1)

    def _fingerprint(self, spec: QuerySpec) -> str:
        return sha256(
            canonical_bytes(
                {
                    "format": "ordinary-answer-coverage-2",
                    "spec": asdict(spec),
                    "ordering": "identity:C:asc",
                }
            )
        ).hexdigest()

    def _after(self, spec: QuerySpec, token: str | None) -> str | None:
        if token is None:
            return None
        from .continuations import decode_continuation, validate_continuation

        value = decode_continuation(token, kind="primitive")
        validate_continuation(
            self.prepared,
            value,
            {
                "release": self.binding.release_id,
                "realization": self.binding.realization_id,
                "query": self._fingerprint(spec),
                "revision": self.binding.data_revision,
            },
        )
        return value["after"]

    def _token(self, spec: QuerySpec, after: str) -> str:
        return base64.urlsafe_b64encode(
            canonical_bytes(
                {
                    "release": self.binding.release_id,
                    "realization": self.binding.realization_id,
                    "revision": self.binding.data_revision,
                    "query": self._fingerprint(spec),
                    "after": after,
                }
            )
        ).decode()

    def _admit_hydration(self, *statements):
        """Bound physical scalar transfer before decoding a selected value/entity graph.

        This is an operational transfer limit, separate from canonical result bytes;
        metadata fields absent from the answer still consume this finite read budget.
        """
        sizes = []
        for stmt in statements:
            scalar_bytes = sum(
                (
                    func.coalesce(func.octet_length(column.cast(Text)), 0)
                    for column in stmt.selected_columns
                ),
                literal(0),
            )
            sizes.append(
                stmt.with_only_columns(
                    func.coalesce(func.sum(scalar_bytes), 0).label("bytes"),
                    maintain_column_froms=True,
                ).order_by(None)
            )
        union = sizes[0].union_all(*sizes[1:]).subquery() if len(sizes) > 1 else sizes[0].subquery()
        size = self.connection.execute(select(func.sum(union.c.bytes))).scalar_one() or 0
        if size > 8 * 1024 * 1024:
            raise ReadLimit(
                "selected value/entity graph exceeds 8 MiB physical hydration budget",
                reason="work_limit",
            )

    def _entities(self, ids: set[str]) -> dict[str, EntityReference]:
        if not ids:
            return {}
        e, m = table("data.entity"), table("data.membership")
        membership_stmt = (
            select(
                e.c.entity_id,
                m.c.class_id,
                m.c.establishment,
            )
            .select_from(e.outerjoin(m, and_(_same_scope(e, m), e.c.entity_id == m.c.entity_id)))
            .where(
                _scope(self.binding, e),
                e.c.entity_id.in_(ids),
            )
            .order_by(e.c.entity_id, m.c.class_id)
        )
        self._admit_hydration(membership_stmt)
        rows = self.connection.execute(membership_stmt).mappings()
        memberships: dict[str, list[Membership]] = defaultdict(list)
        for row in rows:
            items = memberships[row["entity_id"]]
            if row["class_id"] is not None:
                items.append(
                    Membership(class_iri=row["class_id"], establishment=row["establishment"])
                )
        source, observation = table("data.entity_source"), table("kb.observation")
        # Project only the exact declaration's small reference field, not the full report.
        from sqlalchemy import func, literal_column

        declaration = (
            func.jsonb_array_elements(observation.c.payload["entities"])
            .table_valued("value")
            .lateral()
        )
        source_declarations: dict[str, list[EntitySourceReference]] = defaultdict(list)
        declaration_stmt = (
            select(
                source.c.entity_id,
                source.c.observation_id,
                observation.c.observation_key,
                source.c.local_id,
                declaration.c.value.op("->")(literal_column("'reference'")).label("reference"),
            )
            .select_from(
                source.join(observation, source.c.observation_id == observation.c.id).join(
                    declaration,
                    declaration.c.value.op("->>")(literal_column("'id'")) == source.c.local_id,
                )
            )
            .where(_scope(self.binding, source), source.c.entity_id.in_(ids))
            .order_by(source.c.entity_id, observation.c.observation_key, source.c.local_id)
        )
        self._admit_hydration(declaration_stmt)
        for row in self.connection.execute(declaration_stmt).mappings():
            source_declarations[row["entity_id"]].append(
                EntitySourceReference(
                    observation_id=row["observation_id"],
                    observation_key=row["observation_key"],
                    local_id=row["local_id"],
                    reference=DeclaredReference.model_validate(row["reference"], strict=True)
                    if row["reference"] is not None
                    else None,
                )
            )
        return {
            identity: EntityReference(
                entity_id=identity,
                memberships=tuple(items),
                source_declarations=tuple(source_declarations[identity]),
            )
            for identity, items in memberships.items()
        }

    def _discover_values(self, roots):
        """Bound complete graph discovery without fetching value bodies."""
        v, r = table("data.typed_value"), table("data.value_role")
        max_nodes, max_edges, max_bytes = 100_000, 100_000, 8 * 1024 * 1024
        pending = deque(sorted(roots))
        scheduled = set(roots)
        admitted = []
        scalar_total = 0
        examined = 0
        roles: dict[str, list[Any]] = defaultdict(list)
        if len(scheduled) > max_nodes:
            raise ReadLimit("value graph node budget exhausted", reason="work_limit")

        def scalar_size(relation):
            return sum(
                (func.coalesce(func.octet_length(column.cast(Text)), 0) for column in relation.c),
                literal(0),
            )

        while pending:
            frontier = [pending.popleft() for _ in range(min(64, len(pending)))]
            metadata = (
                self.connection.execute(
                    select(v.c.value_id, scalar_size(v).label("bytes"))
                    .where(self.scope(v), v.c.value_id.in_(frontier))
                    .order_by(v.c.value_id.collate("C"))
                    .limit(64)
                )
                .mappings()
                .all()
            )
            for row in metadata:
                scalar_total += row["bytes"]
                if scalar_total > max_bytes:
                    raise ReadLimit(
                        "selected value graph exceeds 8 MiB physical hydration budget",
                        reason="work_limit",
                    )
                admitted.append(row["value_id"])
            if len(metadata) != len(frontier):
                raise ValueError("selected value graph references an unavailable node")
            cursor = None
            while True:
                # Long mapping keys cannot become unbounded adjacency cursor payloads.
                stmt = select(
                    r.c.parent_value_id,
                    case((func.octet_length(r.c.role) <= 8192, r.c.role), else_=None).label("role"),
                    r.c.position,
                    r.c.child_value_id,
                    scalar_size(r).label("bytes"),
                ).where(self.scope(r), r.c.parent_value_id.in_(frontier))
                if cursor is not None:
                    stmt = stmt.where(
                        tuple_(
                            r.c.parent_value_id.collate("C"), r.c.role.collate("C"), r.c.position
                        )
                        > cursor
                    )
                batch_size = min(64, max_edges - examined + 1)
                edges = (
                    self.connection.execute(
                        stmt.order_by(
                            r.c.parent_value_id.collate("C"), r.c.role.collate("C"), r.c.position
                        ).limit(batch_size)
                    )
                    .mappings()
                    .all()
                )
                for row in edges:
                    examined += 1
                    scalar_total += row["bytes"]
                    if examined > max_edges or scalar_total > max_bytes or row["role"] is None:
                        raise ReadLimit(
                            "value graph edge/key/physical-byte budget exhausted",
                            reason="work_limit",
                        )
                    child = row["child_value_id"]
                    if child not in scheduled:
                        if len(scheduled) >= max_nodes:
                            raise ReadLimit(
                                "value graph node budget exhausted", reason="work_limit"
                            )
                        scheduled.add(child)
                        pending.append(child)
                    roles[row["parent_value_id"]].append(row)
                if len(edges) < batch_size:
                    break
                last = edges[-1]
                cursor = (last["parent_value_id"], last["role"], last["position"])
        return admitted, roles

    def _values(
        self, roots: set[str], subjects: set[str]
    ) -> tuple[dict[str, Any], tuple[ValueNode, ...], dict[str, EntityReference]]:
        """Bounded adjacency discovery precedes value-body hydration in batches of 64."""
        v = table("data.typed_value")
        if not roots:
            return {}, (), self._entities(subjects)
        admitted, roles = self._discover_values(roots)
        records = {}
        for keys in batched(admitted, 64, strict=False):
            records.update(
                {
                    row["value_id"]: row
                    for row in self.connection.execute(
                        select(v)
                        .where(self.scope(v), v.c.value_id.in_(keys))
                        .order_by(v.c.value_id.collate("C"))
                        .limit(64)
                    )
                    .mappings()
                    .all()
                }
            )
        # Adjacency batches were ordered by parent/role/position, retaining sequence meaning.
        entities = self._entities(
            subjects
            | {row["entity_id"] for row in records.values() if row["entity_id"] is not None}
        )
        decoded: dict[str, Any] = {}
        visiting: set[str] = set()

        def decode(identity: str) -> Any:
            if identity in decoded:
                return decoded[identity]
            if identity in visiting:
                raise ValueError("cyclic value graph")
            visiting.add(identity)
            row, children = records[identity], roles[identity]
            kind, lexical = row["kind"], row["text_value"]
            if kind in {"string", "entity"}:
                value = row["entity_id"] if kind == "entity" else lexical
            elif kind == "integer":
                value = int(lexical if lexical is not None else row["integer_value"])
            elif kind in {"decimal", "number"}:
                value = Decimal(row["decimal_lexical"])
            elif kind == "float":
                value = float.fromhex(lexical)
            elif kind == "date":
                value = date.fromisoformat(lexical)
            elif kind == "datetime":
                value = datetime.fromisoformat(lexical)
            elif kind == "boolean":
                value = row["boolean_value"]
            elif kind == "null":
                value = None
            elif kind == "sequence":
                value = tuple(decode(child["child_value_id"]) for child in children)
            elif kind in {"record", "mapping"}:
                value = {child["role"]: decode(child["child_value_id"]) for child in children}
            else:
                raise ValueError(f"unsupported admitted value kind {kind}")
            decoded[identity] = value
            visiting.remove(identity)
            return value

        for identity in records:
            decode(identity)
        nodes = tuple(
            ValueNode(
                value_id=identity,
                kind=row["kind"],
                lexical=row["decimal_lexical"]
                if row["decimal_lexical"] is not None
                else row["text_value"],
                datatype=row["datatype"],
                language=row["language"],
                entity=entities.get(row["entity_id"]),
                roles=tuple(
                    ValueRole(
                        role=c["role"], position=c["position"], child_value_id=c["child_value_id"]
                    )
                    for c in roles[identity]
                ),
            )
            for identity, row in sorted(records.items())
        )
        return decoded, nodes, entities

    def coverage(self, family: str | None = None, scope: str | None = None) -> tuple[Coverage, ...]:
        relation = table("data.coverage")
        stmt = select(relation).where(_scope(self.binding, relation))
        if family is not None:
            stmt = stmt.where(relation.c.family == family)
        if scope is not None:
            stmt = stmt.where(relation.c.scope == scope)
        return tuple(
            Coverage(**{key: row[key] for key in Coverage.model_fields})
            for row in self.connection.execute(stmt.order_by(relation.c.coverage_id)).mappings()
        )

    def coverage_summary(self, requirement: CoverageRequirement | None = None) -> CoverageSummary:
        """Inspect only the scoped coverage relation, without hydrating source/value detail."""
        if requirement is None:
            return CoverageSummary(
                state="not_established", diagnostic="no property coverage requirement"
            )
        if requirement.diagnostic is not None:
            return CoverageSummary(
                state="not_established",
                family=requirement.family,
                diagnostic=requirement.diagnostic,
            )
        relation = table("data.coverage")
        scopes = requirement.members | ({"*"} if requirement.global_witness else set())
        rows = (
            self.connection.execute(
                select(
                    relation.c.scope,
                    relation.c.source_outcome,
                    func.count().label("total"),
                    func.count().filter(relation.c.outcome == "complete").label("complete"),
                )
                .where(
                    self.scope(relation),
                    relation.c.family == requirement.family,
                    relation.c.scope.in_(scopes),
                )
                .group_by(relation.c.scope, relation.c.source_outcome)
            )
            .mappings()
            .all()
        )
        counts = {}
        source_counts = defaultdict(int)
        for row in rows:
            total, complete = counts.get(row["scope"], (0, 0))
            counts[row["scope"]] = total + row["total"], complete + row["complete"]
            source_counts[row["source_outcome"]] += row["total"]

        def valid(key):
            return key in counts and counts[key][0] == counts[key][1]

        established = (
            requirement.global_witness
            and valid("*")
            and all(total == complete for total, complete in counts.values())
        ) or (bool(requirement.members) and all(valid(key) for key in requirement.members))
        return CoverageSummary(
            state="established" if established else "not_established",
            family=requirement.family,
            source_outcomes=tuple(
                CoverageSourceCount(source_outcome=key, count=value)
                for key, value in sorted(source_counts.items(), key=lambda item: item[0] or "")
            ),
        )

    def coverage_page(self, family=None, scopes=None, *, after=None, limit=64):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise SemanticRefusal("coverage page limit must be between 1 and 1000")
        relation = table("data.coverage")
        stmt = select(relation).where(self.scope(relation))
        if family is not None:
            stmt = stmt.where(relation.c.family == family)
        if scopes is not None:
            stmt = stmt.where(relation.c.scope.in_(scopes))
        if after is not None:
            stmt = stmt.where(relation.c.coverage_id.collate("C") > after)
        rows = (
            self.connection.execute(
                stmt.order_by(relation.c.coverage_id.collate("C")).limit(limit + 1)
            )
            .mappings()
            .all()
        )
        return tuple(
            Coverage(**{key: row[key] for key in Coverage.model_fields}) for row in rows[:limit]
        ), len(rows) > limit

    def _detail_query_binding(self, query_binding):
        if query_binding is None:
            return None
        if not isinstance(query_binding, QueryBindingReference):
            raise WrongBinding("detail requires a typed query binding")
        if query_binding.release_id != self.binding.release_id:
            raise WrongRelease("detail query binding belongs to another producing release")
        return query_binding.model_dump(mode="json")

    def _detail_selection(self, selection):
        if selection is None:
            return None
        if not isinstance(selection, AnswerSelection):
            raise WrongBinding("detail requires a typed answer selection")
        return selection.model_dump(mode="json")

    def coverage_details(
        self,
        family,
        scopes,
        *,
        continuation=None,
        limit=64,
        max_bytes=1024 * 1024,
        query_binding=None,
        selection=None,
    ):
        """Page only the released requirement's selected scopes under the same binding."""
        if (
            type(limit) is not int
            or not 1 <= limit <= 1000
            or type(max_bytes) is not int
            or not 1 <= max_bytes <= 8 * 1024 * 1024
        ):
            raise SemanticRefusal("unsupported coverage detail page bounds")
        named_binding = self._detail_query_binding(query_binding)
        selected = self._detail_selection(selection)
        scopes = tuple(sorted(scopes))
        identity = {
            "version": 2,
            "release": self.binding.release_id,
            "realization": self.binding.realization_id,
            "revision": self.binding.data_revision,
            "run": self.completed_run_id,
            "cut": self.completed_cut_id,
            "family": family,
            "query_binding": named_binding,
            "selection": selected,
            "scopes": sha256(canonical_bytes(scopes)).hexdigest(),
            "limit": limit,
            "max_bytes": max_bytes,
        }
        after = None
        if continuation is not None:
            try:
                if len(continuation.encode("utf-8")) > 8192:
                    raise ValueError("oversized token")
                body = json.loads(base64.b64decode(continuation, altchars=b"-_", validate=True))
                if set(body) != {*identity, "after"} or not isinstance(body["after"], str):
                    raise ValueError("invalid coverage cursor")
                if canonical_bytes({k: body[k] for k in identity}) != canonical_bytes(identity):
                    raise WrongBinding("coverage continuation differs from the requested binding")
                after = body["after"]
            except (ValueError, TypeError) as error:
                if isinstance(error, WrongBinding):
                    raise
                raise InvalidContinuation("invalid coverage continuation") from error
        rows, more = self.coverage_page(family, scopes, after=after, limit=limit)
        token = (
            base64.urlsafe_b64encode(
                canonical_bytes({**identity, "after": rows[-1].coverage_id})
            ).decode("ascii")
            if more
            else None
        )
        if token is not None and len(token.encode("ascii")) > 8192:
            raise ReadLimit("coverage cursor exceeds 8192 bytes", reason="oversized_item")
        result = InventoryPage(
            binding=self.binding,
            run_id=self.completed_run_id,
            cut_id=self.completed_cut_id,
            root=family,
            collection="coverage",
            query_binding=query_binding,
            selection=selection,
            items=tuple(row.model_dump(mode="python") for row in rows),
            population_complete=not more,
            next_page_token=token,
        )
        if len(canonical_bytes(result.model_dump(mode="json"))) > max_bytes:
            raise ReadLimit(
                "complete coverage detail envelope exceeds max_bytes", reason="oversized_item"
            )
        return result

    def _inventory_statement(self, fact_id, collection):
        f, s, o, oe, e, a, d = (
            table("data." + name)
            for name in (
                "fact",
                "support",
                "occurrence",
                "occurrence_evidence",
                "evidence",
                "assessment",
                "derivation",
            )
        )
        occurrences = select(s.c.occurrence_id).where(self.scope(s), s.c.fact_id == fact_id)
        if collection == "supports":
            return select(o).where(
                self.scope(o), o.c.occurrence_id.in_(occurrences)
            ), o.c.occurrence_id
        if collection == "evidence":
            evidence_ids = select(oe.c.evidence_id).where(
                self.scope(oe), oe.c.occurrence_id.in_(occurrences)
            )
            return select(e).where(
                self.scope(e), e.c.evidence_id.in_(evidence_ids)
            ), e.c.evidence_id
        if collection == "assessments":
            return select(a).where(
                self.scope(a), or_(a.c.fact_id == fact_id, a.c.occurrence_id.in_(occurrences))
            ), a.c.assessment_id
        if collection == "derivations":
            return select(d).where(
                self.scope(d), d.c.conclusion_fact_id == fact_id
            ), d.c.derivation_id
        if collection == "occurrence_contexts":
            context = table("data.occurrence_context")
            return select(context).where(
                self.scope(context), context.c.occurrence_id.in_(occurrences)
            ), context.c.occurrence_id
        if collection == "citation_roles":
            citation = table("data.occurrence_evidence_role")
            key = (
                func.jsonb_build_array(
                    citation.c.occurrence_id, citation.c.evidence_id, citation.c.role
                )
                .cast(Text)
                .label("cursor_identity")
            )
            return select(citation, key).where(
                self.scope(citation), citation.c.occurrence_id.in_(occurrences)
            ), key
        if collection == "support_evidence":
            key = (
                func.jsonb_build_array(oe.c.occurrence_id, oe.c.evidence_id)
                .cast(Text)
                .label("cursor_identity")
            )
            return select(oe, key).where(self.scope(oe), oe.c.occurrence_id.in_(occurrences)), key
        if collection == "derivation_premises":
            premise = table("data.derivation_premise")
            derivations = select(d.c.derivation_id).where(
                self.scope(d), d.c.conclusion_fact_id == fact_id
            )
            key = (
                func.jsonb_build_array(premise.c.derivation_id, premise.c.position)
                .cast(Text)
                .label("cursor_identity")
            )
            return select(premise, key).where(
                self.scope(premise), premise.c.derivation_id.in_(derivations)
            ), key
        if collection in {"alternatives", "alternative_members"}:
            group, member = table("data.alternative_group"), table("data.alternative_member")
            groups = select(member.c.group_id).where(
                self.scope(member), member.c.fact_id == fact_id
            )
            if collection == "alternatives":
                return select(group).where(
                    self.scope(group), group.c.group_id.in_(groups)
                ), group.c.group_id
            key = (
                func.jsonb_build_array(member.c.group_id, member.c.fact_id)
                .cast(Text)
                .label("cursor_identity")
            )
            return select(member, key).where(self.scope(member), member.c.group_id.in_(groups)), key
        if collection == "input_supports":
            inputs = table("data.fact_input")
            key = (
                func.jsonb_build_array(
                    inputs.c.input_realization_id,
                    inputs.c.input_data_revision,
                    inputs.c.input_fact_id,
                    inputs.c.run_id,
                )
                .cast(Text)
                .label("cursor_identity")
            )
            return select(inputs, key).where(self.scope(inputs), inputs.c.fact_id == fact_id), key
        if collection == "establishments":
            establishment = table("data.occurrence_establishment")
            sources = (
                select(
                    o.c.occurrence_id.label("reference_id"),
                    establishment.c.establishment.label("kind"),
                    literal("supports").label("detail_collection"),
                )
                .join(
                    establishment,
                    and_(
                        _same_scope(o, establishment),
                        o.c.occurrence_id == establishment.c.occurrence_id,
                    ),
                )
                .where(self.scope(o), o.c.occurrence_id.in_(occurrences))
            )
            inferred = select(
                d.c.derivation_id.label("reference_id"),
                literal("inference").label("kind"),
                literal("derivations").label("detail_collection"),
            ).where(self.scope(d), d.c.conclusion_fact_id == fact_id)
            origins = sources.union_all(inferred).subquery()
            key = (
                func.jsonb_build_array(origins.c.detail_collection, origins.c.reference_id)
                .cast(Text)
                .label("cursor_identity")
            )
            return select(origins, key), key
        if collection == "identity_exclusion_evidence":
            exclusions, _ = self._inventory_statement(fact_id, "identity_exclusions")
            relation = table("data.identity_exclusion_evidence")
            ids = exclusions.with_only_columns(table("data.identity_exclusion").c.exclusion_id)
            key = (
                func.jsonb_build_array(relation.c.exclusion_id, relation.c.evidence_id)
                .cast(Text)
                .label("cursor_identity")
            )
            return select(relation, key).where(
                self.scope(relation), relation.c.exclusion_id.in_(ids)
            ), key
        if collection == "identity_exclusions":
            relation, values, roles = (
                table("data." + name)
                for name in ("identity_exclusion", "typed_value", "value_role")
            )
            root = self.connection.execute(
                select(f.c.object_value_id, f.c.qualification_value_id).where(
                    self.scope(f), f.c.fact_id == fact_id
                )
            ).one()
            # The recursive relational filter below is over this same immutable graph,
            # whose complete node/edge/byte population has already been admitted.
            self._discover_values({value for value in root if value is not None})
            root_fact = select(f).where(self.scope(f), f.c.fact_id == fact_id).subquery()
            roots = select(root_fact.c.object_value_id).union(
                select(root_fact.c.qualification_value_id)
            )
            closure = (
                select(values.c.value_id)
                .where(self.scope(values), values.c.value_id.in_(roots))
                .cte("inventory_value_closure", recursive=True)
            )
            closure = closure.union(
                select(roles.c.child_value_id)
                .join(closure, roles.c.parent_value_id == closure.c.value_id)
                .where(self.scope(roles))
            )
            entities = (
                select(values.c.entity_id)
                .where(
                    self.scope(values),
                    values.c.value_id.in_(select(closure)),
                    values.c.kind == "entity",
                )
                .union(select(root_fact.c.subject_id))
            )
            return select(relation).where(
                self.scope(relation),
                or_(
                    relation.c.left_entity_id.in_(entities),
                    relation.c.right_entity_id.in_(entities),
                ),
            ), relation.c.exclusion_id
        if collection == "source_reports":
            source, observation = table("data.evidence_source"), table("kb.observation")
            evidence_ids = select(oe.c.evidence_id).where(
                self.scope(oe), oe.c.occurrence_id.in_(occurrences)
            )
            source_ids = select(source.c.observation_id).where(
                self.scope(source), source.c.evidence_id.in_(evidence_ids)
            )
            return (
                select(
                    observation.c.id.label("observation_id"),
                    observation.c.observation_key,
                    observation.c.task_id,
                    observation.c.payload_definition,
                    observation.c.kind,
                ).where(observation.c.id.in_(source_ids)),
                observation.c.observation_key,
            )
        raise SemanticRefusal("unsupported evidence inventory collection")

    def inventory(
        self,
        fact_id,
        collection,
        *,
        continuation=None,
        after_identity=None,
        limit=64,
        max_bytes=1024 * 1024,
        query_binding=None,
        selection=None,
    ):
        """Select identity rows before hydration; reports contain references, never bodies."""
        from pydantic import TypeAdapter

        if (
            type(limit) is not int
            or not 1 <= limit <= 1000
            or type(max_bytes) is not int
            or not 1 <= max_bytes <= 8 * 1024 * 1024
        ):
            raise SemanticRefusal("inventory limits exceed the supported range")
        named_binding = self._detail_query_binding(query_binding)
        selected = self._detail_selection(selection)
        f = table("data.fact")
        if (
            self.connection.execute(
                select(f.c.fact_id).where(self.scope(f), f.c.fact_id == fact_id)
            ).scalar_one_or_none()
            is None
        ):
            raise KeyError(fact_id)
        identity = {
            "inventory_version": 2,
            "release": self.binding.release_id,
            "realization": self.binding.realization_id,
            "revision": self.binding.data_revision,
            "run": self.completed_run_id,
            "cut": self.completed_cut_id,
            "root": fact_id,
            "query_binding": named_binding,
            "selection": selected,
            "collection": collection,
            "limit": limit,
            "max_bytes": max_bytes,
            "start_after": after_identity,
        }
        after = after_identity
        if after is not None and not isinstance(after, str):
            raise InvalidContinuation("invalid inventory identity cursor")
        if continuation is not None:
            try:
                if len(continuation.encode("utf-8")) > 8192:
                    raise ValueError("oversized token")
                body = json.loads(base64.b64decode(continuation, altchars=b"-_", validate=True))
                if set(body) != {*identity, "after"} or not isinstance(body["after"], str):
                    raise ValueError("invalid inventory cursor")
                if canonical_bytes({k: body[k] for k in identity}) != canonical_bytes(identity):
                    raise WrongBinding("inventory continuation differs from the requested binding")
                after = body["after"]
            except (ValueError, TypeError) as error:
                if isinstance(error, WrongBinding):
                    raise
                raise InvalidContinuation("invalid inventory continuation") from error
        stmt, key = self._inventory_statement(fact_id, collection)
        if after is not None:
            stmt = stmt.where(key.collate("C") > after)
        # Transfer identities and scalar lengths before hydrating any metadata row.
        # Raw scalar UTF-8 lengths are a lower bound on their complete JSON encoding.
        scalar_bytes = sum(
            (
                func.coalesce(func.octet_length(column.cast(Text)), 0)
                for column in stmt.selected_columns
            ),
            literal(0),
        )
        selected = (
            self.connection.execute(
                stmt.with_only_columns(
                    key.label("inventory_identity"),
                    scalar_bytes.label("scalar_bytes"),
                    maintain_column_froms=True,
                )
                .order_by(key.collate("C"))
                .limit(limit + 1)
            )
            .mappings()
            .all()
        )
        if any(row["scalar_bytes"] > max_bytes for row in selected[:limit]):
            raise ReadLimit("a complete inventory item exceeds max_bytes", reason="oversized_item")
        if sum(row["scalar_bytes"] for row in selected[:limit]) > max_bytes:
            raise ReadLimit(
                "inventory page exceeds max_bytes; request fewer rows", reason="work_limit"
            )
        rows = (
            self.connection.execute(
                stmt.where(key.in_([row["inventory_identity"] for row in selected[:limit]]))
                .order_by(key.collate("C"))
                .limit(limit)
            )
            .mappings()
            .all()
        )
        more = len(selected) > limit
        items: tuple[dict[str, Any], ...] = tuple(
            {str(k): v for k, v in row.items() if k not in {"release_id", "realization_id"}}
            for row in rows[:limit]
        )
        if collection == "evidence":
            custody = self._source_custody(tuple(row["evidence_id"] for row in items))
            items = tuple({**row, "source": custody.get(row["evidence_id"])} for row in items)
        # Each item is encoded once. The final envelope is checked after admission.
        encoded = [
            canonical_bytes(TypeAdapter(dict[str, Any]).dump_python(item, mode="json"))
            for item in items
        ]
        if any(len(item) > max_bytes for item in encoded):
            raise ReadLimit("a complete inventory item exceeds max_bytes", reason="oversized_item")
        if sum(map(len, encoded)) > max_bytes:
            raise ReadLimit(
                "inventory page exceeds max_bytes; request fewer rows", reason="work_limit"
            )
        token = None
        if more:
            token = base64.urlsafe_b64encode(
                canonical_bytes({**identity, "after": rows[-1][key.name]})
            ).decode("ascii")
            if len(token.encode("ascii")) > 8192:
                raise ReadLimit(
                    "inventory continuation exceeds 8192 bytes", reason="oversized_item"
                )
        page = InventoryPage(
            binding=self.binding,
            run_id=self.completed_run_id,
            cut_id=self.completed_cut_id,
            root=fact_id,
            collection=collection,
            query_binding=query_binding,
            selection=selection,
            items=items,
            population_complete=not more,
            next_page_token=token,
        )
        if len(canonical_bytes(page.model_dump(mode="json"))) > max_bytes:
            raise ReadLimit(
                "complete inventory envelope exceeds max_bytes", reason="oversized_item"
            )
        return page

    def source_report(
        self, fact_id, observation_key, *, max_bytes=1024 * 1024, query_binding=None, selection=None
    ):
        """Explicit immutable report read; a wrong root cannot select another report."""
        self._detail_query_binding(query_binding)
        self._detail_selection(selection)
        if type(max_bytes) is not int or not 1 <= max_bytes <= 8 * 1024 * 1024:
            raise SemanticRefusal("source report byte limit exceeds the supported range")
        stmt, _ = self._inventory_statement(fact_id, "source_reports")
        observation = table("kb.observation")
        owned = stmt.where(observation.c.observation_key == observation_key).subquery()
        row = (
            self.connection.execute(
                select(
                    observation.c.id, observation.c.observation_key, observation.c.payload
                ).where(
                    observation.c.id.in_(select(owned.c.observation_id)),
                    func.octet_length(observation.c.payload.cast(Text)) <= max_bytes * 2,
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            if self.connection.execute(select(owned.c.observation_id)).first() is not None:
                raise ReadLimit("source report exceeds max_bytes", reason="oversized_item")
            raise WrongBinding("source report is unavailable under this fact and binding")
        report = SourceObservationReport(
            binding=self.binding,
            run_id=self.completed_run_id,
            cut_id=self.completed_cut_id,
            root_fact_id=fact_id,
            query_binding=query_binding,
            selection=selection,
            observation_id=row["id"],
            observation_key=row["observation_key"],
            payload=row["payload"],
        )
        if len(canonical_bytes(report.model_dump(mode="json"))) > max_bytes:
            raise ReadLimit(
                "complete source report envelope exceeds max_bytes", reason="oversized_item"
            )
        return report

    def identity_exclusions(self, entity_id: str | None = None) -> tuple[IdentityExclusion, ...]:
        """Source-backed identity constraints from this session's exact snapshot.

        Filtering selects constraints touching the entity, not one side of their required
        endpoint/evidence closure. Separate source declarations of one pair remain separate.
        """
        return self._identity_exclusions(None if entity_id is None else (entity_id,))

    def identity_exclusion_graph(self, entity_id: str | None = None) -> QualifiedGraphProjection:
        """Qualified validation projection with the entire selected constraint closure."""
        from .ontology import (
            GraphProjectionBinding,
            QualifiedGraphProjection,
            QualifiedGraphReference,
        )

        records, nodes = [], {}
        for row in self.identity_exclusions(entity_id):
            records.append(
                {
                    "id": row.exclusion_id,
                    "left": QualifiedGraphReference(row.left.entity.entity_id),
                    "right": QualifiedGraphReference(row.right.entity.entity_id),
                    "left_source": {"kind": row.left.kind, "target": row.left.target},
                    "right_source": {"kind": row.right.kind, "target": row.right.target},
                    "evidence": tuple(QualifiedGraphReference(e.evidence_id) for e in row.evidence),
                    "reason": row.reason,
                    "operation_id": row.operation_id,
                    "operation_version": row.operation_version,
                    "observation_key": row.observation_key,
                    "local_id": row.local_id,
                }
            )
            for endpoint in (row.left, row.right):
                nodes[endpoint.entity.entity_id] = {
                    "kind": "entity",
                    "memberships": tuple(
                        m.model_dump(mode="python") for m in endpoint.entity.memberships
                    ),
                    "input_supports": tuple(
                        s.model_dump(mode="python") for s in endpoint.input_supports
                    ),
                }
            for evidence in row.evidence:
                nodes[evidence.evidence_id] = {
                    "kind": "evidence",
                    "source_uri": evidence.source_uri,
                    "locator": evidence.locator,
                    "provider": evidence.provider,
                    "operation_version": evidence.operation_version,
                    "source": evidence.source.model_dump(mode="python")
                    if evidence.source is not None
                    else None,
                }
        transaction = self.connection.get_transaction()
        return QualifiedGraphProjection(
            self.binding.release_id,
            self.binding.realization_id,
            self.binding.data_revision,
            "qualified-identity-exclusions",
            (),
            nodes,
            {},
            tuple(records),
            contract_binding=GraphProjectionBinding.from_release(self.prepared),
            source_universe=tuple(row["id"] for row in records),
            snapshot_guard=lambda: (
                transaction is not None
                and transaction.is_active
                and not self.connection.closed
                and self.connection.get_transaction() is transaction
            ),
        )

    def _identity_exclusions(
        self, entity_ids: tuple[str, ...] | Select | CompoundSelect | None
    ) -> tuple[IdentityExclusion, ...]:
        if isinstance(entity_ids, tuple) and not entity_ids:
            return ()
        relation, observation = table("data.identity_exclusion"), table("kb.observation")
        stmt = (
            select(relation, observation.c.observation_key)
            .join(
                observation,
                and_(
                    observation.c.release_id == relation.c.release_id,
                    observation.c.id == relation.c.observation_id,
                ),
            )
            .where(_scope(self.binding, relation))
        )
        if entity_ids is not None:
            stmt = stmt.where(
                relation.c.left_entity_id.in_(entity_ids)
                | relation.c.right_entity_id.in_(entity_ids)
            )
        rows = self.connection.execute(stmt.order_by(relation.c.exclusion_id)).mappings().all()
        if not rows:
            return ()
        entities = self._entities(
            {row[key] for row in rows for key in ("left_entity_id", "right_entity_id")}
        )
        inputs = table("data.entity_input")
        input_supports: dict[str, list[InputEntitySupport]] = defaultdict(list)
        for row in self.connection.execute(
            select(inputs)
            .where(_scope(self.binding, inputs), inputs.c.entity_id.in_(entities))
            .order_by(
                inputs.c.entity_id,
                inputs.c.input_realization_id,
                inputs.c.input_data_revision,
                inputs.c.input_entity_id,
            )
        ).mappings():
            input_supports[row["entity_id"]].append(
                InputEntitySupport(**{key: row[key] for key in InputEntitySupport.model_fields})
            )
        link, evidence = table("data.identity_exclusion_evidence"), table("data.evidence")
        evidence_rows = (
            self.connection.execute(
                select(link.c.exclusion_id, evidence)
                .join(
                    evidence,
                    and_(_same_scope(link, evidence), link.c.evidence_id == evidence.c.evidence_id),
                )
                .where(
                    _scope(self.binding, link),
                    link.c.exclusion_id.in_([row["exclusion_id"] for row in rows]),
                )
                .order_by(link.c.exclusion_id, link.c.evidence_id)
            )
            .mappings()
            .all()
        )
        custody = self._source_custody(tuple({row["evidence_id"] for row in evidence_rows}))
        by_exclusion: dict[str, list[Evidence]] = defaultdict(list)
        for row in evidence_rows:
            by_exclusion[row["exclusion_id"]].append(
                Evidence(
                    **{key: row[key] for key in Evidence.model_fields if key != "source"},
                    source=custody.get(row["evidence_id"]),
                )
            )
        return tuple(
            IdentityExclusion(
                exclusion_id=row["exclusion_id"],
                binding=self.binding,
                observation_id=row["observation_id"],
                observation_key=row["observation_key"],
                local_id=row["local_id"],
                reason=row["reason"],
                operation_id=row["operation_id"],
                operation_version=row["operation_version"],
                left=IdentityEndpointReference(
                    kind=row["left_kind"],
                    target=row["left_ref"],
                    entity=entities[row["left_entity_id"]],
                    input_supports=tuple(input_supports[row["left_entity_id"]]),
                ),
                right=IdentityEndpointReference(
                    kind=row["right_kind"],
                    target=row["right_ref"],
                    entity=entities[row["right_entity_id"]],
                    input_supports=tuple(input_supports[row["right_entity_id"]]),
                ),
                evidence=tuple(by_exclusion[row["exclusion_id"]]),
            )
            for row in rows
        )

    def measurements(self, metric: str | None = None) -> tuple[BaseModel, ...]:
        """Read FK-validated measurements and their exact source values from the final cut."""
        from .metrics import metric_definitions

        definitions = metric_definitions(self.prepared)
        run, cut, member, task, result, measurement, config, method = (
            table(name)
            for name in (
                "ops.run",
                "ops.input_cut",
                "ops.cut_task",
                "ops.task",
                "ops.task_result",
                "ops.measurement",
                "ops.method_config",
                "ops.method",
            )
        )
        stmt = (
            select(
                result.c.body,
                task.c.id.label("task_id"),
                task.c.run_id,
                task.c.invocation_key,
                task.c.input_hash,
                task.c.unit_key,
                measurement.c.id.label("measurement_id"),
                measurement.c.source_position,
                measurement.c.metric,
                measurement.c.scope_type,
                measurement.c.scope_id,
                measurement.c.scope_key,
                method.c.name.label("method"),
                method.c.version.label("operation_version"),
                config.c.config_hash.label("configuration_hash"),
            )
            .select_from(
                run.join(cut, cut.c.run_id == run.c.id)
                .join(member, member.c.cut_id == cut.c.id)
                .join(task, task.c.id == member.c.origin_task_id)
                .join(result, result.c.task_id == task.c.id)
                .join(measurement, measurement.c.task_id == task.c.id)
                .join(config, config.c.id == task.c.method_config_id)
                .join(method, method.c.id == config.c.method_id)
            )
            .where(
                run.c.release_id == self.binding.release_id,
                run.c.result_realization_id == self.binding.realization_id,
                cut.c.final.is_(True),
            )
            .distinct()
            .order_by(task.c.id, measurement.c.source_position)
        )
        if metric is not None:
            stmt = stmt.where(measurement.c.metric == metric)
        records = []
        for row in self.connection.execute(stmt).mappings():
            position = row["source_position"]
            source_items = row["body"].get("measurements", ())
            if type(position) is not int or not 0 <= position < len(source_items):
                raise ValueError("measurement lacks an exact source position")
            source = source_items[position]
            if any(
                source.get(key) != row[key]
                for key in ("metric", "scope_type", "scope_id", "scope_key")
            ):
                raise ValueError("measurement differs from its protected source position")
            definition = definitions.get(row["metric"])
            if definition is None:
                raise ValueError("measurement names an unresolved metric")
            subject = {"kind": row["scope_type"]}
            for name in ("scope_id", "scope_key"):
                if row[name] is not None:
                    subject[name] = row[name]
            if subject["kind"] == "run" and "scope_id" not in subject:
                subject["scope_id"] = row["run_id"]
            producer = {
                name: row[name]
                for name in (
                    "invocation_key",
                    "method",
                    "operation_version",
                    "configuration_hash",
                    "input_hash",
                    "unit_key",
                    "run_id",
                    "task_id",
                )
            }
            producer["release_id"] = self.binding.release_id
            records.append(
                self.prepared.validate_json(
                    "SourceBoundMeasurement",
                    json.dumps(
                        {
                            "source_position": position,
                            "metric": definition,
                            "subject": subject,
                            "producer": producer,
                            "value": source["value"],
                            "detail": source["detail"],
                        }
                    ),
                )
            )
        return tuple(records)

    def _occurrence_contexts(
        self, occurrence_ids: tuple[str, ...]
    ) -> tuple[dict[str, OccurrenceContext], dict[str, tuple[CitationRole, ...]]]:
        if not occurrence_ids:
            return {}, {}
        context, roles = table("data.occurrence_context"), table("data.occurrence_evidence_role")
        context_stmt = select(context).where(
            self.scope(context), context.c.occurrence_id.in_(occurrence_ids)
        )
        role_stmt = (
            select(roles)
            .where(self.scope(roles), roles.c.occurrence_id.in_(occurrence_ids))
            .order_by(roles.c.occurrence_id, roles.c.evidence_id)
        )
        self._admit_hydration(context_stmt, role_stmt)
        context_rows = self.connection.execute(context_stmt.limit(100001)).mappings().all()
        role_rows = self.connection.execute(role_stmt.limit(100001)).mappings().all()
        if max(len(context_rows), len(role_rows)) > 100000:
            raise ReadLimit(
                "occurrence context/citation reference budget exhausted", reason="work_limit"
            )
        contexts = {
            row["occurrence_id"]: OccurrenceContext(
                statement_entity_id=row["statement_entity_id"], statement_role=row["statement_role"]
            )
            for row in context_rows
        }
        by_occurrence: dict[str, list[CitationRole]] = defaultdict(list)
        for row in role_rows:
            by_occurrence[row["occurrence_id"]].append(
                CitationRole(evidence_id=row["evidence_id"], role=row["role"])
            )
        return contexts, {key: tuple(value) for key, value in by_occurrence.items()}

    def _source_custody(self, evidence_ids: tuple[str, ...]) -> dict[str, SourceCustody]:
        source, observation, task, inputs = (
            table(name)
            for name in (
                "data.evidence_source",
                "kb.observation",
                "ops.task",
                "kb.observation_input",
            )
        )
        custody_stmt = (
            select(
                source.c.evidence_id,
                source.c.rendition_id,
                source.c.span_id,
                source.c.source_view_id,
                source.c.native_address,
                observation.c.id,
                observation.c.observation_key,
                observation.c.task_id,
                observation.c.payload_definition,
                observation.c.kind,
                task.c.run_id,
            )
            .select_from(
                source.join(observation, source.c.observation_id == observation.c.id).join(
                    task, task.c.id == observation.c.task_id
                )
            )
            .where(_scope(self.binding, source), source.c.evidence_id.in_(evidence_ids))
        )
        self._admit_hydration(custody_stmt)
        receipts = self.connection.execute(custody_stmt).mappings().all()

        dependencies: dict[int, list[str]] = defaultdict(list)
        input_stmt = (
            select(inputs)
            .where(inputs.c.observation_id.in_([row["id"] for row in receipts]))
            .order_by(inputs.c.position)
        )
        self._admit_hydration(input_stmt)
        input_rows = self.connection.execute(input_stmt.limit(100001)).mappings().all()
        if len(input_rows) > 100000:
            raise ReadLimit("source custody input reference budget exhausted", reason="work_limit")
        for row in input_rows:
            dependencies[row["observation_id"]].append(row["source_observation_key"])
        return {
            row["evidence_id"]: SourceCustody(
                observation_id=row["id"],
                observation_key=row["observation_key"],
                task_id=row["task_id"],
                run_id=row["run_id"],
                rendition_id=row["rendition_id"],
                span_id=row["span_id"],
                source_view_id=row["source_view_id"],
                native_address=row["native_address"],
                payload_definition=row["payload_definition"],
                kind=row["kind"],
                input_observation_keys=tuple(dependencies[row["id"]]),
            )
            for row in receipts
        }

    def qualification(
        self, value_id: str, decoded: dict[str, Any], nodes: tuple[ValueNode, ...]
    ) -> Any:
        """Validate the explicit archived subtype carried by the stored qualification node."""
        node = next(node for node in nodes if node.value_id == value_id)
        definition = next(
            (
                definition
                for definition in self.prepared.definitions
                if definition.name == node.datatype or definition.iri == node.datatype
            ),
            None,
        )
        if definition is None:
            raise WrongRelease("qualification datatype is absent from the bound release")
        self.prepared.qualification_definition(definition.name)
        return self.prepared.validate_python(definition.name, decoded[value_id])

    def query(self, spec: QuerySpec, *, continuation: str | None = None) -> QueryResult:
        cls, prop = self._property(spec)
        after = self._after(spec, continuation)
        rows = self.connection.execute(self._selection(spec, after)).mappings().all()
        more, rows = len(rows) > spec.page_size, rows[: spec.page_size]
        output, nodes = self.hydrate_rows(rows, definition=cls)
        requirement = CoverageRequirement(
            prop.iri,
            frozenset({spec.coverage_scope}) if spec.coverage_scope != "*" else frozenset(),
        )
        summary = self.coverage_summary(requirement)
        selection = AnswerSelection(
            parameter_digest=self._fingerprint(spec), projection=spec.projection
        )
        detail = self.coverage_details(prop.iri, requirement.members | {"*"}, selection=selection)
        coverage = tuple(Coverage(**row) for row in detail.items)
        complete_coverage = summary.state == "established"
        token = None
        if more:
            token = self._token(
                spec, rows[-1]["occurrence_id" if spec.projection == "occurrence" else "fact_id"]
            )
        result = QueryResult(
            binding=self.binding,
            selection=selection,
            run_id=self.completed_run_id,
            cut_id=self.completed_cut_id,
            projection=spec.projection,
            rows=output,
            values=nodes,
            coverage=coverage,
            coverage_summary=summary,
            coverage_detail=detail,
            knowledge=(
                "observed"
                if output
                else "absent"
                if complete_coverage and after is None
                else "unknown"
            ),
            continuation=token,
            complete=not more,
        )
        if len(canonical_bytes(result.model_dump(mode="json"))) > spec.max_bytes:
            raise ReadLimit(
                "complete primitive query envelope exceeds max_bytes; reduce page_size",
                reason="oversized_item" if len(output) <= 1 else "work_limit",
            )
        return result

    def explain(
        self, fact_id: str, *, limit=64, max_bytes=1024 * 1024, query_binding=None, selection=None
    ) -> Explanation:
        """Bounded inventories under one snapshot; source report bodies are explicit reads."""
        pages = {
            name: self.inventory(
                fact_id,
                name,
                limit=limit,
                max_bytes=max_bytes,
                query_binding=query_binding,
                selection=selection,
            )
            for name in (
                "supports",
                "occurrence_contexts",
                "citation_roles",
                "evidence",
                "assessments",
                "derivations",
                "source_reports",
                "support_evidence",
                "derivation_premises",
                "alternatives",
                "alternative_members",
                "input_supports",
                "identity_exclusions",
                "identity_exclusion_evidence",
                "establishments",
            )
        }
        # The inventory is the authoritative detail product: retaining the old populated
        # fields would silently imply complete nested evidence/premise populations.
        result = Explanation(
            binding=self.binding,
            run_id=self.completed_run_id,
            cut_id=self.completed_cut_id,
            fact_id=fact_id,
            standing=self.fact_standing({fact_id})[fact_id],
            query_binding=query_binding,
            selection=selection,
            inventories=pages,
        )
        if len(canonical_bytes(result.model_dump(mode="json"))) > max_bytes:
            raise ReadLimit(
                "complete explanation envelope exceeds max_bytes; request inventory pages",
                reason="oversized_item",
            )
        return result
