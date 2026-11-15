"""Actual selected structural CLI/MCP registration with controlled native acquisition."""

from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace

import anyio
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from sqlalchemy import create_engine
from typer.testing import CliRunner

from corpus_structure.cli import structure as cli_adapter
from corpus_structure.cli.app import app
from corpus_structure.intervene import structural_read_tools
from corpus_structure.intervene.semantic_server import build_retained_reader_server
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.serve import structural_products


def test_installed_cli_and_actual_mcp_use_exact_selected_structural_request(monkeypatch, tmp_path):
    engine = create_engine("sqlite://")
    captured = []

    def inspect(conn, request):
        captured.append(request.model_dump(mode="python"))
        return dict(cut_id="cut:actual", cut=dict(read_id="read:actual"),
                    implementation="a" * 64, exact_scope=Decimal("0.12345678901234567890123456789"), reports=[])

    monkeypatch.setattr("corpus_structure.semantic.demand_results.selected_read_snapshot", lambda engine: nullcontext(None))
    monkeypatch.setattr("corpus_structure.semantic.runtime.open_runtime_engine", lambda *a, **k: nullcontext(engine))
    monkeypatch.setattr(cli_adapter, "state", lambda _: SimpleNamespace(settings=lambda: None))
    monkeypatch.setattr(structural_products, "inspect_selected_structures", inspect)
    monkeypatch.setattr(structural_read_tools, "inspect_selected_structures", inspect)
    request = dict(demand_id="demand:actual", project_id="project:actual",
                   roots=[dict(product_id="product:actual", member_id=None, use_id="use:actual", derivation_id="episode:actual")])
    path = tmp_path / "selection.json"
    path.write_bytes(json_bytes(request))
    output = CliRunner().invoke(app, ["structure", "list", str(path), "--json"])
    assert output.exit_code == 0, output.output
    assert json_loads(output.stdout)["exact_scope"] == Decimal("0.12345678901234567890123456789")
    assert CliRunner().invoke(app, ["retained-structure", "--help"]).exit_code != 0

    async def check():
        async with Client(build_retained_reader_server(project="project:actual", read_engine=engine)) as client:
            names = {tool.name for tool in await client.list_tools()}
            assert {"inspect_structures", "inspect_dossier", "inspect_structural_gap", "inspect_source_journey"} <= names
            response = await client.call_tool("inspect_structures", {"request": request})
            assert not response.is_error
            result = response.structured_content
            assert json_loads(result["exact_json"])["exact_scope"] == Decimal("0.12345678901234567890123456789")
            resource = await client.read_resource(result["resource"])
            assert resource and captured[-1]["read_id"] == "read:actual"
            assert captured[-1]["expected_cut"] == "cut:actual"
            assert captured[-1]["implementation"] == "a" * 64
            with pytest.raises(ToolError, match="another server project"):
                await client.call_tool("inspect_structures", {"request": {**request, "project_id": "foreign"}})

    try:
        anyio.run(check)
    finally:
        engine.dispose()
    assert len(captured) == 3
