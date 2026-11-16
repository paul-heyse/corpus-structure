"""Finite projections for genuinely sealed primary-publication fixtures.

These functions read already selected immutable inputs. They schedule no methods,
acquire no provider and introduce no current execution fallback.
"""

from types import SimpleNamespace

from pydantic import JsonValue, TypeAdapter

from corpus_structure.core.method import ObservationDraft, Resources, UnitResult
from corpus_structure.core.vocab import MethodFamily, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.m1_annotations import (
    METHOD,
    LinguisticAnnotationSummary,
    M1AnnotationConfig,
    consume_annotations,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import NativeSourcePin


def m1_annotation_descriptor():
    return SimpleNamespace(
        name=METHOD,
        version="3",
        family=MethodFamily.EXTRACT,
        unit_type=TaskUnitType.SOURCE_VIEW,
        confidence_source=None,
        Config=M1AnnotationConfig,
        resources=Resources(worker="cpu", batch_size=1, max_concurrency=1),
    )


def m1_annotation_result(reader, view, configuration, ref):
    """Emit the original summary from the actual retained primary columns only."""
    if ref.unit_type != TaskUnitType.SOURCE_VIEW or ref.unit_id != view.ref.id:
        raise ValueError("sealed annotation summary requires its exact selected source unit")
    annotations, errors, retained = consume_annotations(
        reader, view, AnnotationProfile(configuration.sentences)
    )
    return UnitResult(
        ref=ref,
        observations=tuple(
            ObservationDraft(
                kind="linguistic_annotation",
                payload=LinguisticAnnotationSummary(
                    block_id=row.block_id,
                    profile_digest=row.profile_digest,
                    dependency_digest=row.dependency_digest,
                    availability=tuple(
                        (column.attribute, column.status) for column in row.availability
                    ),
                ),
                payload_class=LinguisticAnnotationSummary,
                payload_version="1",
                source_view_id=view.ref.id,
            )
            for row in annotations
        )
        if not errors
        else (),
        outcome=ObservationOutcome.FAILED
        if errors
        else ObservationOutcome.PRODUCED
        if annotations
        else ObservationOutcome.EMPTY,
        error="; ".join(errors) if errors else None,
        parse_detail=TypeAdapter(dict[str, JsonValue]).validate_json(
            canonical_bytes(
                dict(
                    recipe=configuration.recipe,
                    source_pin=NativeSourcePin.from_source(native_source_frame(view, ())).values(),
                    characterization_layers=[dict(value) for value in retained["primary_layers"]],
                    annotation_errors=list(errors),
                    exclusions=[],
                )
            )
        ),
    )
