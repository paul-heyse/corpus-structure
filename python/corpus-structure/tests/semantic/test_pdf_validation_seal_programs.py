"""Typed validation and sealing retain purpose and fresh snapshot admission."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
from corpus_structure.semantic.pdf_publication_native import pdf_validation_and_seal_native_sql


def test_generated_validation_and_seal_keep_native_fences(native_rollback):
    connection = native_rollback.connection
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, pdf_validation_and_seal_native_sql(metadata))
    with native_owner(connection, "corpus_sem_writer"):
        for call, expected in (
            ("ops.validate_pdf_build(NULL,NULL,NULL,NULL,NULL)", "P0002"),
            ("ops.seal_pdf_build(NULL,NULL,NULL,NULL,NULL,NULL)", "P0004"),
        ):
            with pytest.raises(DBAPIError) as failure, connection.begin_nested():
                connection.execute(text("SELECT * FROM " + call)).all()
            assert getattr(failure.value.orig, "sqlstate", None) == expected, call


@pytest.mark.parametrize("level", ["REPEATABLE READ", "SERIALIZABLE"])
def test_generated_validation_refuses_stale_snapshot_before_receipt_lookup(
    commit_db_engine, commit_writer_engine, level
):
    with commit_db_engine.begin() as connection, native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, pdf_validation_and_seal_native_sql(metadata))
    with commit_writer_engine.connect().execution_options(isolation_level=level) as connection:
        with pytest.raises(DBAPIError, match="PDF projection admission requires READ COMMITTED") as failure, connection.begin():
            connection.execute(text("SELECT * FROM ops.validate_pdf_build(NULL,NULL,NULL,NULL,NULL)")).all()
        assert getattr(failure.value.orig, "sqlstate", None) == "25000"
