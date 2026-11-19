"""Current target installation and semantic value contracts on owned native databases."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, inspect, text

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.migrations import current_revision, downgrade, upgrade


def test_native_bootstrap_and_subsequent_projection(semantic_bare_engine: Engine) -> None:
    with semantic_bare_engine.begin() as conn:
        assert current_revision(conn) is None
        upgrade(conn)
        catalog = inspect(conn)
        assert {"sem", "data"} <= set(catalog.get_schema_names())
        assert {"data_request", "data_demand", "data_derivation", "task"} <= set(
            catalog.get_table_names(schema="ops")
        )
        assert not {"run", "method", "method_config", "cut_task"} & set(
            catalog.get_table_names(schema="ops")
        )
        assert not {"realization", "fact", "typed_value", "source_view"} & set(
            catalog.get_table_names(schema="data")
        )
        for item in get_metadata().tables.values():
            assert {c["name"] for c in catalog.get_columns(item.name, schema=item.schema)} == set(
                item.c.keys()
            )
        assert "kb" in catalog.get_schema_names()
        assert "meta" not in catalog.get_schema_names()
        assert "claim" not in catalog.get_table_names(schema="kb")


def test_bootstrap_downgrade_refuses_destructive_reversal(commit_db_engine: Engine) -> None:
    with commit_db_engine.begin() as conn:
        before = current_revision(conn)
        with pytest.raises(RuntimeError, match="destructive"):
            downgrade(conn)
        assert current_revision(conn) == before
        assert "data_request" in inspect(conn).get_table_names(schema="ops")


def test_frozen_n29_replays_its_legacy_decimal_semantics(semantic_database_at) -> None:
    from corpus_structure.semantic.identity import canonical_bytes

    lexical = "9" * 10000
    with semantic_database_at("semantic_ddo_pe_n29") as engine, engine.begin() as conn:
        for tag, value, expected in (
            ("string", lexical, lexical),
            ("decimal", lexical, lexical),
            ("decimal", "1e200000", "1" + "0" * 200000),
        ):
            assert conn.scalar(
                text("SELECT data.ddo_normalize(CAST(:value AS jsonb))"),
                {"value": canonical_bytes([tag, value]).decode()},
            ) == [tag, expected]
