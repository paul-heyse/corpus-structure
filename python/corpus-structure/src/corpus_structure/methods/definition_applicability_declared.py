"""Declared applicability from an exact native usage edge and definition carrier."""

from typing import ClassVar

from corpus_structure.semantic.definition_applicability_products import (
    execute_definition_applicability,
)


class DefinitionApplicabilityOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "structure.definition_applicability/declared",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {
            "id": "original-source-view",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "subject-population",
        "context": [
            "original-source",
            "selected-scope",
            "frozen-source-set",
            "authored-usage-passage",
            "selected-native-relationship",
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
                    "coverage": {"role": "source", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
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
                    "source": "frozen-source-set",
                    "coverage": {"role": "components", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                    "source_set": "definition-components",
                },
                "subject_target": "source-set",
            },
            {
                "name": "relationship",
                "parameter": "relationship",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualWitnessedRetrievalProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "definition-relationships",
                    "coverage": {"role": "relationship", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                },
                "subject_target": "source-set",
            },
            {
                "name": "result",
                "kind": "urn:corpus:structural:DeclaredDefinitionApplicabilityReport",
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
                "text": "exact-selected-usage-edge-and-separately-bound-native-definition-component",
            }
        ],
        "invariants": [
            {"kind": "documentation", "text": "exact-source-resolved-component-meaning"},
            {"kind": "documentation", "text": "every-proof-carrier-preserved"},
            {"kind": "documentation", "text": "no-target-or-usage-substitution"},
            {"kind": "documentation", "text": "unknown-transfer-premises-remain-unknown"},
            {"kind": "documentation", "text": "private-reading-does-not-grant-publication"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-usage-and-actual-native-component",
        },
        "outcomes": ["success"],
        "precision_description": "original-native-half-open-extents",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "derive-private-usage-applicability-from-exact-selected-native-relationship",
        "parameters": {
            "component_id": {},
            "decision_id": {},
            "edge_id": {},
            "usage_id": {},
            "start": {},
            "end": {},
            "scope": {"default": "selected"},
            "effective_version": {"default": ""},
            "parent": {"default": ""},
            "defining_occurrence": {"default": False},
        },
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "scan", "roles": ["components"]},
                {"operator": "scan", "roles": ["relationship"]},
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
                "records": "/relationship_input",
                "input_role": "relationship",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "relationship",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "relationship",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "relationship",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "relationship",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "relationship",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject_definition",
                        "input": {
                            "role": "relationship",
                            "projection": "selected-input",
                            "field": "subject_definition",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "relationship",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "relationship",
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
                "reference": "corpus_structure.semantic.definition_applicability_products.execute_definition_applicability",
                "contract": "definitions/profile-assets",
                "role": "same-exact-native-usage-compatibility-policy",
            }
        ],
        "assets": [
            {
                "reference": "declared-definition-products",
                "contract": "definitions/profile-assets",
                "role": "typed-primary-domain-projection",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.definition_products import resolve_definition_port

        return resolve_definition_port(
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
        components: dict,
        relationship: dict,
        component_id: str,
        decision_id: str,
        edge_id: str,
        usage_id: str,
        start: int,
        end: int,
        scope: str,
        effective_version: str,
        parent: str,
        defining_occurrence: bool,
    ) -> dict:
        return execute_definition_applicability(
            self,
            source,
            components,
            relationship,
            component_id=component_id,
            decision_id=decision_id,
            edge_id=edge_id,
            usage_id=usage_id,
            start=start,
            end=end,
            scope=scope,
            effective_version=effective_version,
            parent=parent,
            defining_occurrence=defining_occurrence,
        )
