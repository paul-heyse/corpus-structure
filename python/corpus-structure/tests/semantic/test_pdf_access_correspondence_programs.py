"""Native access correspondence retains float and bounded stream semantics."""

import json
import struct

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
from corpus_structure.semantic.pdf_record_access_native import pdf_access_correspondence_sql


def test_generated_access_programs_bind_in_actual_native_context(native_rollback):
    conn = native_rollback.connection
    execute_native_sql(conn, "CREATE EXTENSION IF NOT EXISTS plpgsql_check VERSION '2.10'")
    with native_owner(conn, "corpus_sem_publisher"):
        execute_native_sql(conn, pdf_access_correspondence_sql(metadata))
        for signature in (
            "ops.pdf_projection_scalar_matches(jsonb,jsonb)",
            "ops.pdf_projection_stream_value(text,text)",
            "ops.pdf_projection_stream_matches(text,text,jsonb)",
            "ops.pdf_check_access_correspondence(text)",
        ):
            failures = (
                conn.execute(
                    text(
                        "SELECT message FROM public.plpgsql_check_function_tb("
                        "CAST(:signature AS regprocedure), fatal_errors=>false) WHERE level='error'"
                    ),
                    dict(signature=signature),
                )
                .scalars()
                .all()
            )
            assert failures == [], (signature, failures)
        query = text(
            "SELECT ops.pdf_projection_scalar_matches(CAST(:value AS jsonb),CAST(:expected AS jsonb))"
        )
        for value, expected, matches in (
            (1, 1, True),
            (1, "1", False),
            (None, None, True),
            (0, {"native_float64": "8000000000000000"}, True),
            (1, {"native_float64": struct.pack(">d", 1.0).hex()}, True),
            (1, {"native_float64": struct.pack(">d", 1.0000000000000002).hex()}, False),
            ("wrong", {"native_float64": "wrong"}, False),
        ):
            assert (
                conn.scalar(query, dict(value=json.dumps(value), expected=json.dumps(expected)))
                is matches
            )
        with pytest.raises(DBAPIError) as malformed, conn.begin_nested():
            conn.scalar(query, dict(value="1", expected=json.dumps({"native_float64": "wrong"})))
        assert getattr(malformed.value.orig, "sqlstate", None) == "22023"
        conn.execute(text("SELECT ops.pdf_check_access_correspondence('controlled-access')"))
    with native_owner(conn, "corpus_sem_writer"):
        with pytest.raises(DBAPIError) as refusal, conn.begin_nested():
            conn.execute(text("SELECT ops.pdf_check_access_correspondence('controlled-access')"))
        assert getattr(refusal.value.orig, "sqlstate", None) == "42501"
