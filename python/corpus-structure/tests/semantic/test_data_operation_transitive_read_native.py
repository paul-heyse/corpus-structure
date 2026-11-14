"""Pinned A consumes B whose authentic required support originates at C."""

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
from semantic.test_data_operation_pinned_reuse_native import CONSUMER, PINNED, PRODUCER
from semantic.test_data_operation_population_native import _complete_ready

DOWNSTREAM = "urn:transitive-scope-consumer"


def _recipe():
    assert PINNED.declaration_content is not None
    document = json.loads(PINNED.declaration_content)
    consumer = json.loads(
        json.dumps(next(op for op in document["operations"] if op["id"] == CONSUMER))
    )
    consumer["id"] = DOWNSTREAM
    consumer["potential_dependencies"] = [CONSUMER]
    consumer["roles"][0]["alternatives"] = [CONSUMER]
    consumer["roles"][0]["selected"] = CONSUMER
    document["operations"].append(consumer)
    return replace(
        PINNED, name="transitive-read-three-scopes", declaration_content=canonical_bytes(document)
    )


CHAIN = _recipe()


def _entry(kernel, receipt):
    with kernel["engine"].connect() as connection:
        row = (
            connection.execute(
                text(
                    "SELECT p.id,p.subject,p.original_source,p.analyzed_scope FROM kb.data_product p JOIN ops.data_derivation_output o ON o.product_id=p.id WHERE o.derivation_id=:episode"
                ),
                {"episode": receipt["derivation_id"]},
            )
            .mappings()
            .one()
        )
    return SourceSetEntry.from_semantic_source(
        DataProductReference(row["id"]),
        context=SubjectContext(
            "ddo-test",
            row["subject"],
            row["original_source"],
            canonical_bytes(row["analyzed_scope"]),
        ),
    )


def _demand(kernel, entry, *, source, operation, inference, subject=None, scope=b"{}"):
    intent = freeze_demand(
        kernel["model"],
        roots=(RootSubject("subject:" + source if subject is None else subject, source, scope),),
        targets=(operation,),
        source_sets=(FrozenSourceSet("selected", (entry,)),),
        inference=inference,
        execution_profile="execution:test",
    )
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
        demand = planner.register(
            intent,
            project="ddo-test",
            release=kernel["prepared"].release_id,
            runtime=kernel["runtime"],
        )
        page = planner.resume(demand["demand_id"])
        ready = planner.ready(page, authorization=b"{}")
    return demand, page, ready


@pytest.mark.db
@pytest.mark.parametrize("ddo_kernel", [CHAIN], indirect=True, ids=["three-scopes"])
def test_transitive_support_revocation_changes_pinned_read_and_fresh_acquisition(ddo_kernel):
    _, _, _, request_c = attach(ddo_kernel, subject="subject:C", original_source="source:C")
    fence = claim(ddo_kernel, request_c)
    c = publish(ddo_kernel, fence, retain(ddo_kernel, fence, outputs=(41,)))
    _, _, (ready_b,) = _demand(
        ddo_kernel,
        _entry(ddo_kernel, c),
        source="source:B",
        operation=CONSUMER,
        inference="produce:B",
    )
    b = _complete_ready(ddo_kernel, ready_b, value=42)
    demand_a, page_a, (ready_a,) = _demand(
        ddo_kernel,
        _entry(ddo_kernel, b),
        source="source:A",
        operation=DOWNSTREAM,
        inference="consume:A",
    )
    # Scope C is not a root or direct frozen SourceSet in A; it is required solely
    # by B's authentic support. Stable continuation must retain the same read.
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        assert (
            planner.resume(demand_a["demand_id"], read_id=page_a["read_id"])["read_id"]
            == page_a["read_id"]
        )
        scope_c = connection.scalar(text("SELECT ops.ddo_scope('ddo-test','source:C')"))
        DataOperationStorage(connection).invoke(
            "revoke_data_support",
            {
                "project_id": "ddo-test",
                "original_source": "source:C",
                "selector_kind": "derivation",
                "selector": c["derivation_id"],
                "reason": "transitive upstream withdrawal",
            },
        )
    with ddo_kernel["engine"].begin() as connection:
        with (
            pytest.raises(DBAPIError, match="pins or current trust differ"),
            connection.begin_nested(),
        ):
            DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection)).resume(
                demand_a["demand_id"], read_id=page_a["read_id"]
            )
        current = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection)).resume(
            demand_a["demand_id"]
        )
        assert current["trust_snapshot"][scope_c] == 1
        assert (
            DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection)).ready(
                current, authorization=b"{}"
            )
            == ()
        )
    with pytest.raises(DBAPIError, match=r"support|revoked"):
        _complete_ready(ddo_kernel, ready_a)
    # A new C event after revocation has the same support scope at nonzero epoch;
    # fresh B/A requests must carry it rather than fail containment as incomplete.
    _, _, _, fresh_request = attach(
        ddo_kernel, subject="subject:C:fresh", original_source="source:C"
    )
    fresh_fence = claim(ddo_kernel, fresh_request)
    fresh_c = publish(ddo_kernel, fresh_fence, retain(ddo_kernel, fresh_fence, outputs=(43,)))
    _, _, (fresh_b,) = _demand(
        ddo_kernel,
        _entry(ddo_kernel, fresh_c),
        source="source:B",
        operation=CONSUMER,
        inference="produce:B:fresh",
    )
    fresh_b_receipt = _complete_ready(ddo_kernel, fresh_b, value=44)
    _, fresh_page, (fresh_a,) = _demand(
        ddo_kernel,
        _entry(ddo_kernel, fresh_b_receipt),
        source="source:A",
        operation=DOWNSTREAM,
        inference="consume:A:fresh",
    )
    assert fresh_page["trust_snapshot"][scope_c] == 1
    assert _complete_ready(ddo_kernel, fresh_a)["derivation_id"]


