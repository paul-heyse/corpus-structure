"""Release-derived Core queries inside one actual PostgreSQL read snapshot.

Continuation starts a new snapshot and refuses a changed data revision. It does not
provide historical reads. SQL selections and strict output adaptation are one operation.
"""

from __future__ import annotations

import base64
import binascii
import json
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection, Engine, Select, and_, exists, literal, select
from sqlalchemy.sql import CompoundSelect
from sqlalchemy.sql.elements import ColumnElement

from .identity import canonical_bytes
from .metadata import table
from .outcomes import ScientificOutcome
from .releases import load_release
from .types import ClassDefinition, PreparedRelease, PropertyDefinition

if TYPE_CHECKING:
    from .ontology import QualifiedGraphProjection


class StaleSnapshot(ValueError):
    """The live realization revision no longer matches a continuation."""


class WrongRelease(ValueError):
    """A handle or selector belongs to another semantic release."""


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

    def __post_init__(self) -> None:
        if self.projection not in {"occurrence", "fact", "accepted"}:
            raise ValueError("unsupported projection")
        if not 1 <= self.page_size <= 10000:
            raise ValueError("page_size must be between 1 and 10000")
        if self.arithmetic_profile != "exact":
            raise ValueError("unsupported arithmetic profile")
        if type(self.subject_ids) is not tuple or any(type(s) is not str for s in self.subject_ids):
            raise TypeError("subject_ids must be a tuple of strings")


class _Envelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


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


class QueryRow(_Envelope):
    fact_id: str
    subject: EntityReference
    property_iri: str
    object_value_id: str
    object: Any
    qualification_value_id: str | None
    qualification: BaseModel | None
    occurrence_id: str | None = None
    source: str | None = None
    item: str | None = None
    context: OccurrenceContext | None = None
    citation_roles: tuple[CitationRole, ...] = ()


class Coverage(_Envelope):
    coverage_id: str
    family: str
    scope: str
    outcome: Literal["complete", "partial", "unanalysed", "failed"]
    reason: str | None
    source_outcome: Literal["complete", "partial", "unknown", "unsupported", "failed"] | None
    required_capability: str | None


class QueryResult(_Envelope):
    binding: SnapshotBinding
    projection: Literal["occurrence", "fact", "accepted"]
    rows: tuple[QueryRow, ...]
    values: tuple[ValueNode, ...]
    coverage: tuple[Coverage, ...]
    knowledge: Literal["observed", "unknown", "absent"]
    continuation: str | None
    complete: bool


class SourceCustody(_Envelope):
    observation_id: int
    observation_key: str
    task_id: int
    run_id: int
    rendition_id: int
    span_id: int | None
    payload_definition: str
    kind: str
    input_observation_keys: tuple[str, ...]


class SourceObservationReport(_Envelope):
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


class Explanation(_Envelope):
    binding: SnapshotBinding
    fact_id: str
    supports: tuple[OccurrenceSupport, ...]
    evidence: tuple[Evidence, ...]
    derivations: tuple[Derivation, ...]
    input_supports: tuple[InputFactSupport, ...] = ()
    source_observations: tuple[SourceObservationReport, ...] = ()
    alternatives: tuple[AlternativeGroup, ...] = ()
    assessments: tuple[Assessment, ...] = ()
    coverage: tuple[Coverage, ...]
    identity_exclusions: tuple[IdentityExclusion, ...] = ()


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


@contextmanager
def read_session(
    store: Engine | _Store, realization_id: str, release_id: str | None = None
) -> Iterator[ReadSession]:
    """Own a fresh REPEATABLE READ, read-only connection, binding exactly once.

    The optional release selector must equal the realization's immutable binding;
    the project's active pointer is deliberately not consulted.
    """
    engine = store if isinstance(store, Engine) else store.engine
    with (
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
        conn.begin(),
    ):
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        realization = table("data.realization")
        row = conn.execute(
            select(realization.c.release_id, realization.c.data_revision).where(
                realization.c.realization_id == realization_id
            )
        ).one_or_none()
        if row is None:
            raise KeyError(realization_id)
        if release_id is not None and row.release_id != release_id:
            raise WrongRelease("release selector differs from realization binding")
        binding = SnapshotBinding(row.release_id, realization_id, row.data_revision, str(uuid4()))
        yield ReadSession(conn, binding, load_release(conn, binding.release_id))


