"""Evaluate selected packed symbols once against pinned contextual evidence."""

from __future__ import annotations

import time
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.core._model.shapes import Cost
from corpus_structure.core.method import Digest, Resources, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.characterization_ports import execute_contextual_profile
from corpus_structure.semantic.construction_products import (
    ConstructionProduct,
    ContextualMeaningProduct,
)
from corpus_structure.semantic.constructions.evaluation import (
    EVALUATION_FAMILIES,
    ContextualEvaluator,
    environment,
    reference,
)
from corpus_structure.semantic.constructions.resources import evaluation_digest
from corpus_structure.semantic.enriched_document_products import RetainedCharacterizationProduct
from corpus_structure.semantic.formal_products import FormalEvidenceProduct
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_products import FrozenNativeSource

from .construction_characterization import ConstructionCharacterizationMethod


class ContextualInterpretationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    characterization_base_document: dict[str, Any] | None = None
    characterization_source_scope: dict[str, Any] | None = None
    characterization_layers: tuple[dict[str, Any], ...] = ()
    characterization_profile: Literal["primary_contextual_meaning"] = "primary_contextual_meaning"
    symbolic_roots: tuple[dict[str, Any], ...] = Field(
        default=(),
        description=(
            "Empty selects actual top-level retained symbolic roots; "
            "source-first proposals are evaluated even with no symbols."
        ),
    )
    context_layers: tuple[dict[str, Any], ...] = ()
    selected_hypotheses: tuple[dict[str, Any], ...] = ()
    selected_proposals: tuple[dict[str, Any], ...] = ()
    selected_choices: tuple[dict[str, Any], ...] = ()
    model: Literal["none"] = "none"
    grammar: str = Field(default_factory=evaluation_digest)
    context: str = "exact-symbolic-and-contextual-environment-1"

    @model_validator(mode="after")
    def frozen_resources(self):
        if self.grammar != evaluation_digest():
            raise ValueError(
                "contextual evaluator differs from its frozen executable resource identity"
            )
        return self

    def require_selection(self):
        if (
            self.characterization_base_document is None
            or self.characterization_source_scope is None
        ):
            raise ValueError("contextual evaluation requires exact base/source selection")
        pins = tuple(ProductReference(**p) for p in self.characterization_layers)
        if len(set(pins)) != len(pins):
            raise ValueError("contextual evaluation repeats an exact input layer")
        context = tuple(ProductReference(**p) for p in self.context_layers)
        refs = tuple(
            reference(r)
            for r in (
                *self.symbolic_roots,
                *self.selected_hypotheses,
                *self.selected_proposals,
                *self.selected_choices,
            )
        )
        if not set(context) <= set(pins) or any(r.product not in pins for r in refs):
            raise ValueError("contextual selections are outside declared exact input layers")
        return (
            ProductReference(**self.characterization_base_document),
            self.characterization_source_scope,
            pins,
        )

    @property
    def families(self):
        return EVALUATION_FAMILIES


