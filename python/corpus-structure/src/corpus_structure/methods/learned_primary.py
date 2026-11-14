"""Owned declared learned-provider producers on exact original source contexts."""

from typing import ClassVar

from corpus_structure.semantic.construction_products import CharacterizationSnapshot
from corpus_structure.semantic.contextual_native_products import execute_contextual_native
from corpus_structure.semantic.learned_primary import (
    LearnedPrimaryProducts,
    execute_learned_primary,
)
from corpus_structure.semantic.sentence_products import SourceAnnotations
from corpus_structure.semantic.source_products import FrozenNativeSource


class MaverickPrimaryOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.maverick/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "source",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
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
                    "source": "original-source",
                    "coverage": "selected-scope",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoMaverickObservations",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
            {
                "name": "candidates",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {},
        "dependencies": ["segment.sentences/source-native"],
        "effects": [],
        "applicability": ["actual-original-source-blocks", "frozen-qualified-native-provider"],
        "invariants": [
            "private-uncalibrated-candidates",
            "exact-original-source-coordinates",
            "no-score-authority-upgrade",
            "raw-native-labels-and-question-populations",
        ],
        "coverage": "complete-original-selected-blocks-with-explicit-limitations",
        "outcomes": ["success", "failed"],
        "precision": "unchanged-native-model-and-original-mapping-policy",
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "native-residency-borrow",
        },
        "behavior": "retain actual maverick observations and source-bound private candidates through the "
        "invocation shared provider lanes",
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "scan", "roles": ["annotations"]},
            ],
        },
        "opaque": [
            {
                "reference": "corpus_structure.semantic.learned_primary.execute_learned_primary",
                "contract": "learned/profile-assets",
                "role": "owned-native-provider-plan",
            },
            {
                "reference": "corpus_structure.semantic.learned_primary.LearnedPrimaryProducts",
                "contract": "learned/profile-assets",
                "role": "typed-native-observations-and-private-candidates",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "learned/profile-assets",
                "role": "exact-original-source",
            },
            {
                "reference": "corpus_structure.semantic.sentence_products.SourceAnnotations",
                "contract": "learned/profile-assets",
                "role": "actual-selected-annotations",
            },
        ],
        "assets": [
            {
                "reference": "maverick-native-profile",
                "contract": "learned/profile-assets",
                "role": "native-policy-source-mapping-and-private-projection",
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
            },
            {
                "output_role": "candidates",
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
            },
            {
                "output_role": "candidates",
                "records": "/members/*/body/pin",
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
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.learned_primary import resolve_learned_primary_port

        return resolve_learned_primary_port(
            prepared,
            model,
            operation,
            family="maverick",
            provider="maverick",
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, binding, execution_owner, check_active):
        self.profile, self.binding, self.execution_owner, self.check_active = (
            profile,
            binding,
            execution_owner,
            check_active,
        )

    def run(
        self, source: FrozenNativeSource, annotations: SourceAnnotations
    ) -> LearnedPrimaryProducts:
        return execute_learned_primary(self, source, annotations)


class DipoPrimaryOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.dipo/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "source",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoDipoObservations",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
            {
                "name": "candidates",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {},
        "dependencies": [],
        "effects": [],
        "applicability": ["actual-original-source-blocks", "frozen-qualified-native-provider"],
        "invariants": [
            "private-uncalibrated-candidates",
            "exact-original-source-coordinates",
            "no-score-authority-upgrade",
            "raw-native-labels-and-question-populations",
        ],
        "coverage": "complete-original-selected-blocks-with-explicit-limitations",
        "outcomes": ["success", "failed"],
        "precision": "unchanged-native-model-and-original-mapping-policy",
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "native-residency-borrow",
        },
        "behavior": "retain actual dipo observations and source-bound private candidates through the "
        "invocation shared provider lanes",
        "binding": {"operator": "all", "children": [{"operator": "scan", "roles": ["source"]}]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.learned_primary.execute_learned_primary",
                "contract": "learned/profile-assets",
                "role": "owned-native-provider-plan",
            },
            {
                "reference": "corpus_structure.semantic.learned_primary.LearnedPrimaryProducts",
                "contract": "learned/profile-assets",
                "role": "typed-native-observations-and-private-candidates",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "learned/profile-assets",
                "role": "exact-original-source",
            },
        ],
        "assets": [
            {
                "reference": "dipo-native-profile",
                "contract": "learned/profile-assets",
                "role": "native-policy-source-mapping-and-private-projection",
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
            },
            {
                "output_role": "candidates",
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
            },
            {
                "output_role": "candidates",
                "records": "/members/*/body/pin",
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
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.learned_primary import resolve_learned_primary_port

        return resolve_learned_primary_port(
            prepared,
            model,
            operation,
            family="dipo",
            provider="dipo",
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, binding, execution_owner, check_active):
        self.profile, self.binding, self.execution_owner, self.check_active = (
            profile,
            binding,
            execution_owner,
            check_active,
        )

    def run(self, source: FrozenNativeSource) -> LearnedPrimaryProducts:
        return execute_learned_primary(self, source)


class D1SourcePrimaryOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.d1_source/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "source",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoD1SourceObservations",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
            {
                "name": "candidates",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {},
        "dependencies": [],
        "effects": [],
        "applicability": ["actual-original-source-blocks", "frozen-qualified-native-provider"],
        "invariants": [
            "private-uncalibrated-candidates",
            "exact-original-source-coordinates",
            "no-score-authority-upgrade",
            "raw-native-labels-and-question-populations",
        ],
        "coverage": "complete-original-selected-blocks-with-explicit-limitations",
        "outcomes": ["success", "failed"],
        "precision": "unchanged-native-model-and-original-mapping-policy",
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "native-residency-borrow",
        },
        "behavior": "retain actual d1 observations and source-bound private candidates through the invocation "
        "shared provider lanes",
        "binding": {"operator": "all", "children": [{"operator": "scan", "roles": ["source"]}]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.learned_primary.execute_learned_primary",
                "contract": "learned/profile-assets",
                "role": "owned-native-provider-plan",
            },
            {
                "reference": "corpus_structure.semantic.learned_primary.LearnedPrimaryProducts",
                "contract": "learned/profile-assets",
                "role": "typed-native-observations-and-private-candidates",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "learned/profile-assets",
                "role": "exact-original-source",
            },
        ],
        "assets": [
            {
                "reference": "d1_source-native-profile",
                "contract": "learned/profile-assets",
                "role": "native-policy-source-mapping-and-private-projection",
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
            },
            {
                "output_role": "candidates",
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
            },
            {
                "output_role": "candidates",
                "records": "/members/*/body/pin",
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
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.learned_primary import resolve_learned_primary_port

        return resolve_learned_primary_port(
            prepared,
            model,
            operation,
            family="d1_source",
            provider="d1",
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, binding, execution_owner, check_active):
        self.profile, self.binding, self.execution_owner, self.check_active = (
            profile,
            binding,
            execution_owner,
            check_active,
        )

    def run(self, source: FrozenNativeSource) -> LearnedPrimaryProducts:
        return execute_learned_primary(self, source)


class D1CandidatesPrimaryOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.d1_candidates/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "source",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "formal",
                "parameter": "formal",
                "kind": "https://corpus-structure.dev/semantic/data-operation-characterization/DdoFormalProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "original-source",
                    "coverage": "selected-scope",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "constructions",
                "parameter": "constructions",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoConstructionProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "original-source",
                    "coverage": "selected-scope",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "contextual",
                "parameter": "contextual",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoContextualNativeProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "original-source",
                    "coverage": "selected-scope",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoD1CandidatesObservations",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
            {
                "name": "candidates",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {},
        "dependencies": [
            "text.formal_evidence/source-native",
            "text.constructions/source-native",
            "text.contextual_native/source-native",
        ],
        "effects": [],
        "applicability": ["actual-original-source-blocks", "frozen-qualified-native-provider"],
        "invariants": [
            "private-uncalibrated-candidates",
            "exact-original-source-coordinates",
            "no-score-authority-upgrade",
            "raw-native-labels-and-question-populations",
        ],
        "coverage": "complete-original-selected-blocks-with-explicit-limitations",
        "outcomes": ["success", "failed"],
        "precision": "unchanged-native-model-and-original-mapping-policy",
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "native-residency-borrow",
        },
        "behavior": "retain actual d1 observations and source-bound private candidates through the invocation "
        "shared provider lanes",
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "scan", "roles": ["formal"]},
                {"operator": "scan", "roles": ["constructions"]},
                {"operator": "scan", "roles": ["contextual"]},
            ],
        },
        "opaque": [
            {
                "reference": "corpus_structure.semantic.learned_primary.execute_learned_primary",
                "contract": "learned/profile-assets",
                "role": "owned-native-provider-plan",
            },
            {
                "reference": "corpus_structure.semantic.learned_primary.LearnedPrimaryProducts",
                "contract": "learned/profile-assets",
                "role": "typed-native-observations-and-private-candidates",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "learned/profile-assets",
                "role": "exact-original-source",
            },
            {
                "reference": "corpus_structure.semantic.construction_products.CharacterizationSnapshot",
                "contract": "learned/profile-assets",
                "role": "actual-selected-formal",
            },
            {
                "reference": "corpus_structure.semantic.construction_products.CharacterizationSnapshot",
                "contract": "learned/profile-assets",
                "role": "actual-selected-constructions",
            },
            {
                "reference": "corpus_structure.semantic.construction_products.CharacterizationSnapshot",
                "contract": "learned/profile-assets",
                "role": "actual-selected-contextual",
            },
        ],
        "assets": [
            {
                "reference": "d1_candidates-native-profile",
                "contract": "learned/profile-assets",
                "role": "native-policy-source-mapping-and-private-projection",
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
            },
            {
                "output_role": "candidates",
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
            },
            {
                "output_role": "candidates",
                "records": "/members/*/body/pin",
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
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.learned_primary import resolve_learned_primary_port

        return resolve_learned_primary_port(
            prepared,
            model,
            operation,
            family="d1_candidates",
            provider="d1",
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, binding, execution_owner, check_active):
        self.profile, self.binding, self.execution_owner, self.check_active = (
            profile,
            binding,
            execution_owner,
            check_active,
        )

    def run(
        self,
        source: FrozenNativeSource,
        formal: CharacterizationSnapshot,
        constructions: CharacterizationSnapshot,
        contextual: CharacterizationSnapshot,
    ) -> LearnedPrimaryProducts:
        return execute_learned_primary(self, source, None, formal, constructions, contextual)


class GlinerCuesPrimaryOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.gliner_cues/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "source",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoGlinerCuesObservations",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
            {
                "name": "candidates",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {},
        "dependencies": [],
        "effects": [],
        "applicability": ["actual-original-source-blocks", "frozen-qualified-native-provider"],
        "invariants": [
            "private-uncalibrated-candidates",
            "exact-original-source-coordinates",
            "no-score-authority-upgrade",
            "raw-native-labels-and-question-populations",
        ],
        "coverage": "complete-original-selected-blocks-with-explicit-limitations",
        "outcomes": ["success", "failed"],
        "precision": "unchanged-native-model-and-original-mapping-policy",
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "native-residency-borrow",
        },
        "behavior": "retain actual gliner observations and source-bound private candidates through the "
        "invocation shared provider lanes",
        "binding": {"operator": "all", "children": [{"operator": "scan", "roles": ["source"]}]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.learned_primary.execute_learned_primary",
                "contract": "learned/profile-assets",
                "role": "owned-native-provider-plan",
            },
            {
                "reference": "corpus_structure.semantic.learned_primary.LearnedPrimaryProducts",
                "contract": "learned/profile-assets",
                "role": "typed-native-observations-and-private-candidates",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "learned/profile-assets",
                "role": "exact-original-source",
            },
        ],
        "assets": [
            {
                "reference": "gliner_cues-native-profile",
                "contract": "learned/profile-assets",
                "role": "native-policy-source-mapping-and-private-projection",
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
            },
            {
                "output_role": "candidates",
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
            },
            {
                "output_role": "candidates",
                "records": "/members/*/body/pin",
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
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.learned_primary import resolve_learned_primary_port

        return resolve_learned_primary_port(
            prepared,
            model,
            operation,
            family="gliner_cues",
            provider="gliner",
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, binding, execution_owner, check_active):
        self.profile, self.binding, self.execution_owner, self.check_active = (
            profile,
            binding,
            execution_owner,
            check_active,
        )

    def run(self, source: FrozenNativeSource) -> LearnedPrimaryProducts:
        return execute_learned_primary(self, source)


class GlinerFunctionPrimaryOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.gliner_function/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "source",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoGlinerFunctionObservations",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
            {
                "name": "candidates",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {},
        "dependencies": [],
        "effects": [],
        "applicability": ["actual-original-source-blocks", "frozen-qualified-native-provider"],
        "invariants": [
            "private-uncalibrated-candidates",
            "exact-original-source-coordinates",
            "no-score-authority-upgrade",
            "raw-native-labels-and-question-populations",
        ],
        "coverage": "complete-original-selected-blocks-with-explicit-limitations",
        "outcomes": ["success", "failed"],
        "precision": "unchanged-native-model-and-original-mapping-policy",
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "native-residency-borrow",
        },
        "behavior": "retain actual gliner observations and source-bound private candidates through the "
        "invocation shared provider lanes",
        "binding": {"operator": "all", "children": [{"operator": "scan", "roles": ["source"]}]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.learned_primary.execute_learned_primary",
                "contract": "learned/profile-assets",
                "role": "owned-native-provider-plan",
            },
            {
                "reference": "corpus_structure.semantic.learned_primary.LearnedPrimaryProducts",
                "contract": "learned/profile-assets",
                "role": "typed-native-observations-and-private-candidates",
            },
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "learned/profile-assets",
                "role": "exact-original-source",
            },
        ],
        "assets": [
            {
                "reference": "gliner_function-native-profile",
                "contract": "learned/profile-assets",
                "role": "native-policy-source-mapping-and-private-projection",
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
            },
            {
                "output_role": "candidates",
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
            },
            {
                "output_role": "candidates",
                "records": "/members/*/body/pin",
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
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.learned_primary import resolve_learned_primary_port

        return resolve_learned_primary_port(
            prepared,
            model,
            operation,
            family="gliner_function",
            provider="gliner",
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, binding, execution_owner, check_active):
        self.profile, self.binding, self.execution_owner, self.check_active = (
            profile,
            binding,
            execution_owner,
            check_active,
        )

    def run(self, source: FrozenNativeSource) -> LearnedPrimaryProducts:
        return execute_learned_primary(self, source)


class ContextualNativePrimaryOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "text.contextual_native/source-native",
        "profile": "derivation",
        "subject": "original-source-view",
        "context": ["original-source", "selected-scope"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "source",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "source",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                    "source": "original-source",
                    "coverage": "selected-scope",
                },
            },
            {
                "name": "formal",
                "parameter": "formal",
                "kind": "https://corpus-structure.dev/semantic/data-operation-characterization/DdoFormalProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "original-source",
                    "coverage": "selected-scope",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "constructions",
                "parameter": "constructions",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoConstructionProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "original-source",
                    "coverage": "selected-scope",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "maverick",
                "parameter": "maverick",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoMaverickObservations",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "original-source",
                    "coverage": "selected-scope",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "dipo",
                "parameter": "dipo",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoDipoObservations",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "original-source",
                    "coverage": "selected-scope",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-learned/DdoContextualNativeProduct",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {},
        "dependencies": [
            "text.formal_evidence/source-native",
            "text.constructions/source-native",
            "text.maverick/source-native",
            "text.dipo/source-native",
        ],
        "effects": [],
        "applicability": ["actual-original-source-blocks", "frozen-qualified-native-provider"],
        "invariants": [
            "private-uncalibrated-candidates",
            "exact-original-source-coordinates",
            "no-score-authority-upgrade",
            "raw-native-labels-and-question-populations",
        ],
        "coverage": "complete-original-selected-blocks-with-explicit-limitations",
        "outcomes": ["success", "failed"],
        "precision": "unchanged-native-model-and-original-mapping-policy",
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "native-residency-borrow",
        },
        "behavior": "derive original-addressed contextual hypotheses from the exact selected actual native "
        "observations without repeated provider inference",
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["source"]},
                {"operator": "scan", "roles": ["formal"]},
                {"operator": "scan", "roles": ["constructions"]},
                {"operator": "scan", "roles": ["maverick"]},
                {"operator": "scan", "roles": ["dipo"]},
            ],
        },
        "opaque": [
            {
                "reference": "corpus_structure.semantic.source_products.FrozenNativeSource",
                "contract": "learned/profile-assets",
                "role": "exact-original-source",
            },
            {
                "reference": "corpus_structure.semantic.construction_products.CharacterizationSnapshot",
                "contract": "learned/profile-assets",
                "role": "actual-selected-formal",
            },
            {
                "reference": "corpus_structure.semantic.construction_products.CharacterizationSnapshot",
                "contract": "learned/profile-assets",
                "role": "actual-selected-constructions",
            },
            {
                "reference": "corpus_structure.semantic.construction_products.CharacterizationSnapshot",
                "contract": "learned/profile-assets",
                "role": "actual-selected-contextual",
            },
            {
                "reference": "corpus_structure.semantic.contextual_native_products.execute_contextual_native",
                "contract": "learned/profile-assets",
                "role": "original-native-contextual-hypothesis-kernel",
            },
        ],
        "assets": [
            {
                "reference": "d1_candidates-native-profile",
                "contract": "learned/profile-assets",
                "role": "native-policy-source-mapping-and-private-projection",
            }
        ],
        "output_witnesses": [],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_native_products import (
            resolve_contextual_native_port,
        )

        return resolve_contextual_native_port(
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

    def run(
        self,
        source: FrozenNativeSource,
        formal: CharacterizationSnapshot,
        constructions: CharacterizationSnapshot,
        maverick: dict,
        dipo: dict,
    ) -> dict:
        return execute_contextual_native(self, source, formal, constructions, maverick, dipo)
