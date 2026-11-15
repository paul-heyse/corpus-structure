"""Purpose-restricted native snapshot of independently authored reference meaning."""

from typing import ClassVar


class SelectedReferenceSnapshotOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "reference.snapshot/declared",
        "profile": "derivation",
        "subject": "independent-reference",
        "subject_definition": {'id': 'independent-reference', 'identifier_kind': 'string', 'scope': 'project'},
        "discovery_relation": 'role-associated',
        "context": ["authored-reference", "frozen-original-source", "protected-evaluator-purpose"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "reference",
                "parameter": "reference",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "origins": ["authored"],
                    "provenance": "exact",
                    "identity_requirements": ["original-source"],
                    "source": "same-original",
                    "coverage": "exact-independent-reference",
                },
            },
            {
                "name": "snapshot",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReferenceSnapshot",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": ["explicit-independent-adjudicated-reference"],
        "invariants": [
            "no-prediction-input",
            "source-release-remains-original",
            "questions-and-denominators-remain-frozen",
            "evaluator-only-kind",
        ],
        "coverage": "exact-frozen-reference-population",
        "outcomes": ["success", "failed"],
        "precision": "exact-authored-semantic-values",
        "dependencies": [],
        "effects": [],
        "parameters": {},
        "behavior": "retain exact independent reference without regrading or recognition",
        "binding": {"operator": "scan", "roles": ["reference"]},
        "output_witnesses": [
            {
                "output_role": "snapshot",
                "records": "",
                "input_role": "reference",
                "comparisons": [
                    {
                        "output_field": "reference_name",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/reference_name",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "author",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/author",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "pass_kind",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/pass_kind",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "direction",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/direction",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_demand_id",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/source_demand_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_cut_id",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/source_cut_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_read_id",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/source_read_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_release_id",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/source_release_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_runtime_id",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/source_runtime_id",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_cut",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/source_cut",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "source_members",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/source_members",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "output_members",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/output_members",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "cases",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/cases",
                        },
                        "encoding": "value",
                    },
                    {
                        "output_field": "retained_correspondence",
                        "input": {
                            "role": "reference",
                            "projection": "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference",
                            "field": "/retained_correspondence",
                        },
                        "encoding": "value",
                    },
                ],
            }
        ],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "none",
            "cancellation": "call-boundary",
            "ownership": "immutable-input-value",
        },
    }

    def run(self, reference: dict) -> dict:
        return dict(reference)
