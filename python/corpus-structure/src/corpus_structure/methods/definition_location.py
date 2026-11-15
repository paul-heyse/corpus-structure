"""Locate genuine retained definition components and model roles without recognition."""

from typing import ClassVar

from corpus_structure.semantic.definition_location_products import execute_definition_location


class DefinitionLocationOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "locate.definition_terms/declared",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {
            "id": "original-source-view",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "subject-population",
        "context": ["original-source", "selected-scope", "retained-definition-components"],
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
                    "origins": ["computation", "original-source"],
                    "identity_requirements": ["episode", "original-source"],
                },
            },
            {
                "name": "components",
                "parameter": "components",
                "kind": "urn:corpus:structural:DeclaredDefinitionComponentsReport",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "components", "description": "exact-selected-source"},
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "selection",
                "parameter": "selection",
                "kind": "https://corpus-structure.dev/semantic/data-operation-definition-location/DdoDefinitionLocationSelection",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "selection", "description": "exact-selected-source"},
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-definition-location/DdoDefinitionLocationReport",
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
                "text": "exact-retained-definition-component-or-independent-role",
            }
        ],
        "invariants": [
            {"kind": "documentation", "text": "no-new-recognition"},
            {
                "kind": "documentation",
                "text": "genuine-native-source-and-semantic-producer-address",
            },
            {
                "kind": "documentation",
                "text": "term-content-and-directed-attachment-identities-remain-distinct",
            },
            {"kind": "documentation", "text": "private-located-proposals-only"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-explicit-component-or-role-selection",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "original-native-half-open-extents",
        "dependencies": [],
        "effects": [],
        "parameters": {},
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "project-exact-retained-definition-spans-into-native-source-occurrences",
        "binding": {"operator": "scan", "roles": ["source", "components", "selection"]},
        "assets": [
            {
                "reference": "definition-location/profile-assets",
                "contract": "definition-location/profile-assets",
                "role": "captured-original-anchor-and-retained-projection-kernels",
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.definition_location_products.execute_definition_location",
                "contract": "definition-location/profile-assets",
                "role": "owned-cpu-retained-location-projection",
            }
        ],
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source_pin",
                "input_role": "source",
                "comparisons": [
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
                        "output_field": "source",
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
                        "output_field": "subject_definition",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "subject_definition",
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
                "records": "/components_input",
                "input_role": "components",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "components",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "components",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "components",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "components",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "components",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject_definition",
                        "input": {
                            "role": "components",
                            "projection": "selected-input",
                            "field": "subject_definition",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "components",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "components",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/selection_input",
                "input_role": "selection",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "selection",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "selection",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "selection",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "selection",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "selection",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject_definition",
                        "input": {
                            "role": "selection",
                            "projection": "selected-input",
                            "field": "subject_definition",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "selection",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "selection",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
        ],
    }

    def __init__(self, inputs):
        self.inputs = inputs

    def run(self, source: dict, components: dict, selection: dict) -> dict:
        return execute_definition_location(self, source, components, selection)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.definition_location_products import (
            resolve_definition_location_port,
        )

        return resolve_definition_location_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )
