"""Reusable source-bound linguistic columns under ordinary source-task custody."""

from dataclasses import asdict
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.method import (
    Digest,
    ObservationDraft,
    Reader,
    Resources,
    UnitRef,
    UnitResult,
)
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_evidence_layers import (
    SPACY_FAMILIES,
    retained_annotation_products,
)
from corpus_structure.semantic.constructions.retained_rules import PRIMARY_RULE_FAMILY
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import NativeSourcePin

METHOD = "extract.m1_annotations"
RECIPE = "m1-owned-linguistic-product-1"


class M1AnnotationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    recipe: Literal["m1-owned-linguistic-product-1"] = RECIPE
    sentences: SentenceConfig = Field(default_factory=lambda: SentenceConfig(exclude=("ner",)))
    max_annotation_chars: int = Field(default=32768, ge=1)
    source_projection_digest: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")
    characterization_layers: tuple[dict, ...] = ()


class LinguisticAnnotationSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    block_id: str
    profile_digest: str
    dependency_digest: str
    availability: tuple[tuple[str, str], ...]


def consume_annotations(
    reader: Reader, view, profile
) -> tuple[tuple, tuple[str, ...], dict[str, Any]]:
    """Read exact retained primary inputs; missing evidence never runs a language model."""
    from hashlib import sha256

    layers = reader.primary_characterization(
        view.ref.id, families=(*SPACY_FAMILIES, PRIMARY_RULE_FAMILY)
    )
    products = retained_annotation_products(layers, view, profile)
    pins = [pin.values() for pin in layers]
    details = dict(
        recipe=RECIPE,
        source_pin=asdict(NativeSourcePin.from_source(native_source_frame(view, ()))),
        characterization_layers=pins,
        annotation_errors=[],
    )
    result = dict(
        method="retained.primary_characterization",
        input_hash=sha256(canonical_bytes(pins)).hexdigest(),
        configuration_hash=sha256(canonical_bytes(profile.identity())).hexdigest(),
        outcome="produced" if products else "empty",
        parse_detail=details,
        primary_layers=pins,
    )
    return products, (), result


class M1Annotations:
    name = METHOD
    version = "3"
    family = MethodFamily.EXTRACT
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = M1AnnotationConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg):
        views = tuple(view for view in run.reader.source_views() if view.analysis_eligible)
        if cfg.source_projection_digest is not None:
            views = tuple(
                view for view in views if view.projection_digest == cfg.source_projection_digest
            )
            if len(views) != 1:
                raise ValueError(
                    "annotation source projection selection must match "
                    "exactly one eligible source view"
                )
        return tuple(UnitRef(TaskUnitType.SOURCE_VIEW, ref.id, ref.key) for ref in views)

    def input_digest(self, unit, cfg):
        view = unit.run.reader.source_view(unit.ref.unit_id)
        return Digest(
            canonical_bytes(
                dict(
                    recipe=cfg.recipe,
                    source=asdict(view.ref),
                    profile=AnnotationProfile(cfg.sentences).identity(),
                    max_annotation_chars=cfg.max_annotation_chars,
                    characterization_layers=cfg.characterization_layers,
                )
            )
        )

    def run(self, units, cfg, ctx):
        results = []
        for unit in units:
            ctx.check_active()
            view = ctx.reader.source_view(unit.ref.unit_id)
            annotations, errors, retained = consume_annotations(
                ctx.reader, view, AnnotationProfile(cfg.sentences)
            )
            results.append(
                UnitResult(
                    ref=unit.ref,
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
                    parse_detail=dict(
                        recipe=cfg.recipe,
                        source_pin=NativeSourcePin.from_source(
                            native_source_frame(view, ())
                        ).values(),
                        characterization_layers=[
                            dict(value) for value in retained["primary_layers"]
                        ],
                        annotation_errors=list(errors),
                        exclusions=[],
                    ),
                )
            )
        return tuple(results)
