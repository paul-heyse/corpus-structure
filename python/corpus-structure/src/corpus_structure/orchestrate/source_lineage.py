"""Read-only shape of sealed historical source-operation associations.

Current execution and recovery are keyed by native demand IDs. This reader keeps
only exact previously recorded lineage; it cannot allocate a new operation ID or
construct execution options.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceOperationLink(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1] = 1
    operation_id: UUID
    role: Literal["capture", "primary", "analytical"]
    capture_run_id: int | None = Field(default=None, strict=True, gt=0)
