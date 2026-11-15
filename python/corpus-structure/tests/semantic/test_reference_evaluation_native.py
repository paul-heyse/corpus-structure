"""Independent protected reference privilege refusals; source search has its current owner."""

import pytest
from psycopg.errors import InsufficientPrivilege, NoDataFound
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


def test_reference_storage_is_unavailable_to_source_writer(
    commit_writer_engine, commit_evaluator_engine
):
    with commit_writer_engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT has_schema_privilege(current_user,'eval','USAGE')")) is False
        )
        with pytest.raises(DBAPIError) as private, conn.begin_nested():
            conn.execute(text("SELECT authored FROM eval.reference_pass"))
        assert isinstance(private.value.orig, InsufficientPrivilege)
        assert private.value.orig.sqlstate == "42501"
    evaluator = commit_evaluator_engine
    with evaluator.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM eval.reference_pass")) == 0
        assert (
            conn.scalar(
                text(
                    "SELECT has_table_privilege(current_user,'eval.reference_pass',"
                    "'INSERT,UPDATE,DELETE,TRUNCATE')"
                )
            )
            is False
        )
        assert (
            conn.scalar(
                text(
                    "SELECT has_table_privilege(current_user,'data.fact',"
                    "'INSERT,UPDATE,DELETE,TRUNCATE')"
                )
            )
            is False
        )
        assert (
            conn.scalar(
                text(
                    "SELECT has_function_privilege(current_user,"
                    "'eval.record_native_reference_pass(bigint,text,text,bytea,jsonb,jsonb)',"
                    "'EXECUTE')"
                )
            )
            is True
        )
        with pytest.raises(DBAPIError) as foreign, conn.begin_nested():
            conn.execute(text("SELECT eval.add_native_reference_unit(1,1,'foreign','[]'::jsonb)"))
        # The current governed function refuses missing foreign custody; an
        # UndefinedFunction from a retired entry point cannot satisfy this control.
        assert isinstance(foreign.value.orig, NoDataFound)
        assert foreign.value.orig.sqlstate == "P0002"
        assert conn.scalar(text("SELECT count(*) FROM eval.reference_unit")) == 0
