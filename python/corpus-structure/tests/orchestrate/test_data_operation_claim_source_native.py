"""A captured production callable executes through native demand custody."""

from pathlib import Path

from sqlalchemy import insert, text

from corpus_structure.orchestrate.data_operations import NativeDemandExecutor
from corpus_structure.semantic.data_operation_admission import (
    admit_data_operation_release,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner, RootSubject, freeze_demand
from corpus_structure.semantic.data_operation_preparation import prepare_data_operation_inputs
from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding

from ..semantic.test_data_operation_storage import (
    _declaration,
    attach,
    claim,
    publish,
    retain,
)
from ..semantic.test_data_operation_storage import ddo_kernel_engine as ddo_kernel_engine


def test_production_claim_source_item_publishes_then_resumes_settled(ddo_kernel_engine, tmp_path):
    module = "corpus_structure.semantic.identity"
    actual = Path(__file__).parents[2] / "src/corpus_structure/semantic/identity.py"
    captured = actual.read_bytes()
    (tmp_path / "identity.py").write_bytes(captured)
    (tmp_path / "schema.yaml").write_text("""id: urn:production-claim-test
name: target
prefixes: {t: 'urn:production-claim-test:'}
default_prefix: t
types:
  integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
  Thing: {}
""")
    (tmp_path / "seed.yaml").write_bytes(canonical_bytes({
        "version": "data-operation-model-v1", "operations": [_declaration()],
    }))
    (tmp_path / "target.yaml").write_text(f"""version: data-operation-inputs-v1
root: target
schemas: [{{name: target, path: schema.yaml}}]
declarations: [{{name: ordinal-source, path: seed.yaml}}]
python:
  sources: [{{module: {module}, path: identity.py}}]
  interpreter: python-3.14
  interpretation: closed-python-operations-v1
  stub_policy: source-authoritative
""")
    bundle, dependencies, profile, prepared = prepare_data_operation_inputs(tmp_path, "target.yaml")
    model = bound_data_operation_model(prepared)
    operation_id = "urn:corpus:operation:claim-source-item"
    operation = model.operation(operation_id)
    assert operation.callable_surfaces[0].declaration == module + ".claim_source_item"
    assert operation.outcomes == ("addressed", "invalid-index")
    assert len(model.implementation_slices) == 1 and model.implementation_slices[0].complete
    runtime = prepare_data_operation_runtime(
        prepared, dependencies.artifacts, execution_profile="execution:test", observed={},
    )
    with ddo_kernel_engine.begin() as connection:
        persist_release(connection, bundle, dependencies, profile, prepared)
        admit_data_operation_release(connection, prepared)
        persist_runtime_binding(connection, prepared, runtime)
        connection.execute(insert(table("data.project")).values(project_id="ddo-test"))

    identities = {(item.owner, item.domain): item.key for item in model.identities}
    source = model.operation("urn:ddo-test:source")
    kernel = {
        "engine": ddo_kernel_engine, "model": model, "prepared": prepared,
        "runtime": runtime.runtime_id, "identities": identities,
        "kind": identities[source.roles[0].kind, "kind"],
    }
    # Establish the input through ordinary native admission, claim and publication.
    _, _, _, attached = attach(kernel)
    fence = claim(kernel, attached)
    publish(kernel, fence, retain(kernel, fence, outputs=(7,)))

    intent = freeze_demand(
        model, roots=(RootSubject("subject:one", "source:test", b'{"page":1}'),),
        targets=(operation_id,), inference="inference:test", execution_profile="execution:test",
    )
    with ddo_kernel_engine.begin() as connection:
        demand = DemandPlanner(model, DataOperationStorage(connection)).register(
            intent, project="ddo-test", release=prepared.release_id, runtime=runtime.runtime_id,
        )["demand_id"]
    executor = NativeDemandExecutor(
        ddo_kernel_engine, prepared, runtime,
        PythonSourceCollection((PythonSource(module, captured, "identity.py"),)),
        runtime_locations={module: actual}, schema=bundle,
    )
    completed = executor.advance(demand)
    assert completed.receipt_count == 1 and len(completed.receipts) == 1
    assert executor.ports[operation_id].function.__module__ == module
    assert executor.ports[operation_id].function.__name__ == "claim_source_item"
    assert executor.budget.used_bytes == 0
    resumed = executor.advance(demand)
    assert resumed.receipt_count == 0 and resumed.receipts == ()
    with ddo_kernel_engine.begin() as connection:
        result = DataOperationStorage(connection).invoke(
            "read_demand_result", {"demand_id": demand, "view": "products"},
        )
        assert len(result["uses"]) == 1
        use = result["uses"][0]
        assert use["fate"] == "fulfilled"
        assert [product["body"] for product in use["products"]] == [["string", "claims/7"]]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 2
        assert connection.scalar(text("SELECT count(*) FROM ops.data_completion_intent")) == 2
        assert connection.scalar(text("SELECT count(*) FROM ops.task WHERE run_id IS NOT NULL")) == 0
