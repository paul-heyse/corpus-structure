"""Declared source-native producer over explicitly acquired immutable inputs."""

from __future__ import annotations

from typing import ClassVar

from corpus_structure.semantic.formal_products import (
    FormalEvidenceProduct,
    FrozenFormalSource,
    execute_formal_profile,
)


class FormalEvidenceOperation:
    """Original source-native entrypoint; the prepared capability supplies resources."""

    __data_operation__: ClassVar[dict] = {
        "id": "text.formal_evidence/source-native",
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
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-characterization/DdoFormalProduct",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["acquired-positioned-formal-profile"],
        "invariants": [
            "original-source-coordinates",
            "positioned-syntax",
            "packed-witness-closure",
        ],
        "coverage": "exact-selected-source-scope",
        "outcomes": ["success", "failed"],
        "precision": "positioned-source-evidence",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "immutable",
        },
        "behavior": "positioned formal characterization without native symbolic evaluation",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["source"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.formal_products.execute_formal_profile",
                "contract": "formal/profile-assets",
                "role": "prepared-parser",
            },
            {
                "reference": "corpus_structure.semantic.formal_products.FrozenFormalSource",
                "contract": "formal/profile-assets",
                "role": "selected-source-boundary",
            },
            {
                "reference": "corpus_structure.semantic.formal_products.FormalEvidenceProduct",
                "contract": "formal/profile-assets",
                "role": "typed-product-boundary",
            },
        ],
        "assets": [
            {
                "reference": "formal-positioned-parser",
                "contract": "formal/profile-assets",
                "role": "grammar-and-implementation-assets",
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        """Acquire this declared owner's prepared capability from exact native custody."""
        from corpus_structure.semantic.formal_products import resolve_formal_evidence_port

        return resolve_formal_evidence_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, options, check_active):
        self.profile = profile
        self.options = options
        self.check_active = check_active

    def run(self, source: FrozenFormalSource) -> FormalEvidenceProduct:
        return execute_formal_profile(self, source)
