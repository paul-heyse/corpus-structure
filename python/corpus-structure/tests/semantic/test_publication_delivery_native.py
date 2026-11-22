"""A receipt is pending for the exact selection before any consumer is queued."""

import json
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import (
    WireComputationalSupportMember,
    WirePublishDataDerivationRequest,
    WireRecordDataFateRequest,
    WireResultBinding,
    WireRevokeDataSupportRequest,
)
from corpus_structure.semantic.canonical_sentences import canonical_sentence_operation_sources
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_service import advance_demand_selection
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    data_operation_definition_projection,
)
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.sentence_products import sentence_product_inputs
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from native_test_support import principal_engine
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE, admit_kernel, prepare_kernel

ROOT = Path(__file__).resolve().parents[4]
PROJECT = "ddo-test"
PRODUCER = "urn:ddo-test:sample"
CONSUMER = "urn:ddo-test:value-consumer"


@pytest.fixture
def delivery_principal(native_settings):
    engines = []

    def acquire(admin, purpose):
        engine = principal_engine(native_settings, purpose, admin.url.database)
        engines.append(engine)
        return engine

    yield acquire
    for engine in engines:
        engine.dispose()


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True)
def test_writer_scheduler_uses_authenticated_wire_and_refuses_reader(
    ddo_kernel, delivery_principal
):
    from corpus_structure.semantic.data_operation_wire import wire_contract_digest

    kernel = ddo_kernel
    demand, _, _, _ = attach(kernel, operation=PRODUCER)
    writer = delivery_principal(kernel.engine, "write")
    reader = delivery_principal(kernel.engine, "read")
    payload = {"demand_id": demand["demand_id"]}
    with writer.begin() as connection:
        raw = connection.scalar(select(func.ops.resume_data_demand(literal(payload, type_=JSONB))))
        assert set(raw) == {"payload", "contract_digest"}
        assert raw["contract_digest"] == wire_contract_digest()
        assert raw["payload"]["demand_id"] == demand["demand_id"]
        admitted = DataOperationStorage(connection).resume_data_demand(payload)
        assert admitted["demand_id"] == demand["demand_id"]
    with pytest.raises(DBAPIError, match="permission denied"), reader.begin() as connection:
        DataOperationStorage(connection).resume_data_demand(payload)
    with reader.begin() as connection:
        public = DataOperationStorage(connection).read_demand_result(payload)
    assert all(
        not {
            "native_readiness",
            "native_settlement",
            "binding_origin_changed",
            "binding_scope_changed",
            "binding_authority_changed",
        }.intersection(row)
        for row in public["obligations"]
    )
    with pytest.raises(DBAPIError, match="input schema"), writer.begin() as connection:
        connection.scalar(
            select(
                func.ops.resume_data_demand(
                    literal(
                        {**payload, "unexpected": True},
                        type_=JSONB,
                    )
                )
            )
        )


