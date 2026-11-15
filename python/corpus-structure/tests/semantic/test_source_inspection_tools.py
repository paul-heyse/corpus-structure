"""Real MCP dispatch over prepared facts and explicit live source navigation."""

from contextlib import contextmanager

import anyio
from fastmcp import Client, FastMCP

from corpus_structure.intervene.source_inspection_tools import register_source_inspection_tools
from corpus_structure.semantic.source_interfaces import SourceInterfaceProjection
from corpus_structure.semantic.source_navigation import NavigationSnapshot, SourceDocument


def test_mcp_prepared_facts_and_actual_navigation(monkeypatch):
    from corpus_structure.semantic import (
        releases,
        source_interface_read,
        source_interfaces,
        source_navigation,
    )

    source = "def twice(x: int) -> int:\n    return x * 2\nresult = twice(3)\n"
    snapshot = NavigationSnapshot(documents=(SourceDocument(path="example.py", content=source),))
    projection = SourceInterfaceProjection(
        model_digest="f" * 64,
        interpreter="python-3.14",
        interpretation="closed-python-operations-v1",
        libraries={"griffe": "2.4.1"},
        modules=(),
        operations=(),
    )
    monkeypatch.setattr(
        releases,
        "open_release",
        lambda connection, release: type("Prepared", (), {"release_id": release})(),
    )
    monkeypatch.setattr(source_interfaces, "read_source_interfaces", lambda prepared: projection)
    monkeypatch.setattr(
        source_interface_read, "read_source_interfaces", lambda prepared: projection
    )
    monkeypatch.setattr(
        source_navigation, "archived_navigation_snapshot", lambda connection, release: snapshot
    )

    @contextmanager
    def reader():
        yield object()

    server = FastMCP("source-inspection-test")
    register_source_inspection_tools(server, reader, project="project")

    async def exercise():
        async with Client(server) as client:
            result = await client.call_tool(
                "inspect_source_interfaces", {"release_id": "release:captured"}
            )
            assert result.structured_content is not None
            assert result.structured_content["standing"] == "prepared"
            assert result.structured_content["projection_id"] == projection.identity
            result = await client.call_tool(
                "navigate_captured_source",
                {
                    "release_id": "release:captured",
                    "request": {
                        "snapshot_id": snapshot.identity,
                        "path": "example.py",
                        "byte_offset": source.encode().index(b"twice(3)"),
                        "operation": "definition",
                    },
                },
            )
            assert result.structured_content is not None
            assert result.structured_content["standing"] == "complete"
            assert result.structured_content["items"][0]["path"] == "example.py"
            refused = await client.call_tool(
                "inspect_source_change_impact",
                {
                    "request": {
                        "project_id": "other",
                        "before_demand_id": "demand:one",
                        "target_release_id": "release:captured",
                    }
                },
                raise_on_error=False,
            )
            assert refused.is_error

    anyio.run(exercise)


def test_cli_navigation_uses_actual_model_command(cli, tmp_path):
    from corpus_structure.cli.source_inspection import NavigationInput
    from corpus_structure.semantic.source_navigation import NavigationRequest

    source = "def f():\n    return 1\nx = f()\n"
    snapshot = NavigationSnapshot(documents=(SourceDocument(path="example.py", content=source),))
    request = NavigationRequest(
        snapshot_id=snapshot.identity,
        path="example.py",
        byte_offset=source.encode().index(b"f()\n", 15),
        operation="definition",
    )
    input = tmp_path / "navigation.json"
    input.write_text(NavigationInput(snapshot=snapshot, request=request).model_dump_json())
    result = cli("model", "source", "navigate", str(input), "--json")
    assert result.exit_code == 0, result.output
    import json

    report = json.loads(result.stdout)
    assert report["standing"] == "complete"
    assert report["items"][0]["utf8_bytes"] == {"start": 4, "end": 5}
