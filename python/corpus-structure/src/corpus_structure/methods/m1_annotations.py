"""Reusable source-bound linguistic columns under ordinary source-task custody."""

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.method import (
    Digest,
    ObservationDraft,
    Resources,
    SourcePreparationReader,
    UnitRef,
    UnitResult,
)
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.annotations import AnnotationProfile, restore_annotations
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.source_preparation import prepare_source
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


class LinguisticAnnotationSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    block_id: str
    profile_digest: str
    dependency_digest: str
    availability: tuple[tuple[str, str], ...]


def consume_annotations(reader: SourcePreparationReader, view, profile):
    """Read the declared upstream batch; missing/failed products never trigger a rerun."""
    result = reader.source_result(view.ref.id, METHOD)
    if result is None:
        raise ValueError("required upstream M1 annotation operation has no source result")
    details = result["parse_detail"]
    if details.get("recipe") != RECIPE or details.get("source_pin") != asdict(
        NativeSourcePin.from_source(native_source_frame(view, ()))
    ):
        raise ValueError("upstream M1 annotation recipe/source binding differs")
    products = restore_annotations(
        details["annotations"], source=native_source_frame(view, ()), profile=profile
    )
    errors = tuple(details.get("annotation_errors", ()))
    if result["outcome"] == "failed" and not errors:
        errors = ("upstream M1 annotation operation failed",)
    return products, errors, result


class M1Annotations:
    name = METHOD
    version = "1"
    family = MethodFamily.EXTRACT
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = M1AnnotationConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg):
        return tuple(
            UnitRef(TaskUnitType.SOURCE_VIEW, ref.id, ref.key)
            for ref in run.reader.source_views()
            if ref.analysis_eligible
        )

    def input_digest(self, unit, cfg):
        view = unit.run.reader.source_view(unit.ref.unit_id)
        return Digest(
            canonical_bytes(
                dict(
                    recipe=cfg.recipe,
                    source=asdict(view.ref),
                    profile=AnnotationProfile(cfg.sentences).identity(),
                    max_annotation_chars=cfg.max_annotation_chars,
                )
            )
        )

    def run(self, units, cfg, ctx):
        results = []
        for unit in units:
            ctx.check_active()
            view = ctx.reader.source_view(unit.ref.unit_id)
            product = prepare_source(
                view,
                profile=AnnotationProfile(cfg.sentences),
                max_annotation_chars=cfg.max_annotation_chars,
                check_active=ctx.check_active,
                annotations_only=True,
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
                        for row in product.annotations
                    )
                    if not product.annotation_errors
                    else (),
                    outcome=ObservationOutcome.FAILED
                    if product.annotation_errors
                    else ObservationOutcome.PRODUCED
                    if product.annotations
                    else ObservationOutcome.EMPTY,
                    error="; ".join(product.annotation_errors)
                    if product.annotation_errors
                    else None,
                    parse_detail=dict(
                        recipe=cfg.recipe,
                        source_pin=NativeSourcePin.from_source(product.source).values(),
                        annotations=[asdict(row) for row in product.annotations],
                        annotation_errors=list(product.annotation_errors),
                        exclusions=list(product.exclusions),
                    ),
                )
            )
        return tuple(results)
