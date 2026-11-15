"""Actual selected topology, public delivery and detached graph reconstruction."""

import base64
from contextlib import contextmanager
from hashlib import sha256

import anyio
import pytest
from fastmcp import Client, FastMCP
from mcp.types import TextResourceContents

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.graph_inspection import GraphInspectionRequest, read_graph_inspection
from corpus_structure.settings import Settings
from semantic.serving_scenarios import declared_serving_case as declared_serving_case
from semantic.serving_scenarios import declared_serving_seed as declared_serving_seed


from semantic.selected_graph_test_support import _selected_snapshot, _offline_snapshot


@pytest.mark.parametrize("encoding", ["jsonl", "parquet"])
def test_actual_selected_precedence_support_public_and_offline(
    declared_serving_case, tmp_path, encoding, cli, monkeypatch
):
    from corpus_structure.intervene.source_inspection_tools import register_source_inspection_tools
    from corpus_structure.semantic import prepare, python_operation_sources
    from corpus_structure.serve.demand_export import export_demand_result, verify_demand_export

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    request = GraphInspectionRequest(
        release_id=stage.prepared.release_id,
        demand_id=stage.demand_id,
        project_id=stage.project_id,
        projection="bound-requests",
        limit=1,
    )
    page = read_graph_inspection(clone.reader.begin, request)
    assert page.standing == "complete"
    assert page.continuation is not None
    second = read_graph_inspection(
        clone.reader.begin, request.model_copy(update={"cursor": page.continuation})
    )
    assert second.snapshot_id == page.snapshot_id
    with pytest.raises(ValueError):
        read_graph_inspection(
            clone.reader.begin,
            request.model_copy(update={"cursor": page.continuation, "scope": {"subject": "wrong"}}),
        )
    snapshot = _selected_snapshot(clone.reader.begin, stage.prepared, request)
    kinds = {node.identity: node.kind for node in snapshot.nodes}
    assert any(
        edge.relation == "selected-input"
        and kinds[edge.source] == "use"
        and kinds[edge.target] == "request"
        for edge in snapshot.occurrences
    )
    assert set(kinds.values()) <= {"request", "use", "population", "obligation"}
    with clone.reader.begin() as connection:
        destination = tmp_path / encoding
        manifest = export_demand_result(
            connection,
            stage.demand_id,
            project_id=stage.project_id,
            destination=destination,
            format=encoding,
            page_rows=1,
        )
    # Reopen the export's exact native cut: request/read contexts must match, not
    # merely have equal topology from two fresh observations.
    pinned = request.model_copy(
        update={
            "read_id": manifest["cut"]["read_id"],
            "expected_cut": manifest["cut_id"],
            "cursor": None,
            "limit": 1000,
        }
    )
    live = _selected_snapshot(clone.reader.begin, stage.prepared, pinned)
    bounded = read_graph_inspection(
        clone.reader.begin, pinned.model_copy(update={"max_examined_bytes": 1024})
    )
    assert bounded.standing == "partial"
    assert json_loads(bounded.pins_json)["cut_id"] == manifest["cut_id"]
    assert json_loads(bounded.pins_json)["read_id"] == manifest["cut"]["read_id"]

    def forbidden(*args, **kwargs):
        raise AssertionError("offline graph inspection must not prepare or parse sources")

    monkeypatch.setattr(prepare, "prepare_release", forbidden)
    monkeypatch.setattr(python_operation_sources.ClosedPythonSources, "__init__", forbidden)
    verify_demand_export(
        destination,
        manifest_digest=sha256((destination / "manifest.json").read_bytes()).hexdigest(),
    )
    offline = _offline_snapshot(destination, "bound-requests")
    assert offline.identity == live.identity
    support_request = pinned.model_copy(update={"projection": "selected-support"})
    support = _selected_snapshot(clone.reader.begin, stage.prepared, support_request)
    assert any(edge.relation == "support" for edge in support.occurrences)
    assert _offline_snapshot(destination, "selected-support").identity == support.identity
    url = clone.reader.url.set(drivername="postgresql").render_as_string(hide_password=False)
    settings = Settings()
    settings = settings.model_copy(
        update={"database": settings.database.model_copy(update={"url": url, "reader_url": url})}
    )
    input_path = tmp_path / "graph.json"
    input_path.write_bytes(json_bytes(pinned.model_dump()))
    command = cli("model", "source", "graph", str(input_path), "--json", settings=lambda: settings)
    assert command.exit_code == 0, command.output
    assert json_loads(command.stdout)["snapshot_id"] == live.identity

    @contextmanager
    def reader():
        with clone.reader.begin() as connection:
            yield connection

    server = FastMCP("selected-native-graph")
    register_source_inspection_tools(
        server, reader, project=stage.project_id, demand=stage.demand_id
    )

    async def inspect():
        async with Client(server) as client:
            result = await client.call_tool(
                "inspect_declared_graph", {"request": pinned.model_dump(mode="json")}
            )
            assert result.structured_content is not None
            assert result.structured_content["snapshot_id"] == live.identity
            handle = base64.urlsafe_b64encode(json_bytes(pinned.model_dump())).decode()
            resource = await client.read_resource("corpus://declared-graph/" + handle)
            assert isinstance(resource[0], TextResourceContents)
            assert json_loads(resource[0].text)["snapshot_id"] == live.identity
            refused = await client.call_tool(
                "inspect_declared_graph",
                {
                    "request": pinned.model_copy(update={"project_id": "wrong"}).model_dump(
                        mode="json"
                    )
                },
                raise_on_error=False,
            )
            assert refused.is_error

    anyio.run(inspect)


