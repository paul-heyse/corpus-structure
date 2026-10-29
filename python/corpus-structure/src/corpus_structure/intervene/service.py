"""Typed current MCP queue, instruction and operation-log results.

SemanticAgentSession and SemanticProjectSession own the application effects.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from corpus_structure.semantic.proposals import ProposalIssue


class ToolFailure(RuntimeError):
    """An envelope or infrastructure failure: reported with `isError`, naming the task."""


class QueueCount(BaseModel):
    run_id: int
    mode: str
    stage: str
    awaiting: int


class QueueStatus(BaseModel):
    queues: list[QueueCount]
    budget_left: int | None = None  # the agent budget (D6 §7.4) is P0-O-2's; none in phase 0 yet


class LeasedTask(BaseModel):
    task_id: int
    run_id: int
    unit_key: str
    parts: int
    chars: int
    previous_issues: tuple[ProposalIssue, ...] = Field(
        default=(), exclude_if=lambda issues: not issues
    )


class QueueNext(BaseModel):
    tasks: list[LeasedTask]


class PartInfo(BaseModel):
    name: str
    chars: int
    pages: int
    hash: str


class Instructions(BaseModel):
    """The part list (`part` absent), or one page of one part."""

    task_id: int
    parts: list[PartInfo]
    part: str | None = None
    page: int | None = None
    page_count: int | None = None
    text: str | None = None


class Released(BaseModel):
    task_id: int
    released: bool
    reason: str


class DirectionRecorded(BaseModel):
    intervention_id: int
    project: str
    file: str
