"""Typed projections of protected operation results; native/model owners enforce semantics."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue

from corpus_structure.core.vocab import TaskUnitType


class OperationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class HeldProgress(OperationResult):
    attempt: int
    holder: str
    packet_hash: str
    result: dict[str, JsonValue]


class ClaimedTask(OperationResult):
    task_id: int
    run_id: int
    release_id: str
    method_config_id: int
    unit_type: TaskUnitType
    unit_id: int | None
    unit_key: str | None
    packet_hash: str | None
    attempt: int
    holder: str
    deadline: datetime
    invocation_key: str
    held_progress: HeldProgress | None


class CompletionReceipt(OperationResult):
    task_id: int
    run_id: int
    release_id: str
    attempt: int
    protocol: Literal["done", "empty", "failed"]
    observation_ids: tuple[int, ...]
    result_digest: str


class CompletionResult(OperationResult):
    receipt: CompletionReceipt
    transaction: Literal["applied", "replay"]


class HoldDecision(OperationResult):
    task_id: int
    attempt: int
    packet_hash: str
    disposition: Literal["held", "proceed"]
