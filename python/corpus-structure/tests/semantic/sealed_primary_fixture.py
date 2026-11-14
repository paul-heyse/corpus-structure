"""Finite projections for genuinely sealed primary-publication fixtures.

These functions read already selected immutable inputs. They schedule no methods,
acquire no provider and introduce no current execution fallback.
"""

from types import SimpleNamespace

from pydantic import JsonValue, TypeAdapter

from corpus_structure.core.method import ObservationDraft, Resources, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
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
    return SimpleNamespace(name=METHOD, version="3", family=MethodFamily.EXTRACT,
        tier=MethodTier.DETERMINISTIC, unit_type=TaskUnitType.SOURCE_VIEW,
        confidence_source=None, Config=M1AnnotationConfig,
        resources=Resources(worker="cpu", batch_size=1, max_concurrency=1))


def m1_annotation_result(reader, view, configuration, ref):
    """Emit the original summary from the actual retained primary columns only."""
    if ref.unit_type != TaskUnitType.SOURCE_VIEW or ref.unit_id != view.ref.id:
        raise ValueError("sealed annotation summary requires its exact selected source unit")
    annotations, errors, retained = consume_annotations(
        reader, view, AnnotationProfile(configuration.sentences)
    )
    return UnitResult(
        ref=ref,
        observations=tuple(ObservationDraft(
            kind="linguistic_annotation",
            payload=LinguisticAnnotationSummary(
                block_id=row.block_id, profile_digest=row.profile_digest,
                dependency_digest=row.dependency_digest,
                availability=tuple((column.attribute, column.status) for column in row.availability)),
            payload_class=LinguisticAnnotationSummary, payload_version="1", source_view_id=view.ref.id)
            for row in annotations) if not errors else (),
        outcome=ObservationOutcome.FAILED if errors else ObservationOutcome.PRODUCED if annotations else ObservationOutcome.EMPTY,
        error="; ".join(errors) if errors else None,
        parse_detail=TypeAdapter(dict[str, JsonValue]).validate_json(canonical_bytes(dict(recipe=configuration.recipe,
            source_pin=NativeSourcePin.from_source(native_source_frame(view, ())).values(),
            characterization_layers=[dict(value) for value in retained["primary_layers"]],
            annotation_errors=list(errors), exclusions=[]))),
    )


def compose_view_descriptor():
    from corpus_structure.methods.characterization import ComposeViewConfig
    return SimpleNamespace(name="text.compose_view", version="1",
        family=MethodFamily.NORMALIZE, tier=MethodTier.DETERMINISTIC,
        unit_type=TaskUnitType.DOCUMENT, confidence_source=None,
        Config=ComposeViewConfig, resources=Resources())


def compose_view_result(reader, configuration, ref):
    """Project the exact admitted sealed manifest selection into its view."""
    from corpus_structure.semantic.characterization import validate_published_view
    from corpus_structure.semantic.product_reference import ProductReference
    base, scope = configuration.require_selection()
    selected = {value.id: value for value in reader.source_views()}
    sources = [selected.get(identity) for identity in scope["source_view_ids"]]
    if not sources or any(value is None or value.native_product != base for value in sources):
        raise ValueError("composition source scope is outside the selected base document")
    if ref.unit_type != TaskUnitType.DOCUMENT or {value.document_id for value in sources if value is not None} != {ref.unit_id}:
        raise ValueError("composition task unit differs from selected document")
    pins = tuple(ProductReference(**value) for value in configuration.characterization_layers)
    layers = reader.characterization_manifests(pins)
    active = pins if configuration.characterization_active_layers is None else tuple(
        ProductReference(**value) for value in configuration.characterization_active_layers)
    coverage = {canonical_bytes(row): row for pin in active for row in layers[pin].payload["coverage"]}
    view = validate_published_view(reader.prepared, dict(format="enriched-document-view-v1",
        base_document=base.values(), release_id=reader.prepared.release_id,
        source_scope=scope, layers=[pin.values() for pin in pins],
        active_layers=[pin.values() for pin in active], profile=configuration.characterization_profile,
        coverage=list(coverage.values())), layers)
    return UnitResult(ref=ref, outcome=ObservationOutcome.PRODUCED, characterization_view=view)
