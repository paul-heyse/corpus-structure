"""Pinned PostgreSQL/ADBC pilot controls over actual native custody boundaries."""

from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal

import pyarrow as pa
import pytest
from adbc_driver_manager import DatabaseError
from sqlalchemy import DateTime, Numeric, Text, cast, column, func, literal, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.elements import BindParameter

from corpus_structure.core.db.adbc_lifetime import (
    open_adbc_connection,
    owned_adbc_child,
    owned_adbc_read,
)
from corpus_structure.semantic.companion_projection import projection
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_jsonb import ContextJSONB
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.demand_results import selected_read_snapshot
from corpus_structure.semantic.runtime import connection_settings
from corpus_structure.serve.companion_export import _literal_statement
from semantic.companion_export_native_support import read_settings
from semantic.sbx_pilot_postgresql import annotation_geometry, annotation_membership
from semantic.test_sentence_partition_chain_native import _private_source


@contextmanager
def _borrow_snapshot(settings, snapshot):
    selected = connection_settings(settings, "read")
    with (
        owned_adbc_read(
            open_adbc_connection(
                selected.database.url,
                driver_path=selected.analytics.adbc_driver_path,
                resolver_mode="builtin",
            )
        ) as bulk,
        owned_adbc_child(bulk.cursor()) as cursor,
    ):
        cursor.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ WRITE")
        # PostgreSQL requires the server-issued snapshot as a SQL literal.
        cursor.execute(
            _literal_statement(
                text("SET TRANSACTION SNAPSHOT :snapshot").bindparams(snapshot=snapshot)
            )
        )
        yield cursor


def snapshot_annotation_rows(settings, snapshot, binding_arguments):
    """Project typed members after the native exact-parent and packet-budget guard."""
    arguments = tuple(
        cast(
            literal(None if argument.value is None else json_bytes(argument.value).decode()), JSONB
        )
        if isinstance(argument, BindParameter) and isinstance(argument.type, (ContextJSONB, JSONB))
        else argument
        for argument in binding_arguments
    )
    packets = func.ops.data_binding_partitions(
        *arguments, 8_388_608, cast(literal(None), Text), cast(literal(None), Text)
    ).table_valued(column("product_id", Text), column("packet", JSONB))
    selected = _literal_statement(select(*packets.c))
    # The guarded TVF still constructs each complete tagged packet internally.
    # Only the requested fields cross the ADBC boundary in this comparison.
    query = f"""
        SELECT packet->>'partition_key' AS partition_key,
               fields->'record_type'->>1 AS record_type,
               (fields->'ordinal'->>1)::bigint AS ordinal,
               (fields->'start'->>1)::bigint AS start,
               (fields->'end'->>1)::bigint AS "end"
        FROM ({selected}) AS guarded
        CROSS JOIN LATERAL jsonb_array_elements(packet->'body'->1)
            WITH ORDINALITY AS item(value, submitted)
        CROSS JOIN LATERAL (
            SELECT jsonb_object_agg(field->>0, field->1) AS fields
            FROM jsonb_array_elements(value->1) AS field
        ) AS projected
        ORDER BY (packet->>'ordinal')::bigint, submitted
    """
    with _borrow_snapshot(settings, snapshot) as cursor:
        cursor.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "true"})
        cursor.execute(query)
        with owned_adbc_child(cursor.fetch_record_batch()) as reader:
            return reader.read_all().to_pylist()


def test_native_typed_sets_preserve_invalid_submitted_order(infrastructure_rollback):
    body = semantic_value(
        [
            {"record_type": "token", "ordinal": 0, "start": 4, "end": 6},
            {"record_type": "token", "ordinal": 0, "start": 1, "end": 12},
            {"record_type": "sentence", "ordinal": 0, "start": 0, "end": 10},
        ]
    )
    assert annotation_geometry(infrastructure_rollback, body, 10) == ((2, True, True, True),)
    assert annotation_membership(infrastructure_rollback, body, (("token", 0), ("token", 1))) == (
        ("token", 1),
    )


