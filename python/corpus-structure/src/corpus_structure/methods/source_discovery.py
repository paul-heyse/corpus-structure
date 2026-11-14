"""Declare selected original-view discovery without manufacturing a capture episode."""

from typing import ClassVar

from corpus_structure.semantic.source_discovery import (
    SourceViewPopulation,
    execute_source_discovery,
)


class SelectedSourceViewsOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "source.selected_views/discovery",
        "profile": "discovery",
        "subject": "original-document",
        "context": ["original-source", "frozen-view-selection"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "original",
                "parameter": "original",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoOriginalDocument",
                "direction": "input", "minimum": 1, "maximum": 1,
                "collection": "scalar", "presence": "required",
                "support": {
                    "provenance": "exact", "source": "same-original",
                    "coverage": "whole-document", "origins": ["original-source"],
                    "identity_requirements": ["original-source"],
                },
            },
            {
                "name": "views", "parameter": "views",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
                "direction": "input", "minimum": 0, "maximum": None,
                "collection": "set", "presence": "optional",
                "subject_field": "/source/document_subject",
                "support": {
                    "provenance": "exact", "source": "same-original",
                    "coverage": "frozen-selected-view-set", "origins": ["original-source", "computation"],
                    "identity_requirements": ["original-source", "episode"],
                },
            },
            {
                "name": "result",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source-discovery/DdoSourceViewPopulation",
                "direction": "output", "minimum": 1, "maximum": 1,
                "collection": "scalar", "presence": "required",
            },
        ],
        "parameters": {"complete": {"value_type": "boolean"}},
        "applicability": ["native-admitted-original-and-exact-view-selection"],
        "invariants": ["original-source-and-context-preserved", "no-recapture", "no-unexamined-universe-closure"],
        "coverage": "frozen-selected-view-set",
        "outcomes": ["success", "failed"],
        "precision": "exact-original-source-addresses",
        "dependencies": [], "effects": [],
        "capabilities": {
            "forms": ["scalar"], "preparation": "resource",
            "prepared_factory": "acquire_port", "cancellation": "call-boundary",
            "ownership": "immutable-input-value",
        },
        "behavior": "closed-or-partial population of explicitly selected authenticated original views",
        "binding": {"operator": "scan", "roles": ["original", "views"]},
        "opaque": [
            {"reference": "corpus_structure.semantic.source_discovery.execute_source_discovery", "contract": "source-discovery/profile-assets", "role": "selected-population-projection"},
            {"reference": "corpus_structure.semantic.source_discovery.SourceViewPopulation", "contract": "source-discovery/profile-assets", "role": "typed-source-population"},
        ],
        "assets": [{"reference": "selected-source-population", "contract": "source-discovery/profile-assets", "role": "original-context-and-member-projection"}],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.source_discovery import resolve_source_discovery_port

        return resolve_source_discovery_port(
            prepared, model, operation, identity=identity, authorize=authorize,
            custody=custody, sources=sources,
        )

    def __init__(self, profile):
        self.profile = profile

    def run(self, original: dict, views: tuple[dict, ...], complete: bool) -> SourceViewPopulation:
        return execute_source_discovery(self, original, views, complete)
