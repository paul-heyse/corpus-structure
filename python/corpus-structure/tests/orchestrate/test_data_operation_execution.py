"""Actual supplied callable to native demand, intent, product and reuse."""

from uuid import uuid4

import pytest
from sqlalchemy import insert, text

from corpus_structure.orchestrate.data_operations import NativeDemandExecutor, NativeDemandExecutionError
from corpus_structure.semantic.data_operation_admission import (
    admit_data_operation_release,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_preparation import prepare_data_operation_inputs
from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding

from ..semantic.test_data_operation_storage import _declaration
from ..semantic.test_data_operation_storage import ddo_kernel_engine as ddo_kernel_engine


@pytest.fixture
def executable(ddo_kernel_engine, tmp_path, monkeypatch):
    name = "ddo_execution_" + uuid4().hex
    metadata = _declaration()
    metadata["id"] = "urn:ddo-execution:answer"
    metadata["roles"][0].update(collection="scalar", maximum=1)
    metadata["parameters"] = {"value": {"value_type": "integer", "default": 7}}
    metadata["capabilities"]["cancellation"] = "call-boundary"
    source = (
        "def answer(*, value: int = 7) -> int:\n    return value\n"
        f"answer__data_operation__ = {metadata!r}\n"
    )
    failed_metadata = {**metadata, "id": "urn:ddo-execution:broken"}
    source += (
        "def broken(*, value: int = 7) -> int:\n    raise ValueError('calculation failed')\n"
        f"broken__data_operation__ = {failed_metadata!r}\n"
    )
    path = tmp_path / (name + ".py")
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    (tmp_path / "schema.yaml").write_text(
        """id: urn:exec
name: target
prefixes: {x: "urn:exec:"}
default_prefix: x
types:
  integer: {base: int, uri: "http://www.w3.org/2001/XMLSchema#integer"}
classes:
  Thing: {}
"""
    )
    (tmp_path / "target.yaml").write_text(f"""version: data-operation-inputs-v1
root: target
schemas: [{{name: target, path: schema.yaml}}]
python:
  sources: [{{module: {name}, path: {name}.py}}]
  interpreter: python-3.14
  interpretation: closed-python-operations-v1
  stub_policy: source-authoritative
""")
    bundle, deps, profile, prepared = prepare_data_operation_inputs(tmp_path, "target.yaml")
    runtime = prepare_data_operation_runtime(
        prepared, deps.artifacts, execution_profile="execution:test", observed={}
    )
    sources = PythonSourceCollection((PythonSource(name, source.encode(), path.name),))
    with ddo_kernel_engine.begin() as conn:
        persist_release(conn, bundle, deps, profile, prepared)
        admit_data_operation_release(conn, prepared)
        persist_runtime_binding(conn, prepared, runtime)
        conn.execute(insert(table("data.project")).values(project_id="execution"))
    return ddo_kernel_engine, prepared, runtime, sources, {name: path}, bundle


def test_actual_callable_publishes_and_settled_resume_does_not_recompute(executable):
    engine, prepared, runtime, sources, locations, bundle = executable
    model = bound_data_operation_model(prepared)
    intent = freeze_demand(
        model,
        roots=(RootSubject("subject:one", "source:one", b"{}"),),
        targets=("urn:ddo-execution:answer",),
        inference="exact",
        execution_profile="execution:test",
    )
    with engine.begin() as conn:
        demand = DemandPlanner(model, DataOperationStorage(conn)).register(
            intent,
            project="execution",
            release=prepared.release_id,
            runtime=runtime.runtime_id,
        )["demand_id"]
    executor = NativeDemandExecutor(
        engine, prepared, runtime, sources, runtime_locations=locations, schema=bundle
    )
    result = executor.advance(demand)
    assert len(result.receipts) == 1
    assert executor.budget.used_bytes == 0
    resumed = executor.advance(demand)
    assert resumed.receipts == ()
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 1
        assert conn.scalar(text("SELECT count(*) FROM ops.data_completion_intent")) == 1
        assert conn.scalar(text("SELECT canonical_body FROM kb.data_product")) == ["integer", "7"]
        assert conn.scalar(text("SELECT count(*) FROM ops.task WHERE run_id IS NOT NULL")) == 0


def test_failed_request_keeps_later_page_siblings_and_bounded_native_receipts(executable):
    engine, prepared, runtime, sources, locations, bundle = executable
    model = bound_data_operation_model(prepared)
    intent = freeze_demand(
        model,
        roots=(RootSubject("subject:one", "source:one", b"{}"),
               RootSubject("subject:two", "source:two", b"{}")),
        targets=("urn:ddo-execution:answer", "urn:ddo-execution:broken"),
        inference="exact", execution_profile="execution:test",
    )
    with engine.begin() as conn:
        demand = DemandPlanner(model, DataOperationStorage(conn)).register(
            intent, project="execution", release=prepared.release_id, runtime=runtime.runtime_id,
        )["demand_id"]
    executor = NativeDemandExecutor(engine, prepared, runtime, sources,
                                    runtime_locations=locations, schema=bundle)
    with pytest.raises(NativeDemandExecutionError) as caught:
        executor.run(demand, limit=1)
    result = caught.value.result
    assert result.receipt_count == 2
    assert len(result.receipts) == 1 and result.receipts_truncated
    assert result.snapshot_standing == "fresh-read"
    assert len(caught.value.failures) == 2
    assert executor.budget.used_bytes == 0
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 2
        assert conn.scalar(text("SELECT count(*) FROM ops.data_publication_receipt")) == 2
        assert conn.scalar(text("SELECT count(*) FROM ops.data_attempt_failure")) == 2
        # Failed infrastructure attempts remain retryable; they did not publish
        # a fabricated domain-level failure outcome or destroy the good answers.
        assert conn.scalar(text("SELECT count(*) FROM ops.task WHERE status='failed'")) == 0
