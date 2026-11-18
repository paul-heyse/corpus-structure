"""Generated certification programs retain native privileges and byte framing."""

from types import SimpleNamespace
from typing import TypedDict

import pytest
from pglast import ast, parse_sql
from pglast.stream import RawStream
from sqlalchemy import Column, MetaData, Table, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
from corpus_structure.semantic.pdf_certification_native import pdf_certification_native_sql
from corpus_structure.semantic.pdf_record_identity import IdentityFold, record_frame


class StreamFixture(TypedDict):
    product_id: str
    revision_id: str
    stream_id: str
    byte_length: int
    byte_root: str
    encoding_profile: str
    serialization_sha256: str | None


def test_generated_certification_entrypoints_keep_writer_fences(native_rollback):
    connection = native_rollback.connection
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, pdf_certification_native_sql(target_metadata=metadata))
    arguments = {
        name: None
        for name in (
            "build",
            "task",
            "attempt",
            "holder",
            "frozen",
            "oracle",
            "state",
            "actual",
            "error",
            "lowering",
            "kind",
            "logical",
            "native",
            "streams",
            "targets",
            "schema",
            "release",
        )
    }
    calls = (
        (
            "ops.record_pdf_producer_certification(:build,:task,:attempt,:holder,:lowering,:kind,:logical,:native,:streams)",
            "P0004",
        ),
        ("ops.read_pdf_certification_requirement(:build,:task,:attempt,:holder,:frozen)", "P0002"),
        ("ops.begin_pdf_roundtrip_oracle(:build,:task,:attempt,:holder,:frozen)", "P0004"),
        (
            "ops.finish_pdf_roundtrip_oracle(:build,:task,:attempt,:holder,:frozen,:oracle,:state,:actual,:error)",
            "P0002",
        ),
        ("ops.read_pdf_certification_targets(:build,:task,:attempt,:holder,:targets)", "P0004"),
        ("ops.pdf_lowering_identity(:release)", "42501"),
        ("ops.pdf_producer_stream_identity(:build,:schema)", "42501"),
    )
    with native_owner(connection, "corpus_sem_writer"):
        for call, expected in calls:
            with pytest.raises(DBAPIError) as failure, connection.begin_nested():
                connection.execute(text("SELECT * FROM " + call), arguments).all()
            assert getattr(failure.value.orig, "sqlstate", None) == expected, call


def test_generated_stream_inventory_matches_independent_python_frames(native_rollback):
    source = metadata.tables["ops.pdf_artifact_stream"]
    fixture = Table(
        "certification_streams",
        MetaData(),
        *(Column(column.name, column.type, nullable=column.nullable) for column in source.c),
        schema="pg_temp",
    )
    supplied = SimpleNamespace(tables={**metadata.tables, "ops.pdf_artifact_stream": fixture})
    declaration = next(
        item.stmt
        for item in parse_sql(pdf_certification_native_sql(target_metadata=supplied))
        if isinstance(item.stmt, ast.CreateFunctionStmt)
        and item.stmt.funcname
        and item.stmt.funcname[-1].sval == "pdf_producer_stream_identity"
    )
    connection = native_rollback.connection
    rows: list[StreamFixture] = [
        {
            "product_id": "owned",
            "revision_id": "owned",
            "stream_id": "z-stream",
            "byte_length": 19,
            "byte_root": "a" * 64,
            "encoding_profile": "profile-z",
            "serialization_sha256": None,
        },
        {
            "product_id": "owned",
            "revision_id": "owned",
            "stream_id": "a-stream",
            "byte_length": 0,
            "byte_root": "b" * 64,
            "encoding_profile": "profile-a",
            "serialization_sha256": "c" * 64,
        },
        {
            "product_id": "owned",
            "revision_id": "owned",
            "stream_id": "á-stream",
            "byte_length": 7,
            "byte_root": "d" * 64,
            "encoding_profile": "profile-unicode",
            "serialization_sha256": "e" * 64,
        },
    ]
    with native_owner(connection, "corpus_sem_publisher"):
        connection.execute(CreateTable(fixture))
        connection.execute(fixture.insert(), [*rows, {**rows[0], "product_id": "another"}])
        execute_native_sql(connection, RawStream()(declaration))
    folded = IdentityFold("pdf-producer-streams-v1")
    for row in sorted(rows, key=lambda row: row["stream_id"].encode("utf-8")):
        folded.add(
            record_frame(
                "schema-control",
                "producer-stream",
                row["stream_id"],
                (
                    (name, row[name])
                    for name in (
                        "byte_length",
                        "byte_root",
                        "encoding_profile",
                        "serialization_sha256",
                    )
                ),
            )
        )
    assert (
        connection.scalar(text("SELECT ops.pdf_producer_stream_identity('owned','schema-control')"))
        == folded.digest().hex()
    )
    assert (
        connection.scalar(
            text("SELECT ops.pdf_producer_stream_identity('absent','schema-control')")
        )
        == IdentityFold("pdf-producer-streams-v1").digest().hex()
    )
