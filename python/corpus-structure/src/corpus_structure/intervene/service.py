"""Typed retained-task inventory and protected operator-direction results."""

from __future__ import annotations

from pydantic import BaseModel


class ToolFailure(RuntimeError):
    """An envelope or infrastructure failure: reported with `isError`, naming the task."""


class QueueCount(BaseModel):
    run_id: int
    mode: str
    stage: str
    awaiting: int


class QueueStatus(BaseModel):
    queues: list[QueueCount]


class DirectionRecorded(BaseModel):
    intervention_id: int
    project: str
    file: str
