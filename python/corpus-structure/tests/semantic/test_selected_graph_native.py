"""Actual selected topology, public delivery and detached graph reconstruction."""

import base64
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
import pytest
from fastmcp import Client, FastMCP
from mcp.types import TextResourceContents

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.graph_inspection import GraphInspectionRequest, read_graph_inspection
from corpus_structure.semantic.selected_graph import selected_graph_snapshot, snapshot_from_index
from corpus_structure.settings import Settings
from semantic.data_operation_kernel_support import ORIGINAL_FACT
from semantic.data_operation_original_support import OriginalSeedRecipe
from semantic.native_record_fixtures import RecordSourceRecipe
from semantic.serving_scenarios import declared_serving_case as declared_serving_case
from semantic.serving_scenarios import declared_serving_seed as declared_serving_seed


def _offline_snapshot(destination, projection):
    from corpus_structure.semantic.archive_reader import open_release_parts
    from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
    from corpus_structure.semantic.demand_results import CutSelection

    manifest = json_loads((destination / "manifest.json").read_bytes())

    def unpack(row):
        return {
            key: bytes.fromhex(value) if key in row["binary"] else value
            for key, value in row["values"].items()
        }

    release = manifest["cut"]["release_id"]
    captured = json_loads((destination / manifest["releases"][release]).read_bytes())
    prepared = open_release_parts(
        release,
        unpack(captured["row"]),
        [unpack(row) for row in captured["inputs"]],
        [unpack(row) for row in captured["artifacts"]],
    )
    scratch = TemporaryDirectory(prefix="offline-graph-")
    index = SelectedRecordIndex(Path(scratch.name) / "inspection.sqlite")
    try:
        for row in (destination / manifest["closure"]).read_bytes().splitlines():
            index.append(row)
        for page in manifest["pages"]:
            index.append_page(json_loads((destination / page).read_bytes()))
        return snapshot_from_index(
            prepared, CutSelection(json_bytes(manifest["cut"])), index, projection
        )
    finally:
        index.close()
        scratch.cleanup()


@pytest.mark.parametrize("encoding", ["jsonl", "parquet"])
def test_actual_selected_precedence_support_public_and_offline(
    declared_serving_case, tmp_path, encoding, cli, monkeypatch
):
    from corpus_structure.intervene.source_inspection_tools import register_source_inspection_tools
    from corpus_structure.semantic import prepare, python_operation_sources
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.serve.demand_export import export_demand_result, verify_demand_export

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    request = GraphInspectionRequest(
        release_id=stage.prepared.release_id,
        demand_id=stage.demand_id,
        project_id=stage.project_id,
        projection="bound-requests",
        limit=1,
    )
    with clone.reader.begin() as connection:
        page = read_graph_inspection(connection, request)
        assert page.standing == "complete"
        assert page.continuation is not None
        second = read_graph_inspection(
            connection, request.model_copy(update={"cursor": page.continuation})
        )
        assert second.snapshot_id == page.snapshot_id
        with pytest.raises(ValueError):
            read_graph_inspection(
                connection,
                request.model_copy(
                    update={"cursor": page.continuation, "scope": {"subject": "wrong"}}
                ),
            )
        snapshot = selected_graph_snapshot(
            connection, open_release(connection, request.release_id), request
        )
        kinds = {node.identity: node.kind for node in snapshot.nodes}
        assert any(
            edge.relation == "selected-input"
            and kinds[edge.source] == "use"
            and kinds[edge.target] == "request"
            for edge in snapshot.occurrences
        )
        assert set(kinds.values()) <= {"request", "use", "population", "obligation"}
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
    with clone.reader.begin() as connection:
        live = selected_graph_snapshot(connection, stage.prepared, pinned)
        bounded = selected_graph_snapshot(
            connection, stage.prepared, pinned.model_copy(update={"max_examined_bytes": 1024})
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
    with clone.reader.begin() as connection:
        support = selected_graph_snapshot(connection, stage.prepared, support_request)
    assert any(edge.relation == "support" for edge in support.occurrences)
    assert _offline_snapshot(destination, "selected-support").identity == support.identity
    url = clone.reader.url.render_as_string(hide_password=False)
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


@pytest.mark.parametrize(
    "ddo_original_source", [OriginalSeedRecipe(RecordSourceRecipe(), ORIGINAL_FACT)], indirect=True
)
def test_actual_original_source_hierarchy_keeps_native_pointer_custody(
    ddo_original_source, tmp_path
):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner, freeze_demand
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.source_admission import acquire_original_source_selection
    from corpus_structure.serve.demand_export import export_demand_result
    from semantic.native_record_fixtures import claim_record_source
    from semantic.original_source_fixture import completed_original_source_reference

    source = claim_record_source(
        ddo_original_source.source,
        writer=ddo_original_source.writer,
        clone=ddo_original_source.clone,
    )
    reference, selectors = completed_original_source_reference(source)
    kernel = ddo_original_source.kernel
    with ddo_original_source.admin.begin() as connection:
        acquired = acquire_original_source_selection(
            connection, kernel.prepared, reference, selectors
        )
        intent = freeze_demand(
            kernel.model,
            roots=(acquired.root,),
            targets=("urn:original-fact-test:consume",),
            inference="source-graph",
            execution_profile="execution:original-fact",
            original_sources=(acquired.selection(),),
        )
        demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
            intent,
            project=source.project_id,
            release=kernel.prepared.release_id,
            runtime=kernel.runtime,
        )["demand_id"]
    request = GraphInspectionRequest(
        release_id=kernel.prepared.release_id,
        demand_id=demand,
        project_id=source.project_id,
        projection="source-hierarchy",
    )
    with kernel.purpose("read").begin() as connection:
        snapshot = selected_graph_snapshot(connection, kernel.prepared, request)
        assert snapshot.nodes
        assert {node.kind for node in snapshot.nodes} == {"record"}
        pointers = {json_loads(node.payload_json)["atom"]["self_ref"] for node in snapshot.nodes}
        assert all(pointer.startswith("#/") for pointer in pointers)
        assert {"#/groups/0", "#/tables/0"} <= pointers
        atoms = {json_loads(node.payload_json)["atom"]["self_ref"]:json_loads(node.payload_json)["atom"] for node in snapshot.nodes}
        cells = atoms["#/tables/0"]["data"]["table_cells"]
        assert [cell["text"] for cell in cells] == ["12", "12"]
        assert [cell["start_col_offset_idx"] for cell in cells] == [0, 1]
        assert any(edge.source.endswith(":#/groups/0") and edge.target.endswith(":#/tables/0") and edge.position == 0 for edge in snapshot.occurrences)
        assert all(edge.relation=="contains" for edge in snapshot.occurrences)
        assert snapshot.occurrences
        destination = tmp_path / "source"
        manifest = export_demand_result(
            connection,
            demand,
            project_id=source.project_id,
            destination=destination,
            format="jsonl",
        )
    pinned = request.model_copy(
        update={"read_id": manifest["cut"]["read_id"], "expected_cut": manifest["cut_id"]}
    )
    with kernel.purpose("read").begin() as connection:
        live = selected_graph_snapshot(connection, kernel.prepared, pinned)
    assert _offline_snapshot(destination, "source-hierarchy").identity == live.identity


