"""Independent source expectations through native publication, Arrow and restricted reads."""

from dataclasses import replace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.arrow_publication import (
    ArrowPublicationBatch,
    publish_arrow_on_connection,
)
from corpus_structure.semantic.domain_operations import _cut_input, consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import publish_on_connection
from corpus_structure.semantic.query import QuerySpec, read_session

from .test_domain_operations import fixture, locate_proposal


def _source(admin, writer, path, monkeypatch, *, outside=False):
    # Author distinct per-occurrence context in the actual immutable source report. The
    # native writer and proposal adapter are unchanged and both validate these inputs.
    locate = locate_proposal

    def author(prepared, raw, frame):
        raw["entities"][0]["reference"] = {
            "description": "source-declared unresolved person",
            "source_uri": "external.html",
            "locator": "#person",
        }
        raw["claims"][0]["evidence"].append(
            {"sentence": "s1", "quote": "Alice is here.", "role": "supporting"}
        )
        raw["claims"][1]["statement_role"] = "premise"
        raw["claims"][1]["evidence"] = [
            {"sentence": "s1", "quote": "Alice is here.", "role": "condition"},
            {"sentence": "s1", "quote": "Alice is here.", "role": "primary"},
        ]
        if outside:
            raw["claims"][0].pop("statement")
            raw["claims"][0].pop("statement_role")
        return locate(prepared, raw, frame)

    monkeypatch.setattr(fixture.__module__ + ".locate_proposal", author)
    return fixture(admin, writer, path, duplicate=True)


def test_occurrences_keep_statement_and_citation_roles_in_query_explain(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch
):
    _prepared, run, cut = _source(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", monkeypatch
    )
    consolidate_cut(semantic_writer_engine, cut, "evaluated")
    with read_session(semantic_reader_engine, "evaluated") as session:
        cls = session.class_handle("Person")
        result = session.query(QuerySpec(cls, session.property_handle(cls, "name")))
        claims = [row for row in result.rows if row.item in {"claims/0", "claims/1"}]
        assert len(claims) == 2 and len({row.fact_id for row in claims}) == 1
        by_item = {row.item: row for row in claims}
        declarations = claims[0].subject.source_declarations
        assert len(declarations) == 1 and declarations[0].local_id == "person"
        assert declarations[0].observation_key == claims[0].source
        assert declarations[0].reference is not None
        assert declarations[0].reference.description == "source-declared unresolved person"
        assert declarations[0].reference.source_uri == "external.html"
        assert declarations[0].reference.locator == "#person"
        first_context, second_context = by_item["claims/0"].context, by_item["claims/1"].context
        assert first_context is not None and second_context is not None
        assert first_context.statement_role == "conclusion"
        assert second_context.statement_role == "premise"
        assert first_context.statement_entity_id != second_context.statement_entity_id
        assert {role.role for role in by_item["claims/0"].citation_roles} == {
            "primary",
            "supporting",
        }
        assert {role.role for role in by_item["claims/1"].citation_roles} == {
            "primary",
            "condition",
        }
        explanation = session.explain(claims[0].fact_id)
        supported = {support.item: support for support in explanation.supports}
        for item in ("claims/0", "claims/1"):
            assert supported[item].context == by_item[item].context
            assert supported[item].citation_roles == by_item[item].citation_roles
        assert explanation.evidence
        for evidence in explanation.evidence:
            assert evidence.source is not None
            assert evidence.source.run_id == run
            assert evidence.source.payload_definition == "AgentStoredBatch"
            assert evidence.source.observation_key == claims[0].source
            assert evidence.source.span_id is not None
        assert len(explanation.source_observations) == 1
        report = explanation.source_observations[0]
        assert report.observation_key == claims[0].source
        assert report.payload["statements"][0]["anchor"] == "page#one"
        assert report.payload["claims"][1]["statement_role"] == "premise"
        # The statement entity links retain their independently declared anchors/kinds.
        statement_class = session.class_handle("SourceStatement")
        statements = session.query(
            QuerySpec(statement_class, session.property_handle(statement_class, "locator"), "fact")
        )
        assert {row.subject.entity_id: row.object for row in statements.rows} == {
            first_context.statement_entity_id: "page#one",
            second_context.statement_entity_id: "page#two",
        }


