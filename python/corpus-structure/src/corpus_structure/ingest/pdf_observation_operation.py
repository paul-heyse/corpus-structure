"""Retain actual recognition requests independently of integration policy."""

from typing import ClassVar

from corpus_structure.semantic.pdf_observations import PdfObservationSetProduct
from corpus_structure.semantic.pdf_transforms import execute_pdf_observation


class PdfObservationOperation:
    __data_operation__: ClassVar[dict] = {
        "validity_family": ["none"],
        "id": "source.pdf_recognition/observe",
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
                "kind": "https://corpus-structure.dev/semantic/data-operation-pdf-capture/DdoPdfCapture",
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
                "name": "result",
                "direction": "output",
                "kind": "https://corpus-structure.dev/semantic/data-operation-pdf-capture/DdoPdfObservationSet",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "parameters": {"pages": {"value_type": "integer", "many": True, "default": []}},
        "dependencies": ["source.pdf/capture"],
        "effects": [
            {
                "name": "retain_pdf_observations",
                "authorization": ["original-source", "exact-selected-pdf", "owned-request-attempt"],
                "idempotency": "request-generation/source-digest/recognition-recipe-digest",
                "fulfillment": "native-observation-set-receipt",
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
            {"kind": "documentation", "text": "exact-original-and-request-byte-custody"},
            {
                "kind": "documentation",
                "text": "failed-partial-and-unknown-coverage-remain-explicit",
            },
            {
                "kind": "documentation",
                "text": "original-publication-and-current-adoption-attribution-are-distinct",
            },
        ],
        "coverage": {
            "binding": "self",
            "result_owners": [{"kind": "implementation", "reference": "self"}],
            "description": "requested-physical-page-observations",
        },
        "outcomes": ["success", "failed"],
        "precision_description": "attributed-raw-request-observations-with-unassessed-source-fidelity",
        "behavior": "Retain actual request outcomes and unknown source coverage; retention is not provider success or accepted source truth.",
        "binding": {"operator": "scan", "roles": ["capture"]},
        "opaque": [
            {
                "reference": "corpus_structure.semantic.pdf_transforms.execute_pdf_observation",
                "contract": "pdf-recognized/profile-assets",
                "role": "owned-native-recognition-retention",
            },
            {
                "reference": "corpus_structure.semantic.pdf_observations.PdfObservationSetProduct",
                "contract": "pdf-recognized/profile-assets",
                "role": "whole-authenticated-observation-set",
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
                "contract": "pdf-recognized/profile-assets",
                "role": "native-parser-models-and-publication-projection",
            },
            {
                "reference": "frozen-native-recognition-policy",
                "contract": "pdf-recognition/policy-v1",
                "role": "recognition-models-and-recovery-policy",
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
                mode="recognized",
            )
        )

    def __init__(self, profile, *, binding, execution_owner, check_active):
        self.profile, self.binding = profile, binding
        self.execution_owner, self.check_active = execution_owner, check_active

    def run(self, capture: dict, pages: tuple[int, ...]) -> PdfObservationSetProduct:
        return execute_pdf_observation(self, capture, pages)
