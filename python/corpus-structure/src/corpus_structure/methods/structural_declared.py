"""Original declared structural computations over explicitly pinned retained inputs."""

from __future__ import annotations

from typing import Any, ClassVar

from corpus_structure.semantic.declared_structural_calls import (
    execute_comparison,
    execute_condition,
)


class DeclaredStructuralComparison:
    __data_operation__: ClassVar[dict[str, Any]] = {
        "id": "structure.compare/declared",
        "profile": "derivation",
        "subject": "actual-focus-source",
        "context": [
            "project",
            "subject",
            "original-source",
            "analyzed-scope",
            "frozen-source-set",
            "authored-passage-selection",
        ],
        "entrypoints": ["run"],
        "consumer_selection": "select_hydrated",
        "roles": [
            {
                "name": "sources",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": 2,
                "collection": "set",
                "presence": "required",
                "parameter": "sources",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "source": "frozen-source-set",
                    "source_set": "structural-sources",
                    "coverage": "exact-selected-source-and-context",
                },
            },
            {
                "name": "reports",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "direction": "input",
                "minimum": 1,
                "maximum": 2,
                "collection": "set",
                "presence": "required",
                "parameter": "reports",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "source": "frozen-source-set",
                    "source_set": "structural-reports",
                    "coverage": "exact-selected-source-and-context",
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:structural:DeclaredComparisonReport",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["exact-native-source-and-retained-complete-predicate-inspection"],
        "invariants": [
            "source-pins-do-not-alias-task-or-view-ids",
            "authored-bounds-select-actual-source-text",
            "missing-inspection-is-not-empty",
            "private-proposal-is-not-independent-semantic-support",
        ],
        "coverage": "exact-selected-passages-and-retained-report-inventory",
        "outcomes": ["success"],
        "precision": "original-native-half-open-extents",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "schema",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "compose-explicit-source-supported-structural-reading-v1",
        "parameters": {
            "question": {"default": "Compare the exact selected retained readings."},
            "scope": {"default": "selected"},
            "inventory_id": {"default": "explicit-native-inputs"},
            "policy_id": {"default": "exact-retained-structural-v1"},
            "left_start": {},
            "left_end": {},
            "right_start": {},
            "right_end": {},
            "left_passage_id": {},
            "right_passage_id": {},
            "left_reading": {},
            "right_reading": {},
            "left_version": {"default": ""},
            "right_version": {"default": ""},
            "left_parent": {"default": ""},
            "right_parent": {"default": ""},
            "left_source_reference": {},
            "right_source_reference": {},
            "left_report_reference": {},
            "right_report_reference": {},
        },
        "binding": {
            "operator": "all",
            "children": [{"operator": "scan", "roles": ["sources", "reports"]}],
        },
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/sources_input/*",
                "input_role": "sources",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
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
                        "output_field": "project_id",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "project_id",
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
                ],
            },
            {
                "output_role": "result",
                "records": "/reports_input/*",
                "input_role": "reports",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "reports",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "reports",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "reports",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "reports",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "reports",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "reports",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "reports",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
            {
                "output_role": "result",
                "records": "/inputs/sources/*",
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
                        "output_field": "kind_contract",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "kind_contract",
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
                        "output_field": "subject",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "subject",
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
                "reference": "corpus_structure.semantic.declared_structural_calls.execute_comparison",
                "contract": "structural/call-assets",
                "role": "original-structural-kernel",
            }
        ],
        "assets": [
            {
                "reference": "structural/call-assets",
                "contract": "structural/call-assets",
                "role": "actual-structural-kernels-and-dto-shapes",
            }
        ],
    }

    def __init__(self, profile):
        self.profile = profile

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.declared_structural_calls import (
            comparison_kernel,
            resolve_structural_call,
        )

        return resolve_structural_call(
            prepared,
            model,
            operation,
            receiver=DeclaredStructuralComparison(None),
            kernel=comparison_kernel,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def select_hydrated(self, inputs):
        return inputs.role("sources"), inputs.role("reports")

    def run(
        self,
        sources: tuple[dict, ...],
        reports: tuple[dict, ...],
        left_source_reference: str,
        right_source_reference: str,
        left_report_reference: str,
        right_report_reference: str,
        left_start: int,
        left_end: int,
        right_start: int,
        right_end: int,
        left_passage_id: str,
        right_passage_id: str,
        left_reading: str,
        right_reading: str,
        question: str = "Compare the exact selected retained readings.",
        scope: str = "selected",
        inventory_id: str = "explicit-native-inputs",
        policy_id: str = "exact-retained-structural-v1",
        left_version: str = "",
        right_version: str = "",
        left_parent: str = "",
        right_parent: str = "",
    ) -> dict:
        return execute_comparison(
            self,
            sources,
            reports,
            left_source_reference=left_source_reference,
            right_source_reference=right_source_reference,
            left_report_reference=left_report_reference,
            right_report_reference=right_report_reference,
            left_start=left_start,
            left_end=left_end,
            right_start=right_start,
            right_end=right_end,
            left_passage_id=left_passage_id,
            right_passage_id=right_passage_id,
            left_reading=left_reading,
            right_reading=right_reading,
            question=question,
            scope=scope,
            inventory_id=inventory_id,
            policy_id=policy_id,
            left_version=left_version,
            right_version=right_version,
            left_parent=left_parent,
            right_parent=right_parent,
        )


class DeclaredConditionQualification:
    __data_operation__: ClassVar[dict[str, Any]] = {
        "id": "structure.condition_qualification/declared",
        "profile": "derivation",
        "subject": "actual-focus-source",
        "context": [
            "project",
            "subject",
            "original-source",
            "analyzed-scope",
            "frozen-source-set",
            "authored-passage-selection",
        ],
        "entrypoints": ["run"],
        "consumer_selection": "select_hydrated",
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
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "source": "frozen-source-set",
                    "source_set": "structural-source",
                    "coverage": "exact-selected-source-and-context",
                },
            },
            {
                "name": "report",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "report",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "identity_requirements": ["episode"],
                    "source": "frozen-source-set",
                    "source_set": "structural-report",
                    "coverage": "exact-selected-source-and-context",
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:structural:DeclaredConditionReport",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["exact-native-source-and-retained-complete-predicate-inspection"],
        "invariants": [
            "source-pins-do-not-alias-task-or-view-ids",
            "authored-bounds-select-actual-source-text",
            "missing-inspection-is-not-empty",
            "private-proposal-is-not-independent-semantic-support",
        ],
        "coverage": "exact-selected-passages-and-retained-report-inventory",
        "outcomes": ["success"],
        "precision": "original-native-half-open-extents",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "schema",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "compose-explicit-source-supported-structural-reading-v1",
        "parameters": {
            "question": {"default": "Compare the exact selected retained readings."},
            "scope": {"default": "selected"},
            "inventory_id": {"default": "explicit-native-inputs"},
            "policy_id": {"default": "exact-retained-structural-v1"},
            "start": {},
            "end": {},
            "passage_id": {},
            "attachment": {},
            "effective_version": {"default": ""},
        },
        "binding": {
            "operator": "all",
            "children": [{"operator": "scan", "roles": ["source", "report"]}],
        },
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/source_input",
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
                "records": "/report_input",
                "input_role": "report",
                "comparisons": [
                    {
                        "output_field": "product_id",
                        "input": {
                            "role": "report",
                            "projection": "selected-input",
                            "field": "product",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "reference",
                        "input": {
                            "role": "report",
                            "projection": "selected-input",
                            "field": "reference",
                        },
                        "encoding": "json",
                    },
                    {
                        "output_field": "kind_contract",
                        "input": {
                            "role": "report",
                            "projection": "selected-input",
                            "field": "kind_contract",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "project_id",
                        "input": {
                            "role": "report",
                            "projection": "selected-input",
                            "field": "project_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "subject",
                        "input": {
                            "role": "report",
                            "projection": "selected-input",
                            "field": "subject",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "original_source",
                        "input": {
                            "role": "report",
                            "projection": "selected-input",
                            "field": "original_source",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "analyzed_scope_meaning",
                        "input": {
                            "role": "report",
                            "projection": "selected-input",
                            "field": "analyzed_scope",
                        },
                        "encoding": "context-meaning-json",
                    },
                ],
            },
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
                "reference": "corpus_structure.semantic.declared_structural_calls.execute_condition",
                "contract": "structural/call-assets",
                "role": "original-structural-kernel",
            }
        ],
        "assets": [
            {
                "reference": "structural/call-assets",
                "contract": "structural/call-assets",
                "role": "actual-structural-kernels-and-dto-shapes",
            }
        ],
    }

    def __init__(self, profile):
        self.profile = profile

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.declared_structural_calls import (
            condition_kernel,
            resolve_structural_call,
        )

        return resolve_structural_call(
            prepared,
            model,
            operation,
            receiver=DeclaredConditionQualification(None),
            kernel=condition_kernel,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def select_hydrated(self, inputs):
        return inputs.one("source"), inputs.one("report")

    def run(
        self,
        source: dict,
        report: dict,
        start: int,
        end: int,
        passage_id: str,
        attachment: str,
        question: str = "Compare the exact selected retained readings.",
        scope: str = "selected",
        inventory_id: str = "explicit-native-inputs",
        policy_id: str = "exact-retained-structural-v1",
        effective_version: str = "",
    ) -> dict:
        return execute_condition(
            self,
            source,
            report,
            start=start,
            end=end,
            passage_id=passage_id,
            attachment=attachment,
            question=question,
            scope=scope,
            inventory_id=inventory_id,
            policy_id=policy_id,
            effective_version=effective_version,
        )
