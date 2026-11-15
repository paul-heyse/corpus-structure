"""Declared original CPU contextual encoder over exact native source occurrences."""

from typing import ClassVar

from corpus_structure.semantic.contextual_encoder import (
    execute_contextual_encoder_profile,
    execute_selected_context_encoder_profile,
)


class ContextualEncodingOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual_vectors/declared",
        "profile": "derivation",
        "subject": "selected-native-source",
        "subject_definition": {'id': 'selected-native-source', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'role-associated',
        "context": [
            "original-source",
            "retained-exact-occurrence",
            "frozen-inventory",
            "acquired-cpu-encoder",
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
                    "source": "same-original",
                    "coverage": "exact-native-source",
                    "origins": ["computation", "original-source"],
                    "identity_requirements": ["episode", "original-source"],
                },
            },
            {
                "name": "occurrence",
                "parameter": "occurrence",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "exact-retained-occurrence",
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
                    "source": "selected-inventory",
                    "coverage": "complete-eligible-population",
                    "identity_requirements": [],
                },
            },
            {
                "name": "query",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
            {
                "name": "vectors",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualVectors",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'one-exact-native-query-carrier-and-complete-inventory'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'original-relative-source-pins'},
            {'kind': 'documentation', 'text': 'captured-cpu-float32-pooling-and-prompts'},
            {'kind': 'documentation', 'text': 'no-inner-process-or-pool'},
            {'kind': 'documentation', 'text': 'exact-profile-and-model-artifacts'},
            {'kind': 'documentation', 'text': 'complete-selected-vector-population'},
        ],
        "coverage": "complete-selected-query-and-inventory",
        "outcomes": ["success", "failed"],
        "precision": None,
        "numerical_policy": {"asset": "contextual/encoder-assets", "pointer": "/numerical_policy", "kind": "urn:corpus:kind:contextual-encoder:NumericalPolicy"},
        "replicate_policy": "explicit-replicates",
        "dependencies": ["retrieve.contextual_inventory/declared"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-reusable-cpu-worker",
        },
        "behavior": "original-contextual-encoder-on-shared-cpu-owner-with-genuine-physical-receipt",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["source", "occurrence", "inventory"]},
        "result_fields": {"query": "query", "vectors": "vectors"},
        "output_witnesses": [
            {
                "output_role": "query",
                "records": "/source_pin",
                "input_role": "occurrence",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": '/pin/subject_definition',
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "document",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/projection_digest",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/membership",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/analyzed_scope_meaning",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/source_product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin/kind_contract",
                        },
                        "encoding": "value",
                    },
                ],
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.contextual_encoder.execute_contextual_encoder_profile",
                "contract": "contextual/encoder-assets",
                "role": "original-acquired-cpu-encoder",
            }
        ],
        "assets": [
            {
                "reference": "cpu-encoder",
                "contract": "contextual/encoder-assets",
                "role": "semantic-cpu-profile-and-model-artifacts",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, source: dict, occurrence: dict, inventory: dict) -> dict[str, dict]:
        return execute_contextual_encoder_profile(self, source, occurrence, inventory)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_encoder import resolve_contextual_encoder_port

        return resolve_contextual_encoder_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )


class SelectedContextEncodingOperation:
    """The three explicit located primary recipes; no lexical fallback or provider inference."""

    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual_vectors/selected-context",
        "profile": "derivation",
        "subject": "selected-native-source",
        "subject_definition": {'id': 'selected-native-source', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'role-associated',
        "context": [
            "original-source",
            "retained-exact-occurrence",
            "frozen-inventory",
            "acquired-cpu-encoder",
            "exact-selected-primary-closure",
            "explicit-context-recipe-and-member",
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
                    "source": "same-original",
                    "coverage": "exact-native-source",
                    "origins": ["computation", "original-source"],
                    "identity_requirements": ["episode", "original-source"],
                },
            },
            {
                "name": "occurrence",
                "parameter": "occurrence",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "exact-retained-occurrence",
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
                    "source": "selected-inventory",
                    "coverage": "complete-eligible-population",
                    "identity_requirements": [],
                },
            },
            {
                "name": "primary",
                "parameter": "primary",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoCharacterizationEnvelope",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": "complete-selected-context-closure",
                    "identity_requirements": ["episode"],
                    "source_set": "query-context-primary",
                },
            },
            {
                "name": "query",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQuery",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
            {
                "name": "vectors",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualVectors",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'one-exact-native-query-carrier-and-complete-inventory'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'original-relative-source-pins'},
            {'kind': 'documentation', 'text': 'captured-cpu-float32-pooling-and-prompts'},
            {'kind': 'documentation', 'text': 'no-inner-process-or-pool'},
            {'kind': 'documentation', 'text': 'exact-profile-and-model-artifacts'},
            {'kind': 'documentation', 'text': 'complete-selected-vector-population'},
            {'kind': 'documentation', 'text': 'requested-context-never-falls-back-to-lexical'},
            {'kind': 'documentation', 'text': 'missing-or-empty-context-refused-before-encoder'},
        ],
        "coverage": "complete-selected-query-and-inventory",
        "outcomes": ["success", "failed"],
        "precision": None,
        "numerical_policy": {"asset": "contextual/encoder-assets", "pointer": "/numerical_policy", "kind": "urn:corpus:kind:contextual-encoder:NumericalPolicy"},
        "replicate_policy": "explicit-replicates",
        "dependencies": ["retrieve.contextual_inventory/declared"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-reusable-cpu-worker",
        },
        "behavior": "encode-exact-located-primary-query-context-on-shared-cpu-owner",
        "parameters": {
            "context_selection": {
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoSelectedQueryContext"
            }
        },
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source", "occurrence", "inventory"]},
                {"operator": "collection", "roles": ["primary"], "collection": "sequence"},
            ],
        },
        "result_fields": {"query": "query", "vectors": "vectors"},
        "output_witnesses": [
            {
                "output_role": "query",
                "records": "",
                "input_role": "occurrence",
                "comparisons": [
                    {
                        "output_field": "source_pin",
                        "input": {
                            "role": "occurrence",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
                            "field": "/pin",
                        },
                        "encoding": "value",
                    }
                ],
            },
            {
                "output_role": "query",
                "records": "/context_inputs/*",
                "input_role": "primary",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": 'subject_definition',
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.contextual_encoder.execute_selected_context_encoder_profile",
                "contract": "contextual/encoder-assets",
                "role": "original-acquired-cpu-encoder",
            }
        ],
        "assets": [
            {
                "reference": "cpu-encoder",
                "contract": "contextual/encoder-assets",
                "role": "semantic-cpu-profile-and-model-artifacts",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(
        self,
        source: dict,
        occurrence: dict,
        inventory: dict,
        primary: tuple[dict, ...],
        context_selection: dict,
    ) -> dict[str, dict]:
        return execute_selected_context_encoder_profile(
            self, source, occurrence, inventory, primary, context_selection
        )

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_encoder import resolve_contextual_encoder_port

        return resolve_contextual_encoder_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )
