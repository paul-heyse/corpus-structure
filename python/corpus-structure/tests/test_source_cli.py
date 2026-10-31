"""Registered native source commands emit runtime results through the real JSON boundary."""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Connection, Engine

from corpus_structure.core.method import SourceViewRef
from corpus_structure.semantic.native_requests import NativeRequestResult
from corpus_structure.semantic.parsing_products import ProductReference


@dataclass
class SourceRuntime:
    engine: MagicMock
    connection: MagicMock
    context: MagicMock
    opened: list[tuple[str, str]]


@pytest.fixture
def source_runtime(monkeypatch):
    from corpus_structure.semantic import pdf_contracts, query, runtime

    controlled = SourceRuntime(
        MagicMock(spec=Engine), MagicMock(spec=Connection), MagicMock(), []
    )

    @contextmanager
    def open_engine(settings, *, application_name, purpose):
        controlled.opened.append((application_name, purpose))
        yield controlled.engine

    @contextmanager
    def read_snapshot(engine):
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
def test_native_products_json_retains_report_shape(cli, source_runtime, empty):
    row = {
        "task_id": 23,
        "product_key": "native_document",
        "content_digest": "a" * 64,
        "release_id": "release-17",
        "health": {"status": "partial", "pages": [1, 2], "ocr": None},
        "runtime_report": {"seconds": 1.5, "ocr": {"enabled": True}},
    }
    rows = [] if empty else [row, {**row, "task_id": 24, "runtime_report": None}]
    source_runtime.connection.execute.return_value.mappings.return_value = rows

    result = cli("source", "native-products", "17", "--json")

    assert result.exit_code == 0, (result.output, result.exception)
    assert result.stderr == ""
    assert json.loads(result.stdout) == rows
    assert source_runtime.opened == [("ci-native-products", "read")]
    source_runtime.context.execution.require_operation.assert_called_once_with(
        "read_native_source"
    )
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
    source_runtime.context.execution.require_operation.assert_called_once_with(
        "read_source_view"
    )
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
