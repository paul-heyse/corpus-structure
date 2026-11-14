"""Original declared canonical sentence/token entrypoint over selected native source."""

from __future__ import annotations

from typing import ClassVar

from corpus_structure.semantic.sentence_products import SentenceInventory, execute_sentence_profile
from corpus_structure.semantic.source_products import FrozenNativeSource


class SentenceEvidenceOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "segment.sentences/source-native",
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
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSentenceInventory",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["captured-original-blocks"],
        "invariants": [
            "original-source-coordinates",
            "atom-preserving-layout",
            "closed-token-sentence-membership",
        ],
        "coverage": "exact-selected-original-blocks",
        "outcomes": ["success", "failed"],
        "precision": "exact-original-projection-offsets",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "immutable",
        },
        "behavior": "existing learned spaCy parser over original atom-preserving canonical layout",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["source"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.sentence_products.execute_sentence_profile",
                "contract": "sentences/profile-assets",
                "role": "prepared-spacy-parser",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "sentences/profile-assets",
                "role": "original-source-boundary",
            },
            {
                "reference": "corpus_structure.semantic.sentence_products.SentenceInventory",
                "contract": "sentences/profile-assets",
                "role": "typed-sentence-product",
            },
        ],
        "assets": [
            {
                "reference": "spacy-original-model-profile",
                "contract": "sentences/profile-assets",
                "role": "learned-parser-model-and-layout",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        """Acquire this declared owner's prepared capability from exact native custody."""
        from corpus_structure.semantic.sentence_products import resolve_sentence_port

        return resolve_sentence_port(
            prepared, model, operation, identity=identity, authorize=authorize,
            custody=custody, sources=sources,
        )

    def __init__(self, profile, check_active, host=None):
        self.profile = profile
        self.check_active = check_active
        self.host = host

    def run(self, source: FrozenNativeSource) -> SentenceInventory:
        return execute_sentence_profile(self, source)
