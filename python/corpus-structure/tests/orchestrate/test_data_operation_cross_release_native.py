"""Actual admitted-release coalescing keeps the original generation basis."""

import json
from dataclasses import replace
from typing import cast

import pytest
from semantic.data_operation_demand_support import attach, cancel_demand, claim, expire_lease
from semantic.data_operation_kernel_support import EXECUTION, STORAGE, admit_kernel, prepare_kernel
from sqlalchemy import text

from corpus_structure.orchestrate.data_operations import (
    NativeDemandExecutionError,
    NativeDemandExecutor,
)
from corpus_structure.semantic._data_operation_wire import WireClaimDataRequestsRequest
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_service import execute_data_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.releases import activate_release


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


def _target_release(kernel, tmp_path):
    recipe = replace(
        EXECUTION,
        name="execution-unrelated-release",
        project_id=None,
        schema_text=EXECUTION.schema_text + "  UnrelatedReleaseMarker: {}\n",
    )
    directory = tmp_path / "target-release"
    directory.mkdir()
    target = prepare_kernel(recipe, directory=directory)
    assert target.prepared.release_id != kernel.prepared.release_id
    assert (
        _intent(target.model).record["operations"][0]["recipe"]
        == _intent(kernel.model).record["operations"][0]["recipe"]
    )
    with kernel.engine.begin() as connection:
        admit_kernel(connection, recipe, preparation=target)
    return target


def _ready(kernel, preparation, demand):
    with kernel.engine.begin() as connection:
        snapshot = DemandPlanner(preparation.model, DataOperationStorage(connection)).resume(demand)
    with kernel.engine.begin() as connection:
        planner = DemandPlanner(preparation.model, DataOperationStorage(connection))
        ready = planner.ready(snapshot, authorization=b"{}")
        return ready, planner.refusals


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
        snapshot = planner.resume(original_demand)
    with ddo_kernel.engine.begin() as connection:
        planner = DemandPlanner(original.model, DataOperationStorage(connection))
        (old_ready,) = planner.ready(snapshot, authorization=b"{}")
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
        admit_kernel(connection, recipe, preparation=target)
        demand = _register(connection, target)
        planner = DemandPlanner(target.model, DataOperationStorage(connection))
        snapshot = planner.resume(demand)
    with ddo_kernel.engine.begin() as connection:
        planner = DemandPlanner(target.model, DataOperationStorage(connection))
        (current_ready,) = planner.ready(snapshot, authorization=b"{}")
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

    if retained:
        resolve_basis = NativeDemandExecutor._basis_context

        def current_only(executor, release_id, runtime_id):
            assert release_id != original.prepared.release_id, (
                "native reconciliation resolved the retired executable capture"
            )
            return resolve_basis(executor, release_id, runtime_id)

        monkeypatch.setattr(NativeDemandExecutor, "_basis_context", current_only)

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


@pytest.mark.parametrize("ddo_kernel", [EXECUTION], indirect=True, ids=["execution"])
@pytest.mark.parametrize("state", ["pending", "active", "expired", "retained", "published"])
def test_active_release_admits_fresh_unleased_capture_and_preserves_existing_authority(
    ddo_kernel, monkeypatch, state, tmp_path
):
    original = ddo_kernel.preparation
    monkeypatch.syspath_prepend(str(original.directory))
    with ddo_kernel.engine.begin() as connection:
        original_demand = _register(connection, original)
    (old_ready,), errors = _ready(ddo_kernel, original, original_demand)
    assert errors == ()
    old = json.loads(old_ready.native)
    fence = None
    if state in {"active", "expired"}:
        fence = claim(ddo_kernel, old, seconds=3600)
        if state == "expired":
            expire_lease(ddo_kernel, fence)
    elif state in {"retained", "published"}:
        if state == "retained":

            def stop_after_retention(self, claim, intent, owner):
                raise RuntimeError("controlled stop after native retention")

            with monkeypatch.context() as patch:
                patch.setattr(NativeDemandExecutor, "_publish", stop_after_retention)
                with pytest.raises(NativeDemandExecutionError):
                    execute_data_demand(
                        ddo_kernel.engine,
                        original_demand,
                        source_root=original.directory,
                        database_capacity=6,
                    )
        else:
            assert (
                execute_data_demand(
                    ddo_kernel.engine,
                    original_demand,
                    source_root=original.directory,
                    database_capacity=6,
                ).receipt_count
                == 1
            )

    target = _target_release(ddo_kernel, tmp_path)
    with ddo_kernel.purpose("admit").begin() as connection:
        activated = activate_release(
            connection,
            "execution",
            target.prepared.release_id,
            expected_parent=None,
            expected_generation=0,
        )
        assert activated.generation == 1
    with ddo_kernel.engine.begin() as connection:
        demand = _register(connection, target)
    ready, errors = _ready(ddo_kernel, target, demand)
    if state == "active":
        assert ready == () and len(errors) == 1
        assert "active producer lease" in str(errors[0])
    elif state == "published":
        assert ready == () and errors == ()
    else:
        (selected,) = ready
        assert errors == ()
        current = json.loads(selected.native)
        assert current["request_id"] == old["request_id"]
        if state == "retained":
            assert (
                current["generation"],
                current["task_id"],
                current["release_id"],
                current["runtime_id"],
            ) == (
                old["generation"],
                old["task_id"],
                original.prepared.release_id,
                original.runtime.runtime_id,
            )
            assert current["action"] == "reconcile" and current["retained_intent_id"]
        else:
            assert current["generation"] == old["generation"] + 1
            assert current["task_id"] != old["task_id"]
            assert (current["release_id"], current["runtime_id"]) == (
                target.prepared.release_id,
                target.runtime.runtime_id,
            )
            assert current["action"] == "compute" and current["retained_intent_id"] is None
            stale_ready, stale_errors = _ready(ddo_kernel, original, original_demand)
            assert stale_ready == () and len(stale_errors) == 1
            assert "inactive demand cannot replace" in str(stale_errors[0])
            with ddo_kernel.engine.connect() as connection:
                assert (
                    connection.scalar(
                        text(
                            "SELECT count(*) FROM ops.data_request_generation WHERE request_id=:request"
                        ),
                        {"request": old["request_id"]},
                    )
                    == 2
                )
                assert (
                    connection.scalar(
                        text("SELECT release_id FROM ops.task WHERE id=:task"),
                        {"task": old["task_id"]},
                    )
                    == original.prepared.release_id
                )
    if state in {"active", "retained", "published"}:
        with ddo_kernel.engine.connect() as connection:
            capture = connection.execute(
                text(
                    "SELECT release_id,runtime_id,generation,live_task_id "
                    "FROM ops.data_request WHERE id=:request"
                ),
                {"request": old["request_id"]},
            ).one()
            assert tuple(capture) == (
                original.prepared.release_id,
                original.runtime.runtime_id,
                old["generation"],
                old["task_id"],
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM ops.data_request_generation WHERE request_id=:request"
                    ),
                    {"request": old["request_id"]},
                )
                == 1
            )


