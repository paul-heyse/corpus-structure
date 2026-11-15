"""Pinned current query pages and exact transport; native acquisition is controlled here."""

from contextlib import nullcontext
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import anyio
import pytest
from fastmcp import Client
from mcp.types import TextResourceContents
from sqlalchemy import create_engine
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.demand_queries import _cursor
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.semantic.rich_queries import RichQueryRefused
from corpus_structure.serve import rich_queries as service
from corpus_structure.serve.rich_knowledge import SelectedRichKnowledge
from semantic.test_rich_queries import query_source as query_source
from semantic.test_rich_queries import statistics as statistics

CUT = dict(
    project_id="query-project",
    demand_id="query-demand",
    read_id="actual-read",
    release_id="actual-release",
    runtime_id="actual-runtime",
    selection={"targets": ["rich.admit"]},
    trust_snapshot={},
    read_snapshot="1:2:",
    frontier_at="2026-11-15T00:00:00+00:00",
    scope={},
)


def request(**changes):
    return service.RichQueryRequest.model_validate(
        {
            "demand_id": "query-demand",
            "project_id": "query-project",
            "product_id": "selected-knowledge",
            "query": {"name": "claims"},
            **changes,
        }
    )


def test_pages_require_exact_cut_root_query_and_installed_meaning(monkeypatch, statistics):
    graph, index = statistics
    ref = graph.root_input.reference
    cut = CutSelection(json_bytes(CUT))
    read = dict(
        demand_id="query-demand",
        read_id="actual-read",
        view="products",
        scope={"operation_id": "rich.admit", "product_ids": ["selected-knowledge"]},
    )
    selected = SelectedRichKnowledge(cut, json_bytes(read), ref, graph.context, index.state)
    seen = []

    def load(connection, demand_id, **kwargs):
        assert demand_id == "query-demand" and kwargs["product_id"] == "selected-knowledge"
        seen.append(kwargs)
        return selected

    monkeypatch.setattr(service, "read_selected_rich_knowledge", load)
    first = service.serve_rich_query(None, request(limit=1))
    assert len(first["rows"]) == 1 and first["cursor"]
    assert first["scope"]["global_completeness"] == "unknown"
    second = service.serve_rich_query(None, request(limit=1, cursor=first["cursor"]))
    assert second["rows"] != first["rows"]
    assert seen[1]["cut"] == cut and seen[1]["continuation"] == read
    pinned = service.RichQueryRequest.model_validate(
        service.decode_rich_cursor(first["resource_handle"])
    )
    assert (
        pinned.expected_cut == cut.identity
        and pinned.read_id == "actual-read"
        and pinned.implementation == first["implementation"]
    )
    assert service.serve_rich_query(None, pinned)["rows"] == first["rows"]
    with pytest.raises(InvalidContinuation):
        service.serve_rich_query(
            None, request(cursor=first["cursor"], query={"name": "claims", "subject": "normal"})
        )
    with pytest.raises(InvalidContinuation, match="implementation"):
        service.serve_rich_query(None, request(implementation="0" * 64))
    monkeypatch.setattr(
        service,
        "read_selected_rich_knowledge",
        lambda *a, **k: SelectedRichKnowledge(
            cut,
            json_bytes(read),
            ref.model_copy(update={"support_references": ()}),
            graph.context,
            index.state,
        ),
    )
    with pytest.raises(InvalidContinuation, match="root support"):
        service.serve_rich_query(None, request(cursor=first["cursor"]))


def test_loaded_query_helper_cannot_be_relabelled_with_changed_source_bytes(monkeypatch):
    original = Path.read_bytes
    target = Path(service.__file__).resolve().parents[1] / "semantic/rich_queries.py"
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda path: (
            original(path) + b"\n# edited after import\n" if path == target else original(path)
        ),
    )
    with pytest.raises(RichQueryRefused, match="source custody"):
        service.serve_rich_query(None, request())


def test_exact_cursor_keeps_fractional_parameters_and_refuses_work_and_response_limits(
    monkeypatch, statistics
):
    graph, index = statistics
    ref = graph.root_input.reference
    cut = CutSelection(json_bytes(CUT))
    monkeypatch.setattr(
        service,
        "read_selected_rich_knowledge",
        lambda *a, **k: SelectedRichKnowledge(cut, b"{}", ref, graph.context, index.state),
    )
    fraction = Decimal("0.123456789123456789123456789123456789")
    selected = request(
        query={"name": "families_where", "predicate": "stat:parameter_role", "value": fraction}
    )
    assert (
        service.decode_rich_cursor(_cursor(selected.model_dump(mode="python")))["query"]["value"]
        == fraction
    )
    with pytest.raises(RichQueryRefused, match="member capacity"):
        service.serve_rich_query(None, request(max_graph_members=1))
    with pytest.raises(RichQueryRefused, match="max_bytes"):
        service.serve_rich_query(None, request(max_bytes=1024))


def test_registered_mcp_and_cli_preserve_exact_query_parameters_and_pinned_resource(
    monkeypatch, tmp_path
):
    from corpus_structure.cli import selected_results
    from corpus_structure.intervene import rich_query_tools
    from corpus_structure.intervene.semantic_server import build_retained_reader_server

    fraction = Decimal("0.123456789123456789123456789123456789")
    selected = request(
        query={"name": "families_where", "predicate": "stat:parameter_role", "value": fraction}
    )
    engine = create_engine("sqlite://")
    seen = []

    def serve(connection, query):
        seen.append(query)
        return dict(
            cut_id="actual-cut",
            rows=[{"fraction": query.query.value}],
            resource_handle=_cursor(query.model_dump(mode="python")),
        )

    monkeypatch.setattr(service, "serve_rich_query", serve)
    monkeypatch.setattr(rich_query_tools, "serve_rich_query", serve)
    monkeypatch.setattr(
        "corpus_structure.semantic.runtime.open_runtime_engine", lambda *a, **k: nullcontext(engine)
    )
    monkeypatch.setattr(selected_results, "state", lambda _: SimpleNamespace(settings=lambda: None))
    parameters = tmp_path / "parameters.json"
    parameters.write_bytes(json_bytes(dict(predicate="stat:parameter_role", value=fraction)))
    result = CliRunner().invoke(
        app,
        [
            "query",
            "families_where",
            "--demand",
            "query-demand",
            "--project",
            "query-project",
            "--product",
            "selected-knowledge",
            "--parameters",
            str(parameters),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json_loads(result.stdout)["rows"][0]["fraction"] == fraction

    async def check():
        async with Client(
            build_retained_reader_server(project="query-project", read_engine=engine)
        ) as client:
            result = await client.call_tool(
                "query_knowledge",
                {"request_json": json_bytes(selected.model_dump(mode="python")).decode()},
            )
            assert not result.is_error
            report = result.structured_content
            assert report is not None
            assert json_loads(report["exact_json"])["rows"][0]["fraction"] == fraction
            resource = await client.read_resource(report["resource"])
            assert isinstance(resource[0], TextResourceContents)
            exact = json_loads(resource[0].text)
            assert json_loads(exact["exact_json"])["rows"][0]["fraction"] == fraction
            refused = await client.call_tool(
                "query_knowledge",
                {
                    "request_json": json_bytes(
                        selected.model_copy(update={"project_id": "another-project"}).model_dump(
                            mode="python"
                        )
                    ).decode()
                },
                raise_on_error=False,
            )
            assert refused.is_error

    try:
        anyio.run(check)
    finally:
        engine.dispose()
    assert len(seen) == 3 and all(item.query.value == fraction for item in seen)
