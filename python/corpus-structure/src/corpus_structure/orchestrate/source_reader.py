"""Source-method reader borrowing a connection only for an actual read.

The existing BoundReader remains the semantic and cache owner. Its public Reader
operations return owned values, so connection checkout can end before native or
scientific computation. Explicit connection consumers own their context instead.
"""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import TypeVar

from sqlalchemy import Engine

from corpus_structure.semantic.operations import BoundReader

_T = TypeVar("_T")


class ScopedSourceReader:
    def __init__(self, engine: Engine, owner: BoundReader):
        self._engine = engine
        self._owner = owner
        self._read_lock = RLock()

    @property
    def prepared(self):
        return self._owner.prepared

    @property
    def math_readings_batch(self):
        return self._owner.math_readings_batch

    @math_readings_batch.setter
    def math_readings_batch(self, value):
        self._owner.math_readings_batch = value

    def _read(self, operation: Callable[[BoundReader], _T]) -> _T:
        with self._read_lock, self._engine.connect() as connection:
            previous = self._owner.conn
            self._owner.conn = connection
            try:
                return operation(self._owner)
            finally:
                self._owner.conn = previous

    def connection(self):
        return self._engine.connect()

    def pdf_context(self):
        return self._read(lambda reader: reader.pdf_context())

    def pdf_contract(self):
        return self._read(lambda reader: reader.pdf_contract())

    def source_views(self):
        return self._read(lambda reader: reader.source_views())

    def source_view(self, source_view_id):
        return self._read(lambda reader: reader.source_view(source_view_id))

    def ancestor_source_views(self, source_view_id):
        return self._read(lambda reader: reader.ancestor_source_views(source_view_id))

    def native_document(self, reference):
        return self._read(lambda reader: reader.native_document(reference))

    def prepare_integrated_pdf_product(
        self, payload, original, recipe_bytes, *, artifacts=(), native_schema=None
    ):
        return self._read(
            lambda reader: reader.prepare_integrated_pdf_product(
                payload,
                original,
                recipe_bytes,
                artifacts=artifacts,
                native_schema=native_schema,
            )
        )

    def prepare_pdf_product(self, payload, original, schema_bytes, recipe_bytes):
        return self._read(
            lambda reader: reader.prepare_pdf_product(
                payload,
                original,
                schema_bytes,
                recipe_bytes,
            )
        )

    def native_product_reference(self, document_id, product_key, digest):
        return self._read(
            lambda reader: reader.native_product_reference(document_id, product_key, digest)
        )

    def source_observations(self, source_view_id, method, kind):
        return self._read(lambda reader: reader.source_observations(source_view_id, method, kind))

    def source_view_coverage(self, source_view_id, method):
        return self._read(lambda reader: reader.source_view_coverage(source_view_id, method))

    def renditions(self):
        return self._read(lambda reader: reader.renditions())

    def content(self, rendition_id):
        return self._read(lambda reader: reader.content(rendition_id))

    def segments(self, rendition_id):
        return self._read(lambda reader: reader.segments(rendition_id))

    def observations(self, rendition_id, method, kind):
        return self._read(lambda reader: reader.observations(rendition_id, method, kind))

    def source_coverage(self, rendition_id, method):
        return self._read(lambda reader: reader.source_coverage(rendition_id, method))

    def measurements(self, method, metric):
        return self._read(lambda reader: reader.measurements(method, metric))

    def artifact(self, artifact_hash):
        return self._read(lambda reader: reader.artifact(artifact_hash))

    def guideline(self):
        return self._read(lambda reader: reader.guideline())

    def original(self, document_id):
        return self._read(lambda reader: reader.original(document_id))