def test_native_requestless_population_fate_survives_tools_and_resources(declared_serving_case):
    from typing import cast
    from corpus_structure.semantic._data_operation_wire import WireRecordDataFateRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.demand_results import read_demand_result
    from corpus_structure.intervene.source_inspection_tools import register_source_inspection_tools
    clone,stage=declared_serving_case,declared_serving_case.stage.agent
    with clone.writer.begin() as connection:
        page=read_demand_result(connection,stage.demand_id,project_id=stage.project_id)
        obligation=page.record["obligations"][0]["obligation_id"]
        recorded=DataOperationStorage(connection).record_data_fate(cast(WireRecordDataFateRequest,dict(obligation_id=obligation,fate="awaiting-population",selection={})))
    request=GraphInspectionRequest(release_id=stage.prepared.release_id,demand_id=stage.demand_id,project_id=stage.project_id,projection="bound-requests",limit=1000)
    with clone.reader.begin() as connection:
        snapshot=selected_graph_snapshot(connection,stage.prepared,request)
    use=next(node for node in snapshot.nodes if node.kind=="use" and json_loads(node.payload_json).get("id")==recorded["use_id"])
    assert json_loads(use.payload_json)["request_id"] is None
    assert json_loads(use.payload_json)["fate"]=="awaiting-population"
    assert any(edge.target==use.identity and edge.source=='ddo.selected-obligation:'+json_bytes(obligation).decode() for edge in snapshot.occurrences)
    pins=json_loads(snapshot.pins_json)
    request=request.model_copy(update={"read_id":pins["read_id"],"expected_cut":pins["cut_id"]})
    @contextmanager
    def reader():
        with clone.reader.begin() as connection:
            yield connection
    server=FastMCP("requestless-native-graph")
    register_source_inspection_tools(server,reader,project=stage.project_id,demand=stage.demand_id)
    async def inspect():
        async with Client(server) as client:
            result=await client.call_tool("inspect_declared_graph",{"request":request.model_dump(mode="json")})
            assert result.structured_content is not None
            assert any(item.get("identity")==use.identity for item in result.structured_content["items"])
            resource=await client.read_resource("corpus://declared-graph/"+base64.urlsafe_b64encode(json_bytes(request.model_dump())).decode())
            assert isinstance(resource[0],TextResourceContents)
            assert any(item.get("identity")==use.identity for item in json_loads(resource[0].text)["items"])
    anyio.run(inspect)
