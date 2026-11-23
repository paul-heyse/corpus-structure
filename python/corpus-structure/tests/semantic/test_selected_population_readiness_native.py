"""The selected population owner wakes its exact waiting consumer."""

import json
from dataclasses import replace
from typing import cast

import pytest

from corpus_structure.semantic._data_operation_wire import (
    WireAttachDataRequestsRequest,
    WireRegisterDataDemandRequest,
    WireRevokeDataSupportRequest,
)
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    DiscoverySelection,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_identity import SemanticRequestKey
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_service import advance_demand_selection
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from native_test_support import principal_engine
from semantic.data_operation_binding_support import discover
from semantic.data_operation_demand_support import claim, publish, retain
from semantic.data_operation_kernel_support import POPULATION, admit_kernel, prepare_kernel
from semantic.population_completion_support import complete_ready


def test_new_discovery_admission_replaces_closure_for_same_product_and_derivation(
    commit_db_engine, native_settings, tmp_path
):
    prepared = prepare_kernel(POPULATION, directory=tmp_path / "replacement-closure")
    with commit_db_engine.begin() as connection:
        kernel = admit_kernel(connection, POPULATION, engine=commit_db_engine, preparation=prepared)
    demand, _, original = discover(kernel, values=())
    demand_id = demand["demand_id"]
    with commit_db_engine.begin() as connection:
        advance_demand_selection(
            connection,
            "ddo-test",
            "replacement-closure",
            demand_id,
            expected_demand_id=None,
            expected_generation=0,
        )
    writer = principal_engine(native_settings, "write", commit_db_engine.url.database)
    try:

        def resume():
            with writer.begin() as connection:
                return DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(
                    demand_id, settlement=True
                )

        before = resume()
        assert before["scheduler_settlement"]["selections"][0]["discovery_complete"] is True
        (producer,) = [
            row for row in before["obligations"] if row["operation_id"] == "urn:discover"
        ]
        request = SemanticRequestKey(
            kernel.identities["urn:discover", "recipe"],
            "doc",
            {},
            {"parameters": {}, "replicate": None},
            "inference:test",
            subject_context=SubjectContext(
                "ddo-test",
                "doc",
                "source:test",
                b'{"page":1}',
                subject_definition=kernel.model.operation("urn:discover").subject,
            ),
        )
        with writer.begin() as connection:
            (attached,) = DataOperationStorage(connection).attach_data_requests(
                cast(
                    WireAttachDataRequestsRequest,
                    {
                        "read_id": before["read_id"],
                        "items": [
                            {
                                "obligation_id": producer["obligation_id"],
                                "request_meaning": json.loads(request.identity.canonical_input),
                                "request_key": request.identity.key,
                                "replicate": None,
                                "binding": {
                                    "inputs": [],
                                    "support": [],
                                    "parameters": semantic_value(request.parameters),
                                    "request_inputs": ["mapping", []],
                                    "inference": "inference:test",
                                    "populations": [],
                                    "read_id": before["read_id"],
                                },
                            }
                        ],
                    },
                )
            )["items"]
        assert attached["state"] == "fulfilled", attached
        adopted = attached["result"]
        assert adopted["request_id"] == request.identity.key
        assert adopted["derivation_id"] == original["evidence"]["derivation_id"]
        assert adopted["use_id"] != original["evidence"]["admission_use_id"]

        # The earlier closure authenticates its own exact use. Equal product and
        # derivation cannot close the newly admitted occurrence implicitly.
        pending = resume()
        assert pending["scheduler_settlement"]["selections"][0]["discovery_complete"] is False
        with writer.begin() as connection:
            assert DemandPlanner(
                kernel.model, DataOperationStorage(connection)
            ).settle_pending_discovery(pending)
        current = resume()
        assert current["scheduler_settlement"]["selections"][0]["discovery_complete"] is True
        (replacement,) = [
            row
            for row in current["populations"]
            if row["name"] == "all-items"
            and row["evidence"]["admission_use_id"] == adopted["use_id"]
        ]
        assert replacement["population_id"] != original["population_id"]
        assert replacement["semantic_key"] == original["semantic_key"]
        assert replacement["evidence"]["product_id"] == original["evidence"]["product_id"]
        assert replacement["evidence"]["derivation_id"] == original["evidence"]["derivation_id"]
        with writer.begin() as connection:
            assert not DemandPlanner(
                kernel.model, DataOperationStorage(connection)
            ).settle_pending_discovery(current)
        assert (
            resume()["scheduler_settlement"]["selections"]
            == current["scheduler_settlement"]["selections"]
        )
    finally:
        writer.dispose()


