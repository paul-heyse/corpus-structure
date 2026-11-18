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


def test_generated_scratch_authorization_checks_actual_owner_columns_and_checks(native_rollback):
    from corpus_structure.semantic.pdf_staging_native import stage_scratch_authorization_sql

    connection = native_rollback.connection
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, stage_scratch_authorization_sql())
        execute_native_sql(
            connection, "CREATE TEMP TABLE wire_reference (value bigint NOT NULL CHECK (value > 0))"
        )
        execute_native_sql(
            connection,
            "CREATE TEMP TABLE wire_matching (LIKE wire_reference INCLUDING CONSTRAINTS)",
        )
        execute_native_sql(
            connection,
            "CREATE TEMP TABLE wire_different_check (value bigint NOT NULL CHECK (value >= 0))",
        )
        execute_native_sql(
            connection, "CREATE TEMP TABLE wire_different_column (value text NOT NULL)"
        )
    execute_native_sql(
        connection,
        "CREATE TEMP TABLE wire_untrusted_owner (LIKE wire_reference INCLUDING CONSTRAINTS)",
    )
    query = text(
        "SELECT ops.require_pdf_stage_scratch(:scratch,CAST('pg_temp.wire_reference' AS regclass))"
    )
    connection.execute(query, {"scratch": "wire_matching"}).one()
    for scratch, message in (
        ("wire_different_check", "private PDF scratch schema differs"),
        ("wire_different_column", "private PDF scratch schema differs"),
        ("wire_untrusted_owner", "untrusted private PDF scratch"),
        ("wire_missing", "untrusted private PDF scratch"),
    ):
        with pytest.raises(DBAPIError, match=message) as failure, connection.begin_nested():
            connection.execute(query, {"scratch": scratch}).all()
        assert getattr(failure.value.orig, "sqlstate", None) == "23514"
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(
            connection,
            "CREATE FUNCTION pg_temp.scratch_trap() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'scratch trigger ran'; END$$",
        )
        execute_native_sql(
            connection,
            "CREATE TRIGGER scratch_trap BEFORE TRUNCATE ON wire_matching FOR EACH STATEMENT EXECUTE FUNCTION pg_temp.scratch_trap()",
        )
    with (
        pytest.raises(DBAPIError, match="untrusted private PDF scratch"),
        connection.begin_nested(),
    ):
        connection.execute(query, {"scratch": "wire_matching"}).all()


def test_generated_stage_ownership_preserves_absence_and_private_entrypoints(native_rollback):
    connection = native_rollback.connection
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, stage_lifecycle_sql(metadata))
    assert connection.scalar(text("SELECT ops.pdf_stage_owner_current(-1,1,'holder')")) is False
    assert connection.execute(text("SELECT * FROM ops.pdf_task_context(NULL)")).all() == []
    with pytest.raises(DBAPIError, match="stale private PDF build owner") as failure, connection.begin_nested():
        connection.execute(text("SELECT * FROM ops.require_pdf_stage_owner(NULL,NULL,NULL)")).all()
    assert getattr(failure.value.orig, "sqlstate", None) == "P0004"
    with native_owner(connection, "corpus_sem_writer"):
        with pytest.raises(DBAPIError) as failure, connection.begin_nested():
            connection.execute(text("SELECT * FROM ops.begin_pdf_build(NULL,NULL,NULL,NULL,NULL,NULL,NULL)")).all()
        assert getattr(failure.value.orig, "sqlstate", None) == "P0004"
        with pytest.raises(DBAPIError) as failure, connection.begin_nested():
            connection.execute(text("SELECT * FROM ops.pdf_stage_owner_current(-1,1,'holder')")).all()
        assert getattr(failure.value.orig, "sqlstate", None) == "42501"


def test_begin_build_uses_the_supplied_physical_upload_profile():
    import json
    from types import SimpleNamespace

    import yaml

    from corpus_structure.semantic.pdf_staging import stage_upload_profile

    sources = dict(metadata.info["physical_sources"])
    declaration = yaml.safe_load(sources["pdf-staging.yaml"])
    profile = json.loads(declaration["annotations"]["pds:upload_profile"])
    profile["max_replay_key_bytes"] = 17
    declaration["annotations"]["pds:upload_profile"] = json.dumps(profile)
    sources["pdf-staging.yaml"] = yaml.safe_dump(declaration).encode()
    supplied = SimpleNamespace(tables=metadata.tables, info={**metadata.info, "physical_sources": sources})
    assert stage_upload_profile(physical_sources=sources)["max_replay_key_bytes"] == 17
    assert "octet_length(p_key) > 17" in stage_lifecycle_sql(supplied)
