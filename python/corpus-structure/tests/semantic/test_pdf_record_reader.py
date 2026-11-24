"""Published serialization preserves independently constructed native values."""

import io
import json
import math
from collections.abc import Iterator, Mapping
from hashlib import sha256
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
    producer = Mock(spec=["require_operation"])
    monkeypatch.setattr(reader, "_payload_context", lambda: producer)
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
    monkeypatch.setattr(reader, "reconstruct_document", refuse_hydration)
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


def test_whole_export_streams_large_parts_and_releases_its_acquired_rows():
    from corpus_structure.core.db.lifetime import BorrowerCancellation, DatabaseOperationCancelled

    value = native()
    value["pages"] = {"1": {"size": {"width": -0.0, "height": 100.0}, "page_no": 1}}
    value["texts"][0]["text"] = ('\u03b1"\n') * 350_000
    value["body"]["meta"] = {"vendor": {"empty": [], "large": "Ω" * 350_000}}
    reader = NativeRows(value)
    reader.cancellation = BorrowerCancellation()

    sink = io.BytesIO()
    for chunk in reader.iter_native_json():
        assert len(chunk) < 1024 * 1024
        sink.write(chunk)
    assert reader._document_stream_descriptors is None
    assert json.loads(sink.getvalue()) == value == reader.reconstruct_document()
    assert math.copysign(1.0, json.loads(sink.getvalue())["pages"]["1"]["size"]["width"]) == -1

    export = reader.iter_native_json()
    next(export)
    assert reader._document_stream_descriptors is not None
    export.close()
    assert reader._document_stream_descriptors is None

    class BrokenSink(io.BytesIO):
        def write(self, chunk, /):
            raise OSError("consumer stopped")

    with pytest.raises(OSError, match="consumer stopped"):
        reader.write_native_json(BrokenSink())
    assert reader._document_stream_descriptors is None

    export = reader.iter_native_json()
    next(export)
    reader.cancellation.request_cancel()
    with pytest.raises(DatabaseOperationCancelled):
        next(export)
    assert reader._document_stream_descriptors is None


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


def test_program_hydration_cannot_invent_whole_document_scope():
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