@pytest.mark.parametrize(
    "damage, message",
    [
        ("role", "undeclared occurrence statement role"),
        ("statement", "occurrence statement context differs"),
        ("citation", "occurrence citation role differs"),
        ("omit_context", "occurrence statement context differs"),
        ("omit_citation_role", "occurrence citation role differs"),
        ("omit_citation_edge", "occurrence citation role differs"),
        ("source_local_id", "entity source local id is outside source declarations"),
        ("source_class", "entity source class is incompatible"),
    ],
)
def test_native_publication_refuses_fabricated_or_omitted_context(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch, damage, message
):
    _, _, cut = _source(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", monkeypatch
    )
    inputs = _cut_input(semantic_writer_engine, cut, "hostile")
    batch = inputs.batch
    if damage == "role":
        batch = replace(
            batch,
            occurrence_context=(
                replace(batch.occurrence_context[0], statement_role="invented"),
                *batch.occurrence_context[1:],
            ),
        )
    elif damage == "statement":
        contexts = batch.occurrence_context
        batch = replace(
            batch,
            occurrence_context=(
                replace(contexts[0], statement_entity_id=contexts[1].statement_entity_id),
                *contexts[1:],
            ),
        )
    elif damage == "citation":
        role = batch.occurrence_evidence_role[0]
        false = "definition" if role.role != "definition" else "supporting"
        batch = replace(
            batch,
            occurrence_evidence_role=(
                replace(role, role=false),
                *batch.occurrence_evidence_role[1:],
            ),
        )
    elif damage == "omit_context":
        batch = replace(batch, occurrence_context=())
    elif damage == "omit_citation_role":
        batch = replace(batch, occurrence_evidence_role=())
    elif damage == "omit_citation_edge":
        batch = replace(batch, occurrence_evidence=(), occurrence_evidence_role=())
    elif damage == "source_local_id":
        row = batch.entity_source[0]
        batch = replace(
            batch, entity_source=(replace(row, local_id="not-declared"), *batch.entity_source[1:])
        )
    else:
        row = batch.entity_source[0]
        statement = batch.occurrence_context[0].statement_entity_id
        assert statement is not None
        batch = replace(
            batch, entity_source=(replace(row, entity_id=statement), *batch.entity_source[1:])
        )
    with (
        pytest.raises(DBAPIError, match=message),
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(
            text("SELECT data.begin_evaluation(:cut,:out)"), {"cut": cut, "out": "hostile"}
        )
        publish_on_connection(conn, batch)
    with semantic_db_engine.connect() as conn:
        assert (
            conn.execute(
                select(table("data.realization").c.realization_id).where(
                    table("data.realization").c.realization_id == "hostile"
                )
            ).first()
            is None
        )


def test_arrow_native_transport_preserves_occurrence_context(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    _, _, cut = _source(
        semantic_db_engine, semantic_writer_engine, tmp_path / "source.html", monkeypatch
    )
    inputs = _cut_input(semantic_writer_engine, cut, "arrow")
    batch = inputs.batch
    assert batch.occurrence_context and batch.occurrence_evidence_role
    arrow = ArrowPublicationBatch.from_rows(batch)
    assert arrow.content == batch.content
    assert {row["statement_role"] for row in arrow.relations["occurrence_context"].to_pylist()} == {
        "conclusion",
        "premise",
    }
    # Source spans are resolved by the production final writer before publication; this
    # low-level transport test intentionally supplies no source links, retaining row roles.
    with (
        semantic_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        conn.execute(text("SELECT data.begin_evaluation(:cut,:out)"), {"cut": cut, "out": "arrow"})
        receipt = publish_arrow_on_connection(conn, arrow)
        assert receipt.data_revision == 1


def test_absent_statement_context_remains_unknown(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch
):
    _, _, cut = _source(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path / "source.html",
        monkeypatch,
        outside=True,
    )
    consolidate_cut(semantic_writer_engine, cut, "outside")
    with read_session(semantic_reader_engine, "outside") as session:
        cls = session.class_handle("Person")
        result = session.query(QuerySpec(cls, session.property_handle(cls, "name")))
        by_item = {row.item: row for row in result.rows}
        assert by_item["claims/0"].context is None
        assert by_item["claims/1"].context is not None
        assert by_item["claims/1"].context.statement_role == "premise"


def test_entity_source_reader_visibility(semantic_db_engine, semantic_reader_engine):
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text(
                    "SELECT has_table_privilege('corpus_sem_reader','data.entity_source','SELECT')"
                )
            )
            is True
        )
    with semantic_reader_engine.connect() as conn:
        assert conn.execute(select(table("data.entity_source"))).all() == []


def test_operational_entity_source_read_does_not_grant_direct_write(semantic_writer_engine):
    from sqlalchemy import insert

    with semantic_writer_engine.connect() as conn:
        assert conn.execute(select(table("data.entity_source"))).all() == []
    with (
        pytest.raises(DBAPIError, match="permission denied for table entity_source"),
        semantic_writer_engine.begin() as conn,
    ):
        conn.execute(
            insert(table("data.entity_source")).values(
                release_id="outside",
                realization_id="outside",
                entity_id="outside",
                observation_id=0,
                local_id="outside",
            )
        )
