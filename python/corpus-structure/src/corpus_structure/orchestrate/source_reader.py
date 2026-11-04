"""Source-method reader borrowing a connection only for an actual read.

The existing BoundReader remains the semantic and cache owner. Its public Reader
operations return owned values, so connection checkout can end before native or
scientific computation. Each coherent read uses the shared read-only snapshot owner.
"""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any, Literal, TypeVar

from sqlalchemy import Engine

from corpus_structure.core.method import SourceViewDraft
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.product_reference import ProductReference

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
        from corpus_structure.semantic.query import read_snapshot

        with self._read_lock, read_snapshot(self._engine) as connection:
            previous = self._owner.conn
            self._owner.conn = connection
            try:
                return operation(self._owner)
            finally:
                self._owner.conn = previous

    def documents(self, originals):
        return self._read(lambda reader: reader.documents(originals))

    def source_view_documents(self):
        return self._read(lambda reader: reader.source_view_documents())

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

    def context_sources(self, source_view_id, request, *, limit, read_budget):
        return self._read(
            lambda reader: reader.context_sources(
                source_view_id, request, limit=limit, read_budget=read_budget
            )
        )

    def source_result(self, source_view_id, method):
        return self._read(lambda reader: reader.source_result(source_view_id, method))

    def source_context_membership(self, source_view_id):
        return self._read(lambda reader: reader.source_context_membership(source_view_id))

    def native_document(self, reference, *, include_candidate_pages: bool = True):
        return self._read(
            lambda reader: reader.native_document(
                reference, include_candidate_pages=include_candidate_pages
            )
        )

    def native_section_drafts(
        self,
        reference: ProductReference,
        *,
        document_id: int,
        selections: tuple[str, ...],
        membership: Literal["direct", "descendants"],
        scope: Any,
        consumer_release: str,
    ) -> tuple[SourceViewDraft, ...]:
        return self._read(
            lambda reader: reader.native_section_drafts(
                reference,
                document_id=document_id,
                selections=selections,
                membership=membership,
                scope=scope,
                consumer_release=consumer_release,
            )
        )

    def capture_pdf_candidates(self, reference, directory):
        return self._read(lambda reader: reader.capture_pdf_candidates(reference, directory))

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

    def measurements(self, method, metric):
        return self._read(lambda reader: reader.measurements(method, metric))

    def artifact(self, artifact_hash):
        return self._read(lambda reader: reader.artifact(artifact_hash))

    def guideline(self):
        return self._read(lambda reader: reader.guideline())

    def original(self, document_id):
        return self._read(lambda reader: reader.original(document_id))
