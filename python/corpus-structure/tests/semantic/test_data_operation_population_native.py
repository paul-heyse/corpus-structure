"""Governed selection from authentic discovery outputs; no caller-created membership."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import insert, text

from corpus_structure.semantic.data_operation_admission import (
    admit_data_operation_release,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_demands import (
    DiscoverySelection,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_identity import SemanticRequestKey, semantic_value
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_preparation import prepare_data_operation_inputs
from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding

from .test_data_operation_storage import _declaration, claim, publish
from .test_data_operation_storage import ddo_kernel_engine as ddo_kernel_engine


def prepare_population(tmp_path):
    (tmp_path / "schema.yaml").write_text("""id: urn:ddo-selection
name: target
prefixes: {t: 'urn:ddo-selection:'}
default_prefix: t
types:
  integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
  boolean: {base: bool, uri: 'http://www.w3.org/2001/XMLSchema#boolean'}
classes:
  Scope:
    attributes:
      page: {range: integer, required: true}
  Context:
    attributes:
      subject: {range: string, required: true}
      original_source: {range: string, required: true}
      analyzed_scope: {range: Scope, required: true, inlined: true}
  Sample:
    attributes:
      value: {range: integer, required: true}
      document_subject: {range: string, required: true}
  Packet:
    attributes:
      member_id: {range: string, required: true}
      kind_contract: {range: string, required: true}
      context: {range: Context, required: true, inlined: true}
      body: {range: Sample, required: true, inlined: true}
  Population:
    attributes:
      complete: {range: boolean, required: true}
      members: {range: Packet, required: true, multivalued: true, inlined_as_list: true}
""")
    producer = _declaration()
    producer.update(id="urn:discover", profile="discovery")
    producer["roles"][0].update(kind="Population", maximum=1, collection="scalar")
    consumer = _declaration()
    consumer.update(id="urn:consumer", dependencies=["urn:discover"])
    consumer["roles"].insert(
        0,
        {
            "name": "items",
            "kind": "Sample",
            "direction": "input",
            "minimum": 1,
            "maximum": None,
            "collection": "set",
            "presence": "required",
            "subject_field": "document_subject",
            "support": {
                "provenance": "exact",
                "source": "same-original",
                "coverage": "selected-scope",
                "identity_requirements": ["episode"],
            },
        },
    )
    consumer["binding"] = {
        "operator": "forall",
        "roles": ["items"],
        "population": "selected-items",
        "children": [
            {
                "operator": "range",
                "operands": [
                    {
                        "kind": "field",
                        "value_type": "integer",
                        "field": {"role": "items", "projection": "Sample", "field": "value"},
                    },
                    {"kind": "literal", "value_type": "integer", "value": 10},
                    {"kind": "literal", "value_type": "integer", "value": 20},
                ],
            }
        ],
    }
    child = _declaration()
    child["id"] = "urn:child"
    (tmp_path / "operations.yaml").write_bytes(
        canonical_bytes(
            {
                "version": "data-operation-model-v1",
                "operations": [producer, consumer, child],
            }
        )
    )
    (tmp_path / "target.yaml").write_text("""version: data-operation-inputs-v1
