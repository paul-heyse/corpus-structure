"""Explicit private authored witness binding and its contextual consumer."""

from typing import ClassVar

from corpus_structure.semantic.contextual_operations import execute_witnessed_retrieval_profile
from corpus_structure.semantic.contextual_witnesses import execute_witness_profile


class ContextualWitnessOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual_witnesses/declared",
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
                "name": "source",
                "parameter": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": {
                        "role": "source",
                        "description": "exact-source-and-assertion-custody",
                    },
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source_set": "contextual-witness-source",
                },
                "subject_target": "source-set",
            },
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
                    "coverage": {
                        "role": "query",
                        "description": "exact-source-and-assertion-custody",
                    },
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
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
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": {
                        "role": "inventory",
                        "description": "exact-source-and-assertion-custody",
                    },
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source_set": "contextual-inventory",
                },
                "subject_target": "source-set",
            },
            {
                "name": "hypotheses",
                "parameter": "hypotheses",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualWitnessHypotheses",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "explicit-authored-hypotheses",
                    "coverage": {
                        "role": "hypotheses",
                        "description": "exact-source-and-assertion-custody",
                    },
                    "identity_requirements": ["original-source"],
                    "origins": ["authored"],
                },
            },
            {
                "name": "cues",
                "parameter": "cues",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": {
                        "role": "cues",
                        "description": "exact-source-and-assertion-custody",
                    },
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source_set": "contextual-witness-cues",
                },
                "subject_target": "source-set",
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualWitnessBindings",
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
            {
                "kind": "documentation",
                "text": "actual-exact-source-cues-and-qualified-query-carrier",
            },
            {
                "kind": "documentation",
                "text": "authored-basis-is-an-attributed-unassessed-assertion",
            },
            {
                "kind": "documentation",
                "text": "private-hypotheses-never-provider-or-accepted-standing",
            },
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-private-authored-source-hypotheses",
        },
        "outcomes": ["success"],
        "replicate_policy": "deterministic-single-result",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "invocation-owned-db-borrow",
        },
        "behavior": "private-authored-source-bound-hypotheses-1",
        "parameters": {},
        "binding": {
            "operator": "scan",
            "roles": ["source", "query", "inventory", "hypotheses", "cues"],
        },
        "output_witnesses": [],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.contextual_witnesses.execute_witness_profile",
                "contract": "contextual/retrieval-assets",
                "role": "exact-private-authored-source-hypotheses",
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

    def run(
        self, source: dict, query: dict, inventory: dict, hypotheses: dict, cues: tuple[dict, ...]
    ) -> dict:
        return execute_witness_profile(self, source, query, inventory, hypotheses, cues)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_witnesses import resolve_witness_port

        return resolve_witness_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )


class ContextualWitnessedRetrievalOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual/with-witnesses",
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
                "name": "scores",
                "parameter": "scores",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualNativeScores",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "scores", "description": "exact-native-scoring-inputs"},
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                },
            },
            {
                "name": "witnesses",
                "parameter": "witnesses",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualWitnessBindings",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "exact-native-witness-binding",
                    "coverage": {
                        "role": "witnesses",
                        "description": "exact-authored-source-binding",
                    },
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualWitnessedRetrievalProduct",
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
            {"kind": "documentation", "text": "exact-postgresql-ranking"},
            {"kind": "documentation", "text": "equal-labels-remain-distinct"},
            {"kind": "documentation", "text": "explicit-relationship-witnesses"},
            {"kind": "documentation", "text": "private-proposal-standing"},
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
        "dependencies": [
            "retrieve.contextual_scores/declared",
            "retrieve.contextual_witnesses/declared",
        ],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "invocation-owned-db-borrow",
        },
        "behavior": "private-authored-witnessed-contextual-reduction-1",
        "parameters": {},
        "binding": {
            "operator": "scan",
            "roles": ["query", "inventory", "vectors", "policy", "witnesses"],
        },
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source_pin",
                "input_role": "query",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject_definition",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/subject_definition",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "document",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/projection_digest",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/membership",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/analyzed_scope_meaning",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/source_product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "query",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                            "field": "/source_pin/kind_contract",
                        },
                        "encoding": "value",
                    },
                ],
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.contextual_operations.execute_witnessed_retrieval_profile",
                "contract": "contextual/retrieval-assets",
                "role": "private-authored-witnessed-relationship-reduction",
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

    def run(
        self,
        query: dict,
        inventory: dict,
        vectors: dict,
        policy: dict,
        scores: dict,
        witnesses: dict,
    ) -> dict:
        return execute_witnessed_retrieval_profile(
            self, query, inventory, vectors, policy, scores, witnesses
        )

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_operations import resolve_retrieval_port

        return resolve_retrieval_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )
