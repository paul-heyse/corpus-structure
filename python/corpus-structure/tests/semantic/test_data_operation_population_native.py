"""Governed selection from authentic discovery outputs; no caller-created membership."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.data_operation_binding_support import discover
from semantic.data_operation_demand_support import claim, publish
from semantic.data_operation_kernel_support import POPULATION

pytestmark = pytest.mark.parametrize("ddo_kernel", [POPULATION], indirect=True, ids=["population"])


@pytest.mark.parametrize("complete", [True, False])
def test_native_selected_population_has_authentic_parent_and_frozen_filter(
    ddo_kernel,
    complete,
):
    demand, consumer, parent = discover(ddo_kernel, complete=complete)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        acquired = storage.invoke("read_demand_result", demand)
        request = {
            **consumer,
            "population_name": "selected-items",
            "parent_population_id": parent["population_id"],
            "read_id": acquired["read_id"],
        }
        selected = storage.invoke("select_data_population", request)
        assert [member["member_id"] for member in selected["members"]] == ["m15"]
        assert selected["complete"] is complete
        assert selected["evidence"]["derivation_id"] == parent["evidence"]["derivation_id"]
        assert selected["evidence"]["selection"]["obligation_id"] == consumer["obligation_id"]
        assert selected["evidence"]["producer_context"]["subject"] == "doc"
        assert storage.invoke("select_data_population", request) == selected
        current = storage.invoke("read_demand_result", demand)
        visible = [
            population
            for population in current["populations"]
            if population["name"] == "selected-items"
        ]
        assert len(visible) == 1
        assert "selected_obligation_id" not in visible[0]
        # Paging the unrelated producer cannot disclose the consumer's selected receipt.
        for page in current["obligations"]:
            single = storage.invoke(
                "read_demand_result",
                {
                    "demand_id": demand["demand_id"],
                    "limit": 1,
                    **(
                        {
                            "after": page["obligation_id"],
                            "selection": current["selection"],
                            "trust_snapshot": current["trust_snapshot"],
                            "read_id": current["read_id"],
                        }
                        if page["obligation_id"] != ""
                        else {}
                    ),
                },
            )
            exposed = {item["obligation_id"] for item in single["obligations"]}
            assert all(
                population["evidence"]["selection"]["obligation_id"] in exposed
                for population in single["populations"]
                if "selection" in population["evidence"]
            )


def test_native_planner_selects_on_one_read_and_attaches_only_after_fresh_read(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner

    demand, consumer, _ = discover(ddo_kernel)
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        assert planner.ready(snapshot, authorization=b"{}") == ()
        assert len(planner.selected_population_ids) == 1
        refreshed = planner.resume(demand["demand_id"])
        assert refreshed["read_id"] != snapshot["read_id"]
        ready = planner.ready(refreshed, authorization=b"{}")
        assert planner.selected_population_ids == ()
        assert len(ready) == 1
        assert ready[0].obligation == consumer["obligation_id"]


def test_native_planner_preserves_ambiguous_authentic_parent_populations(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner

    demand, consumer, _ = discover(ddo_kernel, ambiguous=True)
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        assert planner.ready(snapshot, authorization=b"{}") == ()
        assert planner.selected_population_ids == ()
        current = planner.resume(demand["demand_id"])
        use = next(
            use for use in current["uses"] if use["obligation_id"] == consumer["obligation_id"]
        )
        assert use["fate"] == "awaiting-population"
        assert use["selection"]["reasons"] == [
            {
                "code": "ambiguous-population",
                "location": "urn:consumer/items",
                "detail": "more than one authenticated population fits the declared role",
            }
        ]


def _complete_ready(ddo_kernel, ready, value=1):
    binding = json.loads(ready.binding)
    claim_fence = claim(ddo_kernel, json.loads(ready.native))
    kind = next(
        role.kind
        for operation in ddo_kernel["model"].operations
        if operation.semantic_id == ready.operation
        for role in operation.roles
        if role.direction == "output"
    )
    kind_contract = ddo_kernel["identities"][kind, "kind"]
    with ddo_kernel["engine"].begin() as connection:
        intent = DataOperationStorage(connection).invoke(
            "retain_data_completion_intent",
            {
                **claim_fence,
                "runtime_id": ddo_kernel["runtime"],
                "completion": {
                    "outcome": "success",
                    "implementation_revision": "native-test-source-v1",
                    "inputs": binding["inputs"],
                    "support": binding["support"],
                    "outputs": [
                        {
                            "role": "result",
                            "position": 0,
                            "multiplicity": 1,
                            "product": {
                                "kind_contract": kind_contract,
                                "body": semantic_value(value),
                                "members": [],
                            },
                        }
                    ],
                },
            },
        )
    return publish(ddo_kernel, claim_fence, intent)


def test_native_discovery_children_closed_fanin_and_pinned_resume(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner

    demand, consumer, _parent = discover(ddo_kernel)
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        producing_use = next(use for use in snapshot["uses"] if use["products"])
        planner.expand_discovery(
            snapshot,
            population="all-items",
            product=producing_use["products"][0]["product_id"],
            derivation=producing_use["derivation_id"],
        )
        current = planner.resume(demand["demand_id"])
        children = planner.ready(current, authorization=b"{}")
        assert planner.selected_population_ids  # fan-in waits for its fresh selection read
        assert {request.subject for request in children} == {"item:5", "item:15", "item:25"}
        assert all(request.operation == "urn:child" for request in children)
        assert all(
            request.resolved.subject_context.original_source == "source:test"
            for request in children
        )
    for child in children[:2]:
        _complete_ready(ddo_kernel, child)
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        frontier = planner.ready(planner.resume(demand["demand_id"]), authorization=b"{}")
        aggregate = [request for request in frontier if request.operation == "urn:consumer"]
        assert any(request.operation == "urn:child" for request in frontier)
        assert len(aggregate) == 1 and aggregate[0].obligation == consumer["obligation_id"]
        assert [
            member.member for role in aggregate[0].binding_result.roles for member in role.members
        ] == ["m15"]
    _complete_ready(ddo_kernel, aggregate[0])
    _complete_ready(ddo_kernel, children[2])
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        count = connection.execute(text("SELECT count(*) FROM ops.data_derivation")).scalar_one()
        assert planner.ready(planner.resume(demand["demand_id"]), authorization=b"{}") == ()
        page = planner.resume(demand["demand_id"], limit=1)
        selection, trust, read = page["selection"], page["trust_snapshot"], page["read_id"]
        obligations = list(page["obligations"])
        while page.get("continuation"):
            page = planner.resume(
                demand["demand_id"],
                selection=selection,
                limit=1,
                after=page["continuation"]["after"],
                trust_snapshot=trust,
                read_id=read,
            )
            obligations.extend(page["obligations"])
        assert len({row["obligation_id"] for row in obligations}) == 5
        assert all(row["fate"] == "fulfilled" for row in obligations)
        assert (
            connection.execute(text("SELECT count(*) FROM ops.data_derivation")).scalar_one()
            == count
        )


@pytest.mark.parametrize("complete", [True, False])
@pytest.mark.parametrize("values", [(), (15,)])
def test_native_empty_partial_populations_do_not_invent_closed_children(
    ddo_kernel, complete, values
):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner

    demand, _, _parent = discover(ddo_kernel, complete=complete, values=values)
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        producing_use = next(use for use in snapshot["uses"] if use["products"])
        population = planner.expand_discovery(
            snapshot,
            population="all-items",
            product=producing_use["products"][0]["product_id"],
            derivation=producing_use["derivation_id"],
        )
        assert population["complete"] is complete and len(population["members"]) == len(values)
        current = planner.resume(demand["demand_id"])
        children = [row for row in current["obligations"] if row["operation_id"] == "urn:child"]
        assert {row["subject"] for row in children} == {f"item:{value}" for value in values}
        ready = planner.ready(current, authorization=b"{}")
        if not complete:
            assert all(request.operation != "urn:consumer" for request in ready)
        assert all(
            request.subject in {"doc", *(f"item:{value}" for value in values)} for request in ready
        )


@pytest.mark.parametrize("scopes", [({"page": 1}, {"page": 2})])
def test_discovery_same_local_subject_distinct_contexts_reach_child_publication(ddo_kernel, scopes):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner

    contexts = tuple(
        {"subject": "local", "original_source": "source:test", "analyzed_scope": scope}
        for scope in scopes
    )
    demand, _, population = discover(ddo_kernel, values=(5, 25), member_contexts=contexts)
    assert [member["subject"] for member in population["members"]] == ["local", "local"]
    assert {member["member_id"]: member["analyzed_scope"] for member in population["members"]} == {
        "m5": scopes[0],
        "m25": scopes[1],
    }
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        producer = next(use for use in snapshot["uses"] if use["products"])
        planner.expand_discovery(
            snapshot,
            population="all-items",
            product=producer["products"][0]["product_id"],
            derivation=producer["derivation_id"],
        )
        children = tuple(
            request
            for request in planner.ready(planner.resume(demand["demand_id"]), authorization=b"{}")
            if request.operation == "urn:child"
        )
    assert len(children) == 2
    assert {child.subject for child in children} == {"local"}
    assert len({json.loads(child.native)["request_id"] for child in children}) == 2
    assert sorted(
        (json.loads(child.resolved.subject_context.analyzed_scope) for child in children),
        key=lambda value: json.dumps(value, sort_keys=True),
    ) == sorted(scopes, key=lambda value: json.dumps(value, sort_keys=True))
    receipts = [_complete_ready(ddo_kernel, child) for child in children]
    assert len({receipt["derivation_id"] for receipt in receipts}) == 2
    with ddo_kernel["engine"].connect() as connection:
        uses = DataOperationStorage(connection).invoke("read_demand_result", demand)["uses"]
    child_obligations = {child.obligation for child in children}
    fulfilled = [use for use in uses if use["obligation_id"] in child_obligations]
    assert len(fulfilled) == 2 and all(use["fate"] == "fulfilled" for use in fulfilled)


@pytest.mark.parametrize("scopes", [({"page": 1}, {"page": 1}), ({"page": 1}, {"page": 1.0})])
def test_discovery_duplicate_complete_context_refuses_including_equal_json_numbers(
    ddo_kernel, scopes
):
    contexts = tuple(
        {"subject": "local", "original_source": "source:test", "analyzed_scope": scope}
        for scope in scopes
    )
    with pytest.raises(DBAPIError, match="ambiguous duplicate complete contexts"):
        # The population's declared body uses integer pages; member-header JSON
        # may spell the same number as 1.0. Native packet authentication compares
        # their JSONB meaning before closure checks duplicate complete contexts.
        discover(
            ddo_kernel,
            values=(5, 25),
            member_contexts=contexts,
            member_body_contexts=(
                {
                    "subject": "local",
                    "original_source": "source:test",
                    "analyzed_scope": {"page": 1},
                },
                {
                    "subject": "local",
                    "original_source": "source:test",
                    "analyzed_scope": {"page": 1},
                },
            ),
        )
