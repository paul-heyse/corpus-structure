"""Typed physical execution custody, retained outside semantic product identity."""

from __future__ import annotations

from functools import cache
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from corpus_structure.methods.characterization_resources import ProviderExecutionReceipt
from corpus_structure.methods.native_host import NativeExecutionReceipt

from .cpu_receipts import CPUExecutionReceipt
from .data_operation_json import finite_json_bytes, finite_json_loads
from .established_validity import ProductValidation
from .external_receipts import ExternalExecutionReceipt
from .identity import canonical_bytes
from .pdf_observations import PdfObservationExecutionReceipt
from .pdf_publication import PdfExecutionReceipt
from .schema_validation import prepared_schema_validator

SOURCE = "native/data-operation-execution-evidence.schema.json"
_Identifier = Annotated[str, Field(strict=True, min_length=1)]
_Positive = Annotated[int, Field(strict=True, ge=1)]


class NativeExecutionEvidence(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    version: Literal["native-execution-evidence-v1"]
    request_id: _Identifier
    generation: _Positive
    task_id: _Positive
    attempt: _Positive
    holder: _Identifier
    runtime_id: _Identifier
    host_receipts: tuple[NativeExecutionReceipt, ...]
    cpu_receipts: tuple[CPUExecutionReceipt, ...]
    cpu_replies: tuple[str, ...] = ()
    product_validations: tuple[ProductValidation, ...] = ()
    pdf_receipts: tuple[PdfExecutionReceipt, ...] = ()
    pdf_observation_receipts: tuple[PdfObservationExecutionReceipt, ...] = ()
    provider_receipts: tuple[ProviderExecutionReceipt, ...] = ()
    external_receipts: tuple[ExternalExecutionReceipt, ...] = ()


@cache
def execution_evidence_schema() -> bytes:
    """Derive actual host fields; closed wire policy adds no parallel field inventory."""
    from .data_operation_wire import NativeJsonSchema

    schema = TypeAdapter(NativeExecutionEvidence).json_schema(
        ref_template="#/definitions/{model}", schema_generator=NativeJsonSchema, mode="validation"
    )
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    result = canonical_bytes(schema)
    prepared_schema_validator(result)
    return result


def bind_execution_evidence(
    content: bytes | None,
    *,
    fence: dict,
    runtime_id: str,
    cpu_content: bytes | None = None,
    cpu_reply_content: bytes | None = None,
    product_validation_content: bytes | None = None,
    pdf_content: bytes | None = None,
    pdf_observation_content: bytes | None = None,
    provider_content: bytes | None = None,
    external_content: bytes | None = None,
) -> dict:
    """Bind the capability's original matched host receipts to its native attempt."""
    value = {
        "version": "native-execution-evidence-v1",
        **fence,
        "runtime_id": runtime_id,
        "host_receipts": finite_json_loads(content) if content is not None else [],
        "cpu_receipts": [finite_json_loads(cpu_content)] if cpu_content is not None else [],
        "cpu_replies": [cpu_reply_content.decode("utf-8")] if cpu_reply_content is not None else [],
        "product_validations": [finite_json_loads(product_validation_content)]
        if product_validation_content is not None
        else [],
        "pdf_receipts": [finite_json_loads(pdf_content)] if pdf_content is not None else [],
        "pdf_observation_receipts": [finite_json_loads(pdf_observation_content)]
        if pdf_observation_content is not None
        else [],
        "provider_receipts": finite_json_loads(provider_content)
        if provider_content is not None
        else [],
        "external_receipts": finite_json_loads(external_content)
        if external_content is not None
        else [],
    }
    prepared_schema_validator(execution_evidence_schema()).validate(value)
    checked = NativeExecutionEvidence.model_validate_json(finite_json_bytes(value))
    if checked.cpu_replies and (
        len(checked.cpu_replies) != len(checked.cpu_receipts)
        or any(
            sha256(reply.encode("utf-8")).hexdigest() != receipt.result_digest
            for reply, receipt in zip(checked.cpu_replies, checked.cpu_receipts, strict=True)
        )
    ):
        raise ValueError("retained CPU reply differs from its actual execution receipt")
    claim = tuple(fence[name] for name in ("request_id", "generation", "task_id", "attempt"))
    for receipt in checked.pdf_observation_receipts:
        if (
            receipt.request_id,
            receipt.generation,
            receipt.task_id,
            receipt.attempt,
            receipt.holder,
            receipt.runtime_id,
        ) != (*claim, fence["holder"], runtime_id):
            raise ValueError("observation adoption receipt differs from native attempt/runtime")
    for receipt in checked.provider_receipts:
        # The existing provider handle validates work/cohort/scatter and actual
        # physical exchanges before handing over this typed receipt. Bind its
        # logical attribution to this exact native claim without replaying it.
        if not receipt.logical_members or any(
            (member.request_id, member.generation, member.task_id, member.attempt) != claim
            for member in receipt.logical_members
        ):
            raise ValueError("provider logical receipt differs from native attempt")
    for receipt in checked.external_receipts:
        if (
            receipt.request_id,
            receipt.generation,
            receipt.task_id,
            receipt.attempt,
            receipt.holder,
            receipt.runtime_id,
        ) != (*claim, fence["holder"], runtime_id):
            raise ValueError("external receipt differs from native attempt/runtime")
    return checked.model_dump(mode="json")