def test_exact_snapshot_adbc_retains_nonempty_values_and_interleaved_catalog_cut(
    semantic_bare_engine,
    native_settings,
    tmp_path,
    monkeypatch,
):
    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, "Ada acts."
    ) as source:
        _check_snapshot(source, native_settings)


def _check_snapshot(source, native_settings):
    reader = source.kernel.purpose("read")
    settings = read_settings(native_settings, source.kernel.engine)
    with reader.begin() as connection:
        pin, _ = source.publication(connection)

    # A database comment is a public catalog sentinel on this isolated fixture.
    # It requires no extra grants to application tables or purpose credentials.
    database = source.kernel.engine.dialect.identifier_preparer.quote(
        source.kernel.engine.url.database
    )
    with source.kernel.engine.begin() as control:
        control.exec_driver_sql(f"COMMENT ON DATABASE {database} IS 'pilot-before'")
    sentinel = text(
        "SELECT description FROM pg_catalog.pg_shdescription "
        "WHERE objoid=(SELECT oid FROM pg_catalog.pg_database "
        "WHERE datname=current_database()) AND classoid='pg_database'::regclass"
    )
    expected_time = datetime(2026, 11, 22, 1, 2, 3, 123456, tzinfo=UTC)
    typed = select(
        cast(literal("123456789012345678.123456789"), Numeric(30, 9)).label("exact_decimal"),
        cast(literal(expected_time), DateTime(timezone=True)).label("timestamp"),
        cast(literal("null"), JSONB).label("explicit_null"),
        cast(literal(None), JSONB).label("absent"),
    )
    # The granted native companion function verifies this committed pin before
    # returning its authorized (empty here) family. Count forces that acquisition.
    spec = projection("input")
    guard = (
        select(func.count().label("guarded_rows"))
        .select_from(spec.arrow_statement.subquery("authorized_companion"))
        .cte("guard")
    )
    guarded = typed.add_columns(guard.c.guarded_rows).select_from(guard).params(**pin.model_dump())
    with selected_read_snapshot(reader) as owner:
        assert owner.scalar(sentinel) == "pilot-before"
        snapshot = owner.scalar(select(func.pg_catalog.pg_export_snapshot()))
        with _borrow_snapshot(settings, snapshot) as cursor:
            cursor.execute(_literal_statement(sentinel))
            assert cursor.fetchone() == ("pilot-before",)
            with source.kernel.engine.begin() as control:
                control.exec_driver_sql(f"COMMENT ON DATABASE {database} IS 'pilot-after'")
            cursor.execute(_literal_statement(sentinel))
            assert cursor.fetchone() == ("pilot-before",)
            cursor.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "true"})
            cursor.execute(_literal_statement(guarded))
            with owned_adbc_child(cursor.fetch_record_batch()) as batches:
                result = batches.read_all()
            assert result.num_rows == 1
            assert result["guarded_rows"].to_pylist() == [0]
            assert Decimal(result["exact_decimal"][0].as_py()) == Decimal(
                "123456789012345678.123456789"
            )
            assert result["timestamp"][0].as_py() == expected_time
            assert result.schema.field("explicit_null").type == pa.json_()
            assert result["explicit_null"].to_pylist() == ["null"]
            assert result["absent"].to_pylist() == [None]
    with reader.connect() as fresh:
        assert fresh.scalar(sentinel) == "pilot-after"


def test_adbc_failed_reader_releases_session_for_a_fresh_operation(
    commit_reader_engine,
    native_settings,
    commit_db_engine,
):
    settings = read_settings(native_settings, commit_db_engine)
    with selected_read_snapshot(commit_reader_engine) as owner:
        snapshot = owner.scalar(select(func.pg_catalog.pg_export_snapshot()))
        with (
            pytest.raises(DatabaseError, match="division by zero"),
            _borrow_snapshot(settings, snapshot) as cursor,
        ):
            cursor.execute("SELECT 1/0")
        with _borrow_snapshot(settings, snapshot) as cursor:
            cursor.execute("SELECT 42")
            assert cursor.fetchone() == (42,)