def test_native_requestless_population_fate_survives_tools_and_resources(declared_serving_case):
    from typing import cast

    from corpus_structure.intervene.source_inspection_tools import register_source_inspection_tools
    from corpus_structure.semantic._data_operation_wire import WireRecordDataFateRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.demand_results import read_demand_result

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with clone.writer.begin() as connection:
        page = read_demand_result(connection, stage.demand_id, project_id=stage.project_id)
        obligation = page.record["obligations"][0]["obligation_id"]
        recorded = DataOperationStorage(connection).record_data_fate(
            cast(
                WireRecordDataFateRequest,
                dict(obligation_id=obligation, fate="awaiting-population", selection={}),
            )
        )
    request = GraphInspectionRequest(
        release_id=stage.prepared.release_id,
        demand_id=stage.demand_id,
        project_id=stage.project_id,
        projection="bound-requests",
        limit=1000,
    )
    snapshot = _selected_snapshot(clone.reader.begin, stage.prepared, request)
    use = next(
        node
        for node in snapshot.nodes
        if node.kind == "use" and json_loads(node.payload_json).get("id") == recorded["use_id"]
    )
    assert json_loads(use.payload_json)["request_id"] is None
    assert json_loads(use.payload_json)["fate"] == "awaiting-population"
    assert any(
        edge.target == use.identity
        and edge.source == "ddo.selected-obligation:" + json_bytes(obligation).decode()
        for edge in snapshot.occurrences
    )
    pins = json_loads(snapshot.pins_json)
    request = request.model_copy(
        update={"read_id": pins["read_id"], "expected_cut": pins["cut_id"]}
    )

    @contextmanager
    def reader():
        with clone.reader.begin() as connection:
            yield connection

    server = FastMCP("requestless-native-graph")
    register_source_inspection_tools(
        server, reader, project=stage.project_id, demand=stage.demand_id
    )

    async def inspect():
        async with Client(server) as client:
            result = await client.call_tool(
                "inspect_declared_graph", {"request": request.model_dump(mode="json")}
            )
            assert result.structured_content is not None
            assert any(
                item.get("identity") == use.identity for item in result.structured_content["items"]
            )
            resource = await client.read_resource(
                "corpus://declared-graph/"
                + base64.urlsafe_b64encode(json_bytes(request.model_dump())).decode()
            )
            assert isinstance(resource[0], TextResourceContents)
            assert any(
                item.get("identity") == use.identity
                for item in json_loads(resource[0].text)["items"]
            )

    anyio.run(inspect)


def test_native_graph_reader_exits_before_snapshot_and_topology(declared_serving_case, monkeypatch):
    import sqlite3

    from corpus_structure.semantic import graph_inspection, selected_graph
    from corpus_structure.semantic.graph_runtime import nx

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    request = GraphInspectionRequest(
        release_id=stage.prepared.release_id,
        demand_id=stage.demand_id,
        project_id=stage.project_id,
        projection="bound-requests",
        view="components",
    )
    events, indexes = [], []
    active = False

    @contextmanager
    def reader():
        nonlocal active
        with clone.reader.begin() as connection:
            active = True
            events.append("reader-entered")
            try:
                yield connection
            finally:
                active = False
        # This is after the real reader transaction committed and returned its
        # connection; authentication and FOR SHARE acquisition are not mocked.
        events.append("reader-exited")

    original_snapshot = selected_graph.selected_graph_snapshot
    original_components = nx.strongly_connected_components
    original_budget = selected_graph.selected_graph_budget_snapshot

    def snapshot(prepared, cut, index, selected_request):
        assert not active and events[-1] == "reader-exited"
        assert cut.record["demand_id"] == stage.demand_id
        assert cut.record["read_id"]
        assert tuple(index.records())
        indexes.append(index)
        events.append("snapshot")
        return original_snapshot(prepared, cut, index, selected_request)

    def components(*args, **kwargs):
        assert not active and events[-1] == "snapshot"
        events.append("components")
        return original_components(*args, **kwargs)

    def budget(prepared, selected_request, error):
        assert not active and events[-1] == "reader-exited"
        events.append("budget")
        return original_budget(prepared, selected_request, error)

    monkeypatch.setattr(selected_graph, "selected_graph_snapshot", snapshot)
    monkeypatch.setattr(selected_graph, "selected_graph_budget_snapshot", budget)
    monkeypatch.setattr(nx, "strongly_connected_components", components)
    page = graph_inspection.read_graph_inspection(reader, request)
    assert page.standing == "complete" and page.items
    assert events == ["reader-entered", "reader-exited", "snapshot", "components"]
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        indexes[0].connection.execute("SELECT count(*) FROM records")

    # A fresh budget-limited observation must commit its acquired native read
    # context, too. Reopening that exact cut in another transaction proves it.
    events.clear()
    bounded = graph_inspection.read_graph_inspection(
        reader, request.model_copy(update={"max_examined_bytes": 1024})
    )
    assert bounded.standing == "partial"
    assert events == ["reader-entered", "reader-exited", "budget"]
    pins = json_loads(bounded.pins_json)
    events.clear()
    replay = graph_inspection.read_graph_inspection(
        reader,
        request.model_copy(
            update={
                "max_examined_bytes": 1024,
                "read_id": pins["read_id"],
                "expected_cut": pins["cut_id"],
            }
        ),
    )
    assert replay.snapshot_id == bounded.snapshot_id
    assert events == ["reader-entered", "reader-exited", "budget"]
