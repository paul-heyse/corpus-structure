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

    def characterization_release(self, release_id):
        return self._read(lambda reader: reader.characterization_release(release_id))

    def characterization_view(self, reference):
        return self._read(lambda reader: reader.characterization_view(reference))

    def characterization_memberships(
        self, reference, groups, *, after=None, layer_key=None, limit=100, max_bytes=1_048_576
    ):
        return self._read(
            lambda reader: reader.characterization_memberships(
                reference,
                groups,
                after=after,
                layer_key=layer_key,
                limit=limit,
                max_bytes=max_bytes,
            )
        )

    def characterization_layers(self, references):
        return self._read(lambda reader: reader.characterization_layers(references))

    def primary_characterization(self, source_view_id, *, families):
        return self._read(
            lambda reader: reader.primary_characterization(source_view_id, families=families)
        )

    def source_views(self):
        return self._read(lambda reader: reader.source_views())

    def source_view_ref(self, source_view_id):
        return self._read(lambda reader: reader.source_view_ref(source_view_id))

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

    def source_result(self, source_view_id, method, *, occurrence_ids=(), semantic_types=()):
        return self._read(
            lambda reader: reader.source_result(
                source_view_id, method, occurrence_ids=occurrence_ids, semantic_types=semantic_types
            )
        )

    def retained_source_result(self, source_view_id, task_id, method):
        return self._read(
            lambda reader: reader.retained_source_result(source_view_id, task_id, method)
        )

    def retained_definition_component(self, reference):
        return self._read(lambda reader: reader.retained_definition_component(reference))

    def resolve_definition_component(self, reference):
        return self._read(lambda reader: reader.resolve_definition_component(reference))

    def retained_relationship_decision(self, reference):
        return self._read(lambda reader: reader.retained_relationship_decision(reference))

    def component_semantic_targets(self, targets):
        return self._read(lambda reader: reader.component_semantic_targets(targets))

    def retained_component_section(self, reference, work_digest):
        return self._read(lambda reader: reader.retained_component_section(reference, work_digest))

    def contextual_section_headings(self, sources, source_view_id, scope, effective_version):
        return self._read(
            lambda reader: reader.contextual_section_headings(
                sources, source_view_id, scope, effective_version
            )
        )

    def cached_contextual_vectors(self, **request):
        return self._read(lambda reader: reader.cached_contextual_vectors(**request))

    def contextual_candidates(self, **request):
        return self._read(lambda reader: reader.contextual_candidates(**request))

    def contextual_mutual_neighbors(self, report):
        return self._read(lambda reader: reader.contextual_mutual_neighbors(report))

    def validate_structural_inputs(self, inputs):
        return self._read(lambda reader: reader.validate_structural_inputs(inputs))

    def structural_source_frame(self, inputs, source_ref):
        return self._read(lambda reader: reader.structural_source_frame(inputs, source_ref))

    def structural_source_annotations(self, inputs, source_ref, profile):
        return self._read(
            lambda reader: reader.structural_source_annotations(inputs, source_ref, profile)
        )

    def retained_source_contribution(self, reference):
        return self._read(lambda reader: reader.retained_source_contribution(reference))

    def retained_declaration_parser(self, reference):
        return self._read(lambda reader: reader.retained_declaration_parser(reference))

    def prepare_table_correspondence(self, source_view_id, contributions, weight_scale):
        return self._read(
            lambda reader: reader.prepare_table_correspondence(
                source_view_id, contributions, weight_scale
            )
        )

    def retained_structural_report(self, reference):
        return self._read(lambda reader: reader.retained_structural_report(reference))

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
