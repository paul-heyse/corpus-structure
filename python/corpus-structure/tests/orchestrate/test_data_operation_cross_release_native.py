"""Actual admitted-release coalescing keeps the original generation basis."""

import json
from dataclasses import replace
from typing import cast

import pytest
from semantic.data_operation_demand_support import attach, cancel_demand, claim
from semantic.data_operation_kernel_support import EXECUTION, STORAGE, prepare_kernel
from sqlalchemy import text

from corpus_structure.orchestrate.data_operations import (
    NativeDemandExecutionError,
    NativeDemandExecutor,
)
from corpus_structure.semantic._data_operation_wire import WireClaimDataRequestsRequest
from corpus_structure.semantic.data_operation_admission import admit_data_operation_release
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_service import execute_data_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding


def _intent(model):
    return freeze_demand(
        model,
        roots=(RootSubject("subject:shared", "source:shared", b"{}"),),
        targets=("urn:ddo-execution:answer",),
        inference="exact",
        execution_profile="execution:test",
    )


def _register(connection, preparation):
    return DemandPlanner(preparation.model, DataOperationStorage(connection)).register(
        _intent(preparation.model),
        project="execution",
        release=preparation.prepared.release_id,
        runtime=preparation.runtime.runtime_id,
    )["demand_id"]


@pytest.mark.parametrize("ddo_kernel", [EXECUTION], indirect=True, ids=["execution"])
@pytest.mark.parametrize("retained", [False, True], ids=["compute", "reconcile"])
def test_two_admitted_releases_coalesce_and_use_original_basis_after_creating_demand_cancelled(
    ddo_kernel, monkeypatch, retained, tmp_path
):
    original = ddo_kernel.preparation
    monkeypatch.syspath_prepend(str(original.directory))
    with ddo_kernel.engine.begin() as connection:
        original_demand = _register(connection, original)
        planner = DemandPlanner(original.model, DataOperationStorage(connection))
        (old_ready,) = planner.ready(planner.resume(original_demand), authorization=b"{}")
    old = json.loads(old_ready.native)
    if retained:

        def stop_after_retention(self, claim, intent, owner):
            raise RuntimeError("controlled stop after genuine reply and native retention")

        with monkeypatch.context() as patch:
            patch.setattr(NativeDemandExecutor, "_publish", stop_after_retention)
            with pytest.raises(NativeDemandExecutionError):
                execute_data_demand(
                    ddo_kernel.engine,
                    original_demand,
                    source_root=original.directory,
                    database_capacity=6,
                )

    recipe = replace(
        EXECUTION,
        name="execution-unrelated-release",
        project_id=None,
        schema_text=EXECUTION.schema_text + "  UnrelatedReleaseMarker: {}\n",
    )
    target_directory = tmp_path / "target-release"
    target_directory.mkdir()
    target = prepare_kernel(recipe, directory=target_directory)
    # Separate schema acquisition leaves the sealed original seed untouched.
    # Both releases execute identical captured Python at the original import root.
    assert target.directory != original.directory
    for _, filename, content in EXECUTION.python_sources:
        assert (original.directory / filename).read_bytes() == content
        assert (target.directory / filename).read_bytes() == content
    assert target.prepared.release_id != original.prepared.release_id
    assert (
        _intent(target.model).record["operations"][0]["recipe"]
        == _intent(original.model).record["operations"][0]["recipe"]
    )
    with ddo_kernel.engine.begin() as connection:
        persist_release(
            connection, target.bundle, target.dependencies, target.profile, target.prepared
        )
        admit_data_operation_release(connection, target.prepared)
        persist_runtime_binding(connection, target.prepared, target.runtime)
        demand = _register(connection, target)
        planner = DemandPlanner(target.model, DataOperationStorage(connection))
        (current_ready,) = planner.ready(planner.resume(demand), authorization=b"{}")
        current = json.loads(current_ready.native)
        assert (current["request_id"], current["generation"], current["task_id"]) == (
            old["request_id"],
            old["generation"],
            old["task_id"],
        )
        assert (current["release_id"], current["runtime_id"], current["binding"]) == (
            original.prepared.release_id,
            original.runtime.runtime_id,
            old["binding"],
        )
        DataOperationStorage(connection).cancel_data_demand(
            dict(demand_id=original_demand, reason="creating demand retired")
        )

    result = execute_data_demand(
        ddo_kernel.engine, demand, source_root=original.directory, database_capacity=6
    )
    assert result.receipt_count == 1
    assert (
        execute_data_demand(
            ddo_kernel.engine, demand, source_root=original.directory, database_capacity=6
        ).receipt_count
        == 0
    )
    with ddo_kernel.engine.connect() as connection:
        generation = (
            connection.execute(
                text(
                    "SELECT r.release_id,r.runtime_id,r.generation,r.binding,t.attempt FROM ops.data_request r JOIN ops.task t ON t.id=r.live_task_id WHERE r.id=:id"
                ),
                {"id": old["request_id"]},
            )
            .mappings()
            .one()
        )
        assert (generation["release_id"], generation["runtime_id"], generation["generation"]) == (
            original.prepared.release_id,
            original.runtime.runtime_id,
            old["generation"],
        )
        assert generation["binding"]["read_id"] == old["binding"]["read_id"]
        assert generation["attempt"] == (2 if retained else 1)
        derivation = connection.execute(
            text("SELECT release_id,runtime_id FROM ops.data_derivation")
        ).one()
        assert tuple(derivation) == (original.prepared.release_id, original.runtime.runtime_id)
        assert connection.scalar(text("SELECT count(*) FROM ops.data_completion_intent")) == 1
        assert connection.scalar(text("SELECT canonical_body FROM kb.data_product")) == [
            "integer",
            "7",
        ]


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_stale_attach_generation_cannot_claim_a_replacement_basis(ddo_kernel):
    first, _, _, attached = attach(ddo_kernel)
    cancel_demand(ddo_kernel, first)
    _, _, _, successor = attach(ddo_kernel, targets=("urn:ddo-test:source", "urn:ddo-test:sample"))
    assert successor["request_id"] == attached["request_id"]
    assert successor["generation"] == attached["generation"] + 1
    with ddo_kernel.engine.begin() as connection:
        denied = DataOperationStorage(connection).claim_data_requests(
            cast(
                WireClaimDataRequestsRequest,
                {
                    "holder": "stale-basis",
                    "lease_seconds": 30,
                    "items": [
                        {"request_id": attached["request_id"], "generation": attached["generation"]}
                    ],
                },
            )
        )["items"][0]
        assert denied == {"state": "no-work"}
        assert (
            connection.scalar(
                text("SELECT attempt FROM ops.task WHERE id=:id"), {"id": successor["task_id"]}
            )
            == 0
        )
    current = claim(ddo_kernel, successor, holder="current-basis")
    assert current["generation"] == successor["generation"]
