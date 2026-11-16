"""Current protected complete-record grading and fitting operations."""

from typing import ClassVar

from corpus_structure.evaluate.declared_record_policy import (
    execute_fit_profile,
    execute_grade_profile,
)


class RecordPolicyFit:
    __data_operation__: ClassVar[dict] = {
        "id": "record_policy.fit",
        "profile": "derivation",
        "subject": "knowledge-universe",
        "subject_definition": {
            "id": "knowledge-universe",
            "identifier_kind": "string",
            "scope": "project",
        },
        "discovery_relation": "role-associated",
        "context": [
            "protected-record-grades",
            "exact-frozen-feature-instance",
            "held-out-final-events",
        ],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "feature_grade",
                "parameter": "feature_grade",
                "direction": "input",
                "subject_target": "source-set",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordGrade",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "record-policy-feature-grades",
                    "identity_requirements": ["episode"],
                    "coverage": {
                        "role": "feature_grade",
                        "description": "complete-authenticated-feature-fit-frame",
                    },
                },
            },
            {
                "name": "calibration_grade",
                "parameter": "calibration_grade",
                "direction": "input",
                "subject_target": "source-set",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordGrade",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "record-policy-calibration-grades",
                    "identity_requirements": ["episode"],
                    "coverage": {
                        "role": "calibration_grade",
                        "description": "complete-authenticated-calibration-frame",
                    },
                },
            },
            {
                "name": "specification",
                "parameter": "specification",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordFitSpecification",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "predeclared-fitting-procedure",
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                    "coverage": {
                        "role": "specification",
                        "description": "exact-frozen-feature-and-fit-selection",
                    },
                },
            },
            {
                "name": "fitted",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoFittedRecordPolicy",
                "minimum": 0,
                "maximum": 1,
                "collection": "scalar",
                "presence": "optional",
            },
        ],
        "applicability": [
            {
                "kind": "documentation",
                "text": "actual-fitter-capability-and-separately-evaluator-authorized-calibration",
            }
        ],
        "invariants": [
            {
                "kind": "documentation",
                "text": "exact-feature-recomputation-and-origin-heldout-full-reading-labels",
            }
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "complete-predeclared-fit-and-calibration-frames",
        },
        "outcomes": ["success", "empty"],
        "precision_description": "exact-canonical-frozen-predictor-and-finite-library-fit",
        "dependencies": [],
        "effects": [],
        "parameters": {},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "protected-exact-feature-recomputation-and-final-event-calibration-without-policy-authority",
        "binding": {
            "operator": "scan",
            "roles": ["feature_grade", "calibration_grade", "specification"],
        },
        "opaque": [
            {
                "reference": "corpus_structure.evaluate.declared_record_policy.execute_fit_profile",
                "contract": "record-policy/computation-assets",
                "role": "current-protected-fitting-kernel",
            }
        ],
        "assets": [
            {
                "reference": "record-policy-computation",
                "contract": "record-policy/computation-assets",
                "role": "exact-record-fit-source-and-numerical-contracts",
            }
        ],
    }

    def run(self, feature_grade: dict, calibration_grade: dict, specification: dict) -> dict:
        return execute_fit_profile(self, feature_grade, calibration_grade, specification)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.evaluate.declared_record_policy import acquire_fit_port

        return acquire_fit_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )


class RecordPolicyGrade:
    __data_operation__: ClassVar[dict] = {
        "id": "record_policy.grade",
        "profile": "derivation",
        "subject": "knowledge-universe",
        "subject_definition": {
            "id": "knowledge-universe",
            "identifier_kind": "string",
            "scope": "project",
        },
        "discovery_relation": "role-associated",
        "context": [
            "source-only-independent-references",
            "complete-reading-population",
            "protected-grading",
        ],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "sources",
                "parameter": "sources",
                "direction": "input",
                "subject_target": "source-set",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "minimum": 1,
                "maximum": None,
                "collection": "set",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "record-policy-sources",
                    "identity_requirements": ["episode"],
                    "coverage": {
                        "role": "sources",
                        "description": "every-actual-primary-and-related-consumed-source",
                    },
                },
            },
            {
                "name": "reference_a",
                "parameter": "reference_a",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordReferencePopulationA",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "source-only-independent-a",
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                    "coverage": {
                        "role": "reference_a",
                        "description": "exact-independent-source-only-a",
                    },
                },
            },
            {
                "name": "reference_b",
                "parameter": "reference_b",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordReferencePopulationB",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "source-only-independent-b",
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                    "coverage": {
                        "role": "reference_b",
                        "description": "exact-independent-source-only-b",
                    },
                },
            },
            {
                "name": "adjudication",
                "parameter": "adjudication",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordReferencePopulationC",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "source-only-c-adjudication",
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                    "coverage": {
                        "role": "adjudication",
                        "description": "exact-c-over-retained-independent-a-b",
                    },
                },
            },
            {
                "name": "prediction",
                "parameter": "prediction",
                "direction": "input",
                "subject_target": "source-set",
                "kind": "https://corpus-structure.dev/semantic/data-operation-reading-resolution/DdoResolvedReadingReport",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "record-policy-predictions",
                    "identity_requirements": ["episode"],
                    "coverage": {
                        "role": "prediction",
                        "description": "all-private-readings-including-empty-and-low-score",
                    },
                },
            },
            {
                "name": "specification",
                "parameter": "specification",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordGradeSpecification",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "predeclared-grade-procedure",
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                    "coverage": {
                        "role": "specification",
                        "description": "exact-frozen-prediction-selection-and-feature-algorithm",
                    },
                },
            },
            {
                "name": "grade",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-record-policy/protected/DdoRecordGrade",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [
            {
                "kind": "documentation",
                "text": "source-only-a-b-c-and-actual-current-native-reading-selection",
            }
        ],
        "invariants": [
            {
                "kind": "documentation",
                "text": "complete-family-correctness-preserves-original-identity-and-no-output-coverage",
            }
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "every-eligible-complete-reading-in-frozen-source-population",
        },
        "outcomes": ["success"],
        "precision_description": "strict-complete-family-source-and-evidence-reading",
        "dependencies": [],
        "effects": [],
        "parameters": {},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "protected-complete-reading-grading-without-public-policy-authority",
        "binding": {
            "operator": "all",
            "children": [
                {
                    "operator": "scan",
                    "roles": ["reference_a", "reference_b", "adjudication", "specification"],
                },
                {"operator": "collection", "roles": ["prediction"], "collection": "set"},
                {"operator": "collection", "roles": ["sources"], "collection": "set"},
            ],
        },
        "opaque": [
            {
                "reference": "corpus_structure.evaluate.declared_record_policy.execute_grade_profile",
                "contract": "record-policy/computation-assets",
                "role": "current-complete-family-record-grading",
            }
        ],
        "assets": [
            {
                "reference": "record-policy-computation",
                "contract": "record-policy/computation-assets",
                "role": "exact-record-grading-source-and-domain-contracts",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(
        self,
        sources: tuple[dict, ...],
        reference_a: dict,
        reference_b: dict,
        adjudication: dict,
        prediction: tuple[dict, ...],
        specification: dict,
    ) -> dict:
        return execute_grade_profile(
            self, sources, reference_a, reference_b, adjudication, prediction, specification
        )

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.evaluate.declared_record_policy import acquire_grade_port

        return acquire_grade_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )
