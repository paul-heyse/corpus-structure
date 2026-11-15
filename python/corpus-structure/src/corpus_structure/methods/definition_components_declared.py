"""Generic located definition components from separately retained native products."""

from typing import ClassVar

from corpus_structure.semantic.definition_component_products import execute_definition_components


class DefinitionComponentsOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "structure.definition_components/declared",
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
                    "coverage": "exact-selected-source",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "observation",
                "parameter": "observation",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoGlinerDefinitionObservations",
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
                "name": "candidates",
                "parameter": "candidates",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoGlinerDefinitionCandidatesReport",
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
                "name": "result",
                "kind": "urn:corpus:structural:DeclaredDefinitionComponentsReport",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'actual-located-definition-GLiNER-observations-and-candidates'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'exact-paired-native-request-reply'},
            {'kind': 'documentation', 'text': 'independently-located-term-and-content'},
            {'kind': 'documentation', 'text': 'directed-attachments-only'},
            {'kind': 'documentation', 'text': 'semantic-product-member-references'},
            {'kind': 'documentation', 'text': 'partial-coverage-is-not-absence'},
        ],
        "coverage": "actual-inspected-original-block-windows",
        "outcomes": ["success"],
        "precision": "original-native-half-open-extents",
        "dependencies": ["text.gliner_definitions/source-native"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "project-authentic-located-definition-components-without-model-reexecution",
        "parameters": {},
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "scan", "roles": ["observation"]},
                {"operator": "scan", "roles": ["candidates"]},
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
                "input_role": "candidates",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "candidates",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "candidates",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "candidates",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "candidates",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "candidates",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "candidates",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "candidates",
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
                "reference": "corpus_structure.semantic.definition_component_products.execute_definition_components",
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

    def run(self, source: dict, observation: dict, candidates: dict) -> dict:
        return execute_definition_components(self, source, observation, candidates)
