"""The bounded PDF capture effect; native PDF custody remains its existing authority."""

from dataclasses import dataclass
from typing import Any

from pydantic import TypeAdapter

from .data_operation_effects import ReceiptBearingEffectPort
from .data_operation_ports import PortRefusal
from .pdf_effect_contract import (
    PDF_CAPTURE_EFFECT,
    PDF_ENRICHMENT_EFFECT,
    PDF_INTEGRATION_EFFECT,
    PDF_ORGANIZATION_EFFECT,
    PDF_RECOGNITION_EFFECT,
)
from .pdf_observations import PdfObservationExecutionReceipt
from .pdf_publication import PdfExecutionReceipt, inspect_pdf_execution_receipt


@dataclass(frozen=True)
class PdfCaptureEffectPort(ReceiptBearingEffectPort):
    """An admitted PDF prepared capability with one inspectable native effect contract.

    No effect registry or permission callback is introduced. Existing native
    retain/publish calls independently run ddo_require_pdf_completion and the
    sealed publication projection; Python inspection cannot replace those guards.
    """

    wrapped: Any

    def effect_implementation(self) -> Any:
        return self.wrapped

    def __post_init__(self):
        operation = self.wrapped.operation
        if (
            operation.profile != "command"
            or operation.effects
            not in (
                (PDF_CAPTURE_EFFECT,),
                (PDF_ENRICHMENT_EFFECT,),
                (PDF_INTEGRATION_EFFECT,),
                (PDF_ORGANIZATION_EFFECT,),
                (PDF_RECOGNITION_EFFECT,),
            )
            or operation.capabilities.preparation != "pdf-native"
            or operation.capabilities.prepared_factory is None
        ):
            raise PortRefusal(
                "PDF capture requires its exact admitted effect and acquisition contract"
            )

    @property
    def operation(self):
        return self.wrapped.operation

    @property
    def identity(self):
        return self.wrapped.identity

    @property
    def native_selections(self):
        return self.wrapped.native_selections

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        completion = yield from self.wrapped.plan_python(
            values, binding=binding, check_active=check_active, execution_owner=execution_owner
        )
        claim = execution_owner.claim
        if self.operation.effects == (PDF_RECOGNITION_EFFECT,):
            if claim is None or completion.pdf_observation_evidence is None or completion.pdf_execution_evidence is not None:
                raise PortRefusal("recognition retention requires its actual observation receipt")
            receipt = PdfObservationExecutionReceipt.model_validate_json(completion.pdf_observation_evidence)
            if (receipt.task_id, receipt.attempt, receipt.holder) != (claim.task_id, claim.attempt, claim.holder):
                raise PortRefusal("observation adoption differs from its current native claim")
            from sqlalchemy import bindparam, func, select
            from sqlalchemy.dialects.postgresql import JSONB

            check_active()
            with execution_owner.engine.connect() as connection:
                connection.scalar(select(func.ops.pdf_observation_projection(
                    bindparam("receipt", receipt.model_dump(mode="json"), type_=JSONB),
                    claim.task_id, claim.attempt, claim.holder,
                )))
            check_active()
            return completion
        if completion.pdf_observation_evidence is not None:
            raise PortRefusal("sealed PDF publication cannot acquire observation-set evidence")
        if claim is None or completion.pdf_execution_evidence is None:
            raise PortRefusal("PDF effect requires its active claim and actual sealed receipt")
        receipt = TypeAdapter(PdfExecutionReceipt).validate_json(
            completion.pdf_execution_evidence, strict=True
        )
        if receipt.publication.task_id != claim.task_id:
            raise PortRefusal("PDF effect receipt differs from its logical request task")
        check_active()
        with execution_owner.engine.connect() as connection:
            actual = inspect_pdf_execution_receipt(
                connection,
                receipt.publication,
                attempt=claim.attempt,
                holder=claim.holder,
                replay_key="product:" + receipt.publication.product_key,
            )
        if actual != receipt:
            raise PortRefusal("PDF effect receipt differs from authenticated original publisher")
        check_active()
        return completion
