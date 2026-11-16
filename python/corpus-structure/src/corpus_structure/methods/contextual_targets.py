"""Declared authentic target projection and explicit selected vector assembly."""

from typing import ClassVar

from corpus_structure.semantic.contextual_target_products import (
    execute_target_profile,
    execute_vector_selection_profile,
)


class CuratedContextualTargetsOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual_targets/curated",
        "profile": "discovery",
        "subject": "contextual-registry",
        "subject_definition": {
            "id": "contextual-registry",
            "identifier_kind": "string",
            "scope": "project",
        },
        "discovery_relation": "role-associated",
        "context": ["exact-target-local-source", "explicit-selected-population"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "selection",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoCuratedContextualTargets",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "selection",
                "support": {
                    "provenance": "exact",
                    "source": "explicit-authentic-selected-target",
                    "coverage": {"role": "selection", "description": "exact-selected-target-value"},
                    "identity_requirements": ["original-source"],
                    "origins": ["authored"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualTargetPopulation",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "explicit-retained-target-values"}],
        "invariants": [
            {
                "kind": "documentation",
                "text": "preserve-original-source-and-derived-support-without-new-inference",
            }
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-target-population",
        },
        "outcomes": ["success"],
        "precision_description": None,
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "immutable-invocation-inputs",
        },
        "behavior": "retrieve.contextual_targets/curated-2",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["selection"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.contextual_target_products.execute_target_profile",
                "contract": "contextual/retrieval-assets",
                "role": "exact-target-projection-and-vector-selection",
            }
        ],
        "assets": [
            {
                "reference": "target-projections",
                "contract": "contextual/retrieval-assets",
                "role": "actual-target-and-vector-meaning",
            }
        ],
        "subject_definitions": [
            {"id": "contextual-target", "identifier_kind": "string", "scope": "project"}
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, selection: dict) -> dict:
        return execute_target_profile(self, selection)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_target_products import resolve_target_port

        return resolve_target_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )


class SourceContextualTargetsOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual_targets/components",
        "profile": "discovery",
        "subject": "selected-native-source",
        "subject_definition": {
            "id": "selected-native-source",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "role-associated",
        "context": ["exact-target-local-source", "explicit-selected-population"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "report",
                "kind": "urn:corpus:structural:DeclaredDefinitionComponentsReport",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "report",
                "support": {
                    "provenance": "exact",
                    "source": "explicit-authentic-selected-target",
                    "coverage": {"role": "report", "description": "exact-selected-target-value"},
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualTargetPopulation",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "explicit-retained-target-values"}],
        "invariants": [
            {
                "kind": "documentation",
                "text": "preserve-original-source-and-derived-support-without-new-inference",
            }
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-target-population",
        },
        "outcomes": ["success"],
        "precision_description": None,
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "immutable-invocation-inputs",
        },
        "behavior": "retrieve.contextual_targets/components-2",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["report"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.contextual_target_products.execute_target_profile",
                "contract": "contextual/retrieval-assets",
                "role": "exact-target-projection-and-vector-selection",
            }
        ],
        "assets": [
            {
                "reference": "target-projections",
                "contract": "contextual/retrieval-assets",
                "role": "actual-target-and-vector-meaning",
            }
        ],
        "subject_definitions": [
            {"id": "contextual-target", "identifier_kind": "string", "scope": "project"}
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, report: dict) -> dict:
        return execute_target_profile(self, report)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_target_products import resolve_target_port

        return resolve_target_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )


class ContextualTargetOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual_target/declared",
        "profile": "derivation",
        "subject": "contextual-target",
        "subject_definition": {
            "id": "contextual-target",
            "identifier_kind": "string",
            "scope": "project",
        },
        "discovery_relation": "role-associated",
        "context": ["exact-target-local-source", "explicit-selected-population"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "target",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualTargetMember",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "target",
                "support": {
                    "provenance": "exact",
                    "source": "explicit-authentic-selected-target",
                    "coverage": {"role": "target", "description": "exact-selected-target-value"},
                    "identity_requirements": ["episode"],
                    "origins": ["computation"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualTarget",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "explicit-retained-target-values"}],
        "invariants": [
            {
                "kind": "documentation",
                "text": "preserve-original-source-and-derived-support-without-new-inference",
            }
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-target-population",
        },
        "outcomes": ["success"],
        "precision_description": None,
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "immutable-invocation-inputs",
        },
        "behavior": "retrieve.contextual_target/declared-2",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["target"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.contextual_target_products.execute_target_profile",
                "contract": "contextual/retrieval-assets",
                "role": "exact-target-projection-and-vector-selection",
            }
        ],
        "assets": [
            {
                "reference": "target-projections",
                "contract": "contextual/retrieval-assets",
                "role": "actual-target-and-vector-meaning",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, target: dict) -> dict:
        return execute_target_profile(self, target)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_target_products import resolve_target_port

        return resolve_target_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )


class ContextualVectorSelectionOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "retrieve.contextual_vectors/selection",
        "profile": "derivation",
        "subject": "selected-native-source",
        "subject_definition": {
            "id": "selected-native-source",
            "identifier_kind": "string",
            "scope": "original-source",
        },
        "discovery_relation": "role-associated",
        "context": ["exact-target-local-source", "explicit-selected-population"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "inventory",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualInventory",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "inventory",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": {"role": "inventory", "description": "exact-selected-target-value"},
                    "identity_requirements": ["episode"],
                    "source_set": "contextual-inventory",
                },
                "subject_target": "source-set",
            },
            {
                "name": "query",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualQueryVector",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "query",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": {"role": "query", "description": "exact-selected-target-value"},
                    "identity_requirements": ["episode"],
                    "source_set": "contextual-query-vector",
                },
                "subject_target": "source-set",
            },
            {
                "name": "targets",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualTargetVector",
                "direction": "input",
                "minimum": 0,
                "maximum": None,
                "collection": "set",
                "presence": "optional",
                "parameter": "targets",
                "support": {
                    "provenance": "exact",
                    "source": "frozen-source-set",
                    "coverage": {"role": "targets", "description": "exact-selected-target-value"},
                    "identity_requirements": ["episode"],
                    "source_set": "contextual-target-vectors",
                },
                "subject_target": "source-set",
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualVectors",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [{"kind": "documentation", "text": "explicit-retained-target-values"}],
        "invariants": [
            {
                "kind": "documentation",
                "text": "preserve-original-source-and-derived-support-without-new-inference",
            }
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "exact-selected-target-population",
        },
        "outcomes": ["success"],
        "precision_description": None,
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "call-boundary",
            "ownership": "immutable-invocation-inputs",
        },
        "behavior": "retrieve.contextual_vectors/selection-2",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["inventory", "query", "targets"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.contextual_target_products.execute_vector_selection_profile",
                "contract": "contextual/retrieval-assets",
                "role": "exact-target-projection-and-vector-selection",
            }
        ],
        "assets": [
            {
                "reference": "target-projections",
                "contract": "contextual/retrieval-assets",
                "role": "actual-target-and-vector-meaning",
            }
        ],
    }

    def __init__(self, execute):
        self.execute = execute

    def run(self, inventory: dict, query: dict, targets: tuple[dict, ...]) -> dict:
        return execute_vector_selection_profile(self, inventory, query, targets)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.contextual_target_products import resolve_target_port

        return resolve_target_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )
