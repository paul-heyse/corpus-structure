"""Original stateless operation exposing the retained canonical sentence value."""

from typing import ClassVar

from corpus_structure.semantic.canonical_sentences import canonical_sentence_values


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
            "preparation": "none",
            "cancellation": "call-boundary",
            "ownership": "immutable-input-value",
        },
        "behavior": "declared canonical sentence and tokenization value projection",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["inventory"]},
    }

    def run(self, inventory: dict) -> dict:
        return canonical_sentence_values(inventory)
