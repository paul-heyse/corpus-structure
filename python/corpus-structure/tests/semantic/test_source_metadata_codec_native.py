"""Exact integer metadata encoding; isolated helper execution grants no admission."""

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.source_value_native import source_value_native_sql


@pytest.fixture
def metadata_codec(semantic_bare_engine):
    sql = source_value_native_sql()
    parsed = prepare_sql(sql, source="source-metadata-codec")
    with semantic_bare_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS data")
        for index in range(len(parsed.statements)):
            # Only the recursive pure encoder is required; no deployed semantic head.
            if "CREATE OR REPLACE FUNCTION data.record_json_source(" in parsed.excerpt(index):
                connection.exec_driver_sql(
                    parsed.excerpt(index), execution_options={"no_parameters": True}
                )
        yield connection


def encode(connection, raw):
    return connection.execute(
        text("SELECT data.record_json_source(CAST(:raw AS jsonb))"), {"raw": raw}
    ).scalar_one()


@pytest.mark.db
@pytest.mark.parametrize(
    "value",
    [
        None,
        False,
        True,
        "",
        "Éλ😀",
        0,
        -1,
        2**100,
        -(2**100),
        [],
        {},
        [None, False, 7, ["nested"]],
        {"é": 1, "z": None, "A": False, "😀": {"b": 2, "a": []}},
    ],
)
def test_native_metadata_encoding_matches_python_exact_values_and_canonical_order(
    metadata_codec, value
):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
    actual = encode(metadata_codec, raw)
    expected = json.loads(json.dumps(source_value(json.loads(raw))))
    assert actual == expected
    assert source_python(actual) == value
    if isinstance(value, dict):
        assert [row["name"] for row in actual["fields"]] == sorted(value)
        assert [row["position"] for row in actual["fields"]] == list(range(len(value)))


@pytest.mark.db
@pytest.mark.parametrize(
    "raw", ["0.5", "1.0", "-1.0000000000000000000001", "[1, 0.25]", '{"nested": 1.5}']
)
def test_native_metadata_encoding_refuses_noninteger_numbers_without_rounding(metadata_codec, raw):
    with pytest.raises(DBAPIError, match="exact integer JSON numbers"):
        encode(metadata_codec, raw)


@pytest.mark.db
def test_metadata_sql_null_is_unobserved_and_json_null_is_observed(metadata_codec):
    assert encode(metadata_codec, None) is None
    assert encode(metadata_codec, "null") == {"kind": "null"}
