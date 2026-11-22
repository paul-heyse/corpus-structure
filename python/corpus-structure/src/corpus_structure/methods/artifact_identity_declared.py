"""Declared artifact cohorts from original source maps and genuine navigation."""

from typing import ClassVar

from corpus_structure.semantic.artifact_products import execute_artifact_identity


class ArtifactIdentityOperation:
    __data_operation__: ClassVar[dict] = {
        "validity_family": ["artifact"],
        "id": "structure.artifact_identity/declared",
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
            "subject",
            "original-source",
            "selected-scope",
            "frozen-source-set",
            "explicit-source-work-bindings",
            "authored-passage-selection",
        ],
        "entrypoints": ["run"],
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
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": {"role": "sources", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                    "source_set": "artifact-sources",
                },
                "subject_target": "source-set",
            },
            {
                "name": "constructions",
                "parameter": "constructions",
                "kind": "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct",
                "direction": "input",
                "minimum": 1,
                "maximum": None,
                "collection": "set",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": {"role": "constructions", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                    "source_set": "artifact-constructions",
                },
                "subject_target": "source-set",
            },
            {
                "name": "nominations",
                "parameter": "nominations",
                "kind": "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoScopedRelationsReport",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": {"role": "nominations", "description": "exact-selected-source"},
                    "identity_requirements": ["episode"],
                    "source_set": "artifact-nominations",
                },
                "subject_target": "source-set",
            },
            {
                "name": "result",
                "kind": "urn:corpus:structural:DeclaredArtifactReport",
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
                "text": "explicit-native-source-work-cohort-and-complete-primary-navigation",
            }
        ],
        "invariants": [
            {"kind": "documentation", "text": "semantic-member-references"},
            {
                "kind": "documentation",
                "text": "artifact-discovery-does-not-run-unrelated-scoped-joins",
            },
            {"kind": "documentation", "text": "unbound-source-work-is-not-absence"},
            {"kind": "documentation", "text": "exact-native-numbering-alias-and-revision-custody"},
            {"kind": "documentation", "text": "candidate-private-standing"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-artifact-cohort-and-authored-source-passages",
        },
        "outcomes": ["success"],
        "precision_description": "original-native-half-open-extents",
        "dependencies": ["text.constructions/source-native"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "existing-invocation-cpu-owner",
        },
        "behavior": "score-explicit-native-artifact-cohort-using-retained-navigation",
        "parameters": {
            "selections": {},
            "policy": {},
            "title_threshold": {"default": 70.0},
            "exclusions": {"default": []},
            "known_anchor_ids": {"default": []},
            "nomination_selections": {"default": []},
        },
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "collection", "roles": ["sources"], "collection": "set"},
                {"operator": "collection", "roles": ["constructions"], "collection": "set"},
                {"operator": "collection", "roles": ["nominations"], "collection": "set"},
            ],
        },
        "reference_targets": [
            {
                "output_role": "result",
                "path": "/artifact_identity/records/*/primary_node",
                "input_role": "constructions",
                "variant": "member",
                "occurrence_position": True,
            },
            {
                "output_role": "result",
                "path": "/artifact_identity/records/*/explicit_reference/primary_node",
                "input_role": "constructions",
                "variant": "member",
                "occurrence_position": True,
            },
            {
                "output_role": "result",
                "path": "/artifact_identity/external_nominations/*/primary_node",
                "input_role": "constructions",
                "variant": "member",
                "occurrence_position": True,
            },
            {
                "output_role": "result",
                "path": "/artifact_identity/declared_relationships/*/primary_node",
                "input_role": "constructions",
                "variant": "member",
                "occurrence_position": True,
            },
            {
                "output_role": "result",
                "path": "/artifact_identity/declared_relationships/*/targets/*/work_primary_node",
                "input_role": "constructions",
                "variant": "member",
                "occurrence_position": True,
            },
            {
                "output_role": "result",
                "path": "/artifact_identity/external_nominations/*/relationship",
                "input_role": "nominations",
                "variant": "member",
                "occurrence_binding": True,
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
                "reference": "corpus_structure.semantic.artifact_products.execute_artifact_identity",
                "contract": "artifacts/profile-assets",
                "role": "same-retained-native-artifact-cohort-and-scoring-kernels",
            }
        ],
        "assets": [
            {
                "reference": "declared-artifact-identity",
                "contract": "artifacts/profile-assets",
                "role": "actual-native-artifact-profile",
            }
        ],
        "potential_dependencies": ["structure.scoped_relations/declared"],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.artifact_products import resolve_artifact_port

        return resolve_artifact_port(
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
        sources: tuple[dict, ...],
        constructions: tuple[dict, ...],
        nominations: tuple[dict, ...],
        selections: list[dict],
        nomination_selections: list[dict],
        policy: dict,
        title_threshold: float,
        exclusions: list[list[str]],
        known_anchor_ids: list[str],
    ) -> dict:
        return execute_artifact_identity(
            self,
            sources,
            constructions,
            nominations,
            selections=selections,
            nomination_selections=nomination_selections,
            policy=policy,
            title_threshold=title_threshold,
            exclusions=exclusions,
            known_anchor_ids=known_anchor_ids,
        )
