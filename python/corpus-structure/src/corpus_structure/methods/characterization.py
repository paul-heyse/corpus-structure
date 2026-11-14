"""Compose exact retained characterization layers; this operation performs no inference."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, ClassVar, Literal

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
from corpus_structure.semantic.characterization import validate_published_view
from corpus_structure.semantic.characterization_ports import execute_view_profile
from corpus_structure.semantic.enriched_document_products import (
    EnrichedDocumentProduct,
    RetainedCharacterizationProduct,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_products import FrozenNativeSource


class ComposeViewConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    characterization_base_document: dict[str, Any] | None = None
    characterization_source_scope: dict[str, Any] | None = None
    characterization_layers: tuple[dict[str, Any], ...] = ()
    characterization_active_layers: tuple[dict[str, Any], ...] | None = None
    characterization_profile: Literal["source_only", "selected_layers", "full_characterization"] = (
        "source_only"
    )

    @model_validator(mode="after")
    def exact_selection(self):
        if self.characterization_base_document is not None:
            ProductReference(**self.characterization_base_document)
        pins = [ProductReference(**value) for value in self.characterization_layers]
        if len(set(pins)) != len(pins):
            raise ValueError("composition requires distinct exact layer pins")
        active = (
            pins
            if self.characterization_active_layers is None
            else [ProductReference(**value) for value in self.characterization_active_layers]
        )
        if len(set(active)) != len(active) or not set(active) <= set(pins):
            raise ValueError(
                "active layer selection must be a distinct subset of dependency closure"
            )
        if bool(active) != bool(pins):
            raise ValueError("analytical composition requires active layers")
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
            layers = reader.characterization_manifests(pins)
            active = (
                pins
                if cfg.characterization_active_layers is None
                else tuple(
                    ProductReference(**value) for value in cfg.characterization_active_layers
                )
            )
            coverage = {}
            for pin in active:
                for row in layers[pin].payload["coverage"]:
                    coverage[canonical_bytes(row)] = row
            view = validate_published_view(
                reader.prepared,
                {
                    "format": "enriched-document-view-v1",
                    "base_document": base.values(),
                    "release_id": reader.prepared.release_id,
                    "source_scope": scope,
                    "layers": [pin.values() for pin in pins],
                    "active_layers": [pin.values() for pin in active],
                    "profile": cfg.characterization_profile,
                    "coverage": list(coverage.values()),
                },
                layers,
            )
            results.append(
                UnitResult(
                    ref=unit.ref, outcome=ObservationOutcome.PRODUCED, characterization_view=view
                )
            )
        return results


class ComposeEnrichedDocumentOperation:
    __data_operation__: ClassVar[dict] = {'id': 'text.compose_view/source-native',
     'profile': 'derivation',
     'subject': 'original-document',
     'context': ['original-source', 'selected-scope'],
     'entrypoints': ['run'],
     'roles': [{'name': 'sources',
                'kind': 'https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource',
                'direction': 'input',
                'minimum': 1,
                'maximum': None,
                'collection': 'sequence',
                'presence': 'required',
                'parameter': 'sources',
                'support': {'provenance': 'value_substitution',
                            'identity_requirements': [],
                            'origins': ['computation', 'original-source'],
                            'source': 'original-source',
                            'coverage': 'selected-scope'},
                'subject_field': '/source/document_subject'},
               {'name': 'products',
                'kind': 'https://corpus-structure.dev/semantic/data-operation-source/DdoCharacterizedProduct',
                'direction': 'input',
                'minimum': 0,
                'maximum': None,
                'collection': 'sequence',
                'presence': 'optional',
                'parameter': 'products',
                'support': {'provenance': 'value_substitution',
                            'identity_requirements': [],
                            'origins': ['computation'],
                            'source': 'original-source',
                            'coverage': 'selected-scope'},
                'subject_field': '/source/document_subject'},
               {'name': 'active',
                'kind': 'https://corpus-structure.dev/semantic/data-operation-source/DdoCharacterizedProduct',
                'direction': 'input',
                'minimum': 0,
                'maximum': None,
                'collection': 'sequence',
                'presence': 'optional',
                'parameter': 'active',
                'support': {'provenance': 'value_substitution',
                            'identity_requirements': [],
                            'origins': ['computation'],
                            'source': 'original-source',
                            'coverage': 'selected-scope'},
                'subject_field': '/source/document_subject'},
               {'name': 'result',
                'kind': 'https://corpus-structure.dev/semantic/data-operation-constructions/DdoEnrichedDocumentView',
                'direction': 'output',
                'minimum': 1,
                'maximum': 1,
                'collection': 'scalar',
                'presence': 'required'}],
     'applicability': ['acquired-view-profile'],
     'invariants': ['original-source-coordinates',
                    'governed-semantic-member-references',
                    'explicit-coverage-and-private-standing'],
     'coverage': 'exact-selected-source-scope',
     'outcomes': ['success', 'failed'],
     'precision': 'retained-positioned-characterization',
     'dependencies': [],
     'effects': [],
     'capabilities': {'forms': ['scalar'],
                      'preparation': 'resource',
                      'prepared_factory': 'acquire_port',
                      'cancellation': 'cooperative',
                      'ownership': 'immutable'},
     'behavior': 'compose retained typed view products without upstream language reacquisition',
     'parameters': {'profile': {'value_type': 'string'}},
     'binding': {'operator': 'all',
                 'children': [{'operator': 'collection',
                               'roles': ['sources'],
                               'collection': 'sequence'},
                              {'operator': 'collection',
                               'roles': ['products'],
                               'collection': 'sequence'},
                              {'operator': 'collection', 'roles': ['active'], 'collection': 'sequence'},
                              {'operator': 'membership',
                               'operands': [{'kind': 'parameter',
                                             'name': 'profile',
                                             'value_type': 'string'},
                                            {'kind': 'literal',
                                             'value_type': 'string',
                                             'value': {'json': ['sequence',
                                                                [['string', 'source_only'],
                                                                 ['string', 'selected_layers']]]}}]}]},
     'opaque': [{'reference': 'corpus_structure.semantic.characterization_ports.execute_view_profile',
                 'contract': 'characterization/view-assets',
                 'role': 'prepared-view-resources'},
                {'reference': 'corpus_structure.semantic.source_products.FrozenNativeSource',
                 'contract': 'characterization/view-assets',
                 'role': 'nominal-boundary'},
                {'reference': 'corpus_structure.semantic.enriched_document_products.RetainedCharacterizationProduct',
                 'contract': 'characterization/view-assets',
                 'role': 'nominal-boundary'},
                {'reference': 'corpus_structure.semantic.enriched_document_products.EnrichedDocumentProduct',
                 'contract': 'characterization/view-assets',
                 'role': 'nominal-boundary'}],
     'assets': [{'reference': 'view-profile',
                 'contract': 'characterization/view-assets',
                 'role': 'semantic-implementation-and-schema-assets'}]}

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        """Acquire this declared owner's prepared capability from exact native custody."""
        from corpus_structure.semantic.characterization_ports import resolve_document_view_port

        return resolve_document_view_port(
            prepared, model, operation, identity=identity, authorize=authorize,
            custody=custody, sources=sources,
        )

    def __init__(self, profile, check_active):
        self.profile = profile
        self.check_active = check_active

    def run(
        self,
        sources: tuple[FrozenNativeSource, ...],
        products: tuple[RetainedCharacterizationProduct, ...],
        active: tuple[RetainedCharacterizationProduct, ...],
        profile: str,
    ) -> EnrichedDocumentProduct:
        return execute_view_profile(self, sources, products, active, profile)
