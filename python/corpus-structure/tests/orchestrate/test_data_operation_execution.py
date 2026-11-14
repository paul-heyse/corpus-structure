"""Actual supplied callable to native demand, intent, product and reuse."""

import pytest
from semantic.data_operation_kernel_support import EXECUTION
from sqlalchemy import text

from corpus_structure.orchestrate.data_operations import (
    NativeDemandExecutionError,
    NativeDemandExecutor,
)
from corpus_structure.semantic.data_operation_admission import (
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection

pytestmark = pytest.mark.parametrize("ddo_kernel", [EXECUTION], indirect=True, ids=["execution"])


@pytest.fixture
def executable(ddo_kernel, monkeypatch):
    preparation = ddo_kernel.preparation
    monkeypatch.syspath_prepend(str(preparation.directory))
    sources = PythonSourceCollection(
        tuple(
            PythonSource(module, content, filename)
            for module, filename, content in EXECUTION.python_sources
        )
    )
    locations = {
        module: preparation.directory / filename for module, filename, _ in EXECUTION.python_sources
    }
    return (
        ddo_kernel["engine"],
        ddo_kernel["prepared"],
        preparation.runtime,
        sources,
        locations,
        preparation.bundle,
    )


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


def test_retained_demand_service_executes_archived_inputs_without_a_run_anchor(executable):
    from corpus_structure.semantic.data_operation_service import execute_data_demand

    engine, prepared, runtime, sources, locations, _ = executable
    model = bound_data_operation_model(prepared)
    intent = freeze_demand(
        model,
        roots=(RootSubject("subject:service", "source:original", b"{}"),),
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
    root = next(iter(locations.values())).parent
    result = execute_data_demand(engine, demand, source_root=root)
    assert result.demand_id == demand
    assert result.receipt_count == 1
    resumed = execute_data_demand(engine, demand, source_root=root)
    assert resumed.receipt_count == 0
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 1
        assert conn.scalar(text("SELECT count(*) FROM ops.run")) == 0


def test_failed_request_keeps_later_page_siblings_and_bounded_native_receipts(executable):
    engine, prepared, runtime, sources, locations, bundle = executable
    model = bound_data_operation_model(prepared)
    intent = freeze_demand(
        model,
        roots=(
            RootSubject("subject:one", "source:one", b"{}"),
            RootSubject("subject:two", "source:two", b"{}"),
        ),
        targets=("urn:ddo-execution:answer", "urn:ddo-execution:broken"),
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
