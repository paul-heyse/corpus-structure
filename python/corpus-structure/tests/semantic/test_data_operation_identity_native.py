"""Pure DDO native framing parity; all helper DDL rolls back with its transaction."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256

import pytest
from native_refusals import native_refusal
from sqlalchemy import bindparam, func, select, text
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.semantic.data_operation_identity import canonical_identity
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_values import CollectionValue, OptionalValue
from semantic.data_operation_identity_vectors import (
    CONTEXTUAL_PRODUCTS,
    JSON_MEANING_VECTORS,
    REQUEST,
)
from semantic.test_data_product_admission_programs import product_connection  # noqa: F401


@pytest.mark.db
@pytest.mark.parametrize("vector", CONTEXTUAL_PRODUCTS, ids=lambda vector: vector.name)
def test_deployed_contextual_product_identity_matches_literal(vector, native_read):
    value = vector.native_json()
    assert vector.context.scope.decode() in value
    connection = native_read
    actual = connection.execute(
        text("SELECT data.ddo_identity('product', data.ddo_json_meaning(CAST(:value AS jsonb)))"),
        {"value": value},
    ).scalar_one()
    assert actual == "product:" + sha256(vector.literal).hexdigest()


@pytest.mark.db
def test_deployed_request_identity_matches_literal(native_read):
    actual = native_read.execute(
        text(
            "SELECT data.ddo_identity('semantic-request', data.ddo_json_meaning(CAST(:value AS jsonb)))"
        ),
        {"value": REQUEST.native_json()},
    ).scalar_one()
    assert actual == "semantic-request:" + sha256(REQUEST.literal).hexdigest()


@pytest.mark.db
def test_deployed_subject_context_json_meaning_has_literal_vectors(native_read):
    connection = native_read
    for value, expected in JSON_MEANING_VECTORS:
        actual = connection.execute(
            text("SELECT data.ddo_json_meaning(CAST(:value AS jsonb))"), {"value": value}
        ).scalar_one()
        assert actual == expected


@pytest.mark.db
def test_deployed_frame_matches_independent_literal_vectors(native_read):
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
    conn = native_read
    query = text(
        "SELECT data.canonical_json(jsonb_build_array('ddo','vector','1', "
        "data.ddo_normalize(CAST(:v AS jsonb)))), "
        "data.ddo_identity('vector',CAST(:v AS jsonb))"
    )
    for value, encoded in vectors:
        literal = ('["ddo","vector","1",' + encoded + "]").encode()
        actual, digest = conn.execute(query, {"v": encoded}).one()
        assert actual.encode() == literal
        assert digest == "vector:" + sha256(literal).hexdigest()
        assert canonical_identity("vector", value).canonical_input == literal
    # Numeric fields must have passed the typed lexical codec first.
    for value in (["integer", 1], ["mapping", {}], ["null", None]):
        with conn.begin_nested() as savepoint:
            with native_refusal(
                "23514", message=f"invalid or unsupported DDO semantic tag {value[0]}"
            ):
                conn.execute(query, {"v": json.dumps(value)})
            savepoint.rollback()
    # The deployed codec fixes its encoding version and exposes no caller version argument.


@pytest.mark.db
def test_json_subject_context_encoding_matches_literals_and_python(native_rollback):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_value_native import data_operation_value_sql
    from corpus_structure.semantic.data_operation_values import semantic_value
    from semantic.native_program_support import routine_declaration

    helper = routine_declaration(data_operation_value_sql(), "data", "ddo_json_meaning")
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
        context = SubjectContext(
            "project", "local", "original", value.encode(), subject_definition="original-occurrence"
        )
        actual = connection.execute(
            text("SELECT pg_temp.ddo_json_meaning(CAST(:value AS jsonb))"),
            {"value": json_bytes(context.record).decode()},
        ).scalar_one()
        assert actual == semantic_value(context.identity_record)


@pytest.mark.db
def test_current_canonical_json_preserves_array_text_and_nested_object_order(native_rollback):
    from corpus_structure.semantic.data_operation_value_native import canonical_identity_programs
    from semantic.native_program_support import routine_declaration

    connection = native_rollback.connection
    canonical, _ = canonical_identity_programs(decimal_digits=128)
    connection.exec_driver_sql(
        routine_declaration(canonical.routine.render(), "data", "canonical_json")
    )
    query = text("SELECT pg_temp.canonical_json(CAST(:value AS jsonb))")
    value = [" a\t b\n ", 'quote " with slash \\', "雪 Ω\u00a0", []]
    vectors = (
        (json.dumps(value), json.dumps(value, ensure_ascii=False, separators=(",", ":"))),
        ("[1.00, 1.20, [], true, null]", "[1.00,1.20,[],true,null]"),
        ('[[{"z": [], "aa": " spaced "}]]', '[[{"aa":" spaced ","z":[]}]]'),
    )
    for payload, expected in vectors:
        assert connection.scalar(query, {"value": payload}) == expected


@pytest.mark.db
def test_current_json_meaning_array_pass_keeps_exact_typed_forms(native_rollback):
    from corpus_structure.semantic.data_operation_value_native import data_operation_value_sql
    from semantic.native_program_support import routine_declaration

    connection = native_rollback.connection
    connection.exec_driver_sql(
        routine_declaration(data_operation_value_sql(), "data", "ddo_json_meaning")
    )
    query = text("SELECT pg_temp.ddo_json_meaning(CAST(:value AS jsonb))")
    escaped = 'quote " slash \\ brackets [,] whitespace \t\n 雪 Ω 😀 e\u0301'
    vectors = (
        (None, None),
        ("null", ["null"]),
        ("[]", ["sequence", []]),
        ("[[],[[]]]", ["sequence", [["sequence", []], ["sequence", [["sequence", []]]]]]),
        (
            "[null,true,false,1.200,-0.00,1e3,1e-3]",
            [
                "sequence",
                [
                    ["null"],
                    ["boolean", True],
                    ["boolean", False],
                    ["decimal", "1.2"],
                    ["decimal", "0"],
                    ["decimal", "1000"],
                    ["decimal", "0.001"],
                ],
            ],
        ),
        (json.dumps([escaped]), ["sequence", [["string", escaped]]]),
        (
            '[[{"z":[],"aa":true}],null]',
            [
                "sequence",
                [
                    [
                        "sequence",
                        [["mapping", [["aa", ["boolean", True]], ["z", ["sequence", []]]]]],
                    ],
                    ["null"],
                ],
            ],
        ),
    )
    for payload, expected in vectors:
        actual = connection.scalar(query, {"value": payload})
        assert actual == expected
        if expected is not None:
            encoded = json.dumps(expected, ensure_ascii=False, separators=(",", ":"))
            canonical, identity = connection.execute(
                text(
                    "SELECT data.canonical_json(pg_temp.ddo_json_meaning(CAST(:value AS jsonb))), "
                    "data.ddo_identity('rule-premise',pg_temp.ddo_json_meaning(CAST(:value AS jsonb)))"
                ),
                {"value": payload},
            ).one()
            assert canonical == encoded
            frame = '["ddo","rule-premise","1",' + encoded + "]"
            assert identity == "rule-premise:" + sha256(frame.encode()).hexdigest()


@pytest.mark.db
def test_current_json_meaning_large_typed_members_keep_literal_shape(product_connection):  # noqa: F811
    from corpus_structure.semantic.data_operation_value_native import json_observation_identity

    connection = product_connection
    # A construction-sized output is already encoded as tagged arrays. These
    # literal expectations describe that fixed shape independently of either codec.
    members, expected_members = [], []
    source_text = 'x+1 雪 " quoted \\ source'
    for ordinal in range(4096):
        identity = f"member:{ordinal}"
        members.append(
            ["mapping", [["local_id", ["string", identity]], ["text", ["string", source_text]]]]
        )
        expected_members.append(
            [
                "sequence",
                [
                    ["string", "mapping"],
                    [
                        "sequence",
                        [
                            [
                                "sequence",
                                [
                                    ["string", "local_id"],
                                    ["sequence", [["string", "string"], ["string", identity]]],
                                ],
                            ],
                            [
                                "sequence",
                                [
                                    ["string", "text"],
                                    ["sequence", [["string", "string"], ["string", source_text]]],
                                ],
                            ],
                        ],
                    ],
                ],
            ]
        )
    payload = {"members": ["sequence", members], "read": "same"}
    expected = [
        "mapping",
        [
            ["members", ["sequence", [["string", "sequence"], ["sequence", expected_members]]]],
            ["read", ["string", "same"]],
        ],
    ]
    encoded = json.dumps(expected, ensure_ascii=False, separators=(",", ":"))
    connection.exec_driver_sql("SET LOCAL statement_timeout = '60s'")
    value = bindparam("value", type_=JSONB())
    actual, identity = connection.execute(
        select(
            func.data.canonical_json(func.data.ddo_json_meaning(value)),
            json_observation_identity("rule-premise", value),
        ),
        {"value": payload},
    ).one()
    assert actual == encoded
    frame = '["ddo","rule-premise","1",' + encoded + "]"
    assert identity == "rule-premise:" + sha256(frame.encode()).hexdigest()


@pytest.mark.db
def test_current_json_meaning_bounds_regex_by_rendered_bytes(native_rollback, monkeypatch):
    from corpus_structure.semantic import data_operation_value_native as owner
    from semantic.native_program_support import routine_declaration

    # Exercise the actual branch at a small boundary, including JSON escaping
    # and multibyte UTF-8; do not allocate packet-sized buffers merely to test it.
    monkeypatch.setattr(owner, "_JSON_MEANING_ARRAY_REGEX_BYTES", 64)
    connection = native_rollback.connection
    connection.exec_driver_sql("CREATE TEMP SEQUENCE json_meaning_regex_calls")
    connection.exec_driver_sql(
        "CREATE FUNCTION pg_temp.counted_json_meaning_tokens(text,text,text) "
        "RETURNS SETOF text[] LANGUAGE plpgsql AS $$ BEGIN "
        "PERFORM nextval('pg_temp.json_meaning_regex_calls'); "
        "RETURN QUERY SELECT * FROM pg_catalog.regexp_matches($1,$2,$3); END $$"
    )
    declaration = routine_declaration(owner.data_operation_value_sql(), "data", "ddo_json_meaning")
    counted = declaration.replace("regexp_matches(", "pg_temp.counted_json_meaning_tokens(")
    assert counted != declaration
    connection.exec_driver_sql(counted)
    query = text(
        "SELECT pg_temp.ddo_json_meaning(CAST(:value AS jsonb)), "
        "octet_length(CAST(CAST(:value AS jsonb) AS text)), "
        "data.ddo_identity('rule-premise',pg_temp.ddo_json_meaning(CAST(:value AS jsonb)))"
    )
    for source, rendered_bytes, calls in (
        ("é" * 30, 64, 2),
        ("é" * 31, 66, 0),
        ("\\" * 30, 64, 2),
        ("\\" * 31, 66, 0),
        ("\x01" * 10, 64, 2),
        ("\x01" * 11, 70, 0),
    ):
        connection.exec_driver_sql("SELECT setval('pg_temp.json_meaning_regex_calls',1,false)")
        actual, size, proof = connection.execute(query, {"value": json.dumps([source])}).one()
        expected = ["sequence", [["string", source]]]
        assert actual == expected and size == rendered_bytes
        count, used = connection.execute(
            text("SELECT last_value,is_called FROM pg_temp.json_meaning_regex_calls")
        ).one()
        assert (count if used else 0) == calls
        encoded = json.dumps(expected, ensure_ascii=False, separators=(",", ":"))
        assert (
            proof
            == "rule-premise:"
            + sha256(('["ddo","rule-premise","1",' + encoded + "]").encode()).hexdigest()
        )