def test_publication_delivery_is_atomic_replayable_and_fenced_by_exact_selection(
    commit_db_engine, tmp_path, delivery_principal
):
    admin = commit_db_engine
    writer = delivery_principal(admin, "write")
    physical = get_metadata()

    # Lower the real declaration without running its parser provider. Check its
    # role against the same native source-address routine used for delivery.
    core = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
    bundle = sentence_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    prepared = prepare_release(bundle)
    sources = canonical_sentence_operation_sources()
    model = compile_data_operations(
        schema=bundle,
        python_sources=sources,
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    lowered = json.loads(
        data_operation_definition_projection(
            prepared,
            model,
            native_digest="native:test",
            captured_contracts=sources.boundary_contracts,
        )
    )
    (canonical,) = [
        operation
        for operation in lowered["operations"]
        if operation["operation_id"] == "segment.sentences/canonical-projection"
    ]
    (inventory,) = canonical["input_roles"]
    assert inventory["name"] == "inventory"
    assert inventory["support"]["source"] == "original-source"
    header = literal({"original_source": "source:one"}, type_=JSONB())
    role = literal(inventory, type_=JSONB())
    source_sets = literal({}, type_=JSONB())
    with admin.begin() as connection:
        assert connection.execute(
            select(
                func.ops.ddo_binding_source_address(role, header, "source:one", source_sets),
                func.ops.ddo_binding_source_address(role, header, "source:two", source_sets),
            )
        ).one() == (True, False)

    preparation = prepare_kernel(STORAGE, directory=tmp_path / "delivery-contract")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, STORAGE, engine=admin, preparation=preparation)

    producer_kind = next(
        role.kind for role in kernel.model.operation(PRODUCER).roles if role.direction == "output"
    )
    sample_kind = kernel.identities[producer_kind, "kind"]
    pending = physical.tables["ops.data_publication_delivery"]
    receipts = physical.tables["ops.data_publication_receipt"]
    fulfillments = physical.tables["ops.data_publication_fulfillment"]
    requests = physical.tables["ops.data_request"]

    def prepare_publication(subject, value):
        demand, _, _, attached = attach(
            kernel, subject=subject, operation=PRODUCER, targets=(CONSUMER,)
        )
        fence = claim(kernel, attached, seconds=300)

        def sample_output(completion):
            completion["outputs"][0]["product"].update(
                kind_contract=sample_kind, body=semantic_value({"value": value})
            )

        intent = retain(kernel, fence, mutate=sample_output)
        return demand["demand_id"], fence, intent

    def enroll(connection, scope, demand, expected_demand=None, expected_generation=0):
        return advance_demand_selection(
            connection,
            PROJECT,
            scope,
            demand,
            expected_demand_id=expected_demand,
            expected_generation=expected_generation,
        )

    def advance(scope, demand, expected_demand=None, expected_generation=0):
        with admin.begin() as connection:
            return enroll(connection, scope, demand, expected_demand, expected_generation)

    def publish_in(connection, fence, intent):
        return DataOperationStorage(connection).publish_data_derivation(
            cast(
                WirePublishDataDerivationRequest,
                {**fence, "intent_id": intent["intent_id"]},
            )
        )

    def deliveries(connection, scope, generation):
        return connection.scalars(
            select(pending.c.receipt_id).where(
                pending.c.project_id == PROJECT,
                pending.c.name == scope,
                pending.c.selection_generation == generation,
            )
        ).all()

    def unreconciled(connection, scope, generation):
        return connection.scalars(
            select(func.ops.ddo_unreconciled_publication_origins(PROJECT, scope, generation))
        ).all()

    a, a_fence, a_intent = prepare_publication("subject:a", 12)
    b, b_fence, b_intent = prepare_publication("subject:b", 14)
    c, c_fence, c_intent = prepare_publication("subject:c", 16)
    generation_a = advance("a", a)
    generation_b = advance("b", b)

    with admin.connect() as connection:
        active = connection.begin()
        uncommitted = publish_in(connection, a_fence, a_intent)
        receipt_a = uncommitted["receipt_id"]
        assert deliveries(connection, "a", generation_a.generation) == [receipt_a]
        assert connection.scalars(
            select(fulfillments.c.demand_id).where(fulfillments.c.receipt_id == receipt_a)
        ).all() == [a]
        assert deliveries(connection, "b", generation_b.generation) == []
        assert (
            connection.scalar(
                select(func.count())
                .select_from(requests)
                .where(requests.c.operation_id == CONSUMER)
            )
            == 0
        )
        active.rollback()

    with admin.begin() as connection:
        assert deliveries(connection, "a", generation_a.generation) == []
        assert connection.scalar(select(receipts.c.id).where(receipts.c.id == receipt_a)) is None
        assert (
            connection.scalar(
                select(fulfillments.c.use_id).where(fulfillments.c.receipt_id == receipt_a)
            )
            is None
        )

    committed = publish(kernel, a_fence, a_intent)
    assert committed["receipt_id"] == receipt_a and committed["replayed"] is False
    replay = publish(kernel, a_fence, a_intent)
    assert replay["receipt_id"] == receipt_a and replay["replayed"] is True

    generation_c = advance("a", c, a, generation_a.generation)
    restored_a = advance("a", a, c, generation_c.generation)
    assert restored_a.generation == 3
    assert advance("a", a) == generation_a
    receipt_b = publish(kernel, b_fence, b_intent)["receipt_id"]
    assert publish(kernel, c_fence, c_intent)["replayed"] is False
    with admin.begin() as connection:
        assert deliveries(connection, "a", generation_a.generation) == [receipt_a]
        assert deliveries(connection, "b", generation_b.generation) == [receipt_b]
        # The restored generation reconciles the previously published A,
        # while the late C remains outside either current named scope.
        assert deliveries(connection, "a", generation_c.generation) == []
        assert deliveries(connection, "a", restored_a.generation) == [receipt_a]
        assert unreconciled(connection, "a", generation_c.generation) == []

    for publication_first in (False, True):
        scope = "publication-first" if publication_first else "enrollment-first"
        demand, fence, intent = prepare_publication("subject:" + scope, 18)
        with admin.connect() as enrolling, admin.connect() as publishing:
            enrolling.exec_driver_sql("SET LOCAL lock_timeout = '1s'")
            publishing.exec_driver_sql("SET LOCAL lock_timeout = '1s'")
            if publication_first:
                publication = publish_in(publishing, fence, intent)
                token = enroll(enrolling, scope, demand)
            else:
                token = enroll(enrolling, scope, demand)
                publication = publish_in(publishing, fence, intent)

            # Each statement ran before the other transaction committed.
            assert deliveries(enrolling, scope, token.generation) == []
            assert unreconciled(publishing, scope, token.generation) == []
            receipt = publication["receipt_id"]
            if publication_first:
                publishing.commit()
                enrolling.commit()
            else:
                enrolling.commit()
                publishing.commit()

        with admin.begin() as connection:
            assert deliveries(connection, scope, token.generation) == []
            assert unreconciled(connection, scope, token.generation) == [receipt]
            assert unreconciled(connection, "b", generation_b.generation) == []
        # Ordinary execution resume repairs the committed visibility gap. The
        # operator does not replay enrollment to make its own committed work live.
        for _ in range(2):
            with writer.begin() as connection:
                DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(demand)
        with admin.begin() as connection:
            assert deliveries(connection, scope, token.generation) == [receipt]
            assert unreconciled(connection, scope, token.generation) == []

    uses = physical.tables["ops.demand_use"]

    def snapshot(demand):
        with writer.begin() as connection:
            return DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(demand)

    def recipient(frontier):
        return next(row for row in frontier["obligations"] if row["operation_id"] == CONSUMER)

    wakes = physical.tables["ops.data_obligation_wake"]

    def origin_work(frontier):
        with admin.connect() as connection:
            return tuple(
                connection.execute(
                    select(
                        wakes.c.obligation_id,
                        wakes.c.origin_id,
                        wakes.c.input_role,
                        wakes.c.occurrence,
                    )
                    .where(
                        wakes.c.obligation_id == recipient(frontier)["obligation_id"],
                        wakes.c.origin_kind == "fulfilled-use",
                    )
                    .order_by(wakes.c.id)
                ).mappings()
            )

    with admin.begin() as connection:
        use_a = connection.scalar(
            select(fulfillments.c.use_id).where(fulfillments.c.receipt_id == receipt_a)
        )
        assert use_a is not None
    frontier_a = snapshot(a)
    frontier_b = snapshot(b)
    target_a = recipient(frontier_a)
    assert target_a.get("request_id") is None
    assert origin_work(snapshot(c)) == ()
    (other_work,) = origin_work(frontier_b)
    assert other_work["origin_id"] != use_a
    (work,) = origin_work(frontier_a)
    assert work["origin_id"] == use_a
    assert work["obligation_id"] == target_a["obligation_id"] and work["input_role"] == "source"
    assert work["occurrence"]["output_role"] == "result"
    assert work["occurrence"]["output_position"] == 0 and work["occurrence"]["member_id"] is None
    with writer.begin() as connection:
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        ready = planner.ready(frontier_a, authorization=b"{}")
    assert [item.operation for item in ready] == [CONSUMER]
    assert [item.obligation for item in ready] == [target_a["obligation_id"]]
    attached_frontier = snapshot(a)
    attached_use = next(
        item
        for item in attached_frontier["uses"]
        if item["obligation_id"] == target_a["obligation_id"]
    )
    assert attached_use["fate"] == "attached"
    assert "inputs" in attached_use["selection"]
    binding = cast(WireResultBinding, attached_use["selection"])
    (input_,) = binding["inputs"]
    (support,) = binding["support"]
    assert input_["role"] == support["role"] == "source"
    assert input_["product_id"] == work["occurrence"]["product_id"]
    assert "admission_use_id" in support
    assert cast(WireComputationalSupportMember, support)["admission_use_id"] == use_a
    assert input_["producer_output"] == {
        "role": "result",
        "position": 0,
        "member_id": None,
        "multiplicity": 1,
    }
    assert origin_work(attached_frontier) == (work,)
    assert recipient(snapshot(b)).get("request_id") is None

    extra = "urn:ddo-test:source"
    reusable, source, _, attached = attach(
        kernel, subject="subject:a", operation=PRODUCER, targets=(CONSUMER, extra)
    )
    reused = reusable["demand_id"]
    assert reused != a
    assert attached["fate"] == "fulfilled"
    advance("reused", reused)
    with admin.begin() as connection:
        reuse_id = connection.scalar(
            select(uses.c.id).where(
                uses.c.obligation_id == source["obligation_id"], uses.c.fate == "fulfilled"
            )
        )
        assert reuse_id is not None
        assert (
            connection.scalar(
                select(fulfillments.c.receipt_id).where(fulfillments.c.use_id == reuse_id)
            )
            is None
        )
    frontier_reused = snapshot(reused)
    assert recipient(frontier_reused).get("request_id") is None
    (reuse_work,) = origin_work(frontier_reused)
    assert reuse_work["obligation_id"] == recipient(frontier_reused)["obligation_id"]
    assert reuse_work["origin_id"] == reuse_id and reuse_work["input_role"] == "source"
    current_reused = snapshot(reused)
    extra_obligation = next(
        row for row in current_reused["obligations"] if row["operation_id"] == extra
    )
    assert extra_obligation.get("request_id") is None

    demand, fence, intent = prepare_publication("subject:waiting", 20)
    advance("waiter", demand)

    def remember_wait(frontier):
        with admin.begin() as connection:
            connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_writer")
            DataOperationStorage(connection).record_data_fate(
                cast(
                    WireRecordDataFateRequest,
                    {
                        "obligation_id": recipient(frontier)["obligation_id"],
                        "fate": "awaiting-inputs",
                        "selection": {"read_id": frontier["read_id"], "reasons": []},
                    },
                )
            )

    remember_wait(snapshot(demand))
    assert recipient(snapshot(demand))["binding_origin_changed"] is False
    published = publish(kernel, fence, intent)
    seen = snapshot(demand)
    assert recipient(seen)["binding_origin_changed"] is True
    (pending_work,) = origin_work(seen)
    remember_wait(seen)
    settled_wait = snapshot(demand)
    assert recipient(settled_wait)["binding_origin_changed"] is False
    assert origin_work(settled_wait) == (pending_work,)
    assert recipient(settled_wait)["binding_authority_changed"] is False
    with admin.begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": PROJECT,
                    "original_source": "source:test",
                    "selector_kind": "derivation",
                    "selector": published["derivation_id"],
                    "reason": "retired selected producer episode",
                },
            )
        )
    revoked = snapshot(demand)
    assert recipient(revoked)["binding_authority_changed"] is True
    assert recipient(revoked)["native_readiness"]["ready"] is False
    assert origin_work(revoked) == (pending_work,)
    remember_wait(revoked)
    assert recipient(snapshot(demand))["binding_authority_changed"] is False


