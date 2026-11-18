"""Epoch-zero materialization preserves pins; positive revocation remains fenced."""

import json
from typing import cast as typing_cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import (
    WireRevokeDataSupportRequest,
)
from semantic.data_operation_kernel_support import STORAGE


@pytest.fixture
def snapshot_connection(native_read):
    return native_read


def test_snapshot_comparison_reaches_installed_function(native_rollback):
    from corpus_structure.semantic.native_objects import native_owner

    connection = native_rollback.connection
    test_native_read_and_binding_snapshot_comparisons_preserve_epoch_meaning(
        connection, {"root": 1}, {"root": 2}, True
    )
    with native_owner(connection, "corpus_sem_publisher"):
        connection.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.ddo_trust_snapshot_meaning(snapshot jsonb) "
            "RETURNS jsonb LANGUAGE sql IMMUTABLE RETURN '{}'::jsonb"
        )
    with pytest.raises(AssertionError):
        test_native_read_and_binding_snapshot_comparisons_preserve_epoch_meaning(
            connection, {"root": 1}, {"root": 2}, True
        )


@pytest.mark.db
@pytest.mark.parametrize(
    "pinned, current, changed",
    [
        ({}, {"root": 0}, False),
        ({}, {"root": 0.0, "other": 0}, False),
        ({"root": 1}, {"root": 1, "other": 0}, False),
        ({"root": 1}, {"root": 2}, True),
        ({}, {"unknown-scope": 1}, True),
        ({"root": 1}, {"other": 1}, True),
    ],
)
def test_native_read_and_binding_snapshot_comparisons_preserve_epoch_meaning(
    snapshot_connection,
    pinned,
    current,
    changed,
):
    from sqlalchemy import literal, select
    from sqlalchemy.dialects.postgresql import JSONB

    from corpus_structure.semantic.support_trust_native import trust_snapshot_changed

    query = select(
        trust_snapshot_changed(literal(pinned, type_=JSONB()), literal(current, type_=JSONB()))
    )
    assert snapshot_connection.scalar(query) is changed


@pytest.mark.db
@pytest.mark.parametrize(
    "invalid",
    [
        None,
        "null",
        "[]",
        '{"root":null}',
        '{"root":-1}',
        '{"root":0.5}',
        '{"root":"0"}',
        '{"root":true}',
    ],
)
def test_native_snapshot_meaning_refuses_null_unknown_epoch_and_invalid_shapes(
    snapshot_connection, invalid
):
    with pytest.raises(DBAPIError, match="trust snapshot requires"):
        snapshot_connection.scalar(
            text("SELECT ops.ddo_trust_snapshot_meaning(CAST(:snapshot AS jsonb))"),
            {"snapshot": invalid},
        )


@pytest.mark.db
@pytest.mark.parametrize(
    "pinned, locked, changed",
    [
        ({}, {"root": 0}, False),
        ({"other": 1}, {"root": 0}, False),
        ({"root": 1, "other": 2}, {"root": 1}, False),
        ({"root": 1}, {"root": 2}, True),
        ({}, {"unknown-scope": 1}, True),
    ],
)
def test_native_attachment_checks_locked_positive_epochs_against_full_read_pins(
    snapshot_connection,
    pinned,
    locked,
    changed,
):
    from sqlalchemy import literal, select
    from sqlalchemy.dialects.postgresql import JSONB

    from corpus_structure.semantic.support_trust_native import locked_support_changed

    query = select(
        locked_support_changed(literal(pinned, type_=JSONB()), literal(locked, type_=JSONB()))
    )
    assert snapshot_connection.scalar(query) is changed


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
@pytest.mark.db
def test_native_multi_root_attachment_keeps_one_read_when_zero_epoch_rows_materialize(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import (
        DemandPlanner,
        RootSubject,
        freeze_demand,
    )
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from semantic.data_operation_demand_support import claim, publish, retain

    intent = freeze_demand(
        ddo_kernel["model"],
        roots=(RootSubject("one", "source:one", b"{}"), RootSubject("two", "source:two", b"{}")),
        targets=("urn:ddo-test:source",),
        inference="exact",
        execution_profile="execution:test",
    )
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        demand = planner.register(
            intent,
            project="ddo-test",
            release=ddo_kernel["prepared"].release_id,
            runtime=ddo_kernel["runtime"],
        )["demand_id"]
        pinned = planner.resume(demand)
        explicit_zeros = {
            connection.scalar(
                text("SELECT ops.ddo_scope('ddo-test',:source)"), {"source": source}
            ): 0
            for source in ("source:one", "source:two")
        }
        assert pinned["trust_snapshot"] == explicit_zeros
        # Omitted zero epochs have the same trust meaning as the acquired map.
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        ready = planner.ready({**pinned, "trust_snapshot": {}}, authorization=b"{}")
        assert len(ready) == 2
        assert {request.resolved.subject_context.original_source for request in ready} == {
            "source:one",
            "source:two",
        }
    with ddo_kernel["engine"].begin() as connection:
        planner = DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection))
        reread = planner.resume(demand, read_id=pinned["read_id"])
        assert reread["read_id"] == pinned["read_id"]
        assert reread["trust_snapshot"] == explicit_zeros
        assert list(connection.scalars(text("SELECT epoch FROM ops.data_trust_scope"))) == [0, 0]
    first = next(
        request
        for request in ready
        if request.resolved.subject_context.original_source == "source:one"
    )
    fence = claim(ddo_kernel, json.loads(first.native))
    receipt = publish(ddo_kernel, fence, retain(ddo_kernel, fence))
    # Concrete support epochs remain in authentic publication attribution.
    assert list(receipt["trust_snapshot"].values()) == [0]
    with ddo_kernel["engine"].begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            typing_cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": "ddo-test",
                    "original_source": "source:one",
                    "selector_kind": "derivation",
                    "selector": receipt["derivation_id"],
                    "reason": "positive epoch",
                },
            )
        )
    with (
        ddo_kernel["engine"].begin() as connection,
        pytest.raises(DBAPIError, match="pins or current trust differ"),
    ):
        DemandPlanner(ddo_kernel["model"], DataOperationStorage(connection)).resume(
            demand, read_id=pinned["read_id"]
        )
