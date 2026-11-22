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
    from corpus_structure.semantic import native_protocol_authoring
    from corpus_structure.serve import demand_export

    support_calls = []
    original_support = demand_export.stream_selected_archive

    def support_once(*args, **kwargs):
        support_calls.append(kwargs)
        return original_support(*args, **kwargs)

    monkeypatch.setattr(demand_export, "stream_selected_archive", support_once)

    def unexpected_generation(*args, **kwargs):
        raise AssertionError("export must use the acquiring reader's wire contract")

    monkeypatch.setattr(native_protocol_authoring, "native_protocol_sources", unexpected_generation)
    with clone.reader.begin() as connection:
        manifest = export_demand_result(
            connection,
            stage.demand_id,
            project_id=stage.project_id,
            destination=destination,
            format=encoding,
            page_rows=1,
        )
    assert support_calls == [{"max_bytes": 8388608}]
    expected = sha256((destination / "manifest.json").read_bytes()).hexdigest()
    assert expected == manifest.manifest_digest
    # This authored external recipe has no Python declarations to document.
    assert all(
        artifact["values"]["artifact_name"] != SOURCE_INTERFACE_ARTIFACT
        for name in manifest.manifest.releases.values()
        for artifact in json_loads((destination / name).read_bytes())["artifacts"]
    )

    checked = verify_demand_export(destination, manifest_digest=expected)
    assert checked["cut_id"] == manifest.manifest.cut_id
    pages = [json_loads((destination / name).read_bytes()) for name in manifest.manifest.pages]
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
        json_loads(line)
        for line in (destination / manifest.manifest.closure).read_bytes().splitlines()
    ]
    assert {
        "ops.data_derivation",
        "ops.data_completion_intent",
        "ops.data_publication_receipt",
    } <= {row["relation"] for row in closure}
    assert manifest.manifest.cut["demand_id"] == stage.demand_id
    assert manifest.manifest.cut["project_id"] == stage.project_id

    # Even a newly trusted transfer digest cannot make an incomplete semantic
    # witness valid. Keep every product and archived schema, remove its episode.
    closure_path = destination / manifest.manifest.closure
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
    captured["files"][manifest.manifest.closure].update(
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


@pytest.mark.parametrize("batch_rows", [1, 64])
def test_native_archive_prepares_once_and_keeps_exact_whole_read_support(
    declared_serving_case, batch_rows
):
    from sqlalchemy import event

    from corpus_structure.semantic.demand_results import stream_selected_archive

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    calls = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        calls.append(statement)

    with clone.reader.begin() as connection:
        page = read_demand_result(connection, stage.demand_id, project_id=stage.project_id, limit=1)
        expected = {
            record["key"]: json_bytes(record)
            for record in stream_selected_support(connection, page, whole_read=True)
            if record["relation"] != "ops.data_support_explanation"
        }
        event.listen(connection, "before_cursor_execute", observe)
        actual = list(stream_selected_archive(connection, page.cut, batch_rows=batch_rows))
        event.remove(connection, "before_cursor_execute", observe)
    assert {record["key"]: json_bytes(record) for record in actual} == expected
    assert len(actual) == len(expected)
    assert [record["key"] for record in actual] == sorted(expected)
    assert sum("begin_selected_archive" in statement for statement in calls) == 1
    assert sum("close_selected_archive" in statement for statement in calls) == 1
    assert (
        sum("fetch_selected_archive" in statement for statement in calls)
        == (len(expected) + batch_rows - 1) // batch_rows
    )


def test_native_archive_byte_batches_keep_every_record(declared_serving_case):
    from sqlalchemy import Text, bindparam, cast, func, select
    from sqlalchemy.dialects.postgresql import JSONB

    from corpus_structure.semantic.demand_results import stream_selected_archive

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with clone.reader.begin() as connection:
        page = read_demand_result(connection, stage.demand_id, project_id=stage.project_id, limit=1)
        expected = list(stream_selected_archive(connection, page.cut))
        wire_bytes = select(
            func.octet_length(cast(cast(bindparam("reply", type_=Text), JSONB), Text))
        )

        def size(records):
            return connection.scalar(
                wire_bytes, {"reply": json_bytes({"records": records, "complete": False}).decode()}
            )

        bound = max(size([record]) for record in expected)
        assert bound < size(expected)
        actual = list(stream_selected_archive(connection, page.cut, max_bytes=bound))
    assert actual == expected


def test_native_archive_refuses_one_record_larger_than_byte_bound(declared_serving_case):
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.demand_results import stream_selected_archive

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with pytest.raises(DBAPIError, match=r"max_bytes|byte"), clone.reader.begin() as connection:
        page = read_demand_result(connection, stage.demand_id, project_id=stage.project_id, limit=1)
        list(stream_selected_archive(connection, page.cut, max_bytes=64))


def test_native_archive_handle_ends_with_its_transaction(declared_serving_case):
    from sqlalchemy import Text, bindparam, cast, func, select
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.data_operation_json import native_json_loads

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with clone.reader.connect() as connection:
        with connection.begin():
            page = read_demand_result(
                connection, stage.demand_id, project_id=stage.project_id, limit=1
            )
            opened = connection.scalar(
                select(
                    cast(
                        func.ops.begin_selected_archive(
                            cast(bindparam("cut", type_=Text), JSONB), 64, 8388608
                        ),
                        Text,
                    )
                ),
                {"cut": json_bytes(page.cut.record).decode()},
            )
            handle = native_json_loads(opened)["handle"]
        with pytest.raises(DBAPIError), connection.begin():
            connection.scalar(select(func.ops.fetch_selected_archive(handle)))


def test_export_support_byte_refusal_leaves_no_published_destination(
    declared_serving_case, tmp_path, monkeypatch
):
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.serve import demand_export

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    destination = tmp_path / "refused-export"
    existing_paths = set(tmp_path.iterdir())
    original_support = demand_export.stream_selected_archive

    def oversized_support(connection, cut, **kwargs):
        return original_support(connection, cut, max_bytes=64)

    monkeypatch.setattr(demand_export, "stream_selected_archive", oversized_support)
    with pytest.raises(DBAPIError, match=r"max_bytes|byte"), clone.reader.begin() as connection:
        export_demand_result(
            connection,
            stage.demand_id,
            project_id=stage.project_id,
            destination=destination,
        )
    assert not destination.exists()
    assert set(tmp_path.iterdir()) == existing_paths


def test_native_archive_empty_product_scope_completes(declared_serving_case):
    from corpus_structure.semantic.demand_results import stream_selected_archive

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with clone.reader.begin() as connection:
        page = read_demand_result(
            connection,
            stage.demand_id,
            project_id=stage.project_id,
            scope={"product_ids": ["product:absent-from-declared-serving-fixture"]},
        )
        assert list(stream_selected_archive(connection, page.cut)) == []


@pytest.mark.parametrize("scratch", ["selected_archive_sessions", "selected_archive_keys"])
def test_native_archive_refuses_precreated_scratch(declared_serving_case, scratch):
    from sqlalchemy import Text, bindparam, cast, func, select
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.exc import DBAPIError

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with (
        pytest.raises(DBAPIError, match="scratch custody or shape differs"),
        clone.admin.begin() as connection,
    ):
        page = read_demand_result(connection, stage.demand_id, project_id=stage.project_id, limit=1)
        connection.exec_driver_sql(f"CREATE TEMPORARY TABLE {scratch} (spoof text)")
        connection.scalar(
            select(
                func.ops.begin_selected_archive(
                    cast(bindparam("cut", type_=Text), JSONB), 64, 8388608
                )
            ),
            {"cut": json_bytes(page.cut.record).decode()},
        )


@pytest.mark.parametrize("scratch", ["selected_archive_sessions", "selected_archive_keys"])
def test_native_archive_reader_cannot_read_private_stage(declared_serving_case, scratch):
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.demand_results import stream_selected_archive

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with pytest.raises(DBAPIError, match="permission denied"), clone.reader.begin() as connection:
        page = read_demand_result(connection, stage.demand_id, project_id=stage.project_id, limit=1)
        records = stream_selected_archive(connection, page.cut, batch_rows=1)
        try:
            next(records)
            connection.exec_driver_sql(f"SELECT * FROM pg_temp.{scratch}").all()
        finally:
            records.close()


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
    assert manifest.manifest_digest == expected

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

    assert manifest.manifest.releases
    for release_id, name in manifest.manifest.releases.items():
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
    assert checked["cut_id"] == manifest.manifest.cut_id
    assert checked["inference"] == "not_run"


def test_whole_read_support_is_distinct_and_covers_later_frontier_pages(declared_serving_case):
    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    with clone.reader.begin() as connection:
        complete = read_demand_result(connection, stage.demand_id, project_id=stage.project_id)
        expected = {row["product_id"] for row in complete.members()}
        first = read_demand_result(
            connection,
            stage.demand_id,
            project_id=stage.project_id,
            limit=1,
            view="frontier",
            recheck_bodies=True,
        )
        assert first.continuation is not None
        first_products = {
            product["product_id"] for use in first.record["uses"] for product in use["products"]
        }
        assert first_products < expected
        support = list(stream_selected_support(connection, first, whole_read=True))
    keys = [row["key"] for row in support]
    assert len(keys) == len(set(keys))
    products = {row["record"]["id"] for row in support if row["relation"] == "kb.data_product"}
    assert expected <= products


def test_exported_selected_inputs_use_consumed_selection_without_request_binding(
    declared_serving_case, tmp_path
):
    from corpus_structure.semantic.selected_contribution_input import actual_graph_inputs
    from corpus_structure.semantic.value_codec import decimal_digit_limit
    from corpus_structure.serve.demand_export import verified_demand_export

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    destination = tmp_path / "selected-inputs"
    with clone.reader.begin() as connection:
        receipt = export_demand_result(
            connection,
            stage.demand_id,
            project_id=stage.project_id,
            destination=destination,
            format="jsonl",
            page_rows=1,
        )
    with verified_demand_export(destination, manifest_digest=receipt.manifest_digest) as (
        manifest,
        _,
        _,
        index,
    ):
        assert all("binding" not in row for row in index.rows("ops.data_request"))
        use = next(
            row
            for row in index.frontier_rows("uses")
            if row["fate"] == "fulfilled" and row["selection"].get("inputs")
        )
        references, _ = actual_graph_inputs(
            index,
            use["derivation_id"],
            use_id=use["use_id"],
            cut=manifest.cut_selection,
            max_support_edges=100,
            decimal_fixed_point_digits=decimal_digit_limit(),
        )
        assert {(row.product_id, row.member_id) for row in references} == {
            (row["product_id"], row.get("member_id")) for row in use["selection"]["inputs"]
        }
