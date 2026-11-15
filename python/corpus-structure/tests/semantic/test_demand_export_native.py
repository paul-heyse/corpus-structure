"""Actual native selected closure survives same-session export and detached verification."""

import json
from hashlib import sha256

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.demand_results import read_demand_result, stream_selected_support
from corpus_structure.serve.demand_export import export_demand_result, verify_demand_export
from semantic.serving_scenarios import declared_serving_case as declared_serving_case
from semantic.serving_scenarios import declared_serving_seed as declared_serving_seed


@pytest.mark.parametrize("encoding", ["jsonl", "parquet"])
def test_selected_export_preserves_actual_episode_closure_and_offline_identity(
    declared_serving_case, tmp_path, encoding
):
    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    destination = tmp_path / encoding
    with clone.reader.begin() as connection:
        manifest = export_demand_result(
            connection,
            stage.demand_id,
            project_id=stage.project_id,
            destination=destination,
            format=encoding,
            page_rows=1,
        )
    expected = sha256((destination / "manifest.json").read_bytes()).hexdigest()
    assert expected == manifest["manifest_digest"]
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
