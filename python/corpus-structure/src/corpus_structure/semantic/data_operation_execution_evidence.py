"""Typed physical execution custody, retained outside semantic product identity."""

from __future__ import annotations

import json
from functools import cache
from typing import Annotated, Literal

from jsonschema import Draft7Validator
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from corpus_structure.methods.native_host import NativeExecutionReceipt

from .cpu_receipts import CPUExecutionReceipt
from .identity import canonical_bytes

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
) -> dict:
    """Bind the capability's original matched host receipts to its native attempt."""
    value = {
        "version": "native-execution-evidence-v1",
        **fence,
        "runtime_id": runtime_id,
        "host_receipts": json.loads(content) if content is not None else [],
        "cpu_receipts": [json.loads(cpu_content)] if cpu_content is not None else [],
    }
    Draft7Validator(json.loads(execution_evidence_schema())).validate(value)
    checked = NativeExecutionEvidence.model_validate_json(canonical_bytes(value))
    return checked.model_dump(mode="json")
