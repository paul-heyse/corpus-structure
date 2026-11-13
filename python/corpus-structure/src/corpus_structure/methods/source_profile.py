"""Original declared profiling algorithm over retained source facts."""

from typing import ClassVar

from corpus_structure.semantic.source_profiles import source_profile_values


class SourceProfileOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "profile.segments/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "parameter": "source",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "origins": ["computation", "original-source"],
                    "provenance": "value_substitution",
                    "identity_requirements": [],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source-profile/DdoSourceProfile",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["retained-source-intervals-and-parent-layout"],
        "invariants": ["exact-selected-interval-union", "no-text-recognition"],
        "coverage": "exact-selected-source-scope",
        "outcomes": ["success", "failed"],
        "precision": "integer-counts-and-six-decimal-binary-float-share",
        "dependencies": [],
        "effects": [],
        "parameters": {},
        "behavior": "profile selected original text and native math layout",
        "binding": {"operator": "scan", "roles": ["source"]},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "none",
            "cancellation": "call-boundary",
            "ownership": "immutable-input-value",
        },
    }

    def run(self, source: dict) -> dict:
        return source_profile_values(source)
