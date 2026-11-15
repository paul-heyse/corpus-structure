"""Exact PostgreSQL retrieval from explicitly bound inventory and vector products."""

from typing import ClassVar

from corpus_structure.semantic.contextual_operations import (
    execute_inventory_profile,
    execute_retrieval_profile,
)


class ContextualRetrievalOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual/declared",
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
                    "source": "same-original",
                    "coverage": {"role": "query", "description": "located-occurrence"},
                    "identity_requirements": ["episode"],
                },
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
                    "source": "explicit-inventory",
                    "coverage": {"role": "inventory", "description": "complete-eligible-inventory"},
                    "identity_requirements": [],
                },
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
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualRetrievalProduct",
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
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "invocation-owned-db-borrow",
        },
        "behavior": "one-exact-native-retrieval-and-source-supported-relationship-result",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["query", "inventory", "vectors", "policy"]},
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
                "reference": "corpus_structure.semantic.contextual_operations.execute_retrieval_profile",
                "contract": "contextual/retrieval-assets",
                "role": "exact-postgresql-and-relationship-algorithms",
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
        return execute_retrieval_profile(self, query, inventory, vectors, policy)

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


class ContextualInventoryOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual_inventory/declared",
        "profile": "derivation",
        "subject": "selected-native-source",
        "subject_definition": {
            "id": "selected-native-source",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "role-associated",
        "context": ["exact-target-selection", "eligible-inventory"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "selection",
                "parameter": "selection",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualTargetSelection",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "explicit-target-facts",
                    "coverage": {"role": "selection", "description": "complete-authored-selection"},
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualInventory",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "retained-target-selection"}],
        "invariants": [
            {"kind": "documentation", "text": "exact-private-target-membership"},
            {"kind": "documentation", "text": "declared-scope-and-version"},
            {"kind": "documentation", "text": "equal-labels-never-merge-targets"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "complete-selected-eligible-inventory",
        },
        "outcomes": ["success"],
        "precision_description": "exact-frozen-inventory",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "immutable-invocation-inputs",
        },
        "behavior": "freeze-explicit-targets-without-Reader-or-legacy-component-custody",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["selection"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.contextual_operations.execute_inventory_profile",
                "contract": "contextual/retrieval-assets",
                "role": "frozen-eligibility-and-semantic-grouping",
            }
        ],
        "assets": [
            {
                "reference": "retrieval-algorithms",
                "contract": "contextual/retrieval-assets",
                "role": "actual-retrieval-and-vector-shape-kernels",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, selection: dict) -> dict:
        return execute_inventory_profile(self, selection)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_operations import resolve_inventory_port

        return resolve_inventory_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )
