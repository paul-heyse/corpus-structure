"""Published overflow reads preserve exact JSON floats and stream without N+1 SQL."""

import json
import math
from hashlib import sha256

import pytest
from sqlalchemy import event, text

from corpus_structure.semantic.pdf_record_identity import byte_root, emit_parts
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.pdf_record_reader_native import (
    pdf_companion_export_sql,
    pdf_record_reader_sql,
)
from corpus_structure.semantic.product_reference import ProductReference


@pytest.fixture
def field_database(semantic_bare_engine):
    payloads = {"text": ('A\\"\n\x00Ω' * 20000).encode()}
    # The exact JSON spelling and float payload are deliberately independent from
    # PostgreSQL JSONB's numeric serialization.
    payloads["meta"] = (
        b'{"pointer":"#/texts/0","precise":0.12345678901234568,"signed":-0.0,"nul":"\\u0000","text":'
        + json.dumps('Ω"\\\n' * 20000, ensure_ascii=False).encode()
        + b"}"
    )
    with semantic_bare_engine.begin() as conn:
        for ddl in (
            "CREATE SCHEMA ops",
            "CREATE SCHEMA kb",
            "CREATE TABLE ops.pdf_published_revision(build_id text)",
            "INSERT INTO ops.pdf_published_revision VALUES('b')",
            (
                "CREATE FUNCTION ops.read_pdf_published_revision(p_task "
                "bigint,p_key text,p_digest text) RETURNS SETOF "
                "ops.pdf_published_revision LANGUAGE sql AS $$SELECT * FROM "
                "ops.pdf_published_revision WHERE p_task=42 AND p_key='p' AND "
                "p_digest=repeat('f',64)$$"
            ),
            (
                "CREATE TABLE kb.pdf_record_companion(product_id text,revision_id "
                "text,family text,local_id text,body jsonb,ordinal bigint)"
            ),
            (
                "CREATE TABLE kb.pdf_record_companion_field(product_id "
                "text,revision_id text,family text,local_id text,field_name "
                "text,stream_id text,scalar_kind text)"
            ),
            (
                "CREATE TABLE ops.pdf_artifact_stream(product_id text,revision_id "
                "text,stream_id text,byte_length bigint,serialization_sha256 "
                "text,byte_root text,encoding_profile text)"
            ),
            (
                "CREATE TABLE ops.pdf_artifact_part(product_id text,revision_id "
                "text,stream_id text,ordinal bigint,byte_offset "
                "bigint,byte_length bigint,body bytea,sha256_digest text)"
            ),
            (
                "INSERT INTO kb.pdf_record_companion "
                "VALUES('b','b','native_metadata','formula_outcomes:0','{\"kind\":\"f"
                'ormula_outcomes","ordinal":0,"pointer":"#/texts/0","outcome":"fai'
                "led\",\"has_diagnostic\":true}',0),('b','b','occurrence','o','{\"occu"
                'rrence_id":"o","pointer":"#/texts/0"}\',0)'
            ),
            (
                "INSERT INTO kb.pdf_record_companion_field "
                "VALUES('b','b','native_metadata','formula_outcomes:0','value','me"
                "ta','y'),('b','b','occurrence','o','text','text','s')"
            ),
        ):
            conn.exec_driver_sql(ddl)
        for stream, payload in payloads.items():
            length, root = byte_root([payload])
            conn.execute(
                text(
                    "INSERT INTO ops.pdf_artifact_stream "
                    "VALUES('b','b',:stream,:length,:digest,:root,:profile)"
                ),
                dict(
                    stream=stream,
                    length=length,
                    digest=sha256(payload).hexdigest(),
                    root=root.hex(),
                    profile="pdf-companion-field-json-v1"
                    if stream == "meta"
                    else "pdf-record-scalar-v1:s",
                ),
            )
            for part in emit_parts(stream, [payload]):
                conn.execute(
                    text(
                        "INSERT INTO ops.pdf_artifact_part "
                        "VALUES('b','b',:stream,:ordinal,:offset,:length,:body,:digest)"
                    ),
                    dict(
                        stream=stream,
                        ordinal=part.ordinal,
                        offset=part.offset,
                        length=part.byte_length,
                        body=part.body,
                        digest=part.sha256_digest,
                    ),
                )
        conn.exec_driver_sql(pdf_record_reader_sql(), execution_options={"no_parameters": True})
        conn.exec_driver_sql(pdf_companion_export_sql(), execution_options={"no_parameters": True})
    yield semantic_bare_engine, payloads


def reader(conn):
    return PublishedPdfReader(
        conn,
        ProductReference(42, "p", "f" * 64),
        revision={"build_id": "b", "release_id": "r", "source_digest": "a" * 64},
    )


def test_selected_metadata_preserves_exact_float_bits_and_nul(field_database):
    engine, payloads = field_database
    with engine.connect() as conn:
        value = next(reader(conn).native_metadata("formula_outcomes", pointer="#/texts/0"))
    expected = json.loads(payloads["meta"])
    assert value == expected
    assert value["precise"].hex() == expected["precise"].hex()
    assert math.copysign(1, value["signed"]) == -1
    assert value["nul"] == "\x00"


@pytest.mark.parametrize("family", ["native_metadata", "occurrence"])
def test_overflow_export_uses_one_joined_cursor(field_database, family):
    engine, payloads = field_database
    with engine.connect() as conn:
        queries = []

        def called(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)

        event.listen(conn, "before_cursor_execute", called)
        encoded = b"".join(reader(conn).iter_companion_json(family))
        event.remove(conn, "before_cursor_execute", called)
        assert len(queries) == 1
    value = json.loads(encoded)
    if family == "native_metadata":
        assert set(value) == {"kind", "ordinal", "value"}
        assert payloads["meta"] in encoded
        assert value["value"] == json.loads(payloads["meta"])
        assert math.copysign(1, value["value"]["signed"]) == -1
    else:
        assert value["text"] == payloads["text"].decode()


def test_abandoned_companion_export_closes_owned_cursor(field_database):
    engine, _ = field_database
    with engine.connect() as conn:
        query = text(
            "SELECT count(*) FROM pg_cursors WHERE name<>'' AND statement "
            "LIKE '%read_pdf_companion_export_events%'"
        )
        assert conn.execute(query).scalar_one() == 0
        chunks = reader(conn).iter_companion_json("native_metadata")
        assert next(chunks).startswith(b"{")
        assert conn.execute(query).scalar_one() == 1
        chunks.close()
        assert conn.execute(query).scalar_one() == 0


def test_formula_health_summary_keeps_exact_diagnostic_in_qualified_metadata():
    from corpus_structure.semantic.source_views import formula_health_summary

    reference = ProductReference(42, "p", "f" * 64)
    outcomes = [
        {"pointer": "#/texts/0", "outcome": "succeeded"},
        {"pointer": "#/texts/1", "outcome": "failed", "error": "unsupported\x00symbol"},
    ]
    summary = formula_health_summary(outcomes, reference)
    assert summary == [
        {"pointer": "#/texts/0", "outcome": "succeeded"},
        {
            "pointer": "#/texts/1",
            "outcome": "failed",
            "diagnostic_ref": {
                "task_id": 42,
                "product_key": "p",
                "content_digest": "f" * 64,
                "family": "native_metadata",
                "local_id": "formula_outcomes:1",
            },
        },
    ]
    assert outcomes[1]["error"] == "unsupported\x00symbol"
    assert formula_health_summary(summary, reference) == summary
