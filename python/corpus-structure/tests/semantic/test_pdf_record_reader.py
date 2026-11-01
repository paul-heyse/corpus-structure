"""Published serialization preserves independently constructed native values."""

import io
import codecs
import json
import math
from hashlib import sha256
from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock

import pytest

from corpus_structure.semantic.pdf_record_identity import ScalarDescriptor, byte_root
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.pdf_records import iter_native_records
from corpus_structure.semantic.product_reference import ProductReference


class NativeRows(PublishedPdfReader):
    def __init__(self, value):
        self.reference = ProductReference(42, "integrated", "f" * 64)
        self.revision = {"build_id":"b", "release_id":"release", "source_digest":"a"*64,
                         "schema_digest":"c"*64, "recipe_digest":"d"*64}
        self.streams = {}
        self.profiles = {}
        def write(stream, profile, chunks):
            chunks = tuple(chunks)
            self.streams[stream], self.profiles[stream] = chunks, profile
            length, root = byte_root(chunks)
            return ScalarDescriptor(b"y" if profile == "pdf-record-native-json-v1" else profile[-1:].encode(), length, root)
        self.rows = list(iter_native_records(value, product_id="b", revision_id="b",
            release_id="release", source_digest="a"*64,
            record_id_for=lambda address,kind:kind+":"+address, write_scalar=write))
        self._cached_record = self._record

    def iter_native_json(self) -> Iterator[bytes]:
        from corpus_structure.semantic.pdf_records import _parse_inline, _decode_scalar
        def encode(value):
            return json.dumps(value, ensure_ascii=False, allow_nan=False,
                              separators=(",", ":")).encode("utf-8")
        def scalar(stream_id):
            profile = self._profile(stream_id)
            if profile == "pdf-record-native-json-v1":
                yield from self.scalar(stream_id)
            elif profile == "pdf-record-scalar-v1:s":
                yield b'"'
                decoder = codecs.getincrementaldecoder("utf-8")()
                for chunk in self.scalar(stream_id):
                    yield encode(decoder.decode(chunk))[1:-1]
                yield encode(decoder.decode(b"", final=True))[1:-1]
                yield b'"'
            else:
                yield encode(_decode_scalar(self.scalar(stream_id), profile))
        active = set()
        def record(record_id):
            if record_id in active:
                raise ValueError("published native containment cycle")
            active.add(record_id)
            row = self.record(record_id)
            scalars, structure = json.loads(row["scalars_json"]), json.loads(row["structure_json"])
            array = row["native_type"] == "NativeArray"
            if not array:
                yield b"{"
            first = True
            for field in sorted(scalars.keys() | structure["fields"].keys()):
                if not first:
                    yield b","
                first = False
                if not array:
                    yield encode(field) + b":"
                if field in scalars:
                    yield encode(_parse_inline(scalars[field]))
                    continue
                descriptor = structure["fields"][field]
                kind = descriptor["kind"]
                if kind == "object":
                    yield from record(descriptor["target"])
                elif kind == "parts":
                    yield from scalar(descriptor["stream_id"])
                elif kind in {"array", "map"}:
                    yield b"{" if kind == "map" else b"["
                    count = 0
                    for member in self.members(record_id, field):
                        if member["ordinal"] != count:
                            raise ValueError("published membership inventory/order differs")
                        if count:
                            yield b","
                        if kind == "map":
                            key = member["member_key"]
                            if key is None:
                                key = _decode_scalar(self.scalar(member["member_key_stream_id"]),
                                                     self._profile(member["member_key_stream_id"]))
                            yield encode(key) + b":"
                        if member["value_kind"] == "record":
                            yield from record(member["record_id"])
                        elif member["value_kind"] == "scalar":
                            yield encode(_parse_inline(json.loads(member["scalar_json"])))
                        else:
                            yield from scalar(member["stream_id"])
                        count += 1
                    if count != descriptor["length"]:
                        raise ValueError("published membership inventory differs")
                    yield b"}" if kind == "map" else b"]"
                else:
                    raise ValueError("unsupported published structure descriptor")
            if "extensions" in structure:
                # The native opaque encoder emits one object. Preserve its exact
                # encounter order and stream its interior without parsing the object.
                chunks = iter(self.scalar(structure["extensions"]["stream_id"]))
                pending = b""
                opened = False
                separator = not first
                for chunk in chunks:
                    if not opened:
                        if not chunk.startswith(b"{"):
                            raise ValueError("native extension is not an object")
                        chunk = chunk[1:]
                        opened = True
                    pending += chunk
                    if len(pending) > 1:
                        if separator:
                            yield b","; separator = False
                        yield pending[:-1]
                        pending = pending[-1:]
                if not opened or pending != b"}":
                    raise ValueError("native extension object is incomplete")
            if not array:
                yield b"}"
            active.remove(record_id)
        yield from record(self._one("header")["root_id"])


    def iter_rows(self, family, filters=None, **kwargs) -> Iterator[dict[str, Any]]:
        kind = "document" if family == "header" else family
        for row in self.rows:
            if row.kind == kind and all(row.values.get(k) == v for k,v in (filters or {}).items()):
                yield dict(row.values)

    def scalar(self, stream_id):
        yield from self.streams[stream_id]

    def _profile(self, stream_id):
        return self.profiles[stream_id]


