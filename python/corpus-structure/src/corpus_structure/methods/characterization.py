"""Compose exact retained characterization layers; this operation performs no inference."""

from __future__ import annotations

from typing import ClassVar

from corpus_structure.semantic.characterization_ports import execute_view_profile
from corpus_structure.semantic.enriched_document_products import (
    EnrichedDocumentProduct,
    RetainedCharacterizationProduct,
)
from corpus_structure.semantic.source_products import FrozenNativeSource


class PreparedCompositionReceiver:
    """Shared acquired receiver state; each declared operation owns its callable shape."""

    def __init__(self, profile, check_active):
        self.profile = profile
        self.check_active = check_active


class ComposeEnrichedDocumentOperation(PreparedCompositionReceiver):
    __data_operation__: ClassVar[dict] = {
        "id": "text.compose_view/source-native",
        "profile": "derivation",
        "subject": "original-document",
        "subject_definition": {
            "id": "original-document",
            "identifier_kind": "string",
            "scope": "original-document",
        },
        "discovery_relation": "role-associated",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "sources",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
                "parameter": "sources",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation", "original-source"],
                    "source": "original-source",
                    "coverage": {"role": "sources", "description": "selected-scope"},
                },
                "subject_field": "/source/document_subject",
            },
            {
                "name": "products",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoCharacterizedProduct",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "parameter": "products",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source": "frozen-source-set",
                    "source_set": "selected-characterization-products",
                    "coverage": {"role": "products", "description": "selected-scope"},
                },
                "subject_field": "/source/document_subject",
            },
            {
                "name": "active",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoCharacterizedProduct",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "parameter": "active",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source": "frozen-source-set",
                    "source_set": "active-characterization-products",
                    "coverage": {"role": "active", "description": "selected-scope"},
                },
                "subject_field": "/source/document_subject",
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoEnrichedDocumentView",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "acquired-view-profile"}],
        "invariants": [
            {"kind": "documentation", "text": "original-source-coordinates"},
            {"kind": "documentation", "text": "governed-semantic-member-references"},
            {"kind": "documentation", "text": "explicit-coverage-and-private-standing"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-source-scope",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "retained-positioned-characterization",
        "dependencies": ["source.selected_views/discovery"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "immutable",
        },
        "behavior": "compose retained typed view products without upstream language reacquisition",
        "parameters": {"profile": {"value_type": "string"}},
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "collection", "roles": ["sources"], "collection": "sequence"},
                {"operator": "collection", "roles": ["products"], "collection": "set"},
                {"operator": "collection", "roles": ["active"], "collection": "set"},
                {
                    "operator": "membership",
                    "operands": [
                        {"kind": "parameter", "name": "profile", "value_type": "string"},
                        {
                            "kind": "literal",
                            "value_type": "string",
                            "value": ["source_only", "selected_layers"],
                        },
                    ],
                },
            ],
        },
        "opaque": [
            {
                "reference": "corpus_structure.semantic.characterization_ports.execute_view_profile",
                "contract": "characterization/view-assets",
                "role": "prepared-view-resources",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "characterization/view-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": "corpus_structure.semantic.enriched_document_products.RetainedCharacterizationProduct",
                "contract": "characterization/view-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": "corpus_structure.semantic.enriched_document_products.EnrichedDocumentProduct",
                "contract": "characterization/view-assets",
                "role": "nominal-boundary",
            },
        ],
        "assets": [
            {
                "reference": "view-profile",
                "contract": "characterization/view-assets",
                "role": "semantic-implementation-and-schema-assets",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        """Acquire this declared owner's prepared capability from exact native custody."""
        from corpus_structure.semantic.characterization_ports import resolve_document_view_port

        return resolve_document_view_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def run(
        self,
        sources: tuple[FrozenNativeSource, ...],
        products: tuple[RetainedCharacterizationProduct, ...],
        active: tuple[RetainedCharacterizationProduct, ...],
        profile: str,
    ) -> EnrichedDocumentProduct:
        return execute_view_profile(self, sources, products, active, profile)
