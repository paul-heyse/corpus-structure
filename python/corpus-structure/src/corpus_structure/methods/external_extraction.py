"""Captured rich source packet preparation and mechanical placement owners."""

from typing import ClassVar

from corpus_structure.semantic.external_extraction import execute_rich_profile


class RichExtractionInputOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "prepare.external_extraction",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {'id': 'original-source-view', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'subject-population',
        "context": ["original-source", "rich-source-report-context"],
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
                    "coverage": "explicit-selected-rich-context",
                    "origins": ["computation"],
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
                    "coverage": "explicit-selected-rich-context",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "policy",
                "parameter": "policy",
                "kind": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPolicy",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "explicit-selected-rich-context",
                    "origins": ["authored"],
                    "identity_requirements": ["original-source"],
                },
            },
            {
                "name": "context_sources",
                "parameter": "context_sources",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "sequence",
                "presence": "optional",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "explicit-selected-rich-context",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
                "subject_field": "/source/document",
                "subject_target": "original-source",
            },
            {
                "name": "context_annotations",
                "parameter": "context_annotations",
                "kind": "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "sequence",
                "presence": "optional",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "explicit-selected-rich-context",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
                "subject_field": "/source/document",
                "subject_target": "original-source",
            },
            {
                "name": "scopes",
                "parameter": "scopes",
                "kind": "urn:corpus:math:DeclaredMathScopeProduct",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "sequence",
                "presence": "optional",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "explicit-selected-rich-context",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
                "subject_field": "/source/document",
                "subject_target": "original-source",
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'exact-authenticated-native-inputs'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'no-Reader-or-task-alias-authority'},
            {'kind': 'documentation', 'text': 'retain-rich-fields-and-source-placement'},
            {'kind': 'documentation', 'text': 'no-knowledge-admission'},
        ],
        "coverage": "complete-selected-input",
        "outcomes": ["success"],
        "precision": "mechanically-checked-source-report",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "existing rich external source packet and mechanical proposal placement",
        "parameters": {},
        "binding": {
            "operator": "scan",
            "roles": [
                "source",
                "annotations",
                "policy",
                "context_sources",
                "context_annotations",
                "scopes",
            ],
        },
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
                        "output_field": "source_member",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "member",
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
                        "output_field": "kind_contract",
                        "input": {
                            "role": "source",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "document",
                        "input": {
                            "role": "source",
                            "projection": "DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "source",
                            "projection": "DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "source",
                            "projection": "DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "source",
                            "projection": "DdoSelectedNativeSource",
                            "field": "/source/membership",
                        },
                        "encoding": "value",
                    },
                ],
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.external_extraction",
                "contract": "external-extraction/algorithm-assets",
                "role": "captured-packet-placement-and-reference-kernels",
            }
        ],
        "assets": [
            {
                "reference": "rich-source-report-kernels",
                "contract": "external-extraction/algorithm-assets",
                "role": "existing-decimal-reference-Cascade-and-original-relative-placement",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(
        self,
        source: dict,
        annotations: dict,
        policy: dict,
        context_sources: tuple[dict, ...],
        context_annotations: tuple[dict, ...],
        scopes: tuple[dict, ...],
    ) -> dict:
        return execute_rich_profile(
            self,
            {
                "source": source,
                "annotations": annotations,
                "policy": policy,
                "context_sources": context_sources,
                "context_annotations": context_annotations,
                "scopes": scopes,
            },
        )

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.external_extraction import resolve_rich_port

        return resolve_rich_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )


class RichExtractionPlacementOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "locate.external_extraction",
        "profile": "derivation",
        "subject": "original-source-view",
        "subject_definition": {'id': 'original-source-view', 'identifier_kind': 'string', 'scope': 'original-source'},
        "discovery_relation": 'subject-population',
        "context": ["original-source", "rich-source-report-context"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "packet",
                "parameter": "packet",
                "kind": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "explicit-selected-rich-context",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
                "subject_field": "/source_pin/subject",
            },
            {
                "name": "authored",
                "parameter": "authored",
                "kind": "https://corpus-structure.dev/semantic/agent/AgentAuthoredBatch",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "explicit-selected-rich-context",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoLocatedExternalExtraction",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{'kind': 'documentation', 'text': 'exact-authenticated-native-inputs'}],
        "invariants": [
            {'kind': 'documentation', 'text': 'no-Reader-or-task-alias-authority'},
            {'kind': 'documentation', 'text': 'retain-rich-fields-and-source-placement'},
            {'kind': 'documentation', 'text': 'no-knowledge-admission'},
        ],
        "coverage": "complete-selected-input",
        "outcomes": ["success"],
        "precision": "mechanically-checked-source-report",
        "dependencies": ["extract.rich_external"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "invocation-owned-cpu",
        },
        "behavior": "existing rich external source packet and mechanical proposal placement",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["packet", "authored"]},
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source_pin",
                "input_role": "packet",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": 'subject_definition',
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": '/source_pin/subject_definition',
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "document",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/projection_digest",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/membership",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/analyzed_scope_meaning",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/source_product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "packet",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket",
                            "field": "/source_pin/kind_contract",
                        },
                        "encoding": "value",
                    },
                ],
            }
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.external_extraction",
                "contract": "external-extraction/algorithm-assets",
                "role": "captured-packet-placement-and-reference-kernels",
            }
        ],
        "assets": [
            {
                "reference": "rich-source-report-kernels",
                "contract": "external-extraction/algorithm-assets",
                "role": "existing-decimal-reference-Cascade-and-original-relative-placement",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, packet: dict, authored: dict) -> dict:
        return execute_rich_profile(self, {"packet": packet, "authored": authored})

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.external_extraction import resolve_rich_port

        return resolve_rich_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )
