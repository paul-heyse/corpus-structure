"""Declared region rendering from an exact selected sealed PDF publication."""

from typing import ClassVar

from corpus_structure.semantic.native_requests import execute_pdf_region


class PdfRegionFamily:
    __data_operation__: ClassVar[dict] = {
        "abstract": True,
        "id": "source.pdf_region/render",
        "profile": "derivation",
        "subject": "original-document",
        "subject_definition": {'id': 'original-document', 'identifier_kind': 'string', 'scope': 'original-document'},
        "discovery_relation": 'role-associated',
        "context": ["original-source", "exact-selected-pdf", "native-occurrence-region"],
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
                "kind": "https://corpus-structure.dev/semantic/data-operation-pdf-region/DdoPdfRegion",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {
            "pointer": {"value_type": "string"},
            "region_index": {"value_type": "integer"},
            "scale": {"value_type": "string", "default": "2"},
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
            "native-geometry-only",
            "exact-publisher-support",
        ],
        "coverage": "native-occurrence-region",
        "outcomes": ["success", "failed"],
        "precision": "png-from-native-pdf-point-region",
        "behavior": "render selected native geometry using the authenticated original PDF",
        "binding": {"operator": "scan", "roles": ["capture"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.native_requests.execute_pdf_region",
                "contract": "pdf-region/profile",
                "role": "selected-original-renderer",
            }
        ],
        "assets": [
            {
                "reference": "pdfium-native-region-renderer",
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

    def run(self, capture: dict, pointer: str, region_index: int, scale: str) -> dict:
        return execute_pdf_region(self, capture, pointer, region_index, scale)


class PdfRegionOperation(PdfRegionFamily):
    __data_operation__: ClassVar[dict] = {"abstract": False}
