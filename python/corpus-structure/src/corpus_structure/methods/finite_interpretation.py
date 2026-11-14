"""Declared finite interpretation, distinct from native D1 provider answers."""

from typing import ClassVar

from corpus_structure.semantic.finite_interpretation_products import execute_finite_profile


class FiniteInterpretationOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "interpret.finite_candidates",
        "profile": "derivation",
        "subject": "selected-native-source",
        "context": ["original-source", "retained-candidates", "explicit-factor-policy"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "candidates",
                "parameter": "candidates",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "selected-candidate-population",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "policy",
                "parameter": "policy",
                "kind": "https://corpus-structure.dev/semantic/data-operation-interpretation/DdoFiniteInterpretationPolicy",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "explicit-policy",
                    "coverage": "complete-factor-inputs",
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-interpretation/DdoFiniteInterpretationProduct",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["retained-private-candidates-and-explicit-policy"],
        "invariants": [
            "complete-reading-baseline",
            "no-confidence-as-factor",
            "no-knowledge-admission",
            "finite-factor-dependency-closure",
        ],
        "coverage": "complete-selected-candidate-and-factor-population",
        "outcomes": ["success"],
        "precision": "private-candidate-relative-finite-model",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "retain-baseline-and-real-finite-results-with-unavailable-and-resource-limit-standing",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["candidates", "policy"]},
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source_pin",
                "input_role": "candidates",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "document",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/projection_digest",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/membership",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/analyzed_scope_meaning",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/source_product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "candidates",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                            "field": "/source_pin/kind_contract",
                        },
                        "encoding": "value",
                    },
                ],
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.finite_interpretation_products.execute_finite_profile",
                "contract": "finite/algorithm-assets",
                "role": "finite-template-factor-and-search-kernel",
            }
        ],
        "assets": [
            {
                "reference": "finite-algorithm",
                "contract": "finite/algorithm-assets",
                "role": "actual-finite-algorithm-and-schema",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, candidates: dict, policy: dict) -> dict:
        return execute_finite_profile(self, candidates, policy)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.finite_interpretation_products import resolve_finite_port

        return resolve_finite_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )
