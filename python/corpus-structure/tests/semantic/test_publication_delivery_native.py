"""A receipt is pending for the exact selection before any consumer is queued."""

import json
from pathlib import Path
from typing import cast

from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.model_change import native_model_inputs
from corpus_structure.semantic import migrations
from corpus_structure.semantic._data_operation_wire import WirePublishDataDerivationRequest
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
from corpus_structure.semantic.target_installation import capture_target_installation
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE, admit_kernel, prepare_kernel
from semantic.test_target_installation_native import install_target_root

ROOT = Path(__file__).resolve().parents[4]
PROJECT = "ddo-test"
PRODUCER = "urn:ddo-test:sample"
CONSUMER = "urn:ddo-test:value-consumer"


def test_publication_delivery_is_atomic_replayable_and_fenced_by_exact_selection(
    semantic_bare_engine, tmp_path, monkeypatch
):
    admin = semantic_bare_engine
    physical = get_metadata()
    epoch = capture_target_installation(physical, logical_sources=native_model_inputs(ROOT))
    *_, revision_path = install_target_root(admin, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", revision_path)

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
        assert advance(scope, demand) == token
        assert advance(scope, demand) == token
        with admin.begin() as connection:
            assert deliveries(connection, scope, token.generation) == [receipt]
            assert unreconciled(connection, scope, token.generation) == []

    uses = physical.tables["ops.demand_use"]

    def snapshot(demand):
        with admin.begin() as connection:
            return DemandPlanner(kernel.model, DataOperationStorage(connection)).resume(demand)

    def recipient(frontier):
        return next(row for row in frontier["obligations"] if row["operation_id"] == CONSUMER)

    def routes(frontier):
        with admin.begin() as connection:
            connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_writer")
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            return planner._fulfilled_use_recipients(
                frontier, [row["obligation_id"] for row in frontier["obligations"]]
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
    assert routes(snapshot(c)) == ()
    (other_reason,) = routes(frontier_b)
    assert other_reason["use_id"] != use_a
    assert other_reason["selection_name"] == generation_b.name
    reasons = routes(frontier_a)
    with admin.begin() as connection:
        connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_writer")
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        ready = planner.ready(frontier_a, authorization=b"{}")
    assert [item.operation for item in ready] == [CONSUMER]
    assert [item.obligation for item in ready] == [target_a["obligation_id"]]
    assert len(reasons) == 1
    reason = reasons[0]
    assert reason["use_id"] == use_a
    assert reason["producer_operation"] == PRODUCER
    assert reason["output_role"] == "result" and reason["output_position"] == 0
    assert reason["input_role"] == "source"
    assert reason["selection_name"] == restored_a.name
    assert reason["selection_generation"] == restored_a.generation
    assert reason["successor_fate"] == "pending" and reason["successor_use_id"] is None
    assert set(reason) == {
        "selection_name",
        "selection_generation",
        "use_id",
        "producer_operation",
        "output_role",
        "output_position",
        "recipient_obligation",
        "recipient_operation",
        "input_role",
        "successor_fate",
        "successor_use_id",
    }
    attached_frontier = snapshot(a)
    attached_use = next(
        item
        for item in attached_frontier["uses"]
        if item["obligation_id"] == target_a["obligation_id"]
    )
    with admin.begin() as connection:
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        (attached_reason,) = planner._fulfilled_use_recipients(
            attached_frontier, [target_a["obligation_id"]]
        )
    assert attached_reason == {
        **reason,
        "successor_fate": "attached",
        "successor_use_id": attached_use["use_id"],
    }
    assert recipient(snapshot(b)).get("request_id") is None

    extra = "urn:ddo-test:source"
    reusable, source, _, attached = attach(
        kernel, subject="subject:a", operation=PRODUCER, targets=(CONSUMER, extra)
    )
    reused = reusable["demand_id"]
    assert reused != a
    assert attached["fate"] == "fulfilled"
    reused_selection = advance("reused", reused)
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
    (reuse_reason,) = routes(frontier_reused)
    assert reuse_reason["recipient_operation"] == CONSUMER
    assert reuse_reason["use_id"] == reuse_id
    assert reuse_reason["selection_name"] == reused_selection.name
    current_reused = snapshot(reused)
    extra_obligation = next(
        row for row in current_reused["obligations"] if row["operation_id"] == extra
    )
    assert extra_obligation.get("request_id") is None
