"""Pure DDO native framing parity; all helper DDL rolls back with its transaction."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from importlib.resources import files

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_identity import (
    CollectionValue,
    OptionalValue,
    canonical_identity,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from semantic.data_operation_identity_vectors import CONTEXTUAL_PRODUCTS, JSON_MEANING_VECTORS


@pytest.mark.db
@pytest.mark.parametrize("vector", CONTEXTUAL_PRODUCTS, ids=lambda vector: vector.name)
def test_deployed_contextual_product_identity_matches_literal(vector, native_read):
    value = {
        "body": "body:one",
        "kind": "kind:one",
        "subject": "local",
        "subject_context": {
            "project_id": vector.project,
            "subject": "local",
            "original_source": vector.source,
            "analyzed_scope": json.loads(vector.scope),
        },
    }
    connection = native_read
    actual = connection.execute(
        text("SELECT data.ddo_identity('product', data.ddo_json_meaning(CAST(:value AS jsonb)))"),
        {"value": json.dumps(value)},
    ).scalar_one()
    assert actual == "product:" + sha256(vector.literal).hexdigest()


@pytest.mark.db
def test_deployed_subject_context_json_meaning_has_literal_vectors(native_read):
    connection = native_read
    for value, expected in JSON_MEANING_VECTORS:
        actual = connection.execute(
            text("SELECT data.ddo_json_meaning(CAST(:value AS jsonb))"), {"value": value}
        ).scalar_one()
        assert actual == expected


@pytest.mark.db
def test_native_frame_matches_independent_literal_vectors(native_rollback):
    helper = (
        files("corpus_structure.semantic").joinpath("sql/data_operation_identity.sql").read_text()
    )
    # Literal encodings are independent of both native and Python production codecs.
    vectors = [
        (None, '["null"]'),
        (True, '["boolean",true]'),
        (False, '["boolean",false]'),
        (1, '["integer","1"]'),
        (9007199254740993, '["integer","9007199254740993"]'),
        ("1", '["string","1"]'),
        (Decimal("1.200"), '["decimal","1.2"]'),
        (Decimal("-0.00"), '["decimal","0"]'),
        (0.0, '["float","0x0.0p+0"]'),
        (-0.0, '["float","-0x0.0p+0"]'),
        (date(2026, 11, 12), '["date","2026-11-12"]'),
        (datetime(2026, 11, 12, tzinfo=UTC), '["datetime","2026-11-12T00:00:00+00:00"]'),
        ("e\u0301", '["string","e\u0301"]'),
        ("é😀", '["string","é😀"]'),
        ({"x": []}, '["mapping",[["x",["sequence",[]]]]]'),
        (OptionalValue("present", None), '["present",["null"]]'),
        (OptionalValue("present", []), '["present",["sequence",[]]]'),
        (OptionalValue("known-absent"), '["known-absent"]'),
        (OptionalValue("unknown"), '["unknown"]'),
        (OptionalValue("unavailable"), '["unavailable"]'),
        (CollectionValue("set", (2, 1, 1)), '["set",[["integer","1"],["integer","2"]]]'),
        (
            CollectionValue("bag", (2, 1, 1)),
            '["bag",[["integer","1"],["integer","1"],["integer","2"]]]',
        ),
        (
            CollectionValue("ordered-bag", (2, 1)),
            '["ordered-bag",[["integer","2"],["integer","1"]]]',
        ),
    ]
    # JSONB cannot represent U+0000; this parity contract covers JSONB-compatible text.
    conn = native_rollback.connection
    conn.exec_driver_sql(helper)
    query = text(
        "SELECT pg_temp.ddo_canonical_input('vector','1',CAST(:v AS jsonb)), "
        "pg_temp.ddo_identity_digest('vector','1',CAST(:v AS jsonb))"
    )
    for value, encoded in vectors:
        literal = ('["ddo","vector","1",' + encoded + "]").encode()
        actual, digest = conn.execute(query, {"v": encoded}).one()
        assert bytes(actual) == literal
        assert digest == sha256(literal).hexdigest()
        assert canonical_identity("vector", value).canonical_input == literal
    # Numeric fields must have passed the typed lexical codec first.
    for value in (["integer", 1], ["mapping", {}], ["null", None]):
        with conn.begin_nested() as savepoint:
            with pytest.raises(DBAPIError, match="normalized tagged values"):
                conn.execute(query, {"v": json.dumps(value)})
            savepoint.rollback()
    with conn.begin_nested() as savepoint:
        with pytest.raises(DBAPIError, match="domain/version"):
            conn.execute(text("SELECT pg_temp.ddo_canonical_input('vector','2','[\"null\"]')"))
        savepoint.rollback()


@pytest.mark.db
def test_json_subject_context_encoding_matches_literals_and_python(native_rollback):
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.data_operation_model import SubjectContext

    source = files("corpus_structure.semantic").joinpath("sql/data_operations.sql").read_text()
    start = source.index("CREATE OR REPLACE FUNCTION data.ddo_json_meaning(")
    end = source.index("CREATE OR REPLACE FUNCTION data.ddo_identity(", start)
    helper = source[start:end].replace("data.ddo_json_meaning", "pg_temp.ddo_json_meaning")
    vectors = JSON_MEANING_VECTORS
    connection = native_rollback.connection
    connection.exec_driver_sql(helper)
    for value, expected in vectors:
        assert (
            connection.execute(
                text("SELECT pg_temp.ddo_json_meaning(CAST(:value AS jsonb))"),
                {"value": value},
            ).scalar_one()
            == expected
        )
        context = SubjectContext("project", "local", "original", value.encode())
        actual = connection.execute(
            text("SELECT pg_temp.ddo_json_meaning(CAST(:value AS jsonb))"),
            {"value": json_bytes(context.record).decode()},
        ).scalar_one()
        assert actual == semantic_value(context.identity_record)
