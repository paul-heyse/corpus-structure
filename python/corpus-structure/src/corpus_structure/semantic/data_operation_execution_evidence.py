"""Typed physical execution custody, retained outside semantic product identity."""

from __future__ import annotations

import json
from functools import cache
from hashlib import sha256
from typing import Annotated, Literal

from jsonschema import Draft7Validator
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from corpus_structure.methods.characterization_resources import ProviderExecutionReceipt
from corpus_structure.methods.native_host import NativeExecutionReceipt

from .cpu_receipts import CPUExecutionReceipt
from .external_receipts import ExternalExecutionReceipt
from .identity import canonical_bytes
from .established_validity import ProductValidation
from .pdf_observations import PdfObservationExecutionReceipt
from .pdf_publication import PdfExecutionReceipt

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
    schema = TypeAdapter(NativeExecutionEvidence).json_schema(ref_template="#/definitions/{model}")
    if "$defs" in schema:
        schema["definitions"] = schema.pop("$defs")

    def close(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                node["additionalProperties"] = False
            if node.get("type") == "string":
                node.setdefault("minLength", 1)
            for value in node.values():
                close(value)
        elif isinstance(node, list):
            for value in node:
                close(value)

    close(schema)
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    Draft7Validator.check_schema(schema)
    return canonical_bytes(schema)


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
        "host_receipts": json.loads(content) if content is not None else [],
        "cpu_receipts": [json.loads(cpu_content)] if cpu_content is not None else [],
        "cpu_replies": [cpu_reply_content.decode("utf-8")] if cpu_reply_content is not None else [],
        "product_validations": [json.loads(product_validation_content)]
        if product_validation_content is not None else [],
        "pdf_receipts": [json.loads(pdf_content)] if pdf_content is not None else [],
        "pdf_observation_receipts": [json.loads(pdf_observation_content)]
        if pdf_observation_content is not None
        else [],
        "provider_receipts": json.loads(provider_content) if provider_content is not None else [],
        "external_receipts": json.loads(external_content) if external_content is not None else [],
    }
    Draft7Validator(json.loads(execution_evidence_schema())).validate(value)
    checked = NativeExecutionEvidence.model_validate_json(canonical_bytes(value))
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
