"""Closed discovery contexts govern newly produced child products at native attachment."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identity import canonical_bytes
from semantic.data_operation_binding_support import discover
from semantic.data_operation_kernel_support import POPULATION
from semantic.test_data_operation_population_native import _complete_ready


def _recipe():
    declarations = json.loads(POPULATION.declaration_content)
    consumer = next(op for op in declarations["operations"] if op["id"] == "urn:consumer")
    consumer["roles"][0].update(kind="ChildReport", minimum=0, presence="optional")
    operands = [
        {"kind": "field", "value_type": "subject-context", "field": {"role": "items", "projection": "ChildReport", "field": "@context"}},
        {"kind": "population", "name": "all-items", "value_type": "subject-context", "population_projection": "qualified-context"},
    ]
    consumer["binding"] = {"operator": "all", "children": [{"operator": operator, "operands": operands} for operator in ("membership", "covers")]}
    child = next(op for op in declarations["operations"] if op["id"] == "urn:child")
    child["roles"][0]["kind"] = "ChildReport"
    declarations["operations"].append({**child, "id": "urn:child-other"})
    schema = POPULATION.schema_text + """  ChildReport:
    attributes:
      value: {range: integer, required: true}
      document_subject: {range: string, required: true}
"""
    return replace(POPULATION, name="qualified-context-fanin", schema_text=schema, declaration_content=canonical_bytes(declarations))


CONTEXT_FANIN = _recipe()
pytestmark = pytest.mark.parametrize("ddo_kernel", [CONTEXT_FANIN], indirect=True, ids=["qualified-context"])


def _frontier(kernel, demand):
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
        return planner.ready(planner.resume(demand["demand_id"]), authorization=b"{}")


def test_native_context_fanin_waits_for_new_child_products_and_preserves_pinned_resume(ddo_kernel):
    contexts = [dict(subject="same-local", original_source="source:test", analyzed_scope={"page": page}) for page in (1, 2)]
    demand, consumer, parent = discover(ddo_kernel, values=(5, 15), member_contexts=contexts)
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        use = next(use for use in snapshot["uses"] if use["products"])
        planner.expand_discovery(snapshot, population="all-items", product=use["products"][0]["product_id"], derivation=use["derivation_id"])
    children = _frontier(ddo_kernel, demand)
    assert len(children) == 2 and all(child.operation == "urn:child" for child in children)
    assert {json.loads(child.resolved.subject_context.analyzed_scope)["page"] for child in children} == {1, 2}
    _complete_ready(ddo_kernel, children[0], {"value": 101, "document_subject": "doc"})
    assert not any(ready.operation == "urn:consumer" for ready in _frontier(ddo_kernel, demand))
    _complete_ready(ddo_kernel, children[1], {"value": 202, "document_subject": "doc"})
    aggregate, = _frontier(ddo_kernel, demand)
    assert aggregate.obligation == consumer["obligation_id"]
    assert len(aggregate.binding_result.roles[0].members) == 2
    assert all(member.product != parent["evidence"]["product_id"] for member in aggregate.binding_result.roles[0].members)
    witness = json.loads(aggregate.binding_result.roles[0].population_witness)
    assert witness["projection"] == "qualified-context"
    assert {member["analyzed_scope"]["page"] for member in witness["members"]} == {1, 2}
    # Independently exercise the same protected validator attachment invokes:
    # a portable caller cannot invent a smaller/wrong closure or another project.
    binding = json.loads(aggregate.binding)
    for mutate in ("project", "scope", "missing"):
        meaning = json.loads(aggregate.request)[3]
        raw = json.loads(json.dumps(binding))
        # Request-input witness is a typed semantic mapping. Rebuild from an
        # independent changed value so native reconstruction, not shape, decides.
        from corpus_structure.semantic.data_operation_identity import decode_semantic_value
        inputs = decode_semantic_value(raw["request_inputs"])
        changed = inputs["items"]["population_witness"]["members"]
        if mutate == "project": changed[0]["project_id"] = "wrong-project"
        elif mutate == "scope": changed[0]["analyzed_scope"] = {"page": 99}
        else: changed.pop()
        raw["request_inputs"] = semantic_value(inputs)
        with ddo_kernel["engine"].begin() as connection:
            with pytest.raises(DBAPIError), connection.begin_nested():
                connection.execute(text("SELECT ops.ddo_require_binding(:demand,:operation,:subject,CAST(:meaning AS jsonb),CAST(:binding AS jsonb),CAST(:trust AS jsonb))"), {"demand": demand["demand_id"], "operation": aggregate.operation, "subject": aggregate.subject, "meaning": json.dumps(meaning), "binding": json.dumps(raw), "trust": json.dumps(json.loads(aggregate.resolved.trust_evidence)["trust"])})
    _complete_ready(ddo_kernel, aggregate)
    assert _frontier(ddo_kernel, demand) == ()


@pytest.mark.parametrize("complete", [True, False])
def test_native_context_fanin_distinguishes_complete_empty_from_partial(ddo_kernel, complete):
    demand, _, _ = discover(ddo_kernel, values=(), complete=complete)
    ready = _frontier(ddo_kernel, demand)
    if complete:
        aggregate, = ready
        assert aggregate.operation == "urn:consumer"
        assert aggregate.binding_result.roles[0].state == "known-absent"
        assert aggregate.binding_result.roles[0].members == ()
    else:
        assert ready == ()


def test_native_one_discovery_population_fans_out_without_duplicate_custody(ddo_kernel):
    demand, _, parent = discover(ddo_kernel, values=(5, 15), additional_discovery_targets=("urn:child-other",))
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        use = next(use for use in snapshot["uses"] if use["products"])
        for _ in range(2):
            closed = planner.expand_discovery(snapshot, population="all-items", product=use["products"][0]["product_id"], derivation=use["derivation_id"])
            assert closed["population_id"] == parent["population_id"]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_population WHERE demand_id=:demand"), {"demand": demand["demand_id"]}) == 1
    ready = _frontier(ddo_kernel, demand)
    assert len(ready) == 4
    assert {(child.operation, child.subject) for child in ready} == {(op, subject) for op in ("urn:child", "urn:child-other") for subject in ("item:5", "item:15")}
