"""Declared owned PDF capture over an admitted immutable original document."""

from typing import ClassVar

from corpus_structure.semantic.pdf_capture import PdfCaptureProduct, execute_pdf_capture


class PdfCaptureOperation:
    __data_operation__: ClassVar[dict] = {
        "id": "source.pdf/capture",
        "profile": "command",
        "subject": "original-document",
        "context": ["original-source", "whole-document"],
        "entrypoints": ["run"],
        "roles": [
            {
                "name": "original",
                "parameter": "original",
                "direction": "input",
                "kind": "https://corpus-structure.dev/semantic/data-operation-source/DdoOriginalDocument",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "support": {
                    "provenance": "exact",
                    "origins": ["original-source"],
                    "identity_requirements": ["original-source"],
                    "source": "same-original",
                    "coverage": "whole-document",
                },
            },
            {
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-pdf-capture/DdoPdfCapture",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {},
        "dependencies": [],
        "effects": [
            {
                "name": "publish_pdf_capture",
                "authorization": ["original-source", "owned-request-attempt"],
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
        "behavior": "existing owned finite native PDF capture and sealed publication",
        "binding": {"operator": "scan", "roles": ["original"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.pdf_capture.execute_pdf_capture",
                "contract": "pdf-capture/profile-assets",
                "role": "owned-native-pdf-capture",
            },
            {
                "reference": "corpus_structure.semantic.pdf_capture.PdfCaptureProduct",
                "contract": "pdf-capture/profile-assets",
                "role": "whole-authenticated-publication",
            },
        ],
        "assets": [
            {
                "reference": "frozen-native-pdf-recipe",
                "contract": "pdf-capture/profile-assets",
                "role": "native-parser-models-and-publication-projection",
            }
        ],
    }

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.semantic.data_operation_pdf_effect import PdfCaptureEffectPort
        from corpus_structure.semantic.pdf_capture import resolve_pdf_capture_port

        return PdfCaptureEffectPort(
            resolve_pdf_capture_port(
                prepared,
                model,
                operation,
                identity=identity,
                authorize=authorize,
                custody=custody,
                sources=sources,
            )
        )

    def __init__(self, profile, *, execution_owner, subject_context, check_active):
        self.profile = profile
        self.execution_owner = execution_owner
        self.subject_context = subject_context
        self.check_active = check_active

    def run(self, original: dict) -> PdfCaptureProduct:
        return execute_pdf_capture(self, original)
