"""Declared predicate evidence from actual source, annotation and primary products."""

from typing import ClassVar

from corpus_structure.semantic.predicate_products import execute_predicate_profile


class PredicateEvidenceOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "structure.predicate_evidence/declared",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {
            "id": "original-source-view",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "subject-population",
        "context": ["original-source", "selected-scope", "retained-primary-readings"],
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
                    "coverage": {"role": "source", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "annotations",
                "parameter": "annotations",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "annotations", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "constructions",
                "parameter": "constructions",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "constructions", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "formal",
                "parameter": "formal",
                "kind": "https://corpus-structure.dev/semantic/data-operation-characterization/DdoFormalProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "formal", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoPredicateInspectionReport",
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
                "text": "actual-native-annotations-and-retained-primary-source-readings",
            }
        ],
        "invariants": [
            {"kind": "documentation", "text": "original-relative-source-pins"},
            {"kind": "documentation", "text": "no-downstream-recognition"},
            {"kind": "documentation", "text": "private-proposals-only"},
            {"kind": "documentation", "text": "unavailable-inspection-is-not-empty"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-inspected-native-blocks-with-unavailable-coverage",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "original-native-half-open-extents",
        "dependencies": [
            "segment.sentences/source-native",
            "text.formal_evidence/source-native",
            "text.constructions/source-native",
        ],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "project-retained-primary-predicate-and-qualifier-evidence",
        "parameters": {},
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source", "annotations"]},
                {"operator": "collection", "roles": ["constructions"], "collection": "sequence"},
                {"operator": "collection", "roles": ["formal"], "collection": "sequence"},
            ],
        },
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source_pin",
                "input_role": "source",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_member",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "member",
                        },
                        "encoding": "value",
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
                        "output_field": "subject",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject_definition",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject_definition",
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
                    {
                        "output_field": "document",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/membership",
                        },
                        "encoding": "value",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/source_pin",
                "input_role": "source",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_member",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "member",
                        },
                        "encoding": "value",
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
                        "output_field": "subject",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject_definition",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject_definition",
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
                    {
                        "output_field": "document",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/membership",
                        },
                        "encoding": "value",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/members/*/body/pin",
                "input_role": "source",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_member",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "member",
                        },
                        "encoding": "value",
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
                        "output_field": "subject",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject_definition",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject_definition",
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
                    {
                        "output_field": "document",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/membership",
                        },
                        "encoding": "value",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/members/*/body/anchors/*/pin",
                "input_role": "source",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_member",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "member",
                        },
                        "encoding": "value",
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
                        "output_field": "subject",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject_definition",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject_definition",
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
                    {
                        "output_field": "document",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/membership",
                        },
                        "encoding": "value",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/coordinate_texts/*/pin",
                "input_role": "source",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_member",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "member",
                        },
                        "encoding": "value",
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
                        "output_field": "subject",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject_definition",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject_definition",
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
                    {
                        "output_field": "document",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/membership",
                        },
                        "encoding": "value",
                    },
                ],
            },
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.predicate_products.execute_predicate_profile",
                "contract": "predicates/profile-assets",
                "role": "retained-predicate-kernel",
            }
        ],
        "assets": [
            {
                "reference": "predicate-profile",
                "contract": "predicates/profile-assets",
                "role": "original-predicate-algorithms-and-source-custody",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.predicate_products import resolve_predicate_port

        return resolve_predicate_port(
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
        annotations: dict,
        constructions: tuple[dict, ...],
        formal: tuple[dict, ...],
    ) -> dict:
        return execute_predicate_profile(self, source, annotations, constructions, formal)
