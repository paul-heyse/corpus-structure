"""A lost native connection before outer COMMIT discards current archive effects."""

import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import persist_release
from semantic.data_operation_kernel_support import STORAGE, prepare_kernel


def test_native_disconnect_before_outer_commit_discards_receipt(
    commit_db_engine, commit_admitter_engine
):
    captured = prepare_kernel(STORAGE)
    prepared = captured.prepared
    with (
        pytest.raises(DBAPIError),
        commit_admitter_engine.connect() as conn,
        conn.begin(),
    ):
        assert persist_release(
            conn, captured.bundle, captured.dependencies, captured.profile, prepared
        ) == prepared.release_id
        driver = conn.connection.driver_connection
        assert driver is not None
        driver.close()
    with commit_db_engine.connect() as conn:
        for relation in ("sem.release", "sem.artifact", "sem.data_operation_definition"):
            rows = table(relation)
            assert conn.scalar(
                select(func.count()).select_from(rows).where(rows.c.release_id == prepared.release_id)
            ) == 0
