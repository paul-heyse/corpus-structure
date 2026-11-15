"""Generic located definition components from separately retained native products."""

from typing import ClassVar

from corpus_structure.semantic.definition_component_products import (
    execute_named_definition_components,
)


class NamedDefinitionComponentsOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "structure.definition_named_components/declared",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {'id': 'original-source-view', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'subject-population',
        "context": ["original-source", "selected-scope", "paired-located-definition-products"],
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
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "constructions", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:structural:DeclaredDefinitionComponentsReport",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'actual-retained-native-named-bindings-and-primary-scope'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'no-downstream-language-recognition'},
            {'kind': 'documentation', 'text': 'exact-native-role-bindings'},
            {'kind': 'documentation', 'text': 'genuine-semantic-primary-witnesses'},
            {'kind': 'documentation', 'text': 'missing-coverage-is-not-empty'},
        ],
        "coverage": {"binding": "self", "result_owners": [{"kind":'implementation',"reference":"self"}], "description": "actual-inspected-original-block-windows"},
        "outcomes": ["success"],
        "precision_description": "original-native-half-open-extents",
        "dependencies": ["segment.sentences/source-native", "text.constructions/source-native"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "project-original-named-rule-and-native-display-definition-components",
        "parameters": {},
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "scan", "roles": ["annotations"]},
                {"operator": "scan", "roles": ["constructions"]},
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
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": 'subject_definition',
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
                "input_role": "constructions",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": 'subject_definition',
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "constructions",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "constructions",
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
                "reference": "corpus_structure.semantic.definition_component_products.execute_named_definition_components",
                "contract": "definition-components/profile-assets",
                "role": "paired-native-components-reader",
            }
        ],
        "assets": [
            {
                "reference": "declared-definition-component-profile",
                "contract": "definition-components/profile-assets",
                "role": "original-decoder-and-explicit-source-closure",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.definition_component_products import (
            resolve_definition_components_port,
        )

        return resolve_definition_components_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, prepared, roles=(), context=None, check_active=lambda: None):
        self.prepared, self.roles, self.context, self.check_active = (
            prepared,
            roles,
            context,
            check_active,
        )

    def run(self, source: dict, annotations: dict, constructions: dict) -> dict:
        return execute_named_definition_components(self, source, annotations, constructions)
