"""Published serialization preserves independently constructed native values."""

import io
import json
import math
from collections.abc import Iterator, Mapping
from hashlib import sha256
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.product_reference import ProductReference
from semantic.pdf_record_reader_support import NativeRows as NativeRows
from semantic.pdf_record_reader_support import native as native


def test_streamed_native_json_preserves_values_presence_and_order():
    value = native()
    reader = NativeRows(value)
    sink = io.BytesIO()
    receipt = reader.write_native_json(sink)
    actual = json.loads(sink.getvalue())
    assert actual == value
    assert actual["body"]["children"] == [{"$ref": "#/texts/0"}]
    assert actual["texts"][0]["orig"] == ("A \u03b1 and A")
    assert actual["pages"] == {}
    assert receipt.byte_length == len(sink.getvalue())
    assert receipt.serialization_sha256 == sha256(sink.getvalue()).hexdigest()
    assert reader.native_items(["#/texts/0"])["#/texts/0"]["text"] == ("A \u03b1 and A")


def test_reference_scalar_replay_retains_large_unicode():
    value = native()
    value["texts"][0]["text"] = ('\u03b1\\"\n') * 100_000
    reader = NativeRows(value)
    chunks = list(reader.iter_native_json())
    assert json.loads(b"".join(chunks))["texts"][0]["text"] == value["texts"][0]["text"]


def test_streamed_json_refuses_missing_membership():
    reader = NativeRows(native())
    reader.rows = [
        r
        for r in reader.rows
        if not (
            r.kind == "membership"
            and r.values["parent_id"] == "DoclingDocument:#"
            and r.values["field_name"] == "texts"
        )
    ]
    with pytest.raises(ValueError, match="membership inventory"):
        b"".join(reader.iter_native_json())


def test_streamed_float_retains_negative_zero():
    value = native()
    value["pages"] = {"1": {"size": {"width": -0.0, "height": 100.0}, "page_no": 1}}
    actual = json.loads(b"".join(NativeRows(value).iter_native_json()))
    assert math.copysign(1.0, actual["pages"]["1"]["size"]["width"]) == -1


def test_record_pages_close_result_before_yield_and_bind_same_pin():
    class Result:
        def __init__(self, owner, rows):
            self.owner, self.rows = owner, rows

        def __enter__(self):
            self.owner.open = True
            return self

        def __exit__(self, *args):
            self.owner.open = False

        def __iter__(self):
            return iter((json.dumps(r),) for r in self.rows)

    class Connection:
        open = False

        def __init__(self):
            self.calls = []

        def execute(self, statement):
            values = statement.compile().params
            self.calls.append(values)
            after = values["after"]
            rows = [{"record_id": "one", "_cursor": ["one"]}] if after is None else []
            return Result(self, rows)

    reader = object.__new__(PublishedPdfReader)
    backing = Connection()
    reader.conn = Mock(wraps=backing)
    reader.reference = ProductReference(42, "integrated", "f" * 64)
    rows = reader.iter_rows("native", batch_size=1)
    assert next(rows) == {"record_id": "one"}
    assert not backing.open
    assert list(rows) == []
    assert backing.calls[1]["after"] == ["one"]
    assert {(c["task_id"], c["product_key"], c["content_digest"]) for c in backing.calls} == {
        (42, "integrated", "f" * 64)
    }


@pytest.mark.parametrize("assessment", ["absent", "present", "ambiguous"])
def test_compact_record_descriptor_preserves_health_availability_without_hydration(
    monkeypatch, assessment
):
    reader = object.__new__(PublishedPdfReader)
    reader.revision = dict(kind="integrated", release_id="producer-release")
    producer = Mock()
    monkeypatch.setattr(reader, "_payload_context", lambda: SimpleNamespace(execution=producer))
    health = [dict(source_scope="whole_document", conversion="success")]
    if assessment != "absent":
        health.append(dict(source_fidelity="unassessed", execution_outcome="succeeded"))
    if assessment == "ambiguous":
        health.append(dict(source_fidelity="unknown", execution_outcome="succeeded"))

    def rows(family, filters, **kwargs):
        assert family == "companion" and filters == {"family": "health"}
        yield from (dict(body=value) for value in health)

    def refuse_hydration(*args, **kwargs):
        raise AssertionError("compact metadata must not hydrate native content")

    monkeypatch.setattr(reader, "iter_rows", rows)
    monkeypatch.setattr(reader, "hydrate_document", refuse_hydration)
    if assessment == "ambiguous":
        with pytest.raises(ValueError, match="health inventory is ambiguous"):
            reader.product_descriptor()
    else:
        descriptor = reader.product_descriptor()
        assert descriptor["version"] == 2 and descriptor["revision"] == reader.revision
        if assessment == "absent":
            assert "health" not in descriptor
        else:
            assert descriptor["health"] == health[1]
    producer.require_operation.assert_called_once_with("read_pdf_product")


