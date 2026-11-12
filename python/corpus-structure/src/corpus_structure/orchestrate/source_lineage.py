"""Immutable native operation provenance, separate from serialized semantic intent."""

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SourceOperationLink(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1] = 1
    operation_id: UUID = Field(default_factory=uuid4)
    role: Literal["capture", "primary", "analytical"]
    capture_run_id: int | None = Field(default=None, strict=True, gt=0)

    def options(self) -> dict:
        return {"source_operation": self.model_dump(mode="json")}
