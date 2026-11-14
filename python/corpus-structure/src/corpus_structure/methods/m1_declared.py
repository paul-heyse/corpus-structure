"""Actual declared M1 producer; source selection stays on its governing binding."""

from collections.abc import Generator
from typing import ClassVar

from corpus_structure.methods.m1_source import M1CandidateProduct, M1GlinerReply, M1GlinerRequest
from corpus_structure.semantic.m1_products import execute_declared_m1


class M1SourceCandidatesOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "extract.m1_candidates",
        "profile": "derivation",
        "subject": "selected-native-source",
        "context": [
            "project",
            "original-source",
            "qualified-source-member",
            "complete-selected-context-population",
        ],
        "entrypoints": ["run"],
        "consumer_selection": "select_hydrated",
        "roles": [
            {
                "name": "primary",
                "parameter": "primary",
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
                    "coverage": "exact-selected-source",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "sources",
                "parameter": "sources",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "set",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": "complete-selected-context-population",
                    "identity_requirements": ["episode"],
                },
                "subject_field": "/source/document",
                "subject_target": "original-source",
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["exact-source-annotations-and-closed-bound-context-population"],
        "invariants": [
            "original-relative-source-pins",
            "one-cpu-coroutine-and-native-request-owner",
            "private-candidates-only",
            "complete-inspection-can-have-zero-candidates",
            "failed-provider-is-not-successful-empty-inspection",
        ],
        "coverage": "exact-inspected-regions-with-explicit-partial-or-unavailable-coverage",
        "outcomes": ["success", "failed"],
        "precision": "original-native-half-open-extents",
        "dependencies": ["source.selected_views/discovery", "segment.sentences/source-native"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "invocation-owned-cpu-coroutine-and-native-host",
        },
        "behavior": "one-private-candidate-inspection-report-including-empty-denominator; "
        "genuine-failure-has-no-report",
        "parameters": {},
        "binding": {
            "operator": "all",
            "children": [
                {
                    "operator": "forall",
                    "roles": ["primary"],
                    "population": "m1-primary-source",
                    "children": [{"operator": "all", "children": []}],
                },
                {"operator": "scan", "roles": ["annotations"]},
                {
                    "operator": "forall",
                    "roles": ["sources"],
                    "population": "m1-context-sources",
                    "children": [{"operator": "all", "children": []}],
                },
            ],
        },
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source_pin",
                "input_role": "primary",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_member",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "member",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                    {
                        "output_field": "document",
                        "input": {
                            "role": "primary",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "primary",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "primary",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "primary",
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
                "input_role": "sources",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_member",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "member",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                    {
                        "output_field": "document",
                        "input": {
                            "role": "sources",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "sources",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "sources",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "sources",
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
                "input_role": "primary",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_member",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "member",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "primary",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                    {
                        "output_field": "document",
                        "input": {
                            "role": "primary",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "primary",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "primary",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "primary",
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
                "input_role": "sources",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_member",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "member",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                    {
                        "output_field": "document",
                        "input": {
                            "role": "sources",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "sources",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "sources",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "sources",
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
                "input_role": "sources",
                "comparisons": [
                    {
                        "output_field": "source",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "source_product",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_member",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "member",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                    {
                        "output_field": "document",
                        "input": {
                            "role": "sources",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/document",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "projection_digest",
                        "input": {
                            "role": "sources",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/projection",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "section_pointer",
                        "input": {
                            "role": "sources",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                            "field": "/source/section_pointer",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "membership",
                        "input": {
                            "role": "sources",
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
                "reference": "collections.abc.Generator",
                "contract": "m1/profile-assets",
                "role": "typed-coroutine-return-shape",
            },
            {
                "reference": "corpus_structure.semantic.m1_products.execute_declared_m1",
                "contract": "m1/profile-assets",
                "role": "original-resumable-inspection-kernel",
            },
            {
                "reference": "corpus_structure.methods.m1_source.M1GlinerRequest",
                "contract": "m1/profile-assets",
                "role": "typed-coroutine-message",
            },
            {
                "reference": "corpus_structure.methods.m1_source.M1GlinerReply",
                "contract": "m1/profile-assets",
                "role": "typed-coroutine-message",
            },
            {
                "reference": "corpus_structure.methods.m1_source.M1CandidateProduct",
                "contract": "m1/profile-assets",
                "role": "typed-coroutine-message",
            },
        ],
        "assets": [
            {
                "reference": "m1-inspection-configuration-and-algorithm",
                "contract": "m1/profile-assets",
                "role": "candidate-inspection-profile",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.m1_products import resolve_m1_port

        return resolve_m1_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile):
        self.profile = profile

    def select_hydrated(self, inputs):
        if inputs.selection.binding.operation != self.__data_operation__["id"]:
            raise ValueError("M1 selection belongs to another governing producer")
        return inputs.one("primary"), inputs.one("annotations"), inputs.role("sources")

    def run(
        self, primary: dict, annotations: dict, sources: tuple[dict, ...]
    ) -> Generator[M1GlinerRequest, M1GlinerReply, M1CandidateProduct]:
        return (yield from execute_declared_m1(self, primary, annotations, sources))
