"""Source ABI, continuation and pre-transfer admission controls (component scope)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import psycopg
import pytest
from pydantic import ValidationError
from sqlalchemy import literal, select

from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader, PublishedReadBudget
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.refusal_types import InvalidContinuation, ReadLimit
from corpus_structure.serve import native_source


def request(**changes):
    return native_source.NativeSourceRequest(
        project_id="p",
        demand_id="d",
        read_id="r",
        use_id="u",
        product_id="product",
        derivation_id="episode",
        **changes,
    )


def test_v5_requires_explicit_row_byte_admission_and_refuses_old_meaning():
    selected = request()
    assert (selected.version, selected.limit, selected.max_rows, selected.max_bytes) == (
        5,
        100,
        10000,
        1048576,
    )
    for changes in (
        {"version": 4},
        {"max_bytes": 8388609},
        {"max_rows": 10001},
        {"max_bytes": True},
        {"max_rows": True},
    ):
        with pytest.raises(ValidationError):
            request(**changes)


def test_program_cursor_binds_byte_and_row_work_budgets_and_rejects_old_tokens():
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


def test_program_envelope_refuses_complete_oversized_body(monkeypatch):
    selected = request(max_bytes=1024)
    response = native_source.NativeSourceResponse(
        selection=selected, release_id="r", cut={}, health={}, rows=[{"text": "x" * 2048}]
    )
    monkeypatch.setattr(native_source, "_inspect_native_source", lambda *args, **kwargs: response)
    with pytest.raises(ReadLimit) as caught:
        conn = Mock()
        conn.connection.driver_connection = MagicMock(spec=psycopg.Connection)
        native_source.inspect_native_source(conn, selected)
    assert caught.value.reason == "oversized_item"


def test_postgresql_preflight_admits_only_requested_page_and_refuses_body_transfer(
    infrastructure_rollback,
):
    from sqlalchemy import Text, column, event, table, text

    conn = infrastructure_rollback
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


@pytest.mark.parametrize("bytes_limit,oversized", [(1048576, False), (2048, True)])
def test_current_search_bounds_returned_hits_independently_of_publication_fill(
    monkeypatch, bytes_limit, oversized
):
    from corpus_structure.semantic import pdf_record_reader, pdf_source_search
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.demand_results import CutSelection
    from corpus_structure.serve import source_search
    from semantic.selected_source_contract_support import selection

    pin, cut, publication = selection()
    second = pin.model_copy(update={"product_id": "product:second", "use_id": "use:second"})

    def acquire(connection, reference):
        return SimpleNamespace(
            reference=reference,
            cut=CutSelection(json_bytes(cut)),
            physical=publication,
            prepared=object(),
            original_source="original:selected",
            receipt=SimpleNamespace(publication=publication),
        )

    ensured = Mock()
    ranked = Mock(
        return_value=dict(
            selection="a" * 64,
            more=False,
            rows=[
                dict(
                    source_index=i,
                    section_pointer="#/body",
                    membership="direct",
                    projection_digest="b" * 64,
                    key=str(i),
                    excerpt="Alice " * 130,
                    score=0.1,
                )
                for i in range(2)
            ],
        )
    )
    monkeypatch.setattr(source_search, "acquire_selected_pdf_source", acquire)
    monkeypatch.setattr(pdf_source_search, "projection_recipe", lambda *args: ({}, None))
    monkeypatch.setattr(
        pdf_source_search, "population_identity", lambda source, recipe: source.reference.product_id
    )
    monkeypatch.setattr(pdf_source_search, "ensure_search_projection", ensured)
    monkeypatch.setattr(DataOperationStorage, "rank_pdf_search_projection", ranked)
    monkeypatch.setattr(
        pdf_record_reader,
        "PublishedPdfReader",
        Mock(
            side_effect=AssertionError("cache-hit search must not materialize the population"),
        ),
    )
    selected = source_search.SourceSearchRequest(
        project_id=pin.project_id,
        demand_id=pin.demand_id,
        read_id=pin.read_id,
        sources=(pin, second),
        text="Alice",
        max_rows=10,
        max_bytes=bytes_limit,
    )
    if oversized:
        with pytest.raises(ReadLimit):
            source_search.search_source(Mock(), selected)
    else:
        answer = source_search.search_source(Mock(), selected)
        assert len(answer.rows) == 2 and answer.population_complete
        assert answer.cut["read_id"] == pin.read_id
        with pytest.raises(InvalidContinuation):
            source_search.search_source(Mock(), selected.model_copy(update={"cursor": "e30="}))
    assert ensured.call_count == 2 and ranked.call_count == 1
    payload = ranked.call_args.args[0]
    assert payload["limit"] == 10
    assert all(set(source) == {"source", "recipe"} for source in payload["sources"])
