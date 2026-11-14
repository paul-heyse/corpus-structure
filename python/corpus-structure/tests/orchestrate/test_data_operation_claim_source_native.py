"""A captured production callable executes through native demand custody."""

import json

import pytest
from semantic.data_operation_demand_support import (
    claim,
    publish,
    retain,
)
from semantic.data_operation_kernel_support import CLAIM_SOURCE, CLAIM_SOURCE_PATH, prepare_kernel
from sqlalchemy import text

from corpus_structure.orchestrate.data_operations import NativeDemandExecutor
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection


def _prepare_production_claim():
    preparation = prepare_kernel(CLAIM_SOURCE)
    model = preparation.model
    operation = model.operation("urn:corpus:operation:claim-source-item")
    assert (
        operation.callable_surfaces[0].declaration
        == "corpus_structure.semantic.identity.claim_source_item"
    )
    assert operation.outcomes == ("addressed", "invalid-index")
    assert len(model.implementation_slices) == 1 and model.implementation_slices[0].complete
    return (
        preparation.bundle,
        preparation.dependencies,
        preparation.profile,
        preparation.prepared,
        model,
        CLAIM_SOURCE_PATH,
        CLAIM_SOURCE.python_sources[0][2],
    )


def test_production_claim_source_item_prepares_with_authoritative_builtin_kinds():
    _, _, _, _, model, _, _ = _prepare_production_claim()
    operation = model.operation("urn:corpus:operation:claim-source-item")
    assert {role.name: role.kind for role in operation.roles} == {
        "index": "primitive:integer",
        "address": "primitive:string",
    }
    assert model.operation("urn:ddo-test:source").roles[0].kind == "primitive:integer"


@pytest.mark.parametrize("ddo_kernel", [CLAIM_SOURCE], indirect=True, ids=["claim-source"])
def test_production_claim_source_item_publishes_then_resumes_settled(ddo_kernel):
    bundle, _dependencies, _profile, prepared, model, actual, captured = _prepare_production_claim()
    module = "corpus_structure.semantic.identity"
    operation_id = "urn:corpus:operation:claim-source-item"
    runtime = ddo_kernel.preparation.runtime

    intent = freeze_demand(
        model,
        roots=(RootSubject("subject:one", "source:test", b'{"page":1}'),),
        targets=("urn:ddo-test:source", operation_id),
        inference="inference:test",
        execution_profile="execution:test",
    )
    with ddo_kernel["engine"].begin() as connection:
        demand = DemandPlanner(model, DataOperationStorage(connection)).register(
            intent,
            project="ddo-test",
            release=prepared.release_id,
            runtime=runtime.runtime_id,
        )["demand_id"]
        planner = DemandPlanner(model, DataOperationStorage(connection))
        initial = planner.ready(planner.resume(demand), authorization=b"{}")
        assert len(initial) == 1 and initial[0].operation == "urn:ddo-test:source"
    # Establish the input in this demand through native claim and publication.
    fence = claim(ddo_kernel, json.loads(initial[0].native))
    publish(ddo_kernel, fence, retain(ddo_kernel, fence, outputs=(7,)))
    executor = NativeDemandExecutor(
        ddo_kernel["engine"],
        prepared,
        runtime,
        PythonSourceCollection((PythonSource(module, captured, "identity.py"),)),
        runtime_locations={module: actual},
        schema=bundle,
    )
    completed = executor.advance(demand)
    assert completed.receipt_count == 1 and len(completed.receipts) == 1
    assert executor.ports[operation_id].function.__module__ == module
    assert executor.ports[operation_id].function.__name__ == "claim_source_item"
    assert executor.budget.used_bytes == 0
    resumed = executor.advance(demand)
    assert resumed.receipt_count == 0 and resumed.receipts == ()
    with ddo_kernel["engine"].begin() as connection:
        result = DataOperationStorage(connection).invoke(
            "read_demand_result",
            {"demand_id": demand, "view": "products"},
        )
        assert len(result["uses"]) == 2
        use = next(
            use
            for use in result["uses"]
            if any(product["role"] == "address" for product in use["products"])
        )
        assert use["fate"] == "fulfilled"
        assert [product["body"] for product in use["products"]] == [["string", "claims/7"]]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 2
        assert connection.scalar(text("SELECT count(*) FROM ops.data_completion_intent")) == 2
        assert (
            connection.scalar(text("SELECT count(*) FROM ops.task WHERE run_id IS NOT NULL")) == 0
        )
