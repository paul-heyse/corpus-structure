"""Independent declaration syntax over exact canonical and HanLP products."""

from typing import ClassVar

from corpus_structure.semantic.declaration_products import execute_declaration_profile


class DeclarationSyntaxOperation:
    __data_operation__: ClassVar[dict] = {
        "validity_family": ["none"],
        "id": "text.declaration_syntax/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {
            "id": "original-source-view",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "subject-population",
        "context": ["original-source", "selected-scope", "exact-canonical-and-hanlp-products"],
        "entrypoints": ["run"],
        "reference_targets": [
            {
                "output_role": "result",
                "path": "/term_support/*/references/*",
                "input_role": "hanlp",
                "variant": "partition-item",
                "collection": "rows",
            }
        ],
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
                    "source": "original-source",
                    "coverage": {"role": "source", "description": "selected-scope"},
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
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
                    "source": "original-source",
                    "coverage": {"role": "canonical", "description": "selected-scope"},
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                },
            },
            {
                "name": "hanlp",
                "parameter": "hanlp",
                "kind": "https://corpus-structure.dev/semantic/data-operation-hanlp/DdoHanlpInventory",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "original-source",
                    "coverage": {"role": "hanlp", "description": "selected-scope"},
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoDeclarationSyntaxProduct",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [
            {"kind": "documentation", "text": "actual-canonical-sentences-and-hanlp-native-heads"}
        ],
        "invariants": [
            {"kind": "documentation", "text": "no-reinference"},
            {"kind": "documentation", "text": "exact-native-source-positions"},
            {"kind": "documentation", "text": "no-private-downstream-declaration-recognizer"},
            {"kind": "documentation", "text": "missing-support-is-unknown-not-empty"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-canonical-sentence-population",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "original-native-half-open-extents",
        "dependencies": [
            "segment.sentences/canonical-projection",
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
        "behavior": "retain-shared-declaration-syntax-from-actual-canonical-and-hanlp-facts",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["source", "canonical", "hanlp"]},
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source",
                "input_role": "source",
                "comparisons": [
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
                        "output_field": "document_subject",
                        "input": {
                            "role": "source",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document_subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection",
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
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.declaration_products.execute_declaration_profile",
                "contract": "declarations/profile-assets",
                "role": "native-declaration-syntax-kernel",
            }
        ],
        "assets": [
            {
                "reference": "declaration-profile",
                "contract": "declarations/profile-assets",
                "role": "original-declaration-kernel-and-custody",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.declaration_products import resolve_declaration_port

        return resolve_declaration_port(
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

    def run(self, source: dict, canonical: dict, hanlp: dict) -> dict:
        return execute_declaration_profile(self, source, canonical, hanlp)
