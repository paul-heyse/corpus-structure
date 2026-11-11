"""Compose exact retained characterization layers; this operation performs no inference."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from corpus_structure.core.method import (
    Digest,
    MethodContext,
    Resources,
    SourceRunContext,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.characterization import validate_view
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference


class ComposeViewConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    characterization_base_document: dict[str, Any] | None = None
    characterization_source_scope: dict[str, Any] | None = None
    characterization_layers: tuple[dict[str, Any], ...] = ()
    characterization_profile: Literal["source_only", "selected_layers"] = "source_only"

    @model_validator(mode="after")
    def exact_selection(self):
        if self.characterization_base_document is not None:
            ProductReference(**self.characterization_base_document)
        pins = [ProductReference(**value) for value in self.characterization_layers]
        if len(set(pins)) != len(pins):
            raise ValueError("composition requires distinct exact layer pins")
        if (self.characterization_profile == "source_only") != (not pins):
            raise ValueError("source_only requires no layers; selected_layers requires layers")
        return self

    def require_selection(self):
        if (
            self.characterization_base_document is None
            or self.characterization_source_scope is None
        ):
            raise ValueError("composition requires an explicit base document and source scope")
        return ProductReference(
            **self.characterization_base_document
        ), self.characterization_source_scope


class ComposeViewMethod:
    name = "text.compose_view"
    version = "1"
    family = MethodFamily.NORMALIZE
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = ComposeViewConfig
    resources = Resources()

    def select(self, run: SourceRunContext, cfg: ComposeViewConfig) -> Iterable[UnitRef]:
        base, scope = cfg.require_selection()
        selected = {ref.id: ref for ref in run.reader.source_views()}
        refs = [selected.get(identity) for identity in scope["source_view_ids"]]
        if not refs or any(ref is None or ref.native_product != base for ref in refs):
            raise ValueError("composition source scope is outside the run's selected base document")
        documents = {ref.document_id for ref in refs if ref is not None}
        if len(documents) != 1:
            raise ValueError("composition requires one document")
        return (UnitRef(TaskUnitType.DOCUMENT, next(iter(documents))),)

    def input_digest(self, unit: UnitView, cfg: ComposeViewConfig) -> Digest:
        cfg.require_selection()
        return Digest(
            canonical_bytes(
                {
                    "method": self.name,
                    "version": self.version,
                    "release_id": unit.run.reader.prepared.release_id,
                    "configuration": cfg.model_dump(mode="json"),
                    "document_id": unit.ref.unit_id,
                }
            )
        )

    def run(
        self, units: Sequence[UnitView], cfg: ComposeViewConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        base, scope = cfg.require_selection()
        results = []
        for unit in units:
            reader = unit.run.reader
            if unit.ref not in self.select(unit.run, cfg):
                raise ValueError("composition task unit differs from selected document")
            pins = tuple(ProductReference(**value) for value in cfg.characterization_layers)
            layers = reader.characterization_layers(pins)
            releases = {reader.prepared.release_id: reader.prepared}
            for layer in layers.values():
                release_id = layer.payload["release_id"]
                if release_id not in releases:
                    releases[release_id] = reader.characterization_release(release_id)
            coverage = {}
            for pin in pins:
                for row in layers[pin].payload["coverage"]:
                    coverage[canonical_bytes(row)] = row
            view = validate_view(
                reader.prepared,
                {
                    "format": "enriched-document-view-v1",
                    "base_document": base.values(),
                    "release_id": reader.prepared.release_id,
                    "source_scope": scope,
                    "layers": [pin.values() for pin in pins],
                    "profile": cfg.characterization_profile,
                    "coverage": list(coverage.values()),
                },
                layers,
                releases=releases,
            )
            results.append(
                UnitResult(
                    ref=unit.ref, outcome=ObservationOutcome.PRODUCED, characterization_view=view
                )
            )
        return results