class ContextualInterpretationMethod:
    name = "text.evaluate_context"
    version = "1"
    family = MethodFamily.EXTRACT
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = ContextualInterpretationConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    select = staticmethod(ConstructionCharacterizationMethod.select)

    def input_digest(self, unit, cfg):
        cfg.require_selection()
        return Digest(
            canonical_bytes(
                dict(
                    method=self.name,
                    version=self.version,
                    release_id=unit.run.reader.prepared.release_id,
                    configuration=cfg.model_dump(mode="json"),
                    document_id=unit.ref.unit_id,
                )
            )
        )

    def plan(self, units, cfg, ctx):
        from corpus_structure.semantic.cpu_execution import cpu_method_plan

        return (yield from cpu_method_plan(self, units, cfg, ctx))

    def run(self, units, cfg, ctx):
        from corpus_structure.semantic.cpu_execution import run_cpu_method

        return run_cpu_method(self, units, cfg, ctx)

    def _run_prepared(self, units, cfg, ctx):
        base, scope, pins = cfg.require_selection()
        results = []
        for unit in units:
            started = time.monotonic()
            ctx.check_active()
            if unit.ref not in self.select(unit.run, cfg):
                raise ValueError("contextual evaluation unit differs from selected document")
            reader = unit.run.reader
            layers, pending = {}, pins
            while pending:
                read = reader.characterization_layers(pending)
                if set(read) != set(pending):
                    raise ValueError("evaluation requires complete exact dependency closure")
                layers.update(read)
                pending = tuple(
                    dict.fromkeys(
                        ProductReference(**value)
                        for report in read.values()
                        for value in report.payload["dependencies"]
                        if ProductReference(**value) not in layers
                    )
                )
            if any(layer.base_document != base for layer in layers.values()):
                raise ValueError("contextual input layers belong to another source base")
            releases = {reader.prepared.release_id: reader.prepared}
            for report in layers.values():
                release = report.payload["release_id"]
                if release not in releases:
                    releases[release] = reader.characterization_release(release)
            selected = environment(
                context_layers=tuple(ProductReference(**p) for p in cfg.context_layers),
                hypotheses=tuple(reference(r) for r in cfg.selected_hypotheses),
                proposals=tuple(reference(r) for r in cfg.selected_proposals),
                choices=tuple(reference(r) for r in cfg.selected_choices),
            )
            evaluator = ContextualEvaluator(
                layers,
                check_active=ctx.check_active,
                symbolic_layers=tuple(
                    pin
                    for pin in pins
                    if layers[pin].payload["operation"]["key"] == "text.constructions"
                ),
            )
            report = evaluator.finish(
                reader.prepared,
                scope,
                ctx.characterization_operation(unit.ref),
                tuple(reference(r) for r in cfg.symbolic_roots),
                selected,
                releases=releases,
            )
            results.append(
                UnitResult(
                    ref=unit.ref,
                    outcome=ObservationOutcome.PRODUCED,
                    characterization_layer=report,
                    cost=Cost(wall_ms=round((time.monotonic() - started) * 1000), model="none"),
                )
            )
        return tuple(results)


class ContextualEvaluationOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.contextual_evaluation/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "source",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation", "original-source"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "formal",
                "kind": "https://corpus-structure.dev/semantic/data-operation-characterization/DdoFormalProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
                "parameter": "formal",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "constructions",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoConstructionProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
                "parameter": "constructions",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "supporting",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoCharacterizedProduct",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "sequence",
                "presence": "optional",
                "parameter": "supporting",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoContextualMeaningProduct",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["acquired-contextual-profile"],
        "invariants": [
            "original-source-coordinates",
            "governed-semantic-member-references",
            "explicit-coverage-and-private-standing",
        ],
        "coverage": "exact-selected-source-scope",
        "outcomes": ["success", "failed"],
        "precision": "retained-positioned-characterization",
        "dependencies": ["text.formal_evidence/source-native", "text.constructions/source-native"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "immutable",
        },
        "behavior": "compose retained typed contextual products without upstream language "
        "reacquisition",
        "parameters": {},
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "collection", "roles": ["formal"], "collection": "sequence"},
                {"operator": "collection", "roles": ["constructions"], "collection": "sequence"},
                {"operator": "collection", "roles": ["supporting"], "collection": "sequence"},
            ],
        },
        "opaque": [
            {
                "reference": (
                    "corpus_structure.semantic.characterization_ports.execute_contextual_profile"
                ),
                "contract": "characterization/contextual-assets",
                "role": "prepared-contextual-resources",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "characterization/contextual-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": "corpus_structure.semantic.formal_products.FormalEvidenceProduct",
                "contract": "characterization/contextual-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": "corpus_structure.semantic.construction_products.ConstructionProduct",
                "contract": "characterization/contextual-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": (
                    "corpus_structure.semantic.construction_products.ContextualMeaningProduct"
                ),
                "contract": "characterization/contextual-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": (
                    "corpus_structure.semantic.enriched_document_products."
                    "RetainedCharacterizationProduct"
                ),
                "contract": "characterization/contextual-assets",
                "role": "nominal-boundary",
            },
        ],
        "assets": [
            {
                "reference": "contextual-profile",
                "contract": "characterization/contextual-assets",
                "role": "semantic-implementation-and-schema-assets",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        """Acquire this declared owner's prepared capability from exact native custody."""
        from corpus_structure.semantic.characterization_ports import resolve_contextual_port

        return resolve_contextual_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, check_active):
        self.profile = profile
        self.check_active = check_active

    def run(
        self,
        source: FrozenNativeSource,
        formal: tuple[FormalEvidenceProduct, ...],
        constructions: tuple[ConstructionProduct, ...],
        supporting: tuple[RetainedCharacterizationProduct, ...] = (),
    ) -> ContextualMeaningProduct:
        return execute_contextual_profile(self, source, formal, constructions, supporting)
