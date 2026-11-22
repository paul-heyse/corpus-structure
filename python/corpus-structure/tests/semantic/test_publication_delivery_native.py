"""A receipt is pending for the exact selection before any consumer is queued."""

from pathlib import Path
from typing import cast

from sqlalchemy import func, select

from corpus_structure.schema.model_change import native_model_inputs
from corpus_structure.semantic import migrations
from corpus_structure.semantic._data_operation_wire import WirePublishDataDerivationRequest
from corpus_structure.semantic.data_operation_service import advance_demand_selection
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.target_installation import capture_target_installation
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
    preparation = prepare_kernel(STORAGE, directory=tmp_path / "delivery-contract")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, STORAGE, engine=admin, preparation=preparation)

    producer_kind = next(
        role.kind for role in kernel.model.operation(PRODUCER).roles if role.direction == "output"
    )
    sample_kind = kernel.identities[producer_kind, "kind"]
    pending = physical.tables["ops.data_publication_delivery"]
    receipts = physical.tables["ops.data_publication_receipt"]
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

    def advance(scope, demand, expected_demand=None, expected_generation=0):
        with admin.begin() as connection:
            return advance_demand_selection(
                connection,
                PROJECT,
                scope,
                demand,
                expected_demand_id=expected_demand,
                expected_generation=expected_generation,
            )

    def deliveries(connection, scope, generation):
        return connection.scalars(
            select(pending.c.receipt_id).where(
                pending.c.project_id == PROJECT,
                pending.c.name == scope,
                pending.c.selection_generation == generation,
            )
        ).all()

    a, a_fence, a_intent = prepare_publication("subject:a", 12)
    b, b_fence, b_intent = prepare_publication("subject:b", 14)
    c, c_fence, c_intent = prepare_publication("subject:c", 16)
    generation_a = advance("a", a)
    generation_b = advance("b", b)

    with admin.connect() as connection:
        active = connection.begin()
        uncommitted = DataOperationStorage(connection).publish_data_derivation(
            cast(
                WirePublishDataDerivationRequest,
                {**a_fence, "intent_id": a_intent["intent_id"]},
            )
        )
        receipt_a = uncommitted["receipt_id"]
        assert deliveries(connection, "a", generation_a.generation) == [receipt_a]
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
        # Late publication by C cannot move the restored A selection or add an
        # origin to its generation. Empty delivery alone says nothing about
        # enrollment or coverage of either generation.
        assert deliveries(connection, "a", generation_c.generation) == []
        assert deliveries(connection, "a", restored_a.generation) == []