root: target
schemas: [{name: target, path: schema.yaml}]
declarations: [{name: test-operations, path: operations.yaml}]
""")
    bundle, dependencies, profile, prepared = prepare_data_operation_inputs(tmp_path, "target.yaml")
    model = bound_data_operation_model(prepared)
    runtime = prepare_data_operation_runtime(
        prepared,
        dependencies.artifacts,
        execution_profile="execution:test",
        observed={},
    )
    return bundle, dependencies, profile, prepared, model, runtime


@pytest.fixture
def population_kernel(ddo_kernel_engine, tmp_path):
    bundle, dependencies, profile, prepared, model, runtime = prepare_population(tmp_path)
    with ddo_kernel_engine.begin() as connection:
        persist_release(connection, bundle, dependencies, profile, prepared)
        admit_data_operation_release(connection, prepared)
        persist_runtime_binding(connection, prepared, runtime)
        connection.execute(insert(table("data.project")).values(project_id="ddo-test"))
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    return {
        "engine": ddo_kernel_engine,
        "prepared": prepared,
        "runtime": runtime.runtime_id,
        "identities": identities,
        "model": model,
    }


def discover(
    kernel, *, complete=True, ambiguous=False, values=(5, 15, 25), inference="inference:test"
):
    scope = {"page": 1}
    root = {"subject": "doc", "original_source": "source:test", "analyzed_scope": scope}
    selection = freeze_demand(
        kernel["model"],
        roots=(RootSubject("doc", "source:test", canonical_bytes(scope)),),
        targets=("urn:consumer",),
        inference=inference,
        execution_profile="execution:test",
        discovery=(DiscoverySelection("urn:discover", "result", "urn:child", "all-items"),)
        + (
            (DiscoverySelection("urn:discover", "result", "urn:child", "other-items"),)
            if ambiguous
            else ()
        ),
    ).record
    with kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        demand = storage.invoke(
            "register_data_demand",
            {
                "project_id": "ddo-test",
                "release_id": kernel["prepared"].release_id,
                "runtime_id": kernel["runtime"],
                "root": [root],
                "selection": selection,
                "strength": "value",
            },
        )
        producer = storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:discover",
                **root,
                "parameters": {},
            },
        )
        consumer = storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:consumer",
                **root,
                "parameters": {},
            },
        )
        acquired = storage.invoke("read_demand_result", demand)
        request = SemanticRequestKey(
            kernel["identities"]["urn:discover", "recipe"],
            "doc",
            {},
            {"parameters": {}, "replicate": None},
            inference,
            subject_context=SubjectContext(
                "ddo-test", "doc", root["original_source"], canonical_bytes(root["analyzed_scope"])
            ),
        )
        attached = storage.invoke(
            "attach_data_request",
            {
                **producer,
                "request_meaning": json.loads(request.identity.canonical_input),
                "request_key": request.identity.key,
                "replicate": None,
                "binding": {
                    "inputs": [],
                    "support": [],
                    "parameters": semantic_value(request.parameters),
                    "request_inputs": semantic_value({}),
                    "inference": inference,
                    "populations": [],
                    "read_id": acquired["read_id"],
                },
            },
        )
    sample_kind = kernel["identities"][
        next(k.semantic_id for k in kernel["model"].kinds if k.name == "Sample"), "kind"
    ]
    population_kind = kernel["identities"][
        next(k.semantic_id for k in kernel["model"].kinds if k.name == "Population"), "kind"
    ]
    packets = [
        {
            "member_id": f"m{value}",
            "kind_contract": sample_kind,
            "context": {
                "subject": f"item:{value}",
                "original_source": "source:test",
                "analyzed_scope": scope,
            },
            "body": {"value": value, "document_subject": "doc"},
        }
        for value in values
    ]
    fence = claim(kernel, attached)
    with kernel["engine"].begin() as connection:
        intent = DataOperationStorage(connection).invoke(
            "retain_data_completion_intent",
            {
                **fence,
                "runtime_id": kernel["runtime"],
                "completion": {
                    "outcome": "success",
                    "inputs": [],
                    "support": [],
                    "implementation_revision": "native-test-source-v1",
                    "outputs": [
                        {
                            "role": "result",
                            "position": 0,
                            "multiplicity": 1,
                            "product": {
                                "kind_contract": population_kind,
                                "body": semantic_value({"complete": complete, "members": packets}),
                                "members": [
                                    {**packet, "body": semantic_value(packet["body"])}
                                    for packet in packets
                                ],
                            },
                        }
                    ],
                },
            },
        )
    receipt = publish(kernel, fence, intent)
    with kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        products = storage.invoke(
            "read_demand_result",
            {"demand_id": demand["demand_id"], "view": "products"},
        )
        product = next(use["products"][0] for use in products["uses"] if use["products"])
        parent = storage.invoke(
            "close_data_population",
            {
                "demand_id": demand["demand_id"],
                "name": "all-items",
                "product_id": product["product_id"],
                "derivation_id": receipt["derivation_id"],
                "member_role": "result",
            },
        )
        if ambiguous:
            storage.invoke(
                "close_data_population",
                {
                    "demand_id": demand["demand_id"],
                    "name": "other-items",
                    "product_id": product["product_id"],
                    "derivation_id": receipt["derivation_id"],
                    "member_role": "result",
                },
            )
    return demand, consumer, parent


@pytest.mark.parametrize("complete", [True, False])
def test_native_selected_population_has_authentic_parent_and_frozen_filter(
    population_kernel,
    complete,
):
    kernel = population_kernel
    demand, consumer, parent = discover(kernel, complete=complete)
    with kernel["engine"].begin() as connection:
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


def test_native_planner_selects_on_one_read_and_attaches_only_after_fresh_read(population_kernel):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner

    kernel = population_kernel
    demand, consumer, _ = discover(kernel)
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        assert planner.ready(snapshot, authorization=b"{}") == ()
        assert len(planner.selected_population_ids) == 1
        refreshed = planner.resume(demand["demand_id"])
        assert refreshed["read_id"] != snapshot["read_id"]
        ready = planner.ready(refreshed, authorization=b"{}")
        assert planner.selected_population_ids == ()
        assert len(ready) == 1
        assert ready[0].obligation == consumer["obligation_id"]


def test_native_planner_preserves_ambiguous_authentic_parent_populations(population_kernel):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner

    kernel = population_kernel
    demand, consumer, _ = discover(kernel, ambiguous=True)
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        assert planner.ready(snapshot, authorization=b"{}") == ()
        assert planner.selected_population_ids == ()
        current = planner.resume(demand["demand_id"])
        use = next(
            use for use in current["uses"] if use["obligation_id"] == consumer["obligation_id"]
        )
        assert use["fate"] == "awaiting-population"
        assert use["selection"]["reasons"][0]["code"] == "ambiguous-population"


def _complete_ready(kernel, ready, value=1):
    binding = json.loads(ready.binding)
    claim_fence = claim(kernel, json.loads(ready.native))
    kind = next(
        role.kind
        for operation in kernel["model"].operations
        if operation.semantic_id == ready.operation
        for role in operation.roles
        if role.direction == "output"
    )
    kind_contract = kernel["identities"][kind, "kind"]
    with kernel["engine"].begin() as connection:
        intent = DataOperationStorage(connection).invoke(
            "retain_data_completion_intent",
            {
                **claim_fence,
                "runtime_id": kernel["runtime"],
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
    return publish(kernel, claim_fence, intent)


def test_native_discovery_children_closed_fanin_and_pinned_resume(population_kernel):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner

    kernel = population_kernel
    demand, consumer, _parent = discover(kernel)
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
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
        _complete_ready(kernel, child)
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
        frontier = planner.ready(planner.resume(demand["demand_id"]), authorization=b"{}")
        aggregate = [request for request in frontier if request.operation == "urn:consumer"]
        assert any(request.operation == "urn:child" for request in frontier)
        assert len(aggregate) == 1 and aggregate[0].obligation == consumer["obligation_id"]
        assert [
            member.member for role in aggregate[0].binding_result.roles for member in role.members
        ] == ["m15"]
    _complete_ready(kernel, aggregate[0])
    _complete_ready(kernel, children[2])
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
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
    population_kernel, complete, values
):
    from corpus_structure.semantic.data_operation_demands import DemandPlanner

    kernel = population_kernel
    demand, _, _parent = discover(kernel, complete=complete, values=values)
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
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