@pytest.mark.parametrize("large", [False, True])
def test_native_export_uses_one_ordered_sql_cursor(semantic_bare_engine, large):
    from sqlalchemy import event, text

    from corpus_structure.semantic.pdf_record_reader_native import pdf_native_export_sql

    value = native()
    value["pages"] = {"1": {"size": {"width": -0.0, "height": 100.0}, "page_no": 1}}
    if large:
        value["texts"][0]["text"] = ('\u03b1\\"\n') * 350_000
        value["body"]["meta"] = {"vendor": {"empty": [], "large": "Ω" * 350_000}}
    if large:
        assert len(value["texts"][0]["text"].encode("utf-8")) > 1024 * 1024
    lowered = NativeRows(value)
    with semantic_bare_engine.begin() as conn:
        for ddl in (
            "CREATE SCHEMA ops",
            "CREATE SCHEMA kb",
            "CREATE TABLE ops.pdf_record_document(product_id text,revision_id text,root_id text)",
            (
                "CREATE TABLE kb.pdf_record_native(product_id text,revision_id "
                "text,record_id text,native_type text,scalars_json "
                "jsonb,structure_json jsonb)"
            ),
            (
                "CREATE TABLE kb.pdf_record_membership(product_id "
                "text,revision_id text,parent_id text,field_name text,ordinal "
                "bigint,value_kind text,record_id text,scalar_json "
                "jsonb,stream_id text,member_key text,member_key_stream_id text)"
            ),
            (
                "CREATE FUNCTION ops.read_pdf_published_revision(p_task "
                "bigint,p_product text,p_digest text) RETURNS TABLE(build_id "
                "text) LANGUAGE sql AS $$SELECT 'b'::text WHERE p_task=42 AND "
                "p_product='integrated' AND p_digest=repeat('f',64)$$"
            ),
        ):
            conn.exec_driver_sql(ddl)
        for row in lowered.rows:
            if row.kind == "document":
                fields = ("product_id", "revision_id", "root_id")
                relation = "ops.pdf_record_document"
            elif row.kind == "native":
                fields = (
                    "product_id",
                    "revision_id",
                    "record_id",
                    "native_type",
                    "scalars_json",
                    "structure_json",
                )
                relation = "kb.pdf_record_native"
            elif row.kind == "membership":
                fields = (
                    "product_id",
                    "revision_id",
                    "parent_id",
                    "field_name",
                    "ordinal",
                    "value_kind",
                    "record_id",
                    "scalar_json",
                    "stream_id",
                    "member_key",
                    "member_key_stream_id",
                )
                relation = "kb.pdf_record_membership"
            else:
                continue
            values = {name: row.values.get(name) for name in fields}
            placeholders = [
                f"CAST(:{name} AS jsonb)" if name.endswith("_json") else ":" + name
                for name in fields
            ]
            conn.execute(
                text(
                    f"INSERT INTO {relation}({','.join(fields)}) VALUES({','.join(placeholders)})"
                ),
                values,
            )
        conn.exec_driver_sql(pdf_native_export_sql())
        queries = []

        def called(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)

        event.listen(conn, "before_cursor_execute", called)

        class ScalarReader(PublishedPdfReader):
            # A scalar replay owner exercises formatter boundaries independently of
            # server artifact admission (which has its separate native controls).
            def scalar(self, stream_id):
                from corpus_structure.semantic.pdf_record_identity import emit_parts

                for part in emit_parts(stream_id, lowered.scalar(stream_id)):
                    yield part.body

            def _profile(self, stream_id):
                return lowered._profile(stream_id)

        reader = ScalarReader(
            conn, ProductReference(42, "integrated", "f" * 64), revision=lowered.revision
        )
        results = []

        def returned(conn, clause, multiparams, params, options, result):
            results.append(result)

        event.listen(conn, "after_execute", returned)
        streamed = io.BytesIO()
        for chunk in reader.iter_native_json():
            assert isinstance(chunk, bytes) and len(chunk) < 1024 * 1024
            streamed.write(chunk)
        assert results[-1].closed
        reconstructed = json.loads(streamed.getvalue())
        assert reconstructed == value
        assert type(reconstructed["pages"]["1"]["size"]["height"]) is float

        def logical_identity(rows):
            from corpus_structure.semantic.pdf_record_identity import LogicalIdentity
            from corpus_structure.semantic.pdf_records import native_record_identity_fields

            identity = LogicalIdentity(
                rows._one("header")["native_schema_digest"], "release", "a" * 64
            )
            fields = [
                part
                for row in rows.rows
                if (
                    part := native_record_identity_fields(
                        row, scalar_descriptor=rows.descriptors.__getitem__
                    )
                )
                is not None
            ]
            ordered = sorted(fields, key=lambda p: (p[0].encode(), p[1].encode()))
            for family, key, members in ordered:
                identity.add_record(family, key, members)
            return identity.pin().logical_digest

        # Native identity has independent scalar/fold vectors. Here it assesses the
        # formatter against the authored input, including distinctions JSON equality loses.
        assert logical_identity(NativeRows(reconstructed)) == logical_identity(lowered)
        assert len(queries) == 1
        queries.clear()
        early = reader.iter_native_json()
        next(early)
        early.close()
        assert results[-1].closed
        assert len(queries) == 1
        queries.clear()

        class BrokenSink(io.BytesIO):
            def write(self, chunk, /) -> int:
                raise OSError("consumer stopped")

        with pytest.raises(OSError, match="consumer stopped"):
            reader.write_native_json(BrokenSink())
        assert results[-1].closed
        assert len(queries) == 1
        queries.clear()
        sink = io.BytesIO()
        receipt = reader.write_native_json(sink)
        assert json.loads(sink.getvalue()) == value
        assert math.copysign(1, json.loads(sink.getvalue())["pages"]["1"]["size"]["width"]) == -1
        assert receipt.serialization_sha256 == sha256(sink.getvalue()).hexdigest()
        assert len(queries) == 1
        queries.clear()
        assert reader.hydrate_document() == value
        assert len(queries) == 1
        from corpus_structure.core.db.lifetime import DatabaseOperationCancelled

        cancelled_reader = ScalarReader(
            conn, ProductReference(42, "integrated", "f" * 64), revision=lowered.revision
        )
        cancelled = cancelled_reader.iter_native_json()
        next(cancelled)
        cancelled_reader.cancellation.request_cancel()
        with pytest.raises(DatabaseOperationCancelled):
            next(cancelled)
        assert results[-1].closed
        event.remove(conn, "before_cursor_execute", called)
        event.remove(conn, "after_execute", returned)
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM "
                    "ops.read_pdf_native_events(42,'integrated',repeat('e',64))"
                )
            ).scalar_one()
            == 0
        )