REBOUND_DOWNSTREAM = "urn:rebound-support-dependent"


def _rebound_recipe():
    assert CHAIN.declaration_content is not None
    document = json.loads(CHAIN.declaration_content)
    consumer = next(operation for operation in document["operations"] if operation["id"] == DOWNSTREAM)
    consumer["potential_dependencies"] = [PRODUCER, CONSUMER]
    role = consumer["roles"][0]
    role["presence"] = "required"
    role.pop("alternatives", None)
    role.pop("selected", None)
    role["support"]["identity_requirements"] = []
    role["support"]["provenance"] = "value_substitution"
    dependent = json.loads(json.dumps(consumer))
    dependent["id"] = REBOUND_DOWNSTREAM
    dependent["potential_dependencies"] = [DOWNSTREAM]
    dependent["roles"][0]["support"]["provenance"] = "exact"
    dependent["roles"][0]["support"]["identity_requirements"] = ["episode"]
    document["operations"].append(dependent)
    return replace(CHAIN, name="rebound-selected-support-scopes", declaration_content=canonical_bytes(document))


REBOUND = _rebound_recipe()


@pytest.mark.db
@pytest.mark.parametrize("ddo_kernel", [REBOUND], indirect=True, ids=["rebound-scopes"])
def test_read_and_publication_pin_selected_rebound_support_in_addition_to_original_episode(ddo_kernel):
    # B's original fact supports A. An equivalent B fact will later be produced
    # with independent required support from C, without changing A's computation.
    _, _, _, request_b = attach(ddo_kernel, subject="subject:B", original_source="source:B")
    fence_b = claim(ddo_kernel, request_b)
    original_b = publish(ddo_kernel, fence_b, retain(ddo_kernel, fence_b, outputs=(41,)))
    demand_a, _, (ready_a,) = _demand(ddo_kernel, _entry(ddo_kernel, original_b), source="source:A", operation=DOWNSTREAM, inference="rebound:A")
    original_a = _complete_ready(ddo_kernel, ready_a, value=42)

    _, _, _, request_c = attach(ddo_kernel, subject="subject:C", original_source="source:C")
    fence_c = claim(ddo_kernel, request_c)
    original_c = publish(ddo_kernel, fence_c, retain(ddo_kernel, fence_c, outputs=(41,)))
    _, _, (replacement_b,) = _demand(ddo_kernel, _entry(ddo_kernel, original_c), source="source:B", subject="subject:B", scope=b'{"page":1}', operation=CONSUMER, inference="replacement:B")
    equivalent_b = _complete_ready(ddo_kernel, replacement_b, value=41)
    assert _entry(ddo_kernel, equivalent_b).reference == _entry(ddo_kernel, original_b).reference
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).invoke("revoke_data_support", {"project_id": "ddo-test", "original_source": "source:B", "selector_kind": "derivation", "selector": original_b["derivation_id"], "reason": "replace B support with independently produced equivalent value"})
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        assert planner.ready(planner.resume(demand_a["demand_id"]), authorization=b"{}") == ()
        assert planner.fulfilled_request_ids
        current_a = planner.resume(demand_a["demand_id"])
        assert any(use["derivation_id"] == original_a["derivation_id"] and use["fate"] == "fulfilled" for use in current_a["uses"])
        assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 4

    demand_d, pinned, (ready_d,) = _demand(ddo_kernel, _entry(ddo_kernel, original_a), source="source:D", operation=REBOUND_DOWNSTREAM, inference="inspect-rebound:A")
    with ddo_kernel["engine"].begin() as connection:
        scope_c = connection.scalar(text("SELECT ops.ddo_scope('ddo-test','source:C')"))
        locked = connection.scalar(text("SELECT ops.ddo_lock_support('ddo-test','source:D',CAST(:support AS jsonb))"), {"support": json.dumps(json.loads(ready_d.binding)["support"])})
        assert locked[scope_c] == 0
        DataOperationStorage(connection).invoke("revoke_data_support", {"project_id": "ddo-test", "original_source": "source:C", "selector_kind": "derivation", "selector": original_c["derivation_id"], "reason": "withdraw selected replacement support"})
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        with pytest.raises(DBAPIError, match="pins or current trust differ"), connection.begin_nested():
            planner.resume(demand_d["demand_id"], read_id=pinned["read_id"])
        current = planner.resume(demand_d["demand_id"])
        assert current["trust_snapshot"][scope_c] == 1
        assert planner.ready(current, authorization=b"{}") == ()
    with pytest.raises(DBAPIError, match=r"support|revoked"):
        _complete_ready(ddo_kernel, ready_d)
