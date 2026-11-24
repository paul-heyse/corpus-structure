"""Shared controlled inputs and builders for pdf record reader support."""

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

    def iter_rows(self, family, filters=None, **kwargs) -> Generator[dict[str, Any]]:
        if family == "artifact_stream":
            for stream_id, encoding_profile in self.profiles.items():
                if not filters or filters.get("stream_id") == stream_id:
                    yield {"stream_id": stream_id, "encoding_profile": encoding_profile}
            return
        kind = "document" if family == "header" else family
        for row in self.rows:
            if row.kind == kind and all(row.values.get(k) == v for k, v in (filters or {}).items()):
                yield dict(row.values)

    def scalar(self, stream_id):
        yield from self.streams[stream_id]


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
