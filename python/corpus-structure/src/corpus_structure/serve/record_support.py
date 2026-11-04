"""Pinned source-reading support ledger over existing fact/evidence authorities.

These facts describe released source-reading fields. They do not project the
scientific propositions quoted in those fields, their truth, support or opposition.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import Connection, and_, or_, select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import (
    Evidence,
    OccurrenceSupport,
    QueryRow,
    ReadLimit,
    ReadSession,
)
from corpus_structure.semantic.record_queries import CompletedRecordProjection, RecordReadLimit
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.serve.export import _json as export_json
from corpus_structure.serve.record_results import (
    RecordPage,
    RecordRequest,
    present_record_projection,
    read_record_result_projection,
)


class _Ledger(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ScientificSupportAvailability(_Ledger):
    availability: Literal["unmodeled"] = "unmodeled"
    reason: Literal["no_released_scientific_proposition_projection"] = (
        "no_released_scientific_proposition_projection"
    )


class RecordFieldSupport(_Ledger):
    role: str
    source_reading: dict[str, JsonValue]
    retained_alternatives: tuple[dict[str, JsonValue], ...]
    fact_availability: Literal[
        "published_selected_source_reading", "not_admitted", "no_selected_field_fact"
    ]
    asserted_field_fact: QueryRow | None = None
    supports: tuple[OccurrenceSupport, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    assessments: tuple[dict[str, JsonValue], ...] = ()


class RecordSupportEntry(_Ledger):
    record_id: str
    interpretation_id: str
    family: str
    admission: str
    source_polarity_modality: dict[str, dict[str, JsonValue]]
    fields: tuple[RecordFieldSupport, ...]


class RecordSupportPage(_Ledger):
    version: Literal["source-reading-support-1"] = "source-reading-support-1"
    page: RecordPage
    records: tuple[RecordSupportEntry, ...]
    scientific_support_opposition: ScientificSupportAvailability = ScientificSupportAvailability()
    bibliographic_lineage: Literal["unknown_beyond_stored_citation_roles_and_source_custody"] = (
        "unknown_beyond_stored_citation_roles_and_source_custody"
    )
    support_semantics: str = (
        "supports attach source occurrences and evidence to source-reading field facts; "
        "quoted predicate polarity/modality and metadata fact values do not establish "
        "scientific support or opposition; reading admission/calibration does not establish "
        "source reliability"
    )
    dependence: str = (
        "producer tasks, overlapping windows, occurrences and evidence links are retained "
        "with their identities; repeated links are not independent votes"
    )


def _transport(value):
    return json.loads(json.dumps(value, default=export_json, ensure_ascii=False, allow_nan=False))


class _SupportBudget:
    def __init__(self, conn, projection, request):
        self.conn = conn
        self.rows = request.max_rows - sum(len(rows) for rows in projection.rows.values())
        self.bytes = request.max_bytes - len(
            canonical_bytes(
                dict(
                    rows={
                        name: [asdict(row) for row in rows]
                        for name, rows in projection.rows.items()
                    },
                    coverage=[asdict(row) for row in projection.coverage],
                    report_source_view_ids=dict(projection.report_source_view_ids),
                )
            )
        )

    def consume(self, values):
        for value in values:
            self.rows -= 1
            self.bytes -= len(canonical_bytes(_transport(value))) + 1
            if self.rows < 0 or self.bytes < 0:
                raise RecordReadLimit("record support exceeds the requested transfer budget")

    def read(self, statement):
        if self.rows <= 0 or self.bytes <= 0:
            raise RecordReadLimit("record support transfer budget exhausted")
        try:
            PublishedReadBudget(self.rows, self.bytes).preflight(self.conn, statement)
        except ReadLimit as error:
            raise RecordReadLimit("record support exceeds the requested transfer budget") from error
        rows = [dict(row) for row in self.conn.execute(statement).mappings()]
        self.consume(rows)
        return rows


def read_support_inventory(
    session: ReadSession,
    projection: CompletedRecordProjection,
    page: RecordPage,
    request: RecordRequest,
) -> dict[str, dict[str, Any]]:
    """Hydrate one bounded set of selected field facts, never one explanation per field."""
    if (
        session.binding.release_id,
        session.binding.realization_id,
        session.binding.data_revision,
    ) != (
        projection.release_id,
        projection.realization_id,
        projection.data_revision,
    ) or session.completed_cut_id != projection.cut_id:
        raise SemanticRefusal("source-reading support differs from the pinned record snapshot")
    fact_ids = {
        assertion["fact_id"]
        for answer in page.records
        if len(answer.admission) == 1 and answer.admission[0]["decision"] == "accepted"
        for assertion in answer.assertions
    }
    if not fact_ids:
        return {}
    budget = _SupportBudget(session.connection, projection, request)
    fact, selected = table("data.fact"), table("data.selection")
    facts = budget.read(
        select(fact)
        .join(
            selected,
            and_(
                session.scope(selected),
                selected.c.fact_id == fact.c.fact_id,
            ),
        )
        .where(session.scope(fact), fact.c.fact_id.in_(fact_ids))
        .order_by(fact.c.fact_id)
    )
    if not facts:
        return {}
    fact_ids = {row["fact_id"] for row in facts}
    hydrated, values = session.hydrate_rows(facts)
    budget.consume([row.model_dump(mode="json") for row in hydrated])
    budget.consume([row.model_dump(mode="json") for row in values])
    support, occurrence = table("data.support"), table("data.occurrence")
    occurrences = budget.read(
        select(occurrence)
        .join(
            support,
            and_(
                session.scope(support),
                support.c.occurrence_id == occurrence.c.occurrence_id,
                support.c.fact_id == occurrence.c.fact_id,
            ),
        )
        .where(session.scope(occurrence), support.c.fact_id.in_(fact_ids))
        .order_by(occurrence.c.fact_id, occurrence.c.occurrence_id)
    )
    occurrence_ids = {row["occurrence_id"] for row in occurrences}
    link = table("data.occurrence_evidence")
    links = budget.read(
        select(link)
        .where(session.scope(link), link.c.occurrence_id.in_(occurrence_ids))
        .order_by(link.c.occurrence_id, link.c.evidence_id)
    )
    evidence_ids = {row["evidence_id"] for row in links}
    evidence = table("data.evidence")
    evidence_rows = budget.read(
        select(evidence)
        .where(session.scope(evidence), evidence.c.evidence_id.in_(evidence_ids))
        .order_by(evidence.c.evidence_id)
    )
    custody = session._source_custody(tuple(sorted(evidence_ids)))
    budget.consume([value.model_dump(mode="json") for value in custody.values()])
    contexts, citations = session.load_occurrence_contexts(tuple(sorted(occurrence_ids)))
    budget.consume([value.model_dump(mode="json") for value in contexts.values()])
    budget.consume(
        [value.model_dump(mode="json") for group in citations.values() for value in group]
    )
    assessment = table("data.assessment")
    assessments = budget.read(
        select(assessment)
        .where(
            session.scope(assessment),
            or_(
                assessment.c.fact_id.in_(fact_ids),
                assessment.c.occurrence_id.in_(occurrence_ids),
            ),
        )
        .order_by(assessment.c.assessment_id)
    )
    by_occurrence: dict[str, list[str]] = defaultdict(list)
    for row in links:
        by_occurrence[row["occurrence_id"]].append(row["evidence_id"])
    evidence_index = {
        row["evidence_id"]: Evidence(
            **{key: row[key] for key in Evidence.model_fields if key != "source"},
            source=custody.get(row["evidence_id"]),
        )
        for row in evidence_rows
    }
    supports: dict[str, list[OccurrenceSupport]] = defaultdict(list)
    for row in occurrences:
        supports[row["fact_id"]].append(
            OccurrenceSupport(
                **{
                    key: row[key]
                    for key in (
                        "occurrence_id",
                        "source",
                        "item",
                        "report_object_value_id",
                        "report_qualification_value_id",
                    )
                },
                evidence_ids=tuple(by_occurrence[row["occurrence_id"]]),
                context=contexts.get(row["occurrence_id"]),
                citation_roles=citations.get(row["occurrence_id"], ()),
            )
        )
    inventory = {}
    for row in hydrated:
        members = supports[row.fact_id]
        ids = {identity for member in members for identity in member.evidence_ids}
        occurrences_for_fact = {member.occurrence_id for member in members}
        inventory[row.fact_id] = dict(
            fact=row,
            supports=tuple(members),
            evidence=tuple(evidence_index[key] for key in sorted(ids)),
            assessments=tuple(
                _transport(
                    {
                        key: value
                        for key, value in assessment.items()
                        if key not in {"release_id", "realization_id"}
                    }
                )
                for assessment in assessments
                if assessment["fact_id"] == row.fact_id
                or assessment["occurrence_id"] in occurrences_for_fact
            ),
        )
    return inventory


def present_record_support(
    page: RecordPage, inventory: dict[str, dict[str, Any]], *, max_bytes: int
) -> RecordSupportPage:
    """Retain source-readings and alternatives separately from admitted field facts."""
    records = []
    for answer in page.records:
        if len(answer.admission) != 1:
            raise SemanticRefusal("source-reading support requires a unique native admission")
        standing = str(answer.admission[0]["decision"])
        assertions = {assertion["role"]: assertion for assertion in answer.assertions}
        fields = []
        qualifiers = {}
        raw_fields = answer.record["fields"]
        if not isinstance(raw_fields, list):
            raise SemanticRefusal("record support fields are not a released JSON array")
        for raw in raw_fields:
            if not isinstance(raw, dict):
                raise SemanticRefusal("record support field is not a released object")
            reading = {key: value for key, value in raw.items() if key != "alternatives"}
            role = str(raw["role"])
            if role in {"polarity", "modality"}:
                qualifiers[role] = reading
            assertion = assertions.get(role)
            fact_id = assertion.get("fact_id") if assertion else None
            if assertion and not isinstance(fact_id, str):
                raise SemanticRefusal("record support assertion has no fact identity")
            details = (
                inventory.get(fact_id, {})
                if standing == "accepted" and isinstance(fact_id, str)
                else {}
            )
            raw_alternatives = raw.get("alternatives", [])
            if not isinstance(raw_alternatives, list):
                raise SemanticRefusal("record support alternatives are not a released JSON array")
            alternatives = []
            for alternative in raw_alternatives:
                if not isinstance(alternative, dict):
                    raise SemanticRefusal("record support alternative is not a released object")
                alternatives.append(alternative)
            fields.append(
                RecordFieldSupport(
                    role=role,
                    source_reading=reading,
                    retained_alternatives=tuple(alternatives),
                    fact_availability="published_selected_source_reading"
                    if details
                    else "not_admitted"
                    if standing != "accepted"
                    else "no_selected_field_fact",
                    asserted_field_fact=details.get("fact"),
                    supports=details.get("supports", ()),
                    evidence=details.get("evidence", ()),
                    assessments=details.get("assessments", ()),
                )
            )
        records.append(
            RecordSupportEntry(
                record_id=str(answer.record["record_id"]),
                interpretation_id=str(answer.record["interpretation_id"]),
                family=str(answer.record["family"]),
                admission=standing,
                source_polarity_modality=qualifiers,
                fields=tuple(fields),
            )
        )
    result = RecordSupportPage(page=page, records=tuple(records))
    if len(result.model_dump_json().encode()) > max_bytes:
        raise RecordReadLimit(
            "source-reading support page exceeds response budget; narrow the selection"
        )
    return result


def serve_record_support(conn: Connection, request: RecordRequest) -> RecordSupportPage:
    projection = read_record_result_projection(conn, request)
    page = present_record_projection(projection, request)
    session = ReadSession(
        conn,
        projection.binding,
        projection.prepared,
        completed_run_id=projection.run_id,
        completed_cut_id=projection.cut_id,
    )
    inventory = read_support_inventory(session, projection, page, request)
    return present_record_support(page, inventory, max_bytes=request.page_bytes)
