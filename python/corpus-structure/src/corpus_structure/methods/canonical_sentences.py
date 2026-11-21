"""Original stateless operation exposing the retained canonical sentence value."""

from typing import ClassVar

from corpus_structure.semantic.canonical_sentences import (
    CanonicalProduct,
    execute_canonical_projection,
)


class CanonicalSentenceProjection:
    """Cheap declared boundary stops native-label-only changes before HanLP input."""

    __data_operation__: ClassVar[dict] = {
        "validity_family": ["none"],
        "id": "segment.sentences/canonical-projection",
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
        "reference_targets": [
            {
                "output_role": "result",
                "path": "/annotation",
                "input_role": "inventory",
                "variant": "partition-item",
                "collection": "rows",
                "output_collection": "rows",
            }
        ],
        "roles": [
            {
                "name": "inventory",
                "parameter": "inventory",
                "required_rules": [
                    "segment.sentences/native-row-span",
                    "segment.sentences/exact-source-scope",
                ],
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "source": "original-source",
                    "coverage": {"role": "inventory", "description": "selected-scope"},
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
        "applicability": [{"kind": "documentation", "text": "captured-native-inventory"}],
        "invariants": [
            {"kind": "documentation", "text": "original-source-coordinates"},
            {"kind": "documentation", "text": "closed-token-sentence-membership"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-original-blocks",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "exact-original-projection-offsets",
        "dependencies": ["segment.sentences/source-native"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "immutable-input-value",
        },
        "behavior": "canonical sentence and token rows from selected annotation partitions",
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
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile):
        self.profile = profile

    def run(self, inventory: dict) -> CanonicalProduct:
        return execute_canonical_projection(self, inventory)
