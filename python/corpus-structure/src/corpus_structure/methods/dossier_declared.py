"""Native dossier composition over explicitly selected immutable predecessors."""

from typing import ClassVar

from corpus_structure.semantic.dossier_products import execute_dossier


class DossierOperation:
    __data_operation__: ClassVar[dict] = {
        "validity_family": ["none"],
        "id": "structure.dossier/declared",
        "profile": "derivation",
        "subject": "actual-focus-source",
        "subject_definition": {
            "id": "actual-focus-source",
            "identifier_kind": "string",
            "scope": "selected-source-set",
        },
        "discovery_relation": "role-associated",
        "context": [
            "project",
            "original-source",
            "analyzed-scope",
            "frozen-source-set",
            "authored-dossier-selection",
        ],
        "entrypoints": ["run"],
        "consumer_selection": "select_hydrated",
        "roles": [
            {
                "name": "sources",
                "parameter": "sources",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "set",
                "presence": "required",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "dossier-sources",
                    "coverage": {
                        "role": "sources",
                        "description": "exact-selected-source-and-context",
                    },
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
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "dossier-components",
                    "coverage": {
                        "role": "components",
                        "description": "exact-selected-source-and-context",
                    },
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "definitions",
                "parameter": "definitions",
                "kind": "urn:corpus:structural:DeclaredDefinitionApplicabilityReport",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "dossier-definitions",
                    "coverage": {
                        "role": "definitions",
                        "description": "exact-selected-source-and-context",
                    },
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "comparisons",
                "parameter": "comparisons",
                "kind": "urn:corpus:structural:DeclaredComparisonReport",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "dossier-comparisons",
                    "coverage": {
                        "role": "comparisons",
                        "description": "exact-selected-source-and-context",
                    },
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "candidates",
                "parameter": "candidates",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "dossier-candidates",
                    "coverage": {
                        "role": "candidates",
                        "description": "exact-selected-source-and-context",
                    },
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "relationships",
                "parameter": "relationships",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualWitnessedRetrievalProduct",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "dossier-relationships",
                    "coverage": {
                        "role": "relationships",
                        "description": "exact-selected-source-and-context",
                    },
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "admissions",
                "parameter": "admissions",
                "kind": "urn:corpus:structural-admission:DdoStructuralAdmission",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "subject_target": "source-set",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "source_set": "dossier-admissions",
                    "coverage": {
                        "role": "admissions",
                        "description": "exact-native-structural-admission",
                    },
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "kind": "urn:corpus:structural:DeclaredDossierReport",
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
                "text": "actual-retained-components-and-explicit-predecessor-closure",
            }
        ],
        "invariants": [
            {"kind": "documentation", "text": "no-task-or-view-aliases"},
            {"kind": "documentation", "text": "no-downstream-language-recognition"},
            {"kind": "documentation", "text": "all-selected-endpoint-source-evidence-preserved"},
            {"kind": "documentation", "text": "private-membership-is-not-member-truth"},
            {"kind": "documentation", "text": "missing-independent-assessment-remains-missing"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "explicit-selected-predecessor-and-native-passage-closure",
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
        "behavior": "assemble-native-predecessor-membership-and-bounded-representation",
        "parameters": {
            "component_id": {},
            "candidate_selections": {"default": "[]"},
            "comparison_selections": {"default": "[]"},
            "extra_passages": {"default": "[]"},
            "question": {"default": "Assemble the selected retained definition dossier."},
            "scope": {"default": "selected"},
            "inventory_id": {"default": "explicit-native-dossier"},
            "policy_id": {"default": "exact-retained-dossier-v1"},
            "member_budget": {"default": 12},
            "representation_policy": {"default": "supported-facet-greedy-1"},
        },
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "collection", "roles": ["sources"], "collection": "set"},
                {"operator": "scan", "roles": ["components"]},
                {"operator": "collection", "roles": ["definitions"], "collection": "set"},
                {"operator": "collection", "roles": ["comparisons"], "collection": "set"},
                {"operator": "collection", "roles": ["candidates"], "collection": "set"},
                {"operator": "collection", "roles": ["relationships"], "collection": "set"},
                {"operator": "collection", "roles": ["admissions"], "collection": "set"},
            ],
        },
        "reference_targets": [
            {
                "output_role": "result",
                "path": "/components_input",
                "input_role": "components",
                "variant": "product",
            },
            {
                "output_role": "result",
                "path": "/dossier/root_component",
                "input_role": "components",
                "variant": "member",
            },
        ],
        "output_witnesses": [
            {
                "output_role": "result",
                "records": "/inputs/sources/*",
                "input_role": "sources",
                "comparisons": [
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
                        "output_field": "source",
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
                        "output_field": "subject_definition",
                        "input": {
                            "role": "sources",
                            "projection": "selected-input",
                            "field": "subject_definition",
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
        ],
        "opaque": [
            {
                "reference": "corpus_structure.semantic.dossier_products.execute_dossier",
                "contract": "dossiers/profile-assets",
                "role": "same-retained-structural-membership-kernel",
            }
        ],
        "assets": [
            {
                "reference": "declared-dossier-products",
                "contract": "dossiers/profile-assets",
                "role": "typed-native-predecessor-assembly",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.dossier_products import resolve_dossier_port

        return resolve_dossier_port(
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

    def select_hydrated(self, inputs):
        return (
            inputs.role("sources"),
            inputs.one("components"),
            inputs.role("definitions"),
            inputs.role("comparisons"),
            inputs.role("candidates"),
            inputs.role("relationships"),
            inputs.role("admissions"),
        )

    def run(
        self,
        sources: tuple[dict, ...],
        components: dict,
        definitions: tuple[dict, ...],
        comparisons: tuple[dict, ...],
        candidates: tuple[dict, ...],
        relationships: tuple[dict, ...],
        admissions: tuple[dict, ...],
        component_id: str,
        candidate_selections: str = "[]",
        comparison_selections: str = "[]",
        extra_passages: str = "[]",
        question: str = "Assemble the selected retained definition dossier.",
        scope: str = "selected",
        inventory_id: str = "explicit-native-dossier",
        policy_id: str = "exact-retained-dossier-v1",
        member_budget: int = 12,
        representation_policy: str = "supported-facet-greedy-1",
    ) -> dict:
        return execute_dossier(
            self,
            sources,
            components,
            definitions,
            comparisons,
            candidates,
            relationships,
            admissions,
            component_id=component_id,
            candidate_selections=candidate_selections,
            comparison_selections=comparison_selections,
            extra_passages=extra_passages,
            question=question,
            scope=scope,
            inventory_id=inventory_id,
            policy_id=policy_id,
            member_budget=member_budget,
            representation_policy=representation_policy,
        )
