"""Declared owned PDF capture over an admitted immutable original document."""

from typing import ClassVar

from corpus_structure.semantic.pdf_capture import PdfCaptureProduct
from corpus_structure.semantic.pdf_transforms import execute_pdf_organization


class PdfOrganizationOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "source.pdf_sections/organize",
        "profile": "command",
        "subject": "original-document",
        "context": ["original-source", "whole-document"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "capture",
                "parameter": "capture",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-pdf-capture/DdoPdfCapture",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "origins": ["computation"],
                    "identity_requirements": ["episode"],
                    "source": "same-original",
                    "coverage": "whole-document",
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-pdf-capture/DdoPdfOrganizedPublication",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {},
        "dependencies": ["source.pdf/capture"],
        "effects": [
            {
                "name": "publish_pdf_organization",
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
        "applicability": ["native-admitted-retained-pdf-original"],
        "invariants": [
            "original-byte-custody",
            "actual-frozen-native-validation",
            "exact-publisher-and-replay-attribution",
        ],
        "coverage": "whole-document",
        "outcomes": ["success", "failed"],
        "precision": "native-pdf-records-and-original-coordinates",
        "behavior": "selected inline and cell recognition under exact native source scopes",
        "binding": {"operator": "scan", "roles": ["capture"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.pdf_transforms.execute_pdf_organization",
                "contract": "pdf-organized/execution-custody",
                "role": "owned-native-pdf-capture",
            },
            {
                "reference": "corpus_structure.semantic.pdf_capture.PdfCaptureProduct",
                "contract": "pdf-organized/execution-custody",
                "role": "whole-authenticated-publication",
            },
        ],
        "assets": [
            {
                "reference": "frozen-native-pdf-recipe",
                "contract": "pdf-organized/execution-custody",
                "role": "native-parser-models-and-publication-projection",
            }
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
                mode="organized",
            )
        )

    def __init__(self, profile, *, binding, execution_owner, check_active):
        self.profile = profile
        self.binding = binding
        self.execution_owner = execution_owner
        self.check_active = check_active

    def run(self, capture: dict) -> PdfCaptureProduct:
        return execute_pdf_organization(self, capture)
