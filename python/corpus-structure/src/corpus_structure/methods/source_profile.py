"""Original declared profiling algorithm over retained source facts."""

from typing import ClassVar

from corpus_structure.semantic.source_profiles import source_profile_values


class SourceProfileOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "profile.segments/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {'id': 'original-source-view', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'subject-population',
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
                    "coverage": {"role": "source", "description": "selected-scope"},
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
        "applicability": [{'kind': 'documentation', 'text': 'retained-source-intervals-and-parent-layout'}],
        "invariants": [{'kind': 'documentation', 'text': 'exact-selected-interval-union'}, {'kind': 'documentation', 'text': 'no-text-recognition'}],
        "coverage": {"binding": "self", "result_owners": [{"kind":'implementation',"reference":"self"}], "description": "exact-selected-source-scope"},
        "outcomes": ["success", "failed"],
        "numerical_policy": {"asset": "source-profile/numerical-policy", "pointer": "/numerical_policy", "kind": "urn:corpus:kind:source-profile:NumericalPolicy"},
        "assets": [{"reference": "source-ratio-numerics", "contract": "source-profile/numerical-policy", "role": "selected-source-ratio-policy"}],
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
