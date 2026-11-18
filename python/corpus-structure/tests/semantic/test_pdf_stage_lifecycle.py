"""Generated lifecycle entrypoints retain purpose privileges and stale-fence refusal."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
from corpus_structure.semantic.pdf_staging_native import stage_lifecycle_sql


def test_generated_lifecycle_preserves_writer_and_private_fences(native_rollback):
    connection = native_rollback.connection
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, stage_lifecycle_sql(metadata))
    arguments = {
        "task": None,
        "attempt": None,
        "holder": None,
        "build": None,
        "runtime": None,
        "original": None,
        "recipe": None,
    }
    calls = (
        ("ops.read_pdf_producer_basis(:task,:attempt,:holder,:runtime)", "P0004"),
        ("ops.retain_pdf_original(:task,:attempt,:holder,:original,:recipe)", "P0004"),
        ("ops.inspect_pdf_progress(:build,:task,:attempt,:holder)", "P0004"),
        ("ops.resume_pdf_build(:build,:task,:attempt,:holder)", "P0004"),
        ("ops.abandon_pdf_build(:build,:task,:attempt,:holder)", "P0004"),
        ("ops.require_pdf_build(:build,:task,:attempt,:holder)", "42501"),
    )
    with native_owner(connection, "corpus_sem_writer"):
        for call, expected_state in calls:
            with pytest.raises(DBAPIError) as failure, connection.begin_nested():
                connection.execute(text("SELECT * FROM " + call), arguments).all()
            assert getattr(failure.value.orig, "sqlstate", None) == expected_state
