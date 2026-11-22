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
        "validity_family": ["none"],
        "id": "text.contextual_evaluation/source-native",
        "rules": [
            {
                "id": "text.contextual_evaluation/positioned-source-geometry",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoContextualMeaningProduct",
                "scope": "product",
                "form": "attested",
                "checker": "producer",
                "checker_operation": "text.contextual_evaluation/source-native",
                "checker_callable": "corpus_structure.semantic.construction_products.verify_interpreted_positioned_geometry",
                "parameters": {
                    "paths": ["members"],
                    "input_reads": {
                        "source": [
                            "source.projection",
                            "selectors",
                            "text",
                            "items",
                            "ancestors",
                            "pieces",
                        ]
                    },
                },
            },
            {
                "id": "text.contextual_evaluation/selected-source-coverage",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoContextualMeaningProduct",
                "scope": "product",
                "form": "attested",
                "checker": "producer",
                "checker_operation": "text.contextual_evaluation/source-native",
                "checker_callable": "corpus_structure.semantic.construction_products.verify_interpreted_source_coverage",
                "parameters": {
                    "paths": ["coverage"],
                    "input_reads": {
                        "source": ["source.projection", "text", "items", "ancestors", "pieces"]
                    },
                },
            },
            {
                "id": "text.contextual_evaluation/body-coverage",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoContextualMeaningProduct",
                "scope": "product",
                "form": "attested",
                "checker": "producer",
                "checker_operation": "text.contextual_evaluation/source-native",
                "checker_callable": "corpus_structure.semantic.construction_products.verify_interpreted_body_coverage",
                "parameters": {"paths": ["coverage", "members", "outcome"]},
            },
            {
                "id": "text.contextual_evaluation/literal-source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoContextualMeaningProduct",
                "scope": "product",
                "form": "attested",
                "checker": "producer",
                "checker_operation": "text.contextual_evaluation/source-native",
                "checker_callable": "corpus_structure.semantic.construction_products.verify_interpreted_literal_source",
                "parameters": {
                    "paths": ["source", "selectors", "members"],
                    "input_reads": {"source": ["source", "selectors", "text"]},
                },
            },
        ],
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {
            "id": "original-source-view",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "subject-population",
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
                    "coverage": {"role": "source", "description": "selected-scope"},
                },
            },
            {
                "name": "formal",
                "kind": "https://corpus-structure.dev/semantic/data-operation-characterization/DdoFormalProduct",
                "direction": "input",
                "required_rules": [
                    "text.formal_evidence/examined-scope",
                    "text.formal_evidence/lexical-inventory-links",
                    "text.formal_evidence/literal-source-geometry",
                    "text.formal_evidence/inventory-topology",
                    "text.formal_evidence/symbolic-inventory-positions",
                    "text.formal_evidence/unique-coverage-family",
                ],
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
                    "coverage": {"role": "formal", "description": "selected-scope"},
                },
            },
            {
                "name": "constructions",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct",
                "direction": "input",
                "required_rules": [
                    "text.constructions/body-coverage",
                    "text.constructions/selected-source-coverage",
                    "text.constructions/literal-source",
                    "text.constructions/positioned-source-geometry",
                ],
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
                    "coverage": {"role": "constructions", "description": "selected-scope"},
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
                    "coverage": {"role": "supporting", "description": "selected-scope"},
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
        "applicability": [{"kind": "documentation", "text": "acquired-contextual-profile"}],
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
                "reference": "bisect.bisect_left",
                "contract": "characterization/source-geometry-runtime",
                "role": "native-codec",
            },
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
