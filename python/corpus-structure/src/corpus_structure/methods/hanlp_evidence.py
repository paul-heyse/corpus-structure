"""Declared independent HanLP native characterization over canonical sentences."""

from __future__ import annotations

from typing import ClassVar

from corpus_structure.semantic.canonical_sentences import CanonicalProduct
from corpus_structure.semantic.hanlp_products import HanlpProduct, execute_hanlp_profile
from corpus_structure.semantic.source_products import FrozenNativeSource


class HanlpEvidenceOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.hanlp_native/source-native",
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
                "name": "canonical",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoCanonicalSentences",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "canonical",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-hanlp/DdoHanlpInventory",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["canonical-pretokenized-sentences"],
        "invariants": [
            "original-source-coordinates",
            "no-retokenization",
            "independent-native-head-standings",
        ],
        "coverage": "exact-selected-canonical-sentences",
        "outcomes": ["success", "failed"],
        "precision": "native-one-based-heads-and-half-open-word-spans",
        "dependencies": ["segment.sentences/canonical-projection"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "immutable",
        },
        "behavior": "original HanLP five native heads over retained canonical words",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["source", "canonical"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.hanlp_products.execute_hanlp_profile",
                "contract": "hanlp/profile-assets",
                "role": "prepared-hanlp-native",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "hanlp/profile-assets",
                "role": "original-source-boundary",
            },
            {
                "reference": "corpus_structure.semantic.canonical_sentences.CanonicalProduct",
                "contract": "hanlp/profile-assets",
                "role": "canonical-member-boundary",
            },
            {
                "reference": "corpus_structure.semantic.hanlp_products.HanlpProduct",
                "contract": "hanlp/profile-assets",
                "role": "typed-native-heads",
            },
        ],
        "assets": [
            {
                "reference": "hanlp-native-model-profile",
                "contract": "hanlp/profile-assets",
                "role": "native-checkpoint-heads-and-decoder",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        """Acquire this declared owner's prepared capability from exact native custody."""
        from corpus_structure.semantic.hanlp_products import resolve_hanlp_port

        return resolve_hanlp_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, check_active, host=None):
        self.profile, self.check_active, self.host = profile, check_active, host

    def run(self, source: FrozenNativeSource, canonical: CanonicalProduct) -> HanlpProduct:
        return execute_hanlp_profile(self, source, canonical)
