"""Declared clause projection over retained native linguistic questions."""

from typing import ClassVar

from corpus_structure.semantic.clause_products import execute_clause_classification


class ClauseClassificationOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "structure.clause_classification/declared",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {'id': 'original-source-view', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'subject-population',
        "context": [
            "original-source",
            "selected-scope",
            "retained-predicate-focus",
            "exact-released-question-pairs",
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
                    "coverage": "exact-selected-source",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "predicates",
                "parameter": "predicates",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoPredicateInspectionReport",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "exact-selected-source",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "canonical",
                "parameter": "canonical",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoCanonicalSentences",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "exact-selected-source",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "gliner_observations",
                "parameter": "gliner_observations",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoGlinerFunctionObservations",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "sequence",
                "presence": "optional",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "exact-selected-source",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "gliner_candidates",
                "parameter": "gliner_candidates",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoGlinerFunctionCandidatesReport",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "sequence",
                "presence": "optional",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "exact-selected-source",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "d1_observations",
                "parameter": "d1_observations",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoD1SourceObservations",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "sequence",
                "presence": "optional",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "exact-selected-source",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "d1_candidates",
                "parameter": "d1_candidates",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoD1SourceCandidatesReport",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "sequence",
                "presence": "optional",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "exact-selected-source",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:structural:DeclaredClauseReport",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [
            "exact-retained-native-predicate-focus-and-paired-released-model-questions"
        ],
        "invariants": [
            "no-private-reclassification",
            "no-focal-scope-substitution",
            "released-vocabulary-preserved",
            "rival-observations-retain-all-native-references",
            "missing-function-question-is-failed-not-empty",
            "unprojectable-predicate-focus-is-partial",
        ],
        "coverage": "exact-inspected-native-predicate-focus-population",
        "outcomes": ["success"],
        "precision": "original-native-half-open-extents",
        "dependencies": [
            "structure.predicate_evidence/declared",
            "segment.sentences/canonical-projection",
        ],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "project-exact-retained-function-answers-onto-authentic-predicate-focus",
        "parameters": {
            "passages": {"default": []},
            "focuses": {"default": []},
            "context_policy": {"default": "exact_focus"},
        },
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "scan", "roles": ["predicates"]},
                {"operator": "scan", "roles": ["canonical"]},
                {
                    "operator": "collection",
                    "roles": ["gliner_observations"],
                    "collection": "sequence",
                },
                {
                    "operator": "collection",
                    "roles": ["gliner_candidates"],
                    "collection": "sequence",
                },
                {"operator": "collection", "roles": ["d1_observations"], "collection": "sequence"},
                {"operator": "collection", "roles": ["d1_candidates"], "collection": "sequence"},
            ],
        },
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/sources_input/*",
                "input_role": "source",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/reports_input/*",
                "input_role": "predicates",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "predicates",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "predicates",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "predicates",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "predicates",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "predicates",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "predicates",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "predicates",
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
                "reference": "corpus_structure.semantic.clause_products.execute_clause_classification",
                "contract": "clauses/profile-assets",
                "role": "exact-retained-native-model-to-focus-projection",
            }
        ],
        "assets": [
            {
                "reference": "declared-clause-functions",
                "contract": "clauses/profile-assets",
                "role": "actual-released-question-and-source-context",
            }
        ],
        "potential_dependencies": [
            "text.gliner_function/source-native",
            "text.d1_source/source-native",
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.clause_products import resolve_clause_port

        return resolve_clause_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, inputs):
        self.inputs = inputs

    def run(
        self,
        source: dict,
        predicates: dict,
        canonical: dict,
        gliner_observations: tuple[dict, ...],
        gliner_candidates: tuple[dict, ...],
        d1_observations: tuple[dict, ...],
        d1_candidates: tuple[dict, ...],
        passages: list[dict],
        focuses: list[str],
        context_policy: str,
    ) -> dict:
        return execute_clause_classification(
            self,
            source,
            predicates,
            canonical,
            gliner_observations,
            gliner_candidates,
            d1_observations,
            d1_candidates,
            passages=passages,
            focuses=focuses,
            context_policy=context_policy,
        )
