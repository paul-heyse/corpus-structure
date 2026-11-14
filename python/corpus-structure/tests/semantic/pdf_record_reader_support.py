"""Shared controlled inputs and builders for pdf record reader support."""

import codecs
import json
from collections.abc import Generator
from typing import Any, Literal

from corpus_structure.semantic.pdf_record_identity import ScalarDescriptor, byte_root
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.pdf_records import iter_native_records
from corpus_structure.semantic.product_reference import ProductReference


class NativeRows(PublishedPdfReader):
    def __init__(self, value):
        self.reference = ProductReference(42, "integrated", "f" * 64)
        self.revision = {
            "build_id": "b",
            "release_id": "release",
            "source_digest": "a" * 64,
            "schema_digest": "c" * 64,
            "recipe_digest": "d" * 64,
        }
        self.streams = {}
        self.profiles = {}
        self.descriptors = {}

        def write(stream, profile, chunks):
            chunks = tuple(chunks)
            self.streams[stream], self.profiles[stream] = chunks, profile
            length, root = byte_root(chunks)
            descriptor = ScalarDescriptor(
                b"y" if profile == "pdf-record-native-json-v1" else profile[-1:].encode(),
                length,
                root,
            )
            self.descriptors[stream] = descriptor
            return descriptor

        self.rows = list(
            iter_native_records(
                value,
                product_id="b",
                revision_id="b",
                release_id="release",
                source_digest="a" * 64,
                record_id_for=lambda address, kind: kind + ":" + address,
                write_scalar=write,
            )
        )
        self._cached_record = self._record

    def product_kind(self) -> Literal["native", "integrated"]:
        return "integrated"

    def _native_schema_mapping(self):
        from corpus_structure.semantic.pdf_records import prepare_native_schema_mapping

        return prepare_native_schema_mapping()

    def iter_companion_export_events(self, family):
        for body in self.iter_companions(family):
            yield {"kind": "row", "body": dict(body)}
            yield {"kind": "close"}

    def iter_native_json(self, events=None) -> Generator[bytes]:
        from corpus_structure.semantic.pdf_records import _decode_scalar, _parse_inline

        def encode(value):
            return json.dumps(
                value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode("utf-8")

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
                                key = _decode_scalar(
                                    self.scalar(member["member_key_stream_id"]),
                                    self._profile(member["member_key_stream_id"]),
                                )
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
                            yield b","
                            separator = False
                        yield pending[:-1]
                        pending = pending[-1:]
                if not opened or pending != b"}":
                    raise ValueError("native extension object is incomplete")
            if not array:
                yield b"}"
            active.remove(record_id)

        yield from record(self._one("header")["root_id"])

    def iter_rows(self, family, filters=None, **kwargs) -> Generator[dict[str, Any]]:
        kind = "document" if family == "header" else family
        for row in self.rows:
            if row.kind == kind and all(row.values.get(k) == v for k, v in (filters or {}).items()):
                yield dict(row.values)

    def scalar(self, stream_id):
        yield from self.streams[stream_id]

    def _profile(self, stream_id):
        return self.profiles[stream_id]


def native() -> dict[str, Any]:
    return {
        "schema_name": "DoclingDocument",
        "version": "1.10.0",
        "name": "Independent café",
        "furniture": {
            "self_ref": "#/furniture",
            "children": [],
            "name": "furniture",
            "label": "unspecified",
        },
        "body": {
            "self_ref": "#/body",
            "children": [{"$ref": "#/texts/0"}],
            "name": "body",
            "label": "unspecified",
        },
        "groups": [],
        "texts": [
            {
                "self_ref": "#/texts/0",
                "parent": {"$ref": "#/body"},
                "children": [],
                "label": "text",
                "prov": [],
                "orig": ("A \u03b1 and A"),
                "text": ("A \u03b1 and A"),
                "content_layer": "body",
            }
        ],
        "pictures": [],
        "tables": [],
        "pages": {},
    }
