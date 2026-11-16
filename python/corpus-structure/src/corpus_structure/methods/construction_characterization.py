"""Declared source-native producer over explicitly acquired immutable inputs."""

from __future__ import annotations

from typing import ClassVar

from corpus_structure.semantic.characterization_ports import execute_construction_profile
from corpus_structure.semantic.construction_products import ConstructionProduct
from corpus_structure.semantic.formal_products import FormalEvidenceProduct
from corpus_structure.semantic.sentence_products import SourceAnnotations
from corpus_structure.semantic.source_products import FrozenNativeSource


class ConstructionOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.constructions/source-native",
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
                "name": "sentences",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "sentences",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": {"role": "sentences", "description": "selected-scope"},
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "acquired-construction-profile"}],
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
        "dependencies": [
            "text.formal_evidence/source-native",
            "segment.sentences/source-native",
        ],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "immutable",
        },
        "behavior": "compose retained typed construction products without upstream language "
        "reacquisition",
        "parameters": {},
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "collection", "roles": ["formal"], "collection": "sequence"},
                {"operator": "scan", "roles": ["sentences"]},
            ],
        },
        "opaque": [
            {
                "reference": (
                    "corpus_structure.semantic.characterization_ports.execute_construction_profile"
                ),
                "contract": "characterization/construction-assets",
                "role": "prepared-construction-resources",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "characterization/construction-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": "corpus_structure.semantic.formal_products.FormalEvidenceProduct",
                "contract": "characterization/construction-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": "corpus_structure.semantic.construction_products.ConstructionProduct",
                "contract": "characterization/construction-assets",
                "role": "nominal-boundary",
            },
            {
                "reference": "corpus_structure.semantic.sentence_products.SourceAnnotations",
                "contract": "characterization/construction-assets",
                "role": "nominal-boundary",
            },
        ],
        "assets": [
            {
                "reference": "construction-configuration",
                "contract": "characterization/construction-configuration",
                "role": "frozen-construction-bounds-and-named-rules",
            },
            {
                "reference": "construction-profile",
                "contract": "characterization/construction-assets",
                "role": "semantic-implementation-and-schema-assets",
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        """Acquire this declared owner's prepared capability from exact native custody."""
        from corpus_structure.semantic.characterization_ports import resolve_construction_port

        return resolve_construction_port(
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
        sentences: SourceAnnotations,
    ) -> ConstructionProduct:
        return execute_construction_profile(self, source, formal, sentences)
