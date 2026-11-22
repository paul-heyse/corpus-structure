"""Declared local definition-chain selection over exact primary products."""

from typing import ClassVar

from corpus_structure.semantic.definition_products import execute_definition_declaration


class DefinitionDeclarationOperation:
    __data_operation__: ClassVar[dict] = {
        "validity_family": ["definition"],
        "id": "structure.definition_declaration_components/declared",
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
                    "coverage": {"role": "source", "description": "exact-selected-source"},
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
                "collection": "set",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "syntax", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:structural:DeclaredSyntaxDefinitionComponentsReport",
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
                "text": "exact-positioned-primary-declaration-syntax-and-native-HanLP-premises",
            }
        ],
        "invariants": [
            {"kind": "documentation", "text": "no-downstream-language-recognition"},
            {"kind": "documentation", "text": "semantic-product-member-references"},
            {"kind": "documentation", "text": "three-distinct-characterized-sentences"},
            {"kind": "documentation", "text": "missing-native-premise-is-not-empty"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-local-declaration-passage",
        },
        "outcomes": ["success"],
        "precision_description": "original-native-half-open-extents",
        "dependencies": [
            "text.declaration_syntax/source-native",
        ],
        "reference_targets": [
            {
                "output_role": "result",
                "path": "/syntax_support/*/target",
                "input_role": "syntax",
                "variant": "member",
                "occurrence_position": True,
            },
        ],
        "effects": [],
        "capabilities": {
            "cpu_receipts": 1,
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
                {"operator": "collection", "roles": ["syntax"], "collection": "set"},
            ],
        },
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/inputs/sources/*",
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
        start: int,
        end: int,
        passage_id: str,
        scope: str,
        effective_version: str,
        parent: str,
    ) -> dict:
        return execute_definition_declaration(
            self, source, syntax, start, end, passage_id, scope, effective_version, parent
        )
