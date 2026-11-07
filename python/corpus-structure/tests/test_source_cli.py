"""Registered native source commands emit runtime results through the real JSON boundary."""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Connection, Engine

from corpus_structure.core.method import SourceViewRef
from corpus_structure.semantic.native_requests import NativeRequestResult
from corpus_structure.semantic.product_reference import ProductReference


@dataclass
class SourceRuntime:
    engine: MagicMock
    connection: MagicMock
    context: MagicMock
    opened: list[tuple[str, str]]


@pytest.fixture
def source_runtime(monkeypatch):
    from corpus_structure.semantic import pdf_contracts, query, runtime

    controlled = SourceRuntime(MagicMock(spec=Engine), MagicMock(spec=Connection), MagicMock(), [])

    @contextmanager
    def open_engine(settings, *, application_name, purpose):
        controlled.opened.append((application_name, purpose))
        yield controlled.engine

    @contextmanager
    def read_snapshot(engine, *, cancellation=None):
        assert engine is controlled.engine
        yield controlled.connection

    def context_for_run(conn, run):
        assert conn is controlled.connection
        assert run == 17
        return controlled.context

    monkeypatch.setattr(runtime, "open_runtime_engine", open_engine)
    monkeypatch.setattr(query, "read_snapshot", read_snapshot)
    monkeypatch.setattr(pdf_contracts, "pdf_context_for_run", context_for_run)
    return controlled


@pytest.mark.parametrize("empty", [False, True])
def test_native_products_json_retains_report_shape(cli, source_runtime, empty, monkeypatch):
    row = {
        "task_id": 23,
        "product_key": "native_document",
        "content_digest": "a" * 64,
        "release_id": "release-17",
        "health": {"status": "partial", "pages": [1, 2], "ocr": None},
        "runtime_report": {"seconds": 1.5, "ocr": {"enabled": True}},
    }
    rows = [] if empty else [row, {**row, "task_id": 24, "runtime_report": None}]
    from corpus_structure.semantic import pdf_record_reader, pdf_storage, releases
    from corpus_structure.serve import native_source

    catalog = [{**row, "origin_run": 17} for row in rows]
    by_task = {row["task_id"]: row for row in rows}
    source_runtime.context.release_id = "release-17"

    def execute(statement):
        assert "ops.pdf_selected_product.payload" not in str(statement)
        assert "ops.pdf_selected_product" in str(statement)
        result = MagicMock()
        result.mappings.return_value = catalog
        return result

    def open_release(conn, release):
        assert conn is source_runtime.connection and release == "release-17"
        return source_runtime.context

    def published(conn, pin, *, projection_context):
        assert conn is source_runtime.connection and projection_context is source_runtime.context
        expected = by_task[pin.task_id]
        assert (pin.product_key, pin.content_digest) == (
            expected["product_key"],
            expected["content_digest"],
        )
        return SimpleNamespace(reference=pin, header=expected)

    def verify_pin(conn, task, key, digest, reader):
        assert conn is source_runtime.connection
        assert (task, key, digest) == (
            reader.reference.task_id,
            reader.reference.product_key,
            reader.reference.content_digest,
        )

    def header(reader, run, *, runtime):
        assert run == 17 and runtime
        return SimpleNamespace(**reader.header)

    source_runtime.connection.execute.side_effect = execute
    monkeypatch.setattr(releases, "open_release", open_release)
    monkeypatch.setattr(pdf_record_reader, "published_record_reader", published)
    monkeypatch.setattr(pdf_storage, "_record_product_identity", verify_pin)
    monkeypatch.setattr(native_source, "_published_native_header", header)

    result = cli("source", "native-products", "17", "--json")

    assert result.exit_code == 0, (result.output, result.exception)
    assert result.stderr == ""
    assert json.loads(result.stdout) == rows
    assert source_runtime.opened == [("ci-native-products", "read")]
    source_runtime.context.execution.require_operation.assert_called_once_with("read_native_source")
    source_runtime.context.boundary.validate_json.assert_called_once_with(
        "PdfNativeRunRequest", '{"run_id": 17}'
    )


@pytest.mark.parametrize("empty", [False, True])
def test_native_views_json_retains_nested_pins_and_eligibility(
    cli, monkeypatch, source_runtime, empty
):
    from corpus_structure.semantic import source_views

    view = SourceViewRef(
        id=31,
        key="section-31",
        document_id=5,
        native_product=ProductReference(23, "native_document", "a" * 64),
        section_pointer="#/groups/7",
        membership="descendants",
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        analysis_eligible=False,
    )
    select_views = MagicMock(return_value=() if empty else (view,))
    monkeypatch.setattr(source_views, "selected_source_views", select_views)

    result = cli("source", "views", "17", "--json")

    assert result.exit_code == 0, (result.output, result.exception)
    assert result.stderr == ""
    expected = [
        {
            "id": 31,
            "key": "section-31",
            "document_id": 5,
            "native_product": {
                "task_id": 23,
                "product_key": "native_document",
                "content_digest": "a" * 64,
            },
            "section_pointer": "#/groups/7",
            "membership": "descendants",
            "projection_digest": "b" * 64,
            "recipe_digest": "c" * 64,
            "analysis_eligible": False,
        }
    ]
    assert json.loads(result.stdout) == ([] if empty else expected)
    select_views.assert_called_once_with(source_runtime.connection, 17)
    assert source_runtime.opened == [("ci-source-views", "read")]
    source_runtime.context.execution.require_operation.assert_called_once_with("read_source_view")
    source_runtime.context.boundary.validate_json.assert_called_once_with(
        "PdfNativeRunRequest", '{"run_id": 17}'
    )


