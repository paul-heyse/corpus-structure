"""Explicit retained semantic pins reuse facts, never another demand's work policy."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SourceSetEntry
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_product_reference import DataProductReference
from corpus_structure.semantic.identity import canonical_bytes
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE
from semantic.test_data_operation_population_native import _complete_ready

PRODUCER = "urn:ddo-test:source"
CONSUMER = "urn:explicit-retained-consumer"


def _recipe():
    declarations = json.loads(STORAGE.declaration_content)
    producer = next(op for op in declarations["operations"] if op["id"] == PRODUCER)
    consumer = json.loads(json.dumps(producer))
    consumer.update(id=CONSUMER, potential_dependencies=[PRODUCER])
    consumer["roles"].insert(
        0,
        {
            "name": "items",
            "kind": "integer",
            "direction": "input",
            "minimum": 1,
            "maximum": 1,
            "collection": "scalar",
            "presence": "alternative",
            "alternatives": [PRODUCER],
            "selected": PRODUCER,
            "subject_target": "source-set",
            "support": {
                "provenance": "exact",
                "source": "frozen-source-set",
                "source_set": "selected",
                "coverage": "exact-retained-product",
                "identity_requirements": ["episode"],
            },
        },
    )
    consumer["binding"] = {"operator": "scan", "roles": ["items"]}
    declarations["operations"].append(consumer)
    return replace(
        STORAGE,
        name="explicit-retained-source-pins",
        declaration_content=canonical_bytes(declarations),
    )


PINNED = _recipe()
pytestmark = pytest.mark.parametrize("ddo_kernel", [PINNED], indirect=True, ids=["pinned-retained"])


def _produce(kernel, *, subject, value):
    demand, _, _, attached = attach(kernel, subject=subject, original_source="source:B")
    fence = claim(kernel, attached)
    receipt = publish(kernel, fence, retain(kernel, fence, outputs=(value,)))
    with kernel["engine"].connect() as connection:
        product = connection.scalar(
            text("SELECT product_id FROM ops.data_derivation_output WHERE derivation_id=:episode"),
            {"episode": receipt["derivation_id"]},
        )
    return demand, receipt, product


def _register(kernel, entry, inference="focus-comparison"):
    intent = freeze_demand(
        kernel["model"],
        roots=(RootSubject("focus:A", "source:A", b'{"focus":true}'),),
        targets=(CONSUMER,),
        source_sets=(FrozenSourceSet("selected", (entry,)),),
        inference=inference,
        execution_profile="execution:test",
    )
    assert intent.record["root_operations"] == [CONSUMER]
    with kernel["engine"].begin() as connection:
        return DemandPlanner(kernel["model"], DataOperationStorage(connection)).register(
            intent,
            project="ddo-test",
            release=kernel["prepared"].release_id,
            runtime=kernel["runtime"],
        )


def _ready(kernel, demand):
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
        snapshot = planner.resume(demand["demand_id"])
        return snapshot, planner.ready(snapshot, authorization=b"{}")


def test_native_explicit_retained_pin_crosses_demands_without_hidden_production(ddo_kernel):
    source_demand, original, product = _produce(ddo_kernel, subject="source-subject:B", value=42)
    _, sibling, sibling_product = _produce(ddo_kernel, subject="source-subject:sibling", value=99)
    context = SubjectContext("ddo-test", "source-subject:B", "source:B", b'{"page":1}')
    entry = SourceSetEntry.from_semantic_source(DataProductReference(product), context=context)
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).invoke(
            "cancel_data_demand",
            {"demand_id": source_demand["demand_id"], "reason": "finished source workflow"},
        )
    demand = _register(ddo_kernel, entry)
    snapshot, ready = _ready(ddo_kernel, demand)
    (answer,) = ready
    (actual,) = answer.binding_result.roles[0].members
    assert (actual.product, actual.subject, actual.original_source) == (
        product,
        context.subject,
        context.original_source,
    )
    assert actual.product != sibling_product and actual.support_episodes == (
        original["derivation_id"],
    )
    with ddo_kernel["engine"].connect() as connection:
        obligations = connection.execute(
            text(
                "SELECT operation_id,subject,original_source FROM ops.data_obligation WHERE demand_id=:demand"
            ),
            {"demand": demand["demand_id"]},
        ).all()
        assert obligations == [(CONSUMER, "focus:A", "source:A")]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 2
    # A caller-provided context does not establish another source occurrence.
    wrong_entry = SourceSetEntry.from_semantic_source(
        DataProductReference(product), context=replace(context, subject="forged-context")
    )
    _, wrong = _ready(ddo_kernel, _register(ddo_kernel, wrong_entry, "wrong-context"))
    assert wrong == ()
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).invoke(
            "revoke_data_support",
            {
                "project_id": "ddo-test",
                "original_source": "source:B",
                "selector_kind": "product",
                "selector": product,
                "reason": "the exact retained source was withdrawn",
            },
        )
    _, untrusted = _ready(ddo_kernel, _register(ddo_kernel, entry, "revoked-source"))
    assert untrusted == ()
    with ddo_kernel["engine"].begin() as connection:
        with pytest.raises(DBAPIError, match="trust snapshot changed"), connection.begin_nested():
            connection.execute(
                text(
                    "SELECT * FROM ops.data_binding_rows(:demand,:operation,CAST(:trust AS jsonb),:read,:subject,:source,CAST(:scope AS jsonb))"
                ),
                {
                    "demand": demand["demand_id"],
                    "operation": CONSUMER,
                    "trust": json.dumps(snapshot["trust_snapshot"]),
                    "read": snapshot["read_id"],
                    "subject": "focus:A",
                    "source": "source:A",
                    "scope": '{"focus":true}',
                },
            )
    with pytest.raises(DBAPIError, match="support|revoked"):
        _complete_ready(ddo_kernel, answer)
    with ddo_kernel["engine"].connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 2