@pytest.mark.parametrize("ddo_kernel", [EXECUTION], indirect=True, ids=["execution"])
@pytest.mark.parametrize("committed", [True, False], ids=["lost-commit-ack", "known-rollback"])
def test_native_publication_outcome_is_read_before_a_fresh_executor_retries(
    ddo_kernel, monkeypatch, committed
):
    from psycopg import OperationalError

    from corpus_structure.semantic.claim_lifetime import ClaimOwner, ClaimSettlementUncertain

    preparation = ddo_kernel.preparation
    monkeypatch.syspath_prepend(str(preparation.directory))
    with ddo_kernel.engine.begin() as connection:
        demand = _register(connection, preparation)
    (selected,), errors = _ready(ddo_kernel, preparation, demand)
    assert errors == ()
    original = json.loads(selected.native)
    # Mark only the publication connection. Renewal and intent-retention commits
    # continue normally, so the fault concerns the actual final native effect.
    settle = ClaimOwner.settle
    commit = ddo_kernel.engine.dialect.do_commit
    publication_connections = set()
    lost = []

    def mark_publication(owner, claim, completion):
        def marked(connection):
            result = completion(connection)
            if isinstance(result, dict) and "derivation_id" in result:
                publication_connections.add(id(connection.connection.driver_connection))
                if not committed:
                    lost.append(False)
                    raise RuntimeError("controlled rollback before publication commit")
            return result

        return settle(owner, claim, marked)

    def lose_acknowledgement(connection):
        driver = getattr(connection, "driver_connection", connection)
        selected = id(driver) in publication_connections
        if committed and selected and len(lost) < 2:
            publication_connections.discard(id(driver))
            commit(connection)
            lost.append(True)
            raise OperationalError("controlled publication acknowledgement loss")
        commit(connection)

    with monkeypatch.context() as faults:
        faults.setattr(ClaimOwner, "settle", mark_publication)
        faults.setattr(ddo_kernel.engine.dialect, "do_commit", lose_acknowledgement)
        with pytest.raises(NativeDemandExecutionError) as caught:
            execute_data_demand(
                ddo_kernel.engine, demand, source_root=preparation.directory, database_capacity=6
            )
    if committed:
        assert any(
            isinstance(error, ClaimSettlementUncertain) for error in caught.value.failures
        ), caught.value.failures
        assert lost == [True, True]
    else:
        assert any("controlled rollback" in str(error) for error in caught.value.failures), (
            caught.value.failures
        )
        assert lost == [False]
    with ddo_kernel.engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ops.data_completion_intent")) == 1
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == int(committed)
        producer = connection.execute(
            text("SELECT producer_task_id,producer_attempt FROM ops.data_completion_intent")
        ).one()
        assert producer.producer_task_id == original["task_id"] and producer.producer_attempt == 1

    def forbidden_execution(*args, **options):
        raise AssertionError("committed intent recovery must not resolve the producer again")

    with monkeypatch.context() as retry:
        retry.setattr(NativeDemandExecutor, "_basis_context", forbidden_execution)
        result = execute_data_demand(
            ddo_kernel.engine, demand, source_root=preparation.directory, database_capacity=6
        )
    assert result.receipt_count == int(not committed)
    with ddo_kernel.engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ops.data_completion_intent")) == 1
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 1
        assert connection.scalar(text("SELECT count(*) FROM ops.task WHERE status='running'")) == 0
        assert connection.scalar(text("SELECT canonical_body FROM kb.data_product")) == [
            "integer",
            "7",
        ]
    assert (
        execute_data_demand(
            ddo_kernel.engine, demand, source_root=preparation.directory, database_capacity=6
        ).receipt_count
        == 0
    )