@dataclass(frozen=True)
class ReadSession:
    """A scoped snapshot owner. Use only within ``read_session``."""

    connection: Connection
    binding: SnapshotBinding
    prepared: PreparedRelease
    _property_adapters: dict[tuple[str, str], Any] = field(
        default_factory=dict, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.binding.release_id != self.prepared.release_id:
            raise WrongRelease("prepared release differs from snapshot binding")

    def class_handle(self, name_or_iri: str) -> ClassHandle:
        definition = next(
            (d for d in self.prepared.definitions if name_or_iri in {d.name, d.iri}), None
        )
        if definition is None:
            raise KeyError(name_or_iri)
        return ClassHandle(self.binding.release_id, definition.iri)

    def _class(self, handle: ClassHandle) -> ClassDefinition:
        if handle.release_id != self.binding.release_id:
            raise WrongRelease("class handle differs from snapshot release")
        definition = next((d for d in self.prepared.definitions if d.iri == handle.iri), None)
        if definition is None:
            raise KeyError(handle.iri)
        return definition

    def property_handle(self, cls: ClassHandle, name_or_iri: str) -> PropertyHandle:
        definition = self._class(cls)
        prop = next((p for p in definition.properties if name_or_iri in {p.name, p.iri}), None)
        if prop is None:
            raise KeyError(name_or_iri)
        return PropertyHandle(self.binding.release_id, cls.iri, prop.iri)

    def _property(self, spec: QuerySpec) -> tuple[ClassDefinition, PropertyDefinition]:
        cls = self._class(spec.class_handle)
        handle = spec.property_handle
        if handle.release_id != self.binding.release_id:
            raise WrongRelease("property handle differs from snapshot release")
        if handle.class_iri != cls.iri:
            raise ValueError("property handle belongs to another class")
        prop = next((p for p in cls.properties if p.iri == handle.iri), None)
        if prop is None:
            raise KeyError(handle.iri)
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
                    "format": "semantic-query-1",
                    "spec": asdict(spec),
                    "ordering": "identity:C:asc",
                }
            )
        ).hexdigest()

    def _after(self, spec: QuerySpec, token: str | None) -> str | None:
        if token is None:
            return None
        try:
            value = json.loads(base64.urlsafe_b64decode(token.encode()))
            if set(value) != {"release", "realization", "revision", "query", "after"}:
                raise ValueError("unexpected continuation fields")
            if value["release"] != self.binding.release_id:
                raise WrongRelease("continuation differs from snapshot release")
            if value["realization"] != self.binding.realization_id:
                raise ValueError("continuation differs from realization")
            if value["query"] != self._fingerprint(spec) or type(value["after"]) is not str:
                raise ValueError(
                    "continuation differs from query parameters/projection/order/profile"
                )
            if (
                type(value["revision"]) is not int
                or value["revision"] != self.binding.data_revision
            ):
                raise StaleSnapshot("data changed; restart query in a new snapshot")
            return value["after"]
        except (KeyError, json.JSONDecodeError, UnicodeError, binascii.Error, TypeError) as exc:
            raise ValueError("invalid continuation") from exc

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

    def _entities(self, ids: set[str]) -> dict[str, EntityReference]:
        if not ids:
            return {}
        e, m = table("data.entity"), table("data.membership")
        rows = self.connection.execute(
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
        ).mappings()
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
        for row in self.connection.execute(
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
        ).mappings():
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

    def _values(
        self, roots: set[str], subjects: set[str]
    ) -> tuple[dict[str, Any], tuple[ValueNode, ...], dict[str, EntityReference]]:
        """One recursive set traversal, two bulk reads; no per-row database queries."""
        v, r = table("data.typed_value"), table("data.value_role")
        if not roots:
            return {}, (), self._entities(subjects)
        closure = (
            select(v.c.value_id)
            .where(
                _scope(self.binding, v),
                v.c.value_id.in_(roots),
            )
            .cte("value_closure", recursive=True)
        )
        closure = closure.union(
            select(r.c.child_value_id)
            .join(
                closure,
                r.c.parent_value_id == closure.c.value_id,
            )
            .where(_scope(self.binding, r))
        )
        records = {
            row["value_id"]: row
            for row in self.connection.execute(
                select(v).where(
                    _scope(self.binding, v), v.c.value_id.in_(select(closure.c.value_id))
                )
            ).mappings()
        }
        roles: dict[str, list[Any]] = defaultdict(list)
        for row in self.connection.execute(
            select(r)
            .where(
                _scope(self.binding, r),
                r.c.parent_value_id.in_(records),
            )
            .order_by(r.c.role, r.c.position)
        ).mappings():
            roles[row["parent_value_id"]].append(row)
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

    def identity_exclusions(self, entity_id: str | None = None) -> tuple[IdentityExclusion, ...]:
        """Source-backed identity constraints from this session's exact snapshot.

        Filtering selects constraints touching the entity, not one side of their required
        endpoint/evidence closure. Separate source declarations of one pair remain separate.
        """
        return self._identity_exclusions(None if entity_id is None else (entity_id,))

    def identity_exclusion_graph(self, entity_id: str | None = None) -> QualifiedGraphProjection:
        """Qualified validation projection with the entire selected constraint closure."""
        from .ontology import QualifiedGraphProjection, QualifiedGraphReference

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
        return QualifiedGraphProjection(
            self.binding.release_id,
            self.binding.realization_id,
            self.binding.data_revision,
            "qualified-identity-exclusions",
            (),
            nodes,
            {},
            tuple(records),
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
        contexts = {
            row["occurrence_id"]: OccurrenceContext(
                statement_entity_id=row["statement_entity_id"], statement_role=row["statement_role"]
            )
            for row in self.connection.execute(
                select(context).where(
                    _scope(self.binding, context), context.c.occurrence_id.in_(occurrence_ids)
                )
            ).mappings()
        }
        by_occurrence: dict[str, list[CitationRole]] = defaultdict(list)
        for row in self.connection.execute(
            select(roles)
            .where(_scope(self.binding, roles), roles.c.occurrence_id.in_(occurrence_ids))
            .order_by(roles.c.occurrence_id, roles.c.evidence_id)
        ).mappings():
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
        receipts = (
            self.connection.execute(
                select(
                    source.c.evidence_id,
                    source.c.rendition_id,
                    source.c.span_id,
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
            .mappings()
            .all()
        )
        dependencies: dict[int, list[str]] = defaultdict(list)
        for row in self.connection.execute(
            select(inputs)
            .where(inputs.c.observation_id.in_([row["id"] for row in receipts]))
            .order_by(inputs.c.position)
        ).mappings():
            dependencies[row["observation_id"]].append(row["source_observation_key"])
        return {
            row["evidence_id"]: SourceCustody(
                observation_id=row["id"],
                observation_key=row["observation_key"],
                task_id=row["task_id"],
                run_id=row["run_id"],
                rendition_id=row["rendition_id"],
                span_id=row["span_id"],
                payload_definition=row["payload_definition"],
                kind=row["kind"],
                input_observation_keys=tuple(dependencies[row["id"]]),
            )
            for row in receipts
        }

    def qualification(self, value_id: str, decoded: dict[str, Any], nodes: tuple[ValueNode, ...]) -> Any:
        """Validate the explicit archived subtype carried by the stored qualification node."""
        node = next(node for node in nodes if node.value_id == value_id)
        definition = next((definition for definition in self.prepared.definitions
                           if definition.name == node.datatype or definition.iri == node.datatype), None)
        if definition is None:
            raise WrongRelease("qualification datatype is absent from the bound release")
        self.prepared.qualification_definition(definition.name)
        return self.prepared.validate_python(definition.name, decoded[value_id])

    def query(self, spec: QuerySpec, *, continuation: str | None = None) -> QueryResult:
        cls, prop = self._property(spec)
        after = self._after(spec, continuation)
        rows = self.connection.execute(self._selection(spec, after)).mappings().all()
        more, rows = len(rows) > spec.page_size, rows[: spec.page_size]
        roots = {
            row[key]
            for row in rows
            for key in ("object_value_id", "qualification_value_id")
            if row[key] is not None
        }
        decoded, nodes, entities = self._values(roots, {row["subject_id"] for row in rows})
        key = (cls.name, prop.name)
        if key not in self._property_adapters:
            self._property_adapters[key] = self.prepared.property_adapter(
                *key, item=prop.multivalued
            )
        adapter = self._property_adapters[key]
        contexts, citation_roles = self._occurrence_contexts(
            tuple(row["occurrence_id"] for row in rows if row.get("occurrence_id") is not None)
        )
        output = tuple(
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
                occurrence_id=row.get("occurrence_id"),
                source=row.get("source"),
                item=row.get("item"),
                context=contexts.get(row["occurrence_id"])
                if row.get("occurrence_id") is not None
                else None,
                citation_roles=citation_roles.get(row["occurrence_id"], ())
                if row.get("occurrence_id") is not None
                else (),
            )
            for row in rows
        )
        coverage = self.coverage(prop.iri, spec.coverage_scope)
        complete_coverage = bool(coverage) and all(c.outcome == "complete" for c in coverage)
        token = None
        if more:
            token = self._token(
                spec, rows[-1]["occurrence_id" if spec.projection == "occurrence" else "fact_id"]
            )
        return QueryResult(
            binding=self.binding,
            projection=spec.projection,
            rows=output,
            values=nodes,
            coverage=coverage,
            knowledge="observed" if output else "absent" if complete_coverage else "unknown",
            continuation=token,
            complete=not more,
        )

    def explain(self, fact_id: str) -> Explanation:
        """Support and derivation references from this session's same MVCC snapshot."""
        f = table("data.fact")
        fact = (
            self.connection.execute(
                select(f).where(_scope(self.binding, f), f.c.fact_id == fact_id)
            )
            .mappings()
            .one_or_none()
        )
        if fact is None:
            raise KeyError(fact_id)
        s, o, oe, e = (
            table("data." + n) for n in ("support", "occurrence", "occurrence_evidence", "evidence")
        )
        supports = (
            self.connection.execute(
                select(o)
                .select_from(
                    s.join(
                        o,
                        and_(
                            _same_scope(s, o),
                            s.c.occurrence_id == o.c.occurrence_id,
                        ),
                    )
                )
                .where(_scope(self.binding, s), s.c.fact_id == fact_id)
                .order_by(o.c.occurrence_id)
            )
            .mappings()
            .all()
        )
        contexts, citation_roles = self._occurrence_contexts(
            tuple(row["occurrence_id"] for row in supports)
        )
        links: dict[str, list[str]] = defaultdict(list)
        evidence: dict[str, Evidence] = {}
        for row in self.connection.execute(
            select(oe.c.occurrence_id, *e.c)
            .select_from(
                oe.join(
                    e,
                    and_(
                        _same_scope(oe, e),
                        oe.c.evidence_id == e.c.evidence_id,
                    ),
                )
            )
            .where(
                _scope(self.binding, oe),
                oe.c.occurrence_id.in_([r["occurrence_id"] for r in supports]),
            )
            .order_by(oe.c.evidence_id)
        ).mappings():
            links[row["occurrence_id"]].append(row["evidence_id"])
            evidence[row["evidence_id"]] = Evidence(
                **{k: row[k] for k in Evidence.model_fields if k != "source"}
            )
        custody = self._source_custody(tuple(evidence))
        observation = table("kb.observation")
        source_observations = tuple(
            SourceObservationReport(
                observation_id=row["id"],
                observation_key=row["observation_key"],
                payload=row["payload"],
            )
            for row in self.connection.execute(
                select(observation.c.id, observation.c.observation_key, observation.c.payload)
                .where(observation.c.id.in_({source.observation_id for source in custody.values()}))
                .order_by(observation.c.observation_key)
            ).mappings()
        )
        evidence = {
            key: value.model_copy(update={"source": custody.get(key)})
            for key, value in evidence.items()
        }
        d, p = table("data.derivation"), table("data.derivation_premise")
        derivations = (
            self.connection.execute(
                select(d)
                .where(
                    _scope(self.binding, d),
                    d.c.conclusion_fact_id == fact_id,
                )
                .order_by(d.c.derivation_id)
            )
            .mappings()
            .all()
        )
        premises: dict[str, list[str]] = defaultdict(list)
        for row in self.connection.execute(
            select(p)
            .where(
                _scope(self.binding, p),
                p.c.derivation_id.in_([r["derivation_id"] for r in derivations]),
            )
            .order_by(p.c.position)
        ).mappings():
            premises[row["derivation_id"]].append(row["premise_fact_id"])
        input_relation = table("data.fact_input")
        input_supports = tuple(
            InputFactSupport(**{name: row[name] for name in InputFactSupport.model_fields})
            for row in self.connection.execute(
                select(input_relation).where(
                    _scope(self.binding, input_relation), input_relation.c.fact_id == fact_id
                )
            ).mappings()
        )
        group, member = table("data.alternative_group"), table("data.alternative_member")
        groups = (
            self.connection.execute(
                select(group)
                .join(
                    member, and_(_same_scope(group, member), group.c.group_id == member.c.group_id)
                )
                .where(_scope(self.binding, group), member.c.fact_id == fact_id)
                .order_by(group.c.group_id)
            )
            .mappings()
            .all()
        )
        members: dict[str, list[str]] = defaultdict(list)
        for row in self.connection.execute(
            select(member)
            .where(
                _scope(self.binding, member), member.c.group_id.in_([g["group_id"] for g in groups])
            )
            .order_by(member.c.group_id, member.c.fact_id)
        ).mappings():
            members[row["group_id"]].append(row["fact_id"])
        assessment = table("data.assessment")
        assessments = tuple(
            Assessment(**{name: row[name] for name in Assessment.model_fields})
            for row in self.connection.execute(
                select(assessment)
                .where(
                    _scope(self.binding, assessment),
                    (assessment.c.fact_id == fact_id)
                    | assessment.c.occurrence_id.in_(
                        select(o.c.occurrence_id).where(
                            _scope(self.binding, o), o.c.fact_id == fact_id
                        )
                    ),
                )
                .order_by(assessment.c.assessment_id)
            ).mappings()
        )
        value_relation, roles = table("data.typed_value"), table("data.value_role")
        roots = (fact["object_value_id"], fact["qualification_value_id"])
        closure = (
            select(value_relation.c.value_id)
            .where(_scope(self.binding, value_relation), value_relation.c.value_id.in_(roots))
            .cte("exclusion_value_closure", recursive=True)
        )
        closure = closure.union(
            select(roles.c.child_value_id)
            .join(closure, roles.c.parent_value_id == closure.c.value_id)
            .where(_scope(self.binding, roles))
        )
        referenced_entities = (
            select(value_relation.c.entity_id)
            .where(
                _scope(self.binding, value_relation),
                value_relation.c.value_id.in_(select(closure)),
                value_relation.c.kind == "entity",
            )
            .union(select(literal(fact["subject_id"])))
        )
        return Explanation(
            identity_exclusions=self._identity_exclusions(referenced_entities),
            alternatives=tuple(
                AlternativeGroup(
                    **{
                        key: row[key]
                        for key in AlternativeGroup.model_fields
                        if key != "member_fact_ids"
                    },
                    member_fact_ids=tuple(members[row["group_id"]]),
                )
                for row in groups
            ),
            assessments=assessments,
            input_supports=input_supports,
            binding=self.binding,
            fact_id=fact_id,
            supports=tuple(
                OccurrenceSupport(
                    **{
                        k: row[k]
                        for k in OccurrenceSupport.model_fields
                        if k not in {"evidence_ids", "context", "citation_roles"}
                    },
                    evidence_ids=tuple(links[row["occurrence_id"]]),
                    context=contexts.get(row["occurrence_id"]),
                    citation_roles=citation_roles.get(row["occurrence_id"], ()),
                )
                for row in supports
            ),
            evidence=tuple(evidence.values()),
            source_observations=source_observations,
            derivations=tuple(
                Derivation(
                    derivation_id=row["derivation_id"],
                    rule=row["rule"],
                    rule_version=row["rule_version"],
                    premise_fact_ids=tuple(premises[row["derivation_id"]]),
                )
                for row in derivations
            ),
            coverage=self.coverage(),
        )
