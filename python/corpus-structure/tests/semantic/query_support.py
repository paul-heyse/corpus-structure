"""Shared controlled inputs and builders for query support."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import insert

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.identity import fact_key, occurrence_key
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    CoverageRow,
    EntityRow,
    EvidenceRow,
    FactRow,
    MembershipRow,
    MembershipSupportRow,
    OccurrenceEvidenceRow,
    OccurrenceRow,
    PublicationBatch,
    RoleRow,
    SelectionRow,
    SupportRow,
    ValueRow,
)
from corpus_structure.semantic.releases import persist_release

Z = "realization:query"


PREFIX = "https://example.org/sp04/"


def archive(engine, extra=b""):
    bundle = SourceBundle(
        "journey",
        (
            SourceArtifact(
                "journey",
                b"""id: https://example.org/sp04
name: query_journey
prefixes:
  ex: https://example.org/sp04/
default_prefix: ex
types:
  string:
    base: str
  decimal:
    base: Decimal
enums:
  Resolution:
    permissible_values:
      unresolved: {}
classes:
  Observatory:
    attributes:
      exact_signal:
        range: decimal
        multivalued: true
      points_to:
        range: DeclaredEndpoint
      absent_note:
        range: string
      readings:
        range: Reading
        inlined: true
  DeclaredEndpoint:
    attributes:
      resolution_status:
        range: Resolution
  Reading:
    attributes:
      number:
        range: decimal
        required: true
      unit:
        range: string
        required: true
      ordered_labels:
        range: string
        multivalued: true
      optional_note:
        range: string
  Qualification:
    attributes:
      modality:
        range: string
        required: true
      attribution:
        range: string
        annotations:
          cs:key_role: provenance
"""
                + extra,
            ),
        ),
    )
    from corpus_structure.semantic.composed import composed_dependencies

    deps = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, deps, profile)
    with engine.begin() as conn:
        persist_release(conn, bundle, deps, profile, prepared)
    return prepared


def seed(engine):
    prepared = archive(engine)
    with engine.begin() as conn:
        conn.execute(
            insert(table("data.project")).values(
                project_id="project:query", active_release_id=prepared.release_id
            )
        )
        conn.execute(
            insert(table("data.realization")).values(
                realization_id=Z, release_id=prepared.release_id, project_id="project:query"
            )
        )
    return prepared


def candidate(prepared):
    r = prepared.release_id
    p = PREFIX + "exact_signal"
    qualification = {"modality": "asserted"}
    signal = fact_key(r, Z, "observatory", p, Decimal("1.2300"), qualification)
    relation = fact_key(
        r, Z, "observatory", PREFIX + "points_to", "unresolved-endpoint", qualification
    )
    status = fact_key(
        r, Z, "unresolved-endpoint", PREFIX + "resolution_status", "unresolved", qualification
    )
    reading = {
        "number": Decimal("3.000"),
        "unit": "kelvin",
        "ordered_labels": ("second", "first", "second"),
    }
    reading_fact = fact_key(r, Z, "observatory", PREFIX + "readings", reading, qualification)
    o1, o2 = (
        occurrence_key(r, Z, "same-source", item) for item in ("repeated-item:1", "repeated-item:2")
    )
    return PublicationBatch(
        r,
        Z,
        "journey",
        entity=(EntityRow("observatory"), EntityRow("unresolved-endpoint")),
        membership=(
            MembershipRow("observatory", PREFIX + "Observatory", "source assertion"),
            MembershipRow("unresolved-endpoint", PREFIX + "DeclaredEndpoint", "declared reference"),
        ),
        typed_value=(
            ValueRow("exact", "decimal", decimal_lexical="1.2300"),
            ValueRow("report-one", "decimal", decimal_lexical="+001.23000"),
            ValueRow("report-two", "decimal", decimal_lexical="123e-2"),
            ValueRow("endpoint", "entity", entity_id="unresolved-endpoint"),
            ValueRow("unresolved", "string", text_value="unresolved"),
            ValueRow("q-one", "record", datatype=PREFIX + "Qualification"),
            ValueRow("q-two", "record", datatype=PREFIX + "Qualification"),
            ValueRow("modality", "string", text_value="asserted"),
            ValueRow("alice", "string", text_value="Alice"),
            ValueRow("bob", "string", text_value="Bob"),
            ValueRow("reading", "record", datatype=PREFIX + "Reading"),
            ValueRow("reading-number", "decimal", decimal_lexical="3.000"),
            ValueRow("unit", "string", text_value="kelvin"),
            ValueRow("labels", "sequence"),
            ValueRow("first", "string", text_value="first"),
            ValueRow("second", "string", text_value="second"),
            ValueRow("explicit-null", "null"),
        ),
        value_role=(
            RoleRow("q-one", "modality", 0, "modality"),
            RoleRow("q-one", "attribution", 0, "alice"),
            RoleRow("q-two", "modality", 0, "modality"),
            RoleRow("q-two", "attribution", 0, "bob"),
            RoleRow("reading", "number", 0, "reading-number"),
            RoleRow("reading", "unit", 0, "unit"),
            RoleRow("reading", "ordered_labels", 0, "labels"),
            RoleRow("labels", "item", 0, "second"),
            RoleRow("labels", "item", 1, "first"),
            RoleRow("labels", "item", 2, "second"),
        ),
        fact=(
            FactRow(signal, "observatory", p, "exact", "q-one"),
            FactRow(relation, "observatory", PREFIX + "points_to", "endpoint", "q-one"),
            FactRow(
                status, "unresolved-endpoint", PREFIX + "resolution_status", "unresolved", "q-one"
            ),
            FactRow(reading_fact, "observatory", PREFIX + "readings", "reading", "q-one"),
        ),
        occurrence=(
            OccurrenceRow(o1, signal, "same-source", "repeated-item:1", "report-one", "q-one"),
            OccurrenceRow(o2, signal, "same-source", "repeated-item:2", "report-two", "q-two"),
        ),
        support=(SupportRow(signal, o1), SupportRow(signal, o2)),
        selection=(
            SelectionRow(signal),
            SelectionRow(relation),
            SelectionRow(status),
            SelectionRow(reading_fact),
        ),
        evidence=(
            EvidenceRow("evidence-one", "urn:source", "line:1", "native-test", "1"),
            EvidenceRow("evidence-two", "urn:source", "line:2", "native-test", "1"),
        ),
        occurrence_evidence=(
            OccurrenceEvidenceRow(o1, "evidence-one"),
            OccurrenceEvidenceRow(o2, "evidence-two"),
        ),
        membership_support=(
            MembershipSupportRow("observatory", PREFIX + "Observatory", "evidence-one"),
            MembershipSupportRow(
                "unresolved-endpoint", PREFIX + "DeclaredEndpoint", "evidence-two"
            ),
        ),
        coverage=(
            CoverageRow("unknown-note", PREFIX + "absent_note", "*", "unanalysed", "not extracted"),
            CoverageRow("complete-signal", p, "*", "complete"),
        ),
    )
