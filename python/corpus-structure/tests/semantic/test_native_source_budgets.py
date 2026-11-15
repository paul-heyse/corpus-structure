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
        selection=selected, release_id="r", cut={}, health={}, rows=[{"text": "x" * 2048}]
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
    from corpus_structure.orchestrate import semantic_references
    from corpus_structure.semantic import operations
    from corpus_structure.semantic import retained_agent_packets as semantic

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


@pytest.mark.parametrize("bytes_limit,oversized", [(1048576, False), (2048, True)])
def test_current_search_shares_budget_across_exact_source_population_before_ranking(
    monkeypatch, bytes_limit, oversized
):
    from corpus_structure.ingest import pdf_section_views
    from corpus_structure.semantic import pdf_record_reader, source_products
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.demand_results import CutSelection
    from corpus_structure.serve import source_search
    from semantic.selected_source_contract_support import selection

    pin, cut, publication = selection()
    second = pin.model_copy(update={"product_id": "product:second", "use_id": "use:second"})
    budgets = []

    def acquire(connection, reference):
        return SimpleNamespace(
            reference=reference,
            cut=CutSelection(json_bytes(cut)),
            physical=publication,
            prepared=object(),
            original_source="original:selected",
            receipt=SimpleNamespace(publication=publication),
        )

    def reader(connection, physical, *, projection_context, read_budget):
        budgets.append(read_budget)
        return SimpleNamespace(read_budget=read_budget)

    def sections(reader, *, selections, membership, scope):
        assert selections == ("#/body",) and membership == "descendants"
        return [
            SimpleNamespace(
                section_pointer="#/body",
                membership=membership,
                text="Alice " * 130,
                pieces=(),
                items=(),
                ancestors=(),
                health={},
            )
        ]

    ranked = Mock(return_value=())
    monkeypatch.setattr(source_search, "acquire_selected_pdf_source", acquire)
    monkeypatch.setattr(pdf_record_reader, "PublishedPdfReader", reader)
    monkeypatch.setattr(pdf_section_views, "published_section_projections", sections)
    monkeypatch.setattr(
        source_products.FrozenNativeSource,
        "from_projection",
        lambda *args, **kwargs: SimpleNamespace(
            value={"source": {"projection": "projection:controlled"}}
        ),
    )
    monkeypatch.setattr(source_search, "_rank_sections", ranked)
    request = source_search.SourceSearchRequest(
        project_id=pin.project_id,
        demand_id=pin.demand_id,
        read_id=pin.read_id,
        sources=(pin, second),
        sections=("#/body",),
        membership="descendants",
        text="Alice",
        max_rows=10,
        max_bytes=bytes_limit,
    )
    if oversized:
        with pytest.raises(ReadLimit):
            source_search.search_source(Mock(), request)
        ranked.assert_not_called()
    else:
        answer = source_search.search_source(Mock(), request)
        assert answer.rows == [] and answer.population_complete
        assert answer.cut["read_id"] == pin.read_id
        assert len(ranked.call_args.args[1]) == 2
        with pytest.raises(InvalidContinuation):
            source_search.search_source(Mock(), request.model_copy(update={"cursor": "e30="}))
    assert len(budgets) >= 2 and all(budget is budgets[0] for budget in budgets[:2])
    assert budgets[0].max_rows == 10