def test_selected_population_wakes_only_exact_waiter(commit_db_engine, tmp_path):
    admin = commit_db_engine
    prepared = prepare_kernel(POPULATION, directory=tmp_path / "selected-population")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, POPULATION, engine=admin, preparation=prepared)

    demand, selected, parent = discover(
        kernel, additional_roots=(RootSubject("another doc", "source:test", b'{"page":1}'),)
    )
    demand_id = demand["demand_id"]

    def resume(**pins):
        with admin.begin() as connection:
            return DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(
                demand_id, **pins
            )

    def consumers(page):
        return {
            str(row["obligation_id"]): row
            for row in page["obligations"]
            if row["operation_id"] == "urn:consumer"
        }

    before = resume()
    targets = consumers(before)
    holder = str(selected["obligation_id"])
    assert {row["subject"] for row in targets.values()} == {"doc", "another doc"}
    with admin.begin() as connection:
        storage = DataOperationStorage(connection)
        for row in targets.values():
            storage.record_data_fate(
                {
                    "obligation_id": row["obligation_id"],
                    "fate": "awaiting-population",
                    "selection": {
                        "read_id": before["read_id"],
                        "reasons": [],
                    },
                }
            )
    waiting = resume()
    assert all(not row["binding_origin_changed"] for row in consumers(waiting).values())

    with admin.begin() as connection:
        receipt = DataOperationStorage(connection).select_data_population(
            {
                "obligation_id": selected["obligation_id"],
                "population_name": "selected-items",
                "parent_population_id": parent["population_id"],
                "read_id": waiting["read_id"],
            }
        )
    replay = resume(
        read_id=waiting["read_id"],
        selection=waiting["selection"],
        trust_snapshot=waiting["trust_snapshot"],
    )
    assert all(not row["binding_origin_changed"] for row in consumers(replay).values())

    current = resume()
    for key, row in consumers(current).items():
        assert row["binding_origin_changed"] is (key == holder)

    with admin.begin() as connection:
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        (consumer,) = [
            request
            for request in planner.ready(current, authorization=b"{}")
            if request.operation == "urn:consumer"
        ]
    assert consumer.obligation == holder
    assert receipt["evidence"]["selection"]["obligation_id"] == holder
    after = consumers(resume())
    assert {key: row["fate"] for key, row in after.items()} == {
        key: "attached" if key == holder else "awaiting-population" for key in targets
    }


@pytest.mark.parametrize(
    "complete,values,minimum,expected",
    [
        (False, (), 1, "pending"),
        (True, (), 1, "unavailable"),
        (True, (5,), 1, "unavailable"),
        (True, (15,), 2, "unavailable"),
        (True, (), 0, "settled"),
    ],
)
def test_native_closed_population_decision_preserves_pending_and_min_zero(
    commit_db_engine, native_settings, tmp_path, complete, values, minimum, expected
):
    """Native filtered closure, never an empty Python/local queue, owns absence."""
    assert POPULATION.declaration_content is not None
    declarations = json.loads(POPULATION.declaration_content)
    consumer = next(row for row in declarations["operations"] if row["id"] == "urn:consumer")
    next(role for role in consumer["roles"] if role["name"] == "items")["minimum"] = minimum
    if minimum == 0:
        next(role for role in consumer["roles"] if role["name"] == "items")["presence"] = "optional"
    recipe = replace(
        POPULATION,
        name="bounded-population-decision",
        declaration_content=canonical_bytes(declarations),
    )
    prepared = prepare_kernel(recipe, directory=tmp_path / "population-decision")
    with commit_db_engine.begin() as connection:
        kernel = admit_kernel(connection, recipe, engine=commit_db_engine, preparation=prepared)
    demand, selected, _ = discover(kernel, complete=complete, values=values)
    with commit_db_engine.begin() as connection:
        advance_demand_selection(
            connection,
            "ddo-test",
            "population-decision",
            demand["demand_id"],
            expected_demand_id=None,
            expected_generation=0,
        )
    writer = principal_engine(native_settings, "write", commit_db_engine.url.database)
    try:

        def resume():
            with writer.begin() as connection:
                return DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(
                    demand["demand_id"], settlement=True
                )

        def ready(page):
            with writer.begin() as connection:
                return DemandPlanner(kernel.model, DataOperationStorage(connection)).ready(
                    page, authorization=b"{}"
                )

        def target(page):
            return next(
                row
                for row in page["obligations"]
                if row["obligation_id"] == selected["obligation_id"]
            )

        before = resume()
        assert target(before)["binding_unavailable"] is False
        assert before["scheduler_settlement"]["selections"][0]["state"] == "pending"
        # Native selection materializes the complete eligible population at the
        # binding owner. Any actual discovered child remains independently owned.
        for request in ready(before):
            assert request.operation == "urn:child"
            complete_ready(kernel, request)
        observed = resume()
        assert target(observed)["binding_unavailable"] is (expected == "unavailable")
        requests = ready(observed)
        if expected == "settled":
            (request,) = requests
            assert request.operation == "urn:consumer"
            assert request.binding_result.roles[0].state == "known-absent"
            complete_ready(kernel, request)
        else:
            assert all(request.operation != "urn:consumer" for request in requests)
            for request in requests:
                complete_ready(kernel, request)
        final = resume()
        scope = final["scheduler_settlement"]["selections"][0]
        assert scope["state"] == expected
        assert scope["discovery_complete"] is complete
        if expected == "unavailable":
            assert target(final)["fate"] == "unavailable"
            assert target(final)["native_settlement"][0]["state"] == "unavailable"
            assert scope["unavailable_count"] == 1 and scope["pending_count"] == 0
        elif expected == "pending":
            assert target(final)["binding_unavailable"] is False and scope["pending_count"] >= 1
        else:
            assert (
                scope["unavailable_count"]
                == scope["pending_count"]
                == scope["uncovered_count"]
                == 0
            )
    finally:
        writer.dispose()


@pytest.mark.parametrize("outcome", ["empty", "failed"])
def test_terminal_discovery_without_outputs_requires_valid_empty_completion(
    commit_db_engine, native_settings, tmp_path, outcome
):
    prepared = prepare_kernel(POPULATION, directory=tmp_path / "terminal-discovery")
    with commit_db_engine.begin() as connection:
        kernel = admit_kernel(connection, POPULATION, engine=commit_db_engine, preparation=prepared)
    selection = freeze_demand(
        kernel.model,
        roots=(RootSubject("doc", "source:test", b'{"page":1}'),),
        targets=("urn:discover",),
        discovery=(DiscoverySelection("urn:discover", "result", "urn:child", "all-items"),),
        inference="inference:test",
        execution_profile="execution:test",
    ).record
    with commit_db_engine.begin() as connection:
        registered = DataOperationStorage(connection).register_data_demand(
            cast(
                WireRegisterDataDemandRequest,
                {
                    "project_id": "ddo-test",
                    "release_id": kernel.prepared.release_id,
                    "runtime_id": kernel["runtime"],
                    "root": selection["roots"],
                    "selection": selection,
                    "strength": "value",
                },
            )
        )
        advance_demand_selection(
            connection,
            "ddo-test",
            "terminal-discovery",
            registered["demand_id"],
            expected_demand_id=None,
            expected_generation=0,
        )
    writer = principal_engine(native_settings, "write", commit_db_engine.url.database)
    try:

        def resume():
            with writer.begin() as connection:
                return DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(
                    registered["demand_id"], settlement=True
                )

        before = resume()
        initial_scope = before["scheduler_settlement"]["selections"][0]
        assert initial_scope["discovery_complete"] is False
        assert initial_scope["state"] == "pending" and initial_scope["obligation_count"] == 1
        with writer.begin() as connection:
            (ready,) = DemandPlanner(kernel.model, DataOperationStorage(connection)).ready(
                before, authorization=b"{}"
            )
        assert ready.operation == "urn:discover"
        fence = claim(kernel, json.loads(ready.native))
        intent = retain(kernel, fence, outputs=(), outcome=outcome)
        retained = resume()
        assert retained["scheduler_settlement"]["selections"][0]["discovery_complete"] is False
        publication = publish(kernel, fence, intent)
        completed = resume()
        (scope,) = completed["scheduler_settlement"]["selections"]
        assert scope["discovery_complete"] is (outcome == "empty")
        assert scope["state"] == ("settled" if outcome == "empty" else "pending")
        assert scope["obligation_count"] == 1
        assert completed["populations"] == []
        (use,) = completed["uses"]
        assert use["derivation_id"] == publication["derivation_id"]
        assert use["products"] == []
        if outcome == "empty":
            with commit_db_engine.begin() as connection:
                DataOperationStorage(connection).revoke_data_support(
                    cast(
                        WireRevokeDataSupportRequest,
                        {
                            "project_id": "ddo-test",
                            "original_source": "source:test",
                            "selector_kind": "derivation",
                            "selector": publication["derivation_id"],
                            "reason": "terminal discovery authority withdrawn",
                        },
                    )
                )
            revoked = resume()
            assert revoked["scheduler_settlement"]["selections"][0]["discovery_complete"] is False
            assert revoked["scheduler_settlement"]["selections"][0]["state"] == "pending"
    finally:
        writer.dispose()
