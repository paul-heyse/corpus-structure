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

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    PublicationBatch,
    SelectionRow,
    publish_batch,
)
from corpus_structure.semantic.query import QuerySpec, StaleSnapshot, WrongRelease, read_session
from semantic.query_support import (
    PREFIX as PREFIX,
)
from semantic.query_support import (
    Z as Z,
)
from semantic.query_support import (
    archive as archive,
)
from semantic.query_support import (
    candidate as candidate,
)
from semantic.query_support import (
    seed as seed,
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
    commit_db_engine, commit_writer_engine, commit_reader_engine
):
    prepared = seed(commit_db_engine)
    batch = candidate(prepared)
    assert publish_batch(commit_writer_engine, batch).data_revision == 1
    with read_session(commit_reader_engine, Z) as session:
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
    with pytest.raises(WrongRelease), read_session(commit_reader_engine, Z, "release:wrong"):
        pytest.fail("wrong selector admitted")


def test_snapshot_continuation_pointer_change_and_revision_refusal(
    commit_db_engine, commit_writer_engine, commit_reader_engine
):
    prepared = seed(commit_db_engine)
    batch = candidate(prepared)
    publish_batch(commit_writer_engine, batch)
    newer = archive(commit_db_engine, b"\n# a different immutable semantic release\n")
    with read_session(commit_reader_engine, Z) as old:
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
        with commit_db_engine.begin() as conn:
            conn.execute(
                update(table("data.project")).values(
                    active_release_id=newer.release_id, generation=1
                )
            )
        with read_session(commit_reader_engine, Z) as fresh:
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
        assert publish_batch(commit_writer_engine, changed).data_revision == 2
        assert len(old.query(spec(old, projection="accepted")).rows) == 1
        assert len(old.inventory(batch.fact[0].fact_id, "supports").items) == 2
        assert len(old.query(request, continuation=first.continuation).rows) == 1
    with read_session(commit_reader_engine, Z) as current:
        assert current.binding.data_revision == 2
        with pytest.raises(StaleSnapshot):
            current.query(request, continuation=first.continuation)
        assert current.query(spec(current, projection="accepted")).rows == ()
        assert current.query(spec(current, projection="fact")).rows


def test_wrong_handles_refused_and_strict_outputs_preserve_records(
    commit_db_engine, commit_writer_engine, commit_reader_engine
):
    prepared = seed(commit_db_engine)
    publish_batch(commit_writer_engine, candidate(prepared))
    with read_session(commit_reader_engine, Z) as session:
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
    commit_db_engine, commit_writer_engine, commit_reader_engine, monkeypatch
):
    from corpus_structure.semantic import query

    prepared = seed(commit_db_engine)
    publish_batch(commit_writer_engine, candidate(prepared))
    loads = []
    loader = query.open_release

    def counted(conn, release_id):
        loads.append(release_id)
        return loader(conn, release_id)

    monkeypatch.setattr(query, "open_release", counted)
    statements = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    with read_session(commit_reader_engine, Z) as session:
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


def test_reader_transaction_refuses_writes(commit_db_engine, commit_reader_engine):
    seed(commit_db_engine)
    with read_session(commit_reader_engine, Z) as session, pytest.raises(DBAPIError):
        session.connection.execute(insert(table("data.project")).values(project_id="forbidden"))
