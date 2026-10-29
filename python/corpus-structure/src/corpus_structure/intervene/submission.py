"""Typed automated semantic proposal outcomes shared by MCP and fixture consumers."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel

class ItemIssue(BaseModel):
    path: str
    category: str
    code: str
    message: str


class QuoteIssue(BaseModel):
    path: str
    quote: str
    sentence: str | None
    outcome: Literal["coarse", "dropped"]
    code: str | None = None


class RuleFinding(BaseModel):
    rule: str
    severity: str
    claim: str
    message: str


class SubmissionResult(BaseModel):
    submission_disposition: (
        Literal["held", "completed_accepted", "completed_refused", "refused_context"] | None
    ) = None
    task_id: int
    status: Literal["held", "done", "empty", "not_open"]
    task_open: bool
    reason: str | None = None  # why a task is not open: twin_settled, cancelled, leased_again, …
    rejected: list[ItemIssue] = []
    quotes: list[QuoteIssue] = []
    dropped: list[ItemIssue] = []
    findings: list[RuleFinding] = []
    accepted: dict[str, int] = {}
    observation_id: int | None = None
    cascade_version: str | None = None

    @property
    def clean(self) -> bool:
        return not (self.rejected or self.quotes or self.dropped or self.findings)
