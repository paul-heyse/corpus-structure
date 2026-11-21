"""Actual native admission of an external assertion; model identity remains asserted."""

from dataclasses import dataclass
from typing import Annotated, ClassVar, Literal

from pydantic import ConfigDict, Field


@dataclass(frozen=True)
class ExternalExecutionReceipt:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)

    version: Literal["external-execution-receipt-v1"]
    receipt_id: Annotated[str, Field(min_length=1)]
    packet_id: Annotated[str, Field(min_length=1)]
    packet_digest: Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")]
    request_id: Annotated[str, Field(min_length=1)]
    generation: Annotated[int, Field(ge=1)]
    task_id: Annotated[int, Field(ge=1)]
    attempt: Annotated[int, Field(ge=1)]
    holder: Annotated[str, Field(min_length=1)]
    runtime_id: Annotated[str, Field(min_length=1)]
    admitting_principal: Annotated[str, Field(min_length=1)]
    actor_assertion: Annotated[str, Field(min_length=1)]
    model_assertion: Annotated[str, Field(min_length=1)] | None
    result_digest: Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")]
