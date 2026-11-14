"""Original stateless operation exposing the retained canonical sentence value."""

from typing import ClassVar

from corpus_structure.semantic.canonical_sentences import (
    CanonicalProduct,
    execute_canonical_projection,
)


class CanonicalSentenceProjection:
    """Cheap declared boundary stops native-label-only changes before HanLP input."""

    __data_operation__: ClassVar[dict] = {
        "id": "segment.sentences/canonical-projection",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "inventory",
                "parameter": "inventory",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSentenceInventory",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoCanonicalSentences",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["captured-native-inventory"],
        "invariants": ["original-source-coordinates", "closed-token-sentence-membership"],
        "coverage": "exact-selected-original-blocks",
        "outcomes": ["success", "failed"],
        "precision": "exact-original-projection-offsets",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "immutable-input-value",
        },
        "behavior": "canonical sentence and tokenization members from the acquired output model",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["inventory"]},
        "opaque": [
            {
                "reference": (
                    "corpus_structure.semantic.canonical_sentences.execute_canonical_projection"
                ),
                "contract": "canonical/profile-assets",
                "role": "prepared-canonical-projection",
            },
            {
                "reference": "corpus_structure.semantic.canonical_sentences.CanonicalProduct",
                "contract": "canonical/profile-assets",
                "role": "typed-canonical-product",
            },
        ],
        "assets": [
            {
                "reference": "canonical-output-model-projection",
                "contract": "canonical/profile-assets",
                "role": "canonical-model-and-projection",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        """Acquire this declared owner's prepared capability from exact native custody."""
        from corpus_structure.semantic.canonical_sentences import resolve_canonical_sentence_port

        return resolve_canonical_sentence_port(
            prepared, model, operation, identity=identity, authorize=authorize,
            custody=custody, sources=sources,
        )

    def __init__(self, profile):
        self.profile = profile

    def run(self, inventory: dict) -> CanonicalProduct:
        return execute_canonical_projection(self, inventory)
