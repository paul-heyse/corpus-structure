"""Current composite CLI/MCP transport; native acquisition is controlled here."""

import json
from contextlib import nullcontext
from types import SimpleNamespace

import anyio
from fastmcp import Client
from sqlalchemy import create_engine
from typer.testing import CliRunner

from corpus_structure.cli import selected_results as cli_adapter
from corpus_structure.cli.app import build_full_app
from corpus_structure.intervene import contribution_facet_tools
from corpus_structure.intervene.semantic_server import build_retained_reader_server
from corpus_structure.semantic.selected_pages import encode_cursor as _cursor
from corpus_structure.serve import contribution_facets

app = build_full_app()


def test_cli_and_registered_mcp_preserve_current_composite_scope(monkeypatch):
    engine = create_engine("sqlite://")
    captured = []
    monkeypatch.setattr(
        "corpus_structure.semantic.demand_results.selected_read_snapshot",
        lambda selected: nullcontext(None),
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.runtime.open_runtime_engine", lambda *a, **k: nullcontext(engine)
    )
    monkeypatch.setattr(cli_adapter, "state", lambda _: SimpleNamespace(settings=lambda: None))

    def inspect(conn, request):
        captured.append(request.model_dump(mode="python"))
        return {
            "cut_id": "cut:controlled",
            "items": [],
            "cursor": None,
            "resource_handle": _cursor(request.model_dump(mode="python", exclude_unset=True)),
        }

    monkeypatch.setattr(contribution_facets, "serve_contribution_facets", inspect)
    monkeypatch.setattr(contribution_facet_tools, "serve_contribution_facets", inspect)
    result = CliRunner().invoke(
        app,
        [
            "contributions",
            "list",
            "--demand",
            "selected-demand",
            "--project",
            "selected-project",
            "--operation",
            "rich.consolidate",
            "--product",
            "selected-product",
            "--member",
            "actual-member",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["cut_id"] == "cut:controlled"

    async def check():
        async with Client(
            build_retained_reader_server(project="selected-project", read_engine=engine)
        ) as client:
            tools = {tool.name for tool in await client.list_tools()}
            assert "read_result" in tools and "query_knowledge" in tools
            assert not tools & {
                "contributions",
                "contextual_neighborhood",
                "source_decision_diagnosis",
                "source_decision_journey",
                "structural_gap",
                "structural_products",
                "dossier_representation",
            }
            assert "inspect_contributions" in tools and "compare_identity_exclusions" in tools
            response = await client.call_tool("inspect_contributions", {"request": captured[0]})
            assert not response.is_error

    try:
        anyio.run(check)
    finally:
        engine.dispose()
    assert len(captured) == 2 and captured[0] == captured[1]
