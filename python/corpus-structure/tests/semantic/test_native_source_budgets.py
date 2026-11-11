"""Source ABI, continuation and pre-transfer admission controls (component scope)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import psycopg
import pytest
from pydantic import ValidationError
from sqlalchemy import literal, select

from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader, PublishedReadBudget
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import ReadLimit
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.serve import native_source


def request(**changes):
    return native_source.NativeSourceRequest(
        run_id=1, task_id=2, product_key="native", content_digest="a" * 64, **changes
    )


def test_v4_requires_explicit_row_byte_admission_and_refuses_old_meaning():
    selected = request()
    assert (selected.version, selected.limit, selected.max_rows, selected.max_bytes) == (
        4,
        100,
        10000,
        1048576,
    )
    for changes in (
        {"version": 3},
        {"max_bytes": 8388609},
        {"max_rows": 10001},
        {"max_bytes": True},
        {"max_rows": True},
    ):
        with pytest.raises(ValidationError):
            request(**changes)


def test_native_cursor_binds_byte_and_row_work_budgets_and_rejects_old_tokens():
    selected = request()
    token = native_source._source_cursor(selected, 17)
    assert native_source._source_position(selected.model_copy(update={"cursor": token})) == 17
    for changes in ({"max_bytes": 2048}, {"max_rows": 10}):
        with pytest.raises(InvalidContinuation):
            native_source._source_position(selected.model_copy(update={"cursor": token, **changes}))
    with pytest.raises(InvalidContinuation):
        native_source._source_position(selected.model_copy(update={"cursor": "e30="}))


@pytest.mark.parametrize(
    "summary,reason",
    [
        (dict(rows=3, bytes=30, largest=10), "work_limit"),
        (dict(rows=1, bytes=2049, largest=2049), "oversized_item"),
        (dict(rows=2, bytes=1800, largest=900), "work_limit"),
    ],
)
def test_preflight_transfers_only_lengths_and_refuses_before_row_body(summary, reason):
    conn = Mock()
    conn.execute.return_value.one.return_value = SimpleNamespace(**summary)
    budget = PublishedReadBudget(2, 1024, bytes=256)
    with pytest.raises(ReadLimit) as caught:
        budget.preflight(conn, select(literal("body").label("payload")).limit(1))
    assert caught.value.reason == reason
    statement = conn.execute.call_args.args[0]
    assert set(statement.selected_columns.keys()) == {"rows", "bytes", "largest"}
    assert "octet_length" in str(statement)
    # The caller's page limit remains inside a second detection-row bound.
    assert len(statement.compile().params) >= 3
    assert conn.execute.call_count == 1


def test_shared_budget_counts_canonical_utf8_and_reserves_artifacts_before_chunks():
    budget = PublishedReadBudget(10, 10)
    budget.value("é")  # quote + two UTF-8 bytes + quote
    assert budget.bytes == 4
    budget.reserve(6)
    assert budget.bytes == 10
    with pytest.raises(ReadLimit, match="byte-work"):
        budget.reserve(1)


def test_scalar_length_refuses_before_first_artifact_part():
    reader = object.__new__(PublishedPdfReader)
    reader.reference = ProductReference(2, "native", "a" * 64)
    reader.revision = {"release_id": "r", "source_digest": "a" * 64}
    reader.read_budget = PublishedReadBudget(10, 10)
    reader._one = Mock(
        return_value=dict(byte_length=11, serialization_sha256="b" * 64, byte_root="c" * 64)
    )
    reader.iter_rows = Mock(side_effect=AssertionError("artifact body must not be requested"))
    with pytest.raises(ReadLimit) as caught:
        next(reader.scalar("large"))
    assert caught.value.reason == "oversized_item"
    reader.iter_rows.assert_not_called()


def test_native_envelope_refuses_complete_oversized_body(monkeypatch):
    selected = request(max_bytes=1024)
    response = native_source.NativeSourceResponse(
        selection=selected, release_id="r", health={}, rows=[{"text": "x" * 2048}]
    )
    monkeypatch.setattr(native_source, "_inspect_native_source", lambda *args, **kwargs: response)
    with pytest.raises(ReadLimit) as caught:
        conn = Mock()
        conn.connection.driver_connection = MagicMock(spec=psycopg.Connection)
        native_source.inspect_native_source(conn, selected)
    assert caught.value.reason == "oversized_item"


def test_postgresql_preflight_admits_only_requested_page_and_refuses_body_transfer(
    semantic_bare_engine,
):
    from sqlalchemy import Text, column, event, table, text

    with semantic_bare_engine.begin() as conn:
        conn.execute(text("CREATE TABLE selected_body(id int, payload text)"))
        conn.execute(text("INSERT INTO selected_body VALUES (1,'ok'),(2,repeat('x',4096))"))
        body = table("selected_body", column("id"), column("payload", Text))
        budget = PublishedReadBudget(10, 1024)
        query = select(body).order_by(body.c.id)
        budget.preflight(conn, query.limit(1))
        assert budget.rows == 1
        statements = []
        event.listen(
            conn,
            "before_cursor_execute",
            lambda c, cur, statement, params, ctx, many: statements.append(statement),
        )
        with pytest.raises(ReadLimit) as caught:
            budget.preflight(conn, query.where(body.c.id == 2))
        assert caught.value.reason == "oversized_item"
        assert len(statements) == 1 and "octet_length" in statements[0]
        assert "count(*)" in statements[0]


def test_interactive_packet_propagates_one_budget_and_refuses_whole_packet(monkeypatch):
    from corpus_structure.methods.math import native
    from corpus_structure.orchestrate import semantic, semantic_references
    from corpus_structure.semantic import operations

    budget = PublishedReadBudget(10, 10)
    config = {"mode": "extract"}
    reader = SimpleNamespace(read_budget=budget, characterization_selection=())
    view = SimpleNamespace(reader=reader, options={"agent_configs": {"extract": config}})
    monkeypatch.setattr(operations, "lock_input_snapshot", lambda *args: None)
    run_view = Mock(return_value=view)
    monkeypatch.setattr(semantic, "run_view", run_view)
    monkeypatch.setattr(
        semantic, "_unit", lambda *args: SimpleNamespace(source_view_id=7, document_id=3)
    )
    references = Mock(return_value=())
    monkeypatch.setattr(semantic_references, "document_references", references)
    monkeypatch.setattr(
        native,
        "native_proposal_packet",
        lambda *args, **kwargs: SimpleNamespace(parts=lambda: [SimpleNamespace(text="x" * 11)]),
    )
    with pytest.raises(ReadLimit) as caught:
        semantic._packet_for_unit(Mock(), 1, Mock(), "unit", config, read_budget=budget)
    assert caught.value.reason == "oversized_item"
    assert run_view.call_args.kwargs["read_budget"] is budget
    assert references.call_args.kwargs["read_budget"] is budget


def test_source_search_uses_one_budget_and_refuses_old_cursor(monkeypatch):
    from corpus_structure.semantic import pdf_contracts, source_views
    from corpus_structure.serve import source_search

    monkeypatch.setattr(pdf_contracts, "pdf_context_for_run", lambda *args: Mock())
    selected = Mock(return_value=())
    rows = Mock(return_value=[])
    monkeypatch.setattr(source_views, "selected_source_views", selected)
    monkeypatch.setattr(source_search, "source_search_rows", rows)
    request = source_search.SourceSearchRequest(run_id=1, text="Alice", max_bytes=1024)
    answer = source_search.search_source(Mock(), request)
    assert answer.version == "integrated-source-4" and answer.population_complete
    assert selected.call_args.kwargs["read_budget"] is rows.call_args.kwargs["read_budget"]
    with pytest.raises(InvalidContinuation):
        source_search.search_source(Mock(), request.model_copy(update={"cursor": "e30="}))


def test_source_search_preflights_selected_scalar_bytes_on_postgresql(semantic_bare_engine):
    from sqlalchemy import event, text

    from corpus_structure.serve.source_search import source_search_rows

    with semantic_bare_engine.begin() as conn:
        for ddl in (
            "CREATE SCHEMA kb",
            "CREATE SCHEMA ops",
            "CREATE TABLE kb.document(id bigint,source_uri text)",
            "CREATE TABLE kb.source_view(id bigint,document_id bigint,native_task_id bigint,"
            "native_product_key text,native_content_digest text,section_pointer text,"
            "membership text,projection_digest text,projection jsonb)",
            "CREATE TABLE ops.run_source_view(run_id bigint,source_view_id bigint,"
            "supersedes_source_view_id bigint)",
            "INSERT INTO kb.document VALUES(1,repeat('u',4096))",
            "INSERT INTO kb.source_view VALUES(1,1,2,'native',repeat('a',64),'#/body','direct',"
            "repeat('b',64),'{\"text\":\"Alice publishes exact evidence.\"}')",
            "INSERT INTO ops.run_source_view VALUES(1,1,NULL)",
        ):
            conn.execute(text(ddl))
        statements = []
        event.listen(
            conn,
            "before_cursor_execute",
            lambda c, cur, statement, params, ctx, many: statements.append(statement),
        )
        with pytest.raises(ReadLimit) as caught:
            source_search_rows(
                conn, run_id=1, text="Alice", limit=1, read_budget=PublishedReadBudget(10, 1024)
            )
        assert caught.value.reason == "oversized_item"
        assert len(statements) == 1 and "octet_length" in statements[0]
