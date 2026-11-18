"""Declared native source discovery from an exact sealed PDF capture product."""

from typing import ClassVar

from corpus_structure.semantic.pdf_views import execute_pdf_views
from corpus_structure.semantic.source_discovery import SourceViewPopulation


class PdfSourceViewsFamily:
    __data_operation__: ClassVar[dict] = {
        "validity_family": ["none"],
        "abstract": True,
        "id": "source.pdf_views/discovery",
        "profile": "discovery",
        "subject": "original-document",
        "subject_definition": {
            "id": "original-document",
            "identifier_kind": "string",
            "scope": "original-document",
        },
        "subject_definitions": [
            {"id": "original-source-view", "identifier_kind": "string", "scope": "original-source"}
        ],
        "discovery_relation": "role-associated",
        "context": ["original-source", "actual-sealed-pdf", "frozen-relative-section-selection"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "capture",
                "parameter": "capture",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-pdf-capture/DdoPdfPublication",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "alternative",
                "alternatives": ["source.pdf/capture"],
                "selected": "source.pdf/capture",
                "support": {
                    "provenance": "exact",
                    "source": "same-original",
                    "coverage": {"role": "capture", "description": "whole-document"},
                    "origins": ["computation"],
                    "identity_requirements": ["episode", "alternative"],
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source-discovery/DdoSourceViewPopulation",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {
            "sections": {"value_type": "string", "many": True, "default": []},
            "membership": {"value_type": "string", "default": "direct"},
        },
        "dependencies": ["source.pdf/capture"],
        "effects": [],
        "applicability": [
            {"kind": "documentation", "text": "selected-authenticated-native-pdf-capture"}
        ],
        "invariants": [
            {"kind": "documentation", "text": "exact-original-relative-coordinates"},
            {"kind": "documentation", "text": "no-ambient-publication-selection"},
            {"kind": "documentation", "text": "closed-inspected-section-selection"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "frozen-relative-section-selection",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "actual-published-native-atom-and-ancestor-projection",
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "pinned-read-borrow",
        },
        "behavior": "project the exact selected sealed PDF into original-addressed source members without recognition or recapture",
        "binding": {
            "operator": "all",
            "children": [
                {"operator": "scan", "roles": ["capture"]},
                {
                    "operator": "membership",
                    "operands": [
                        {"kind": "parameter", "name": "membership", "value_type": "string"},
                        {
                            "kind": "literal",
                            "value_type": "string",
                            "value": ["direct", "descendants"],
                        },
                    ],
                },
            ],
        },
        "opaque": [
            {
                "reference": "corpus_structure.semantic.pdf_views.execute_pdf_views",
                "contract": "pdf-views/profile-assets",
                "role": "authenticated-pdf-source-projection",
            },
            {
                "reference": "corpus_structure.semantic.source_discovery.SourceViewPopulation",
                "contract": "pdf-views/profile-assets",
                "role": "typed-complete-source-population",
            },
        ],
        "assets": [
            {
                "reference": "pdf-domain/contract.json",
                "contract": "pdf-native/helper-bindings",
                "role": "native-pdf-helper-bindings",
            },
            {
                "reference": "published-section-projection",
                "contract": "pdf-views/profile-assets",
                "role": "original-native-sections-and-coordinates",
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.pdf_views import resolve_pdf_views_port

        return resolve_pdf_views_port(
            prepared,
            model,
            operation,
            identity=identity,
            authorize=authorize,
            custody=custody,
            sources=sources,
        )

    def __init__(self, profile, *, binding, execution_owner, check_active):
        self.profile, self.binding, self.execution_owner, self.check_active = (
            profile,
            binding,
            execution_owner,
            check_active,
        )

    def run(
        self, capture: dict, sections: tuple[str, ...], membership: str
    ) -> SourceViewPopulation:
        return execute_pdf_views(self, capture, sections, membership)


class PdfSourceViewsOperation(PdfSourceViewsFamily):
    __data_operation__: ClassVar[dict] = {"abstract": False}