@pytest.mark.parametrize("failed", [False, True])
def test_native_request_json_emits_dataclass_and_preserves_failure_exit(
    cli, monkeypatch, source_runtime, failed
):
    from corpus_structure.semantic import native_requests

    payload = {"items": [{"pointer": "#/texts/2", "definedness": {"status": "defined"}}]}
    completed = NativeRequestResult(
        run_id=18,
        task_id=42,
        cut_id=None if failed else 9,
        status="failed" if failed else "source_ready",
        source_view_id=31,
        product_digest=None if failed else "d" * 64,
        result=None if failed else payload,
        error="budget exhausted" if failed else None,
    )
    request = MagicMock(return_value=completed)
    monkeypatch.setattr(native_requests, "request_source_view", request)

    result = cli(
        "source",
        "native-request",
        "17",
        "31",
        "assessment",
        "--pointer",
        "#/texts/2",
        "--question",
        "definedness",
        "--predicate",
        "positive",
        "--seconds",
        "0.75",
        "--json",
    )

    assert result.exit_code == (1 if failed else 0), (result.output, result.exception)
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "run_id": 18,
        "task_id": 42,
        "cut_id": None if failed else 9,
        "status": "failed" if failed else "source_ready",
        "source_view_id": 31,
        "product_digest": None if failed else "d" * 64,
        "artifact_digest": None,
        "result": None if failed else payload,
        "error": "budget exhausted" if failed else None,
    }
    request.assert_called_once_with(
        source_runtime.engine,
        source_run_id=17,
        source_view_id=31,
        demand="assessment",
        pointer="#/texts/2",
        region_index=None,
        scale=2,
        question="definedness",
        predicate="positive",
        seconds=0.75,
        code_commit="native-source-cli-v2",
    )
    assert source_runtime.opened == [("ci-native-request", "write")]


def test_current_inspection_preserves_exact_product_and_companion_selector(
    cli, monkeypatch, source_runtime
):
    from corpus_structure.serve import native_source

    read = MagicMock(
        return_value=native_source.NativeSourceResponse(
            selection=native_source.NativeSourceRequest(
                run_id=17,
                task_id=23,
                product_key="integrated",
                content_digest="a" * 64,
                view="manifest",
                collection="coverage",
            ),
            release_id="release-17",
            health={},
            rows=[{"outcome": "unknown"}],
        )
    )
    monkeypatch.setattr(native_source, "inspect_native_source", read)
    result = cli(
        "source",
        "inspect",
        "17",
        "--producing-task",
        "23",
        "--product",
        "integrated",
        "--native-digest",
        "a" * 64,
        "--native-view",
        "manifest",
        "--collection",
        "coverage",
        "--json",
    )
    assert result.exit_code == 0, (result.output, result.exception)
    selected = read.call_args.args[1]
    assert selected.version == 4
    assert selected.content_digest == "a" * 64
    assert selected.view == "manifest" and selected.collection == "coverage"
    assert json.loads(result.stdout)["rows"] == [{"outcome": "unknown"}]
    old = cli("source", "inspect", "17", "4")
    assert old.exit_code != 0


def test_source_coverage_summary_keeps_page_counts_and_continuation(
    cli, source_runtime, monkeypatch
):
    from corpus_structure.serve import native_source

    def inspect(conn, request, *, cancellation):
        assert conn is source_runtime.connection
        assert request.collection == "coverage"
        return native_source.NativeSourceResponse(
            selection=request,
            release_id="release-17",
            health={},
            rows=[{"rows": [{"outcome": "missing"}, {"outcome": "ready"}]}],
            next_cursor="next-coverage-page",
            population_complete=False,
        )

    monkeypatch.setattr(native_source, "inspect_native_source", inspect)
    args = (
        "source",
        "inspect",
        "17",
        "--producing-task",
        "23",
        "--product",
        "native_document",
        "--native-digest",
        "a" * 64,
        "--native-view",
        "manifest",
        "--collection",
        "coverage",
    )
    full = cli(*args, "--json")
    assert full.exit_code == 0, full.output
    assert "rows" in json.loads(full.stdout)

    projected = cli(*args, "--view", "summary", "--json")
    assert projected.exit_code == 0, projected.output
    assert json.loads(projected.stdout) == {
        "selection": json.loads(full.stdout)["selection"],
        "release_id": "release-17",
        "outcome": "source_ready",
        "page_outcomes": {"missing": 1, "ready": 1},
        "page_rows": 2,
        "next_cursor": "next-coverage-page",
    }
    human = cli(*args)
    assert human.exit_code == 0, human.output
    assert "missing: 1, ready: 1" in human.stdout
    assert "a" * 64 in human.stdout.replace("\n", "").replace(" ", "")
