"""Declared owned PDF capture over an admitted immutable original document."""

from typing import ClassVar

from corpus_structure.semantic.pdf_capture import PdfCaptureProduct
from corpus_structure.semantic.pdf_transforms import execute_pdf_integration


class PdfIntegrationOperation:
    __data_operation__: ClassVar[dict] = {
        "abstract": True,
        "id": "source.pdf_integrated/reconcile",
        "profile": "command",
        "subject": "original-document",
        "subject_definition": {
            "id": "original-document",
            "identifier_kind": "string",
            "scope": "original-document",
        },
        "discovery_relation": "role-associated",
        "context": ["original-source", "whole-document"],
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
                    "coverage": {"role": "capture", "description": "whole-document"},
                },
            },
            {
                "name": "observations",
                "parameter": "observations",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-pdf-capture/DdoPdfObservationSet",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "alternative",
                "alternatives": ["source.pdf_recognition/observe"],
                "selected": "source.pdf_recognition/observe",
                "support": {
                    "provenance": "exact",
                    "origins": ["computation"],
                    "identity_requirements": ["episode", "alternative"],
                    "source": "same-original",
                    "coverage": {
                        "role": "observations",
                        "description": "requested-physical-page-observations",
                    },
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-pdf-capture/DdoPdfIntegratedPublication",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "dependencies": ["source.pdf/capture", "source.pdf_recognition/observe"],
        "effects": [
            {
                "name": "publish_pdf_integration",
                "authorization": ["original-source", "exact-selected-pdf", "owned-request-attempt"],
                "idempotency": "request-generation/source-digest/recipe-digest",
                "fulfillment": "sealed-native-pdf-receipt",
            }
        ],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "pdf-native",
            "prepared_factory": "acquire_port",
            "cancellation": "cooperative",
            "ownership": "owned-pdf-build",
        },
        "applicability": [
            {"kind": "documentation", "text": "native-admitted-retained-pdf-original"}
        ],
        "invariants": [
            {"kind": "documentation", "text": "original-byte-custody"},
            {"kind": "documentation", "text": "actual-frozen-native-validation"},
            {"kind": "documentation", "text": "exact-publisher-and-replay-attribution"},
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "whole-document",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "native-pdf-records-and-original-coordinates",
        "behavior": "deterministic integration policy over explicitly selected retained observations",
        "binding": {"operator": "scan", "roles": ["capture", "observations"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.pdf_transforms.execute_pdf_integration",
                "contract": "pdf-integrated/execution-custody",
                "role": "owned-native-pdf-capture",
            },
            {
                "reference": "corpus_structure.semantic.pdf_capture.PdfCaptureProduct",
                "contract": "pdf-integrated/execution-custody",
                "role": "whole-authenticated-publication",
            },
        ],
        "assets": [
            {
                "reference": "pdf-domain/contract.json",
                "contract": "pdf-native/helper-bindings",
                "role": "native-pdf-helper-bindings",
            },
            {
                "reference": "frozen-native-pdf-recipe",
                "contract": "pdf-integrated/execution-custody",
                "role": "native-parser-models-and-publication-projection",
            },
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.data_operation_pdf_effect import PdfCaptureEffectPort
        from corpus_structure.semantic.pdf_transforms import resolve_pdf_transform_port

        return PdfCaptureEffectPort(
            resolve_pdf_transform_port(
                prepared,
                model,
                operation,
                identity=identity,
                authorize=authorize,
                custody=custody,
                sources=sources,
                mode="integrated",
            )
        )

    def __init__(self, profile, *, binding, execution_owner, check_active):
        self.profile = profile
        self.binding = binding
        self.execution_owner = execution_owner
        self.check_active = check_active

    def run(self, capture: dict, observations: dict) -> PdfCaptureProduct:
        return execute_pdf_integration(self, capture, observations)
