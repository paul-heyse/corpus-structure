"""Independent protected reference privilege and physical projection expectations."""

import pytest
from psycopg.errors import InsufficientPrivilege, NoDataFound
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.serve.source_search import source_search_rows


def test_reference_storage_is_unavailable_to_source_writer(
    semantic_db_engine, semantic_writer_engine, semantic_evaluator_engine
):
    with semantic_writer_engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT has_schema_privilege(current_user,'eval','USAGE')")) is False
        )
        with pytest.raises(DBAPIError) as private, conn.begin_nested():
            conn.execute(text("SELECT authored FROM eval.reference_pass"))
        assert isinstance(private.value.orig, InsufficientPrivilege)
        assert private.value.orig.sqlstate == "42501"
    evaluator = semantic_evaluator_engine
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
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text(
                    "SELECT indexdef LIKE '%USING btree (native_task_id, native_product_key, "
                    "section_pointer)%' FROM pg_indexes WHERE schemaname='kb' "
                    "AND tablename='source_view' "
                    "AND indexname='ix_source_view_native_task_id_native_product_key_sectio_0359'"
                )
            )
            is True
        )
        # Current search derives its vector from SourceView.projection['text'];
        # execute that consumer's query without inventing a retained rendition index.
        assert source_search_rows(conn, run_id=1, text="foreign", limit=1) == []
