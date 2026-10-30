"""Independent protected reference privilege and physical projection expectations."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


def test_reference_storage_is_unavailable_to_source_writer(
    semantic_db_engine, semantic_writer_engine, semantic_evaluator_engine
):
    with semantic_writer_engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT has_schema_privilege(current_user,'eval','USAGE')")) is False
        )
        with pytest.raises(DBAPIError):
            conn.execute(text("SELECT authored FROM eval.reference_pass"))
    evaluator = semantic_evaluator_engine
    with evaluator.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM eval.reference_pass")) == 0
        assert (
            conn.scalar(
                text("SELECT has_table_privilege(current_user,'eval.reference_pass','INSERT')")
            )
            is False
        )
        assert (
            conn.scalar(text("SELECT has_table_privilege(current_user,'data.fact','INSERT')"))
            is False
        )
        assert (
            conn.scalar(
                text(
                    "SELECT has_function_privilege(current_user,"
                    "'eval.record_reference_pass(bigint,text,text,bytea,jsonb)','EXECUTE')"
                )
            )
            is True
        )
        with pytest.raises(DBAPIError):
            conn.execute(text("SELECT eval.add_reference_unit(1,1,'foreign','[]'::jsonb)"))
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text(
                    "SELECT indexdef LIKE '%USING gin%' FROM pg_indexes WHERE schemaname='kb' "
                    "AND indexname='ix_rendition_canonical_text_search'"
                )
            )
            is True
        )
