"""The selected population owner wakes its exact waiting consumer."""

import json
from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_demands import DemandPlanner, RootSubject
from corpus_structure.semantic.data_operation_service import advance_demand_selection
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identity import canonical_bytes
from native_test_support import principal_engine
from semantic.data_operation_binding_support import discover
from semantic.data_operation_kernel_support import POPULATION, admit_kernel, prepare_kernel
from semantic.population_completion_support import complete_ready


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
