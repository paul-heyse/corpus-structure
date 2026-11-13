"""Epoch-zero materialization preserves pins; positive revocation remains fenced."""

import json
from importlib.resources import files

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from .test_data_operation_storage import ddo_kernel_engine as ddo_kernel_engine
from .test_data_operation_storage import kernel as kernel


@pytest.fixture
def snapshot_connection(semantic_bare_engine):
    source = files("corpus_structure.semantic").joinpath("sql/data_operations.sql").read_text()
    start = source.index("CREATE OR REPLACE FUNCTION ops.ddo_trust_snapshot_meaning(")
    end = source.index("END $$;", start) + len("END $$;")
    helper = source[start:end].replace(
        "ops.ddo_trust_snapshot_meaning", "pg_temp.ddo_trust_snapshot_meaning"
    )
    with semantic_bare_engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql(helper)
            yield connection
        finally:
            transaction.rollback()


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
    source = files("corpus_structure.semantic").joinpath("sql/data_operations.sql").read_text()
    start = source.index(
        " IF snapshot IS DISTINCT FROM ops.ddo_trust_snapshot_meaning(p_trust)"
    ) + len(" IF ")
    end = source.index(" THEN RAISE EXCEPTION 'binding trust snapshot changed'", start)
    binding_guard = source[start:end].replace(
        "ops.ddo_trust_snapshot_meaning", "pg_temp.ddo_trust_snapshot_meaning"
    )
    read_guard = (
        "pg_temp.ddo_trust_snapshot_meaning(boundary.trust_snapshot) IS DISTINCT FROM snapshot"
    )
    sql = text(
        """WITH arguments AS (
 SELECT pg_temp.ddo_trust_snapshot_meaning(CAST(:current AS jsonb)) snapshot,
 CAST(:pinned AS jsonb) p_trust),
 boundary AS (SELECT 'read:one' AS id,CAST(:pinned AS jsonb) trust_snapshot)
 SELECT """
        + read_guard
        + ","
        + binding_guard
        + " FROM arguments,boundary"
    )
    assert tuple(
        snapshot_connection.execute(
            sql,
            {
                "current": json.dumps(current),
                "pinned": json.dumps(pinned),
            },
        ).one()
    ) == (changed, changed)


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
            text("SELECT pg_temp.ddo_trust_snapshot_meaning(CAST(:snapshot AS jsonb))"),
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
    source = files("corpus_structure.semantic").joinpath("sql/data_operations.sql").read_text()
    start = source.index(" IF NOT (ops.ddo_trust_snapshot_meaning(read_trust)") + len(" IF ")
    end = source.index(" THEN", start)
    guard = source[start:end].replace(
        "ops.ddo_trust_snapshot_meaning", "pg_temp.ddo_trust_snapshot_meaning"
    )
    actual = snapshot_connection.scalar(
        text(
            "WITH arguments AS (SELECT CAST(:pinned AS jsonb) read_trust,"
            "CAST(:locked AS jsonb) snapshot) SELECT " + guard + " FROM arguments"
        ),
        {"pinned": json.dumps(pinned), "locked": json.dumps(locked)},
    )
    assert actual is changed


@pytest.mark.db
def test_native_multi_root_attachment_keeps_one_read_when_zero_epoch_rows_materialize(kernel):
    from corpus_structure.semantic.data_operation_demands import (
        DemandPlanner,
        RootSubject,
        freeze_demand,
    )
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage

    from .test_data_operation_storage import claim, publish, retain

    intent = freeze_demand(
        kernel["model"],
        roots=(RootSubject("one", "source:one", b"{}"), RootSubject("two", "source:two", b"{}")),
        targets=("urn:ddo-test:source",),
        inference="exact",
        execution_profile="execution:test",
    )
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
        demand = planner.register(
            intent,
            project="ddo-test",
            release=kernel["prepared"].release_id,
            runtime=kernel["runtime"],
        )["demand_id"]
        pinned = planner.resume(demand)
        assert pinned["trust_snapshot"] == {}
        ready = planner.ready(pinned, authorization=b"{}")
        assert len(ready) == 2
        assert {request.resolved.subject_context.original_source for request in ready} == {
            "source:one",
            "source:two",
        }
        reread = planner.resume(demand, read_id=pinned["read_id"])
        assert reread["read_id"] == pinned["read_id"] and reread["trust_snapshot"] == {}
        assert list(connection.scalars(text("SELECT epoch FROM ops.data_trust_scope"))) == [0, 0]
    first = next(
        request
        for request in ready
        if request.resolved.subject_context.original_source == "source:one"
    )
    fence = claim(kernel, json.loads(first.native))
    receipt = publish(kernel, fence, retain(kernel, fence))
    # Concrete support epochs remain in authentic publication attribution.
    assert list(receipt["trust_snapshot"].values()) == [0]
    with kernel["engine"].begin() as connection:
        DataOperationStorage(connection).invoke(
            "revoke_data_support",
            {
                "project_id": "ddo-test",
                "original_source": "source:one",
                "selector_kind": "derivation",
                "selector": receipt["derivation_id"],
                "reason": "positive epoch",
            },
        )
    with (
        kernel["engine"].begin() as connection,
        pytest.raises(DBAPIError, match="pins or current trust differ"),
    ):
        DemandPlanner(kernel["model"], DataOperationStorage(connection)).resume(
            demand, read_id=pinned["read_id"]
        )
