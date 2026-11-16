"""Declared exact PostgreSQL score observations, separate from CPU reduction."""

from typing import ClassVar

from corpus_structure.semantic.contextual_scores import execute_scoring_profile


class ContextualScoringOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual_scores/declared",
        "profile": "derivation",
        "subject": "selected-native-source",
        "subject_definition": {
            "id": "selected-native-source",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "role-associated",
        "context": [
            "original-source",
            "located-occurrence",
            "frozen-inventory",
            "exact-encoder-space",
        ],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "query",
                "parameter": "query",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": {"role": "query", "description": "located-occurrence"},
                    "identity_requirements": ["episode"],
                    "source_set": "contextual-query",
                },
                "subject_target": "source-set",
            },
            {
                "name": "inventory",
                "parameter": "inventory",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualInventory",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "value_substitution",
                    "source": "frozen-source-set",
                    "coverage": {"role": "inventory", "description": "complete-eligible-inventory"},
                    "identity_requirements": [],
                    "source_set": "contextual-inventory",
                },
                "subject_target": "source-set",
            },
            {
                "name": "vectors",
                "parameter": "vectors",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualVectors",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "selected-inventory-and-query",
                    "coverage": {"role": "vectors", "description": "complete-selected-inputs"},
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "policy",
                "parameter": "policy",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualRetrievalPolicy",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "explicit-policy",
                    "coverage": {
                        "role": "policy",
                        "description": "complete-relationship-constraints",
                    },
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualNativeScores",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [
            {
                "kind": "documentation",
                "text": "complete-admitted-inventory-profile-and-vector-population",
            }
        ],
        "invariants": [
            {"kind": "documentation", "text": "exact-native-dense-fts-alias-score-observations"}
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "complete-frozen-eligible-inventory",
        },
        "outcomes": ["success"],
        "numerical_policy": {
            "asset": "contextual/retrieval-numerical-policy",
            "pointer": "/policy",
            "kind": "urn:corpus:kind:contextual-retrieval:NumericalPolicy",
        },
        "replicate_policy": "retained-observation-single-result",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "invocation-owned-db-borrow",
        },
        "behavior": "declared-contextual-native-scores-2",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["query", "inventory", "vectors", "policy"]},
        "output_witnesses": [],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.contextual_scores.execute_scoring_profile",
                "contract": "contextual/retrieval-assets",
                "role": "exact-native-score-observations",
            }
        ],
        "assets": [
            {
                "reference": "retrieval-numerics",
                "contract": "contextual/retrieval-numerical-policy",
                "role": "selected-fts-cosine-and-rank-policy",
            },
            {
                "reference": "retrieval-algorithms",
                "contract": "contextual/retrieval-assets",
                "role": "actual-retrieval-and-vector-shape-kernels",
            },
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, query: dict, inventory: dict, vectors: dict, policy: dict) -> dict:
        return execute_scoring_profile(self, query, inventory, vectors, policy)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_scores import resolve_scoring_port

        return resolve_scoring_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )
