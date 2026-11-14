"""Declared source-native producer over explicitly acquired immutable inputs."""

from __future__ import annotations

from typing import ClassVar

from corpus_structure.semantic.characterization_ports import execute_contextual_profile
from corpus_structure.semantic.construction_products import (
    ConstructionProduct,
    ContextualMeaningProduct,
)
from corpus_structure.semantic.enriched_document_products import RetainedCharacterizationProduct
from corpus_structure.semantic.formal_products import FormalEvidenceProduct
from corpus_structure.semantic.source_products import FrozenNativeSource


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
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct",
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
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
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
                {"operator": "collection", "roles": ["supporting"], "collection": "set"},
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
