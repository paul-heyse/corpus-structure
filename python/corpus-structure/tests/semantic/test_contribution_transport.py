"""CLI and registered MCP share the complete v3 selector/facet request contract."""

import json
from contextlib import nullcontext
from types import SimpleNamespace

import anyio
from fastmcp import Client
from sqlalchemy import create_engine
from typer.testing import CliRunner

from corpus_structure.cli import contributions as cli_adapter
from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.serve import contributions as journey


def test_cli_and_registered_mcp_preserve_the_same_v3_request(monkeypatch):
    engine = create_engine("sqlite://")
    captured = []
    monkeypatch.setattr(
        "corpus_structure.semantic.query.read_snapshot", lambda _: nullcontext(None)
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.runtime.open_runtime_engine", lambda *a, **k: nullcontext(engine)
    )
    monkeypatch.setattr(cli_adapter, "state", lambda _: SimpleNamespace(settings=lambda: None))

    def inspect(conn, request):
        captured.append(request.model_dump(mode="json"))
        return journey.ContributionPage(
            run_id=7,
            cut_id=4,
            binding={},
            selection=request.selection(),
            items=(),
            inventory_counts={},
            population_paging_complete=True,
            interpretation="included",
            assessment="included",
        )

    monkeypatch.setattr(journey, "serve_contributions", inspect)
    result = CliRunner().invoke(
        cli_adapter.app,
        [
            "list",
            "--run",
            "7",
            "--operation-version",
            "1",
            "--contribution-id",
            "cid",
            "--occurrence-id",
            "occ",
            "--include-interpretation",
            "--include-assessment",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["version"] == "contribution-inspection-3"

    async def check():
        async with Client(build_semantic_server(SemanticAgentSession(engine, 7))) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            schema = json.dumps(tools["contributions"].input_schema)
            for field in (
                "operation_version",
                "contribution_id",
                "occurrence_id",
                "include_interpretation",
                "include_assessment",
            ):
                assert field in schema
            response = await client.call_tool("contributions", {"request": captured[0]})
            assert not response.is_error

    try:
        anyio.run(check)
    finally:
        engine.dispose()
    assert len(captured) == 2 and captured[0] == captured[1]
