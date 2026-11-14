"""Declared local definition-chain selection over exact primary products."""

from typing import ClassVar

from corpus_structure.semantic.definition_products import execute_definition_declaration


class DefinitionDeclarationOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "structure.definition_declaration_components/declared",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": [
            "original-source",
            "selected-scope",
            "authored-declaration-passage",
            "retained-native-premises",
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
                "name": "syntax",
                "parameter": "syntax",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoDeclarationSyntaxProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "exact-selected-source",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "hanlp",
                "parameter": "hanlp",
                "kind": "https://corpus-structure.dev/semantic/data-operation-hanlp/DdoHanlpInventory",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "sequence",
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
        "applicability": ["exact-positioned-primary-declaration-syntax-and-native-HanLP-premises"],
        "invariants": [
            "no-downstream-language-recognition",
            "semantic-product-member-references",
            "three-distinct-characterized-sentences",
            "missing-native-premise-is-not-empty",
        ],
        "coverage": "exact-selected-local-declaration-passage",
        "outcomes": ["success"],
        "precision": "original-native-half-open-extents",
        "dependencies": [
            "text.declaration_syntax/source-native",
            "text.hanlp_native/source-native",
        ],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "select-domain-declaration-chain-from-retained-primary-native-syntax",
        "parameters": {
            "start": {},
            "end": {},
            "passage_id": {},
            "scope": {"default": "selected"},
            "effective_version": {"default": ""},
            "parent": {"default": ""},
        },
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "collection", "roles": ["syntax"], "collection": "sequence"},
                {"operator": "collection", "roles": ["hanlp"], "collection": "sequence"},
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
                "input_role": "syntax",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "syntax",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "syntax",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "syntax",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "syntax",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "syntax",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "syntax",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "syntax",
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
                "reference": "corpus_structure.semantic.definition_products.execute_definition_declaration",
                "contract": "definitions/profile-assets",
                "role": "same-retained-native-declaration-domain-selection",
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
        syntax: tuple[dict, ...],
        hanlp: tuple[dict, ...],
        start: int,
        end: int,
        passage_id: str,
        scope: str,
        effective_version: str,
        parent: str,
    ) -> dict:
        return execute_definition_declaration(
            self, source, syntax, hanlp, start, end, passage_id, scope, effective_version, parent
        )
