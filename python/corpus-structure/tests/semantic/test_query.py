"""SP04 native archived release -> protected publication -> restricted snapshot reads.

Expected meanings/supports are authored independently of the query implementation.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from typing import Any, Literal

import pytest
from pydantic import ValidationError
from sqlalchemy import event, insert, select, text, update
from sqlalchemy.exc import DBAPIError

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
    publish_batch,
)
from corpus_structure.semantic.query import QuerySpec, StaleSnapshot, WrongRelease, read_session
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


def spec(
    session,
    name="exact_signal",
    projection: Literal["occurrence", "fact", "accepted"] = "occurrence",
    **kwargs,
):
    cls = session.class_handle("Observatory")
    return QuerySpec(cls, session.property_handle(cls, name), projection, **kwargs)


def test_archived_new_declarations_native_occurrence_fact_explain(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine
):
    prepared = seed(semantic_db_engine)
    batch = candidate(prepared)
    assert publish_batch(semantic_writer_engine, batch).data_revision == 1
    with read_session(semantic_reader_engine, Z) as session:
        assert session.connection.scalar(text("SELECT current_user")) == "corpus_sem_reader"
        assert session.connection.scalar(text("SHOW transaction_isolation")) == "repeatable read"
        assert session.connection.scalar(text("SHOW transaction_read_only")) == "on"
        occurrences = session.query(spec(session))
        # Equality uses semantic Decimal meaning, including lexical scale/exponent variants.
        fact_table = table("data.fact")
        for operand in ("1.23000", "123e-2", "+001.23"):
            matched = (
                session.connection.execute(
                    select(fact_table.c.fact_id).where(
                        session.scope(fact_table),
                        session.object_predicate(PREFIX + "exact_signal", operand),
                    )
                )
                .scalars()
                .all()
            )
            assert matched == [batch.fact[0].fact_id]
        assert {row.occurrence_id for row in occurrences.rows} == {
            o.occurrence_id for o in batch.occurrence
        }
        assert {row.source for row in occurrences.rows} == {"same-source"}
        assert {row.object for row in occurrences.rows} == {Decimal("1.23")}
        assert {
            row.qualification.model_dump()["attribution"]
            for row in occurrences.rows
            if row.qualification is not None
        } == {"Alice", "Bob"}
        assert {node.lexical for node in occurrences.values if node.kind == "decimal"} == {
            "+001.23000",
            "123e-2",
        }
        facts = session.query(spec(session, projection="fact"))
        accepted = session.query(spec(session, projection="accepted"))
        assert len(facts.rows) == len(accepted.rows) == 1
        assert facts.rows[0].object == Decimal("1.23")
        assert facts.rows[0].qualification is not None
        assert facts.rows[0].qualification.model_dump()["attribution"] == "Alice"
        assert facts.rows[0].occurrence_id is None
        assert facts.binding == accepted.binding == occurrences.binding == session.binding
        explanation = session.explain(batch.fact[0].fact_id)
        assert explanation.binding == session.binding
        links = explanation.inventories["support_evidence"].items
        assert {
            support["occurrence_id"]: tuple(
                link["evidence_id"]
                for link in links
                if link["occurrence_id"] == support["occurrence_id"]
            )
            for support in explanation.inventories["supports"].items
        } == {
            batch.occurrence[0].occurrence_id: ("evidence-one",),
            batch.occurrence[1].occurrence_id: ("evidence-two",),
        }
        assert {
            (e["evidence_id"], e["locator"]) for e in explanation.inventories["evidence"].items
        } == {
            ("evidence-one", "line:1"),
            ("evidence-two", "line:2"),
        }
        assert {
            s["report_qualification_value_id"] for s in explanation.inventories["supports"].items
        } == {"q-one", "q-two"}
        relation = session.query(spec(session, "points_to", "accepted"))
        assert relation.rows[0].object == "unresolved-endpoint"
        reference = next(node.entity for node in relation.values if node.kind == "entity")
        assert reference is not None and reference.entity_id == "unresolved-endpoint"
        endpoint = session.class_handle("DeclaredEndpoint")
        state = session.query(
            QuerySpec(endpoint, session.property_handle(endpoint, "resolution_status"), "accepted")
        )
        assert [(r.subject.entity_id, r.object) for r in state.rows] == [
            ("unresolved-endpoint", "unresolved")
        ]
        # Source assertions do not invent derivations from unrelated scalar premises.
        # Admitted proof/explanation integration is exercised by test_inference.py.
        assert session.inventory(batch.fact[1].fact_id, "derivations").items == ()
        empty = session.query(spec(session, "absent_note", "fact"))
        assert empty.rows == () and empty.knowledge == "unknown"
        assert empty.coverage[0].outcome == "unanalysed"
        with pytest.raises(FrozenInstanceError):
            mutable: Any = session.binding
            mutable.data_revision = 9
    with pytest.raises(WrongRelease), read_session(semantic_reader_engine, Z, "release:wrong"):
        pytest.fail("wrong selector admitted")


def test_snapshot_continuation_pointer_change_and_revision_refusal(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine
):
    prepared = seed(semantic_db_engine)
    batch = candidate(prepared)
    publish_batch(semantic_writer_engine, batch)
    newer = archive(semantic_db_engine, b"\n# a different immutable semantic release\n")
    with read_session(semantic_reader_engine, Z) as old:
        request = spec(old, page_size=1)
        first = old.query(request)
        assert first.continuation is not None and not first.complete
        import base64
        import json

        high = json.loads(base64.urlsafe_b64decode(first.continuation))
        high["after"] = "zzzzzzzzzz"
        token = base64.urlsafe_b64encode(json.dumps(high).encode()).decode()
        empty_page = old.query(request, continuation=token)
        assert empty_page.rows == () and empty_page.complete
        assert empty_page.coverage[0].outcome == "complete"
        assert empty_page.knowledge == "unknown"
        with semantic_db_engine.begin() as conn:
            conn.execute(
                update(table("data.project")).values(
                    active_release_id=newer.release_id, generation=1
                )
            )
        with read_session(semantic_reader_engine, Z) as fresh:
            assert fresh.binding.release_id == prepared.release_id
            second = fresh.query(request, continuation=first.continuation)
            assert second.complete and second.continuation is None
            assert {first.rows[0].occurrence_id, second.rows[0].occurrence_id} == {
                o.occurrence_id for o in batch.occurrence
            }
            assert fresh.binding.capture_id != old.binding.capture_id
            with pytest.raises(ValueError, match="parameters"):
                fresh.query(replace(request, projection="fact"), continuation=first.continuation)
            with pytest.raises(ValueError, match="parameters"):
                fresh.query(
                    replace(request, subject_ids=("other",)), continuation=first.continuation
                )
            for token in ("%ÿ", "abc", "e30=", "W10=", "AA=="):
                with pytest.raises(ValueError):
                    fresh.query(request, continuation=token)
        changed = PublicationBatch(
            prepared.release_id,
            Z,
            "deselect",
            selection=(SelectionRow(batch.fact[0].fact_id, False),),
        )
        assert publish_batch(semantic_writer_engine, changed).data_revision == 2
        assert len(old.query(spec(old, projection="accepted")).rows) == 1
        assert len(old.inventory(batch.fact[0].fact_id, "supports").items) == 2
        assert len(old.query(request, continuation=first.continuation).rows) == 1
    with read_session(semantic_reader_engine, Z) as current:
        assert current.binding.data_revision == 2
        with pytest.raises(StaleSnapshot):
            current.query(request, continuation=first.continuation)
        assert current.query(spec(current, projection="accepted")).rows == ()
        assert current.query(spec(current, projection="fact")).rows


def test_wrong_handles_refused_and_strict_outputs_preserve_records(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine
):
    prepared = seed(semantic_db_engine)
    publish_batch(semantic_writer_engine, candidate(prepared))
    with read_session(semantic_reader_engine, Z) as session:
        request = spec(session)
        with pytest.raises(WrongRelease):
            session.query(
                replace(request, class_handle=replace(request.class_handle, release_id="other"))
            )
        with pytest.raises(WrongRelease):
            session.query(
                replace(
                    request, property_handle=replace(request.property_handle, release_id="other")
                )
            )
        with pytest.raises(ValueError, match="another class"):
            session.query(
                replace(
                    request,
                    property_handle=replace(request.property_handle, class_iri=PREFIX + "Reading"),
                )
            )
        with pytest.raises(ValueError, match="unknown release name"):
            session.property_handle(request.class_handle, 'arbitrary" SQL identifier')
        result = session.query(spec(session, "readings", "accepted"))
        record = result.rows[0].object
        assert record.model_dump(exclude_unset=True) == {
            "number": Decimal("3.000"),
            "unit": "kelvin",
            "ordered_labels": ("second", "first", "second"),
        }
        assert "optional_note" not in record.model_fields_set
        assert [
            r.child_value_id
            for node in result.values
            if node.value_id == "labels"
            for r in node.roles
        ] == ["second", "first", "second"]
        decoded, nodes, _ = session._values({"explicit-null"}, set())
        assert decoded == {"explicit-null": None}
        assert nodes[0].kind == "null" and nodes[0].roles == ()
        # The output boundary is the prepared property's strict adapter, not a
        # permissive object/dict shell that drops undeclared fields/qualification.
        with pytest.raises(ValidationError):
            prepared.property_adapter("Observatory", "exact_signal", item=True).validate_python(
                "1.23", strict=True
            )
        with pytest.raises(ValidationError):
            prepared.validate_python(
                "Qualification", {"modality": "asserted", "silently_dropped": True}
            )


def test_release_loaded_once_and_recursive_values_batched(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, monkeypatch
):
    from corpus_structure.semantic import query

    prepared = seed(semantic_db_engine)
    publish_batch(semantic_writer_engine, candidate(prepared))
    loads = []
    loader = query.open_release

    def counted(conn, release_id):
        loads.append(release_id)
        return loader(conn, release_id)

    monkeypatch.setattr(query, "open_release", counted)
    statements = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    with read_session(semantic_reader_engine, Z) as session:
        event.listen(session.connection, "before_cursor_execute", observe)
        request = spec(session, "readings", "accepted")
        result = session.query(request)
        assert len(result.values) == 9
        assert len(statements) <= 32
        assert not any("WITH RECURSIVE" in statement for statement in statements)
        graph_reads = [
            statement
            for statement in statements
            if "FROM data.typed_value" in statement or "FROM data.value_role" in statement
        ]
        assert graph_reads and all("LIMIT" in statement for statement in graph_reads)
        session.query(spec(session))
        assert loads == [prepared.release_id]
    assert session.connection.closed


def test_reader_transaction_refuses_writes(semantic_db_engine, semantic_reader_engine):
    seed(semantic_db_engine)
    with read_session(semantic_reader_engine, Z) as session, pytest.raises(DBAPIError):
        session.connection.execute(insert(table("data.project")).values(project_id="forbidden"))