def test_dependency_free_waiter_observes_local_candidate_arrival_and_departure(
    commit_db_engine, tmp_path, delivery_principal
):
    admin = commit_db_engine
    writer, reader = (delivery_principal(admin, purpose) for purpose in ("write", "read"))
    target = "urn:ddo-test:consumer"
    other = "urn:ddo-test:source"
    prepared = prepare_kernel(STORAGE, directory=tmp_path / "local-readiness")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, STORAGE, engine=admin, preparation=prepared)

    targets = (target, PRODUCER, other)
    demand, producer, _, matching = attach(kernel, operation=PRODUCER, targets=targets)
    second, _, _, unrelated = attach(kernel, operation=other, targets=targets)
    assert demand["demand_id"] == second["demand_id"]

    def snapshot():
        with writer.begin() as connection:
            return DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(
                demand["demand_id"]
            )

    def candidate(page):
        return next(row for row in page["obligations"] if row["operation_id"] == target)

    def remember(page, obligation):
        observed = {"read_id": page["read_id"], "reasons": []}
        with admin.begin() as connection:
            DataOperationStorage(connection).record_data_fate(
                {
                    "obligation_id": obligation,
                    "fate": "awaiting-inputs",
                    "selection": observed,
                }
            )

    def target_bindings(page):
        with writer.begin() as connection:
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            return tuple(
                request
                for request in planner.bound_requests(page, authorization=b"{}")
                if request.operation == target
            )

    first = snapshot()
    target_id = candidate(first)["obligation_id"]
    assert candidate(first)["native_readiness"] is None
    with pytest.raises(DBAPIError, match="permission denied"), reader.begin() as connection:
        DataOperationStorage(connection).resume_data_demand({"demand_id": demand["demand_id"]})
    remember(first, target_id)
    fence = claim(kernel, unrelated)
    publish(kernel, fence, retain(kernel, fence, outputs=(15,)))
    unchanged = snapshot()
    assert candidate(unchanged)["binding_origin_changed"] is False
    assert target_bindings(unchanged) == ()

    sample_kind = kernel.identities[
        next(
            role.kind
            for role in kernel.model.operation(PRODUCER).roles
            if role.direction == "output"
        ),
        "kind",
    ]

    def sample_output(completion):
        completion["outputs"][0]["product"].update(
            kind_contract=sample_kind, body=semantic_value({"value": 15})
        )

    fence = claim(kernel, matching)
    published = publish(kernel, fence, retain(kernel, fence, mutate=sample_output))
    arrived = snapshot()
    assert candidate(arrived)["binding_origin_changed"] is True
    with reader.begin() as connection:
        public = DataOperationStorage(connection).read_demand_result(
            {"demand_id": demand["demand_id"]}
        )
    assert "binding_origin_changed" not in candidate(public)
    (bound,) = target_bindings(arrived)
    (member,) = bound.resolved.roles[0].members
    assert member.support_episodes == (published["derivation_id"],)
    remember(arrived, target_id)
    assert candidate(snapshot())["binding_origin_changed"] is False

    remember(snapshot(), producer["obligation_id"])
    departed = snapshot()
    assert candidate(departed)["binding_origin_changed"] is True
    assert candidate(departed)["binding_authority_changed"] is False
    assert target_bindings(departed) == ()
    assert candidate(snapshot())["binding_origin_changed"] is False