def test_integrated_v2_export_preserves_metadata_and_distinct_bindings():
    class Export(NativeRows):
        def iter_companions(self, family) -> Iterator[Mapping[str, Any]]:
            if family == "native_metadata":
                yield {
                    "kind": "runtime_report",
                    "ordinal": 0,
                    "value": {"provider": "actual-provider"},
                }
            elif family == "request_outcome":
                yield {"state": "failed", "primary": True}

    reader = Export(native())
    sink = io.BytesIO()
    receipt = reader.write_integrated_json(sink, binding={"selection": "independent"})
    exported = json.loads(sink.getvalue())
    assert exported["export_profile"] == "pdf-integrated-record-export-v2"
    assert exported["product"]["version"] == 2
    assert exported["product"]["revision"] == reader.revision
    assert exported["product"]["logical_digest"] == "f" * 64
    assert exported["product"]["content"] == native()
    assert exported["product"]["native_metadata"][0]["value"]["provider"] == "actual-provider"
    assert exported["product"]["request_outcomes"] == [{"state": "failed", "primary": True}]
    assert receipt.serialization_sha256 == sha256(sink.getvalue()).hexdigest()
    assert receipt.serialization_sha256 != exported["product"]["logical_digest"]


def test_integrated_export_refuses_native_kind():
    class Native(NativeRows):
        def product_kind(self):
            return "native"

    sink = io.BytesIO()
    with pytest.raises(ValueError, match="requires an integrated product"):
        Native(native()).write_integrated_json(sink)
    assert sink.getvalue() == b""


def test_explicit_native_hydration_uses_flat_health_contract():
    class Materialized(NativeRows):
        def iter_companions(self, family) -> Iterator[Mapping[str, Any]]:
            if family == "health":
                yield {
                    "source_scope": "page_range",
                    "page_start": 2,
                    "page_end": 4,
                    "conversion": "partial",
                    "issues": ["failed page"],
                    "display_coverage": "partial",
                }

        def native_metadata(self, kind, *, pointer=None, page_nos=None):
            if kind == "formula_outcomes":
                yield {"pointer": "#/texts/0", "outcome": "failed"}

    value = Materialized(native()).native_product_values()
    assert value["source_scope"] == "page_range"
    assert (value["page_start"], value["page_end"]) == (2, 4)
    assert "page_start" not in value["health"]
    assert value["health"]["conversion"] == "partial"
    assert "source_scope" not in value["health"]
    assert value["health"]["formula_outcomes"][0]["outcome"] == "failed"


def test_native_hydration_cannot_invent_whole_document_scope():
    class Missing(NativeRows):
        def iter_companions(self, family) -> Iterator[Mapping[str, Any]]:
            return iter(())

    with pytest.raises(ValueError, match="scope is absent"):
        Missing(native()).native_product_values()


def test_complete_export_supports_native_document_and_preserves_companions():
    class Native(NativeRows):
        def product_kind(self):
            return "native"

        def iter_companions(self, family):
            if family == "request_outcome":
                yield {"state": "failed", "primary": True}

    sink = io.BytesIO()
    receipt = Native(native()).write_complete_json(sink, binding={"selection": "exact"})
    exported = json.loads(sink.getvalue())
    assert exported["export_profile"] == "pdf-complete-record-export-v1"
    assert exported["product"]["kind"] == "native"
    assert exported["product"]["content"] == native()
    assert exported["product"]["request_outcomes"] == [{"state": "failed", "primary": True}]
    assert receipt.serialization_sha256 == sha256(sink.getvalue()).hexdigest()
