"""Declared qualified PNG input for the existing local Chandra producer."""

from typing import ClassVar

from corpus_structure.semantic.native_requests import execute_pdf_visual_input


class PdfVisualInputFamily:
    __data_operation__: ClassVar[dict] = {
        "abstract": True,
        "id": "source.visual_input/render",
        "profile": "derivation",
        "subject": "original-document",
        "subject_definition": {'id': 'original-document', 'identifier_kind': 'string', 'scope': 'original-document'},
        "discovery_relation": 'role-associated',
        "context": ["original-source", "exact-selected-pdf", "page-or-native-region"],
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
                    "origins": ["computation"],
                    "identity_requirements": ["episode", "alternative"],
                    "source": "same-original",
                    "coverage": "whole-document",
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-visual/DdoVisualInput",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {
            "selection": {
                "kind": "https://corpus-structure.dev/semantic/data-operation-visual/DdoVisualSelection"
            }
        },
        "dependencies": ["source.pdf/capture"],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "resource",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "selected-original-render",
        },
        "applicability": ["authenticated-sealed-pdf-publication"],
        "invariants": [
            "exact-original-byte-digest",
            "qualified-crop-transform",
            "exact-publisher-support",
        ],
        "coverage": "page-or-native-region",
        "outcomes": ["success", "failed"],
        "precision": "qualified-png-and-native-pdf-point-transform",
        "behavior": "render the exact page or native crop with the incumbent visual geometry kernel",
        "binding": {"operator": "scan", "roles": ["capture"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.native_requests.execute_pdf_visual_input",
                "contract": "pdf-region/profile",
                "role": "selected-original-visual-renderer",
            }
        ],
        "assets": [
            {
                "reference": "visual-pdfium-renderer",
                "contract": "pdf-region/profile",
                "role": "native-geometry-and-rendering-policy",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.native_requests import PreparedPdfRegionPort

        port = PreparedPdfRegionPort(
            identity, model, model.operation(operation), prepared, authorize, custody, sources
        )
        port.verify()
        return port

    def __init__(self, port, *, binding, execution_owner, check_active):
        self.port, self.binding, self.execution_owner, self.check_active = (
            port,
            binding,
            execution_owner,
            check_active,
        )

    def run(self, capture: dict, selection: dict) -> dict:
        return execute_pdf_visual_input(self, capture, selection)


class PdfVisualInputOperation(PdfVisualInputFamily):
    __data_operation__: ClassVar[dict] = {"abstract": False}
