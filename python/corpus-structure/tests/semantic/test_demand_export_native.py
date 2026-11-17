"""Actual native selected closure survives same-session export and detached verification."""

import json
import sys
from hashlib import sha256

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.demand_results import read_demand_result, stream_selected_support
from corpus_structure.semantic.source_interfaces import (
    SOURCE_INTERFACE_ARTIFACT,
    read_source_interfaces,
)
from corpus_structure.serve.demand_export import export_demand_result, verify_demand_export
from semantic.data_operation_kernel_support import EXECUTION
from semantic.declared_scenarios import declared_serving_case as declared_serving_case
from semantic.declared_scenarios import declared_serving_seed as declared_serving_seed


@pytest.mark.parametrize("encoding", ["jsonl", "parquet"])
def test_selected_export_preserves_actual_episode_closure_and_offline_identity(
    declared_serving_case, tmp_path, encoding, monkeypatch
):
    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    destination = tmp_path / encoding
    from corpus_structure.serve import demand_export
    support_calls = []
    original_support = demand_export.stream_selected_support

    def support_once(*args, **kwargs):
        support_calls.append(kwargs)
        return original_support(*args, **kwargs)

    monkeypatch.setattr(demand_export, "stream_selected_support", support_once)
    with clone.reader.begin() as connection:
        manifest = export_demand_result(
            connection,
            stage.demand_id,
            project_id=stage.project_id,
            destination=destination,
            format=encoding,
            page_rows=1,
        )
    assert len(support_calls) == 1 and support_calls[0]["whole_read"] is True
    expected = sha256((destination / "manifest.json").read_bytes()).hexdigest()
    assert expected == manifest["manifest_digest"]
    # This authored external recipe has no Python declarations to document.
    assert all(
        artifact["values"]["artifact_name"] != SOURCE_INTERFACE_ARTIFACT
        for name in manifest["releases"].values()
        for artifact in json_loads((destination / name).read_bytes())["artifacts"]
    )

    checked = verify_demand_export(destination, manifest_digest=expected)
    assert checked["cut_id"] == manifest["cut_id"]
    pages = [json_loads((destination / name).read_bytes()) for name in manifest["pages"]]
    outputs = [output for page in pages for use in page["uses"] for output in use["products"]]
    assert sorted(int(output["body"][1]) for output in outputs) == [3, 5, 7]
    source_episode = json.loads(stage.source_receipt)["derivation_id"]
    assert {
        use["derivation_id"]
        for page in pages
        for use in page["uses"]
        if any(int(output["body"][1]) in {3, 5} for output in use["products"])
    } == {source_episode}
    closure = [
        json_loads(line) for line in (destination / manifest["closure"]).read_bytes().splitlines()
    ]
    assert {
        "ops.data_derivation",
        "ops.data_completion_intent",
        "ops.data_publication_receipt",
    } <= {row["relation"] for row in closure}
    assert manifest["cut"]["demand_id"] == stage.demand_id
    assert manifest["cut"]["project_id"] == stage.project_id

    # Even a newly trusted transfer digest cannot make an incomplete semantic
    # witness valid. Keep every product and archived schema, remove its episode.
    closure_path = destination / manifest["closure"]
    retained = [
        row
        for row in closure
        if not (
            (row["relation"] == "ops.data_derivation" and row["record"]["id"] == source_episode)
            or (
                row["relation"].startswith("ops.data_derivation_")
                and row["record"]["derivation_id"] == source_episode
            )
        )
    ]
    altered = b"".join(json_bytes(row) + b"\n" for row in retained)
    closure_path.write_bytes(altered)
    captured = json_loads((destination / "manifest.json").read_bytes())
    captured["files"][manifest["closure"]].update(
        sha256=sha256(altered).hexdigest(), bytes=len(altered)
    )
    changed = json_bytes(captured)
    (destination / "manifest.json").write_bytes(changed)
    with pytest.raises(ValueError):
        verify_demand_export(destination, manifest_digest=sha256(changed).hexdigest())


def test_selected_product_scope_filters_inside_native_page_and_keeps_support(
    declared_serving_case,
):
    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with clone.reader.begin() as connection:
        complete = read_demand_result(connection, stage.demand_id, project_id=stage.project_id)
        result = next(row for row in complete.members() if row["body"] == 7)
        selected = read_demand_result(
            connection,
            stage.demand_id,
            project_id=stage.project_id,
            scope={"product_ids": [result["product_id"]]},
            limit=1,
        )
        assert [row["body"] for row in selected.members()] == [7]
        assert selected.continuation is None
        support = list(stream_selected_support(connection, selected))
    products = {row["record"]["id"] for row in support if row["relation"] == "kb.data_product"}
    assert {row["product_id"] for row in complete.members()} <= products
    assert selected.cut.record["scope"] == {"product_ids": [result["product_id"]]}


@pytest.mark.parametrize("ddo_kernel", [EXECUTION], indirect=True)
@pytest.mark.parametrize("encoding", ["jsonl", "parquet"])
def test_python_producer_export_keeps_prepared_interfaces_readable_offline(
    ddo_kernel, tmp_path, encoding, monkeypatch
):
    from corpus_structure.semantic.data_operation_demands import (
        DemandPlanner,
        RootSubject,
        freeze_demand,
    )
    from corpus_structure.semantic.data_operation_service import execute_data_demand
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage

    kernel = ddo_kernel
    intent = freeze_demand(
        kernel.model,
        roots=(RootSubject("one", "source:one", b"{}"),),
        targets=("urn:ddo-execution:answer",),
        inference="detached-python-source-facts",
        execution_profile="execution:test",
    )
    with kernel.engine.begin() as connection:
        demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
            intent,
            project="execution",
            release=kernel.prepared.release_id,
            runtime=kernel.runtime,
        )["demand_id"]
    module = kernel.recipe.python_sources[0][0]
    monkeypatch.delitem(sys.modules, module, raising=False)
    monkeypatch.syspath_prepend(str(kernel.preparation.directory))
    executed = execute_data_demand(
        kernel.engine,
        demand,
        project_id="execution",
        source_root=kernel.preparation.directory,
        database_capacity=4,
    )
    assert executed.receipt_count == 1
    destination = tmp_path / encoding
    with kernel.engine.begin() as connection:
        selected = read_demand_result(connection, demand, project_id="execution")
        assert [row["body"] for row in selected.members()] == [7]
        manifest = export_demand_result(
            connection,
            demand,
            project_id="execution",
            destination=destination,
            format=encoding,
            page_rows=1,
        )
    expected = sha256((destination / "manifest.json").read_bytes()).hexdigest()
    assert manifest["manifest_digest"] == expected

    # Detached verification and interface reads must consume the captured release
    # facts without preparing a release or reparsing currently installed sources.
    from corpus_structure.semantic import (
        data_operation_compilation,
        prepare,
        python_operation_sources,
    )
    from corpus_structure.semantic.archive_reader import open_release_parts

    def forbid_reanalysis(*args, **kwargs):
        raise AssertionError("detached release reads must not reanalyse target sources")

    monkeypatch.setattr(python_operation_sources.ClosedPythonSources, "__init__", forbid_reanalysis)
    monkeypatch.setattr(data_operation_compilation, "compile_data_operations", forbid_reanalysis)
    monkeypatch.setattr(prepare, "prepare_release", forbid_reanalysis)

    def unpack(row):
        return {
            key: bytes.fromhex(value) if key in row["binary"] else value
            for key, value in row["values"].items()
        }

    assert manifest["releases"]
    for release_id, name in manifest["releases"].items():
        captured = json_loads((destination / name).read_bytes())
        artifact_rows = [unpack(row) for row in captured["artifacts"]]
        sidecars = [
            row for row in artifact_rows if row["artifact_name"] == SOURCE_INTERFACE_ARTIFACT
        ]
        assert len(sidecars) == 1
        sidecar = sidecars[0]["content"]
        assert sha256(sidecar).hexdigest() == sidecars[0]["content_digest"]
        detached = open_release_parts(
            release_id,
            unpack(captured["row"]),
            [unpack(row) for row in captured["inputs"]],
            artifact_rows,
        )
        interfaces = read_source_interfaces(detached)
        assert interfaces is not None
        assert interfaces.version == "data-operation-source-interfaces-v2"
        assert interfaces.content == sidecar
        assert interfaces.operations
        assert all(operation.documentation is not None for operation in interfaces.operations)
        assert (
            json.loads(detached.manifest)["data_operation_source_interfaces"]
            == sha256(sidecar).hexdigest()
        )

    checked = verify_demand_export(destination, manifest_digest=expected)
    assert checked["outcome"] == "passed"
    assert checked["cut_id"] == manifest["cut_id"]
    assert checked["inference"] == "not_run"


def test_whole_read_support_is_distinct_and_covers_later_frontier_pages(declared_serving_case):
    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with clone.reader.begin() as connection:
        complete = read_demand_result(connection, stage.demand_id, project_id=stage.project_id)
        expected = {row["product_id"] for row in complete.members()}
        first = read_demand_result(connection, stage.demand_id, project_id=stage.project_id,
                                   limit=1, view="frontier", recheck_bodies=True)
        assert first.continuation is not None
        first_products = {product["product_id"] for use in first.record["uses"] for product in use["products"]}
        assert first_products < expected
        support = list(stream_selected_support(connection, first, whole_read=True))
    keys = [row["key"] for row in support]
    assert len(keys) == len(set(keys))
    products = {row["record"]["id"] for row in support if row["relation"] == "kb.data_product"}
    assert expected <= products