def native():
    return {"schema_name":"DoclingDocument", "version":"1.10.0", "name":"Independent café",
            "furniture":{"self_ref":"#/furniture", "children":[], "name":"furniture", "label":"unspecified"},
            "body":{"self_ref":"#/body", "children":[{"$ref":"#/texts/0"}], "name":"body", "label":"unspecified"},
            "groups":[], "texts":[{"self_ref":"#/texts/0", "parent":{"$ref":"#/body"},
              "children":[], "label":"text", "prov":[], "orig":"A α and A", "text":"A α and A",
              "content_layer":"body"}], "pictures":[], "tables":[], "pages":{}}


def test_streamed_native_json_preserves_values_presence_and_order():
    value = native()
    reader = NativeRows(value)
    sink = io.BytesIO()
    receipt = reader.write_native_json(sink)
    actual = json.loads(sink.getvalue())
    assert actual == value
    assert actual["body"]["children"] == [{"$ref":"#/texts/0"}]
    assert actual["texts"][0]["orig"] == "A α and A"
    assert actual["pages"] == {}
    assert receipt.byte_length == len(sink.getvalue())
    assert receipt.serialization_sha256 == sha256(sink.getvalue()).hexdigest()
    assert reader.native_items(["#/texts/0"])["#/texts/0"]["text"] == "A α and A"


def test_large_unicode_scalar_is_serialized_in_bounded_chunks():
    value = native()
    value["texts"][0]["text"] = 'α\\"\n' * 100_000
    reader = NativeRows(value)
    chunks = list(reader.iter_native_json())
    assert max(map(len,chunks)) < 1024 * 1024
    assert json.loads(b"".join(chunks))["texts"][0]["text"] == value["texts"][0]["text"]


def test_streamed_json_refuses_missing_membership():
    reader = NativeRows(native())
    reader.rows = [r for r in reader.rows if not (r.kind == "membership" and r.values["parent_id"] == "DoclingDocument:#" and r.values["field_name"] == "texts")]
    with pytest.raises(ValueError, match="membership inventory"):
        b"".join(reader.iter_native_json())


def test_streamed_float_retains_negative_zero():
    value = native()
    value["pages"] = {"1":{"size":{"width":-0.0,"height":100.0},"page_no":1}}
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
            return iter((r,) for r in self.rows)
    class Connection:
        open = False
        def __init__(self):
            self.calls = []
        def execute(self, statement, values):
            self.calls.append(values)
            after = values["after"]
            rows = [{"record_id":"one", "_cursor":["one"]}] if after is None else []
            return Result(self, rows)
    reader = object.__new__(PublishedPdfReader)
    backing = Connection()
    reader.conn = Mock(wraps=backing)
    reader.reference = ProductReference(42, "integrated", "f"*64)
    rows = reader.iter_rows("native", batch_size=1)
    assert next(rows) == {"record_id":"one"}
    assert not backing.open
    assert list(rows) == []
    assert backing.calls[1]["after"] == '["one"]'
    assert {(c["task"],c["product"],c["digest"]) for c in backing.calls} == {(42,"integrated","f"*64)}


def context_reader():
    class Context(NativeRows):
        def context_rows(self, family, pointers, section_pointer):
            bodies = {
                "input":[("2", {"role":"recognition","task_id":12,"product_key":"B","content_digest":"b"*64})],
                "occurrence":[("o", {"occurrence_id":"o","pointer":"#/texts/0","kind":"item"})],
                "relation":[("r", {"relation_id":"r","kind":"decision","outcome":"selected","endpoints":[
                    {"role":"output","occurrence_id":"o"},
                    {"role":"input","input_index":2,"occurrence_id":"prior"}]})],
                "coverage":[("c", {"coverage_id":"c","outcome":"partial"})],
                "mapping_report":[],
            }
            for local_id, body in bodies[family]:
                yield {"local_id":local_id,"body":body}
    return Context(native())


def test_context_preserves_input_ordinals_and_resolves_output_pin():
    value = context_reader().source_context(["#/texts/0"], "#/body")
    assert value["inputs"][0]["input_index"] == 2
    relation = value["relations"][0]
    assert relation["endpoints"][0]["target_content_digest"] == "f"*64
    assert relation["endpoints"][1]["target_task_id"] == 12
    assert relation["endpoints"][1]["occurrence_id"] == "prior"
    assert value["coverage"][0]["body"]["outcome"] == "partial"


def test_context_refuses_budget_without_truncating_evidence():
    with pytest.raises(ValueError,match="row budget"):
        context_reader().source_context(["#/texts/0"], "#/body", row_budget=3)


def test_native_export_uses_one_ordered_sql_cursor(semantic_bare_engine):
    from sqlalchemy import event, text
    from corpus_structure.semantic.pdf_record_reader_native import pdf_native_export_sql
    value = native()
    value["pages"] = {"1":{"size":{"width":-0.0,"height":100.0},"page_no":1}}
    lowered = NativeRows(value)
    with semantic_bare_engine.begin() as conn:
        for ddl in (
            "CREATE SCHEMA ops", "CREATE SCHEMA kb",
            "CREATE TABLE ops.pdf_record_document(product_id text,revision_id text,root_id text)",
            "CREATE TABLE kb.pdf_record_native(product_id text,revision_id text,record_id text,native_type text,scalars_json jsonb,structure_json jsonb)",
            "CREATE TABLE kb.pdf_record_membership(product_id text,revision_id text,parent_id text,field_name text,ordinal bigint,value_kind text,record_id text,scalar_json jsonb,stream_id text,member_key text,member_key_stream_id text)",
            "CREATE FUNCTION ops.read_pdf_published_revision(p_task bigint,p_product text,p_digest text) RETURNS TABLE(build_id text) LANGUAGE sql AS $$SELECT 'b'::text WHERE p_task=42 AND p_product='integrated' AND p_digest=repeat('f',64)$$",
        ):
            conn.exec_driver_sql(ddl)
        for row in lowered.rows:
            if row.kind == "document":
                fields=("product_id","revision_id","root_id")
                relation="ops.pdf_record_document"
            elif row.kind == "native":
                fields=("product_id","revision_id","record_id","native_type","scalars_json","structure_json")
                relation="kb.pdf_record_native"
            elif row.kind == "membership":
                fields=("product_id","revision_id","parent_id","field_name","ordinal","value_kind","record_id","scalar_json","stream_id","member_key","member_key_stream_id")
                relation="kb.pdf_record_membership"
            else:
                continue
            values={name:row.values.get(name) for name in fields}
            placeholders=[f"CAST(:{name} AS jsonb)" if name.endswith("_json") else ":"+name for name in fields]
            conn.execute(text(f"INSERT INTO {relation}({','.join(fields)}) VALUES({','.join(placeholders)})"),values)
        conn.exec_driver_sql(pdf_native_export_sql())
        queries=[]
        def called(conn,cursor,statement,parameters,context,executemany):
            queries.append(statement)
        event.listen(conn,"before_cursor_execute",called)
        reader=PublishedPdfReader(conn, ProductReference(42,"integrated","f"*64),revision=lowered.revision)
        sink=io.BytesIO()
        receipt=reader.write_native_json(sink)
        assert json.loads(sink.getvalue()) == value
        assert math.copysign(1,json.loads(sink.getvalue())["pages"]["1"]["size"]["width"]) == -1
        assert receipt.serialization_sha256 == sha256(sink.getvalue()).hexdigest()
        assert len(queries) == 1
        event.remove(conn,"before_cursor_execute",called)
        assert conn.execute(text("SELECT count(*) FROM ops.read_pdf_native_events(42,'integrated',repeat('e',64))")).scalar_one() == 0
