"""Generated frozen custody keeps task fences and fresh-statement snapshot admission."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
from corpus_structure.semantic.pdf_publication_native import pdf_freeze_native_sql


def test_generated_recipe_and_frozen_helpers_keep_purpose_fences(native_rollback):
    connection = native_rollback.connection
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, pdf_freeze_native_sql(get_metadata()))
    calls = (
        ("ops.bind_pdf_stage_recipe(NULL,NULL,NULL,NULL)", "P0004"),
        ("ops.require_pdf_frozen(NULL,NULL,NULL,NULL,NULL)", "42501"),
        ("ops.freeze_pdf_build(NULL,NULL,NULL,NULL,NULL)", "P0002"),
    )
    with native_owner(connection, "corpus_sem_writer"):
        for call, expected in calls:
            with pytest.raises(DBAPIError) as failure, connection.begin_nested():
                connection.execute(text("SELECT * FROM " + call)).all()
            assert getattr(failure.value.orig, "sqlstate", None) == expected, call


@pytest.mark.parametrize("level", ["REPEATABLE READ", "SERIALIZABLE"])
def test_generated_freeze_refuses_stale_snapshot_before_claim_inspection(
    commit_db_engine, commit_writer_engine, level
):
    with commit_db_engine.begin() as connection, native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, pdf_freeze_native_sql(get_metadata()))
    with commit_writer_engine.connect().execution_options(isolation_level=level) as connection:
        with (
            pytest.raises(DBAPIError, match="PDF freeze requires READ COMMITTED") as failure,
            connection.begin(),
        ):
            connection.execute(text("SELECT ops.freeze_pdf_build(NULL,NULL,NULL,NULL,NULL)")).all()
        assert getattr(failure.value.orig, "sqlstate", None) == "25000"
