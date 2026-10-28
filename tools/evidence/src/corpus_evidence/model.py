"""The evidence record: one finalized result of an investigation (ADR-0010).

A record says what was established, why it was investigated, how, from which inputs, with which
outputs and headline results, and what consumes it. It is written when a result is accepted, not
for every run; a revised result supersedes its record. Paths are relative to the record's evidence
folder; `finalize` fills the content hashes that let `check` notice an output changed afterwards.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SCHEMA_VERSION = 1

RecordId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9.\-]*$", max_length=80)]
# A reference to another record: `id` within the same folder, or `<folder>/<id>` across folders.
RecordRef = Annotated[
    str,
    StringConstraints(pattern=r"^([0-9]{4}-[0-9]{2}-[0-9]{2}_[a-z0-9\-]+/)?[a-z0-9][a-z0-9.\-]*$"),
]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FileRef(_Strict):
    """A file or directory in the evidence folder; a directory hashes as its sorted contents."""

    path: Annotated[str, StringConstraints(min_length=1)]
    role: str | None = Field(
        default=None, description="e.g. environment, input-batch, table, report"
    )
    sha256: Sha256 | None = Field(default=None, description="Filled by `finalize`")

    @model_validator(mode="after")
    def _relative(self) -> FileRef:
        if self.path.startswith("/") or ".." in self.path.split("/"):
            raise ValueError(f"path must be relative to the evidence folder: {self.path}")
        return self


class Result(_Strict):
    """A headline figure, stated with its denominator or unit when it has one."""

    name: str
    value: int | float | str | bool
    of: int | None = Field(
        default=None, description="Denominator, when the value is a count of something"
    )
    unit: str | None = None
    note: str | None = None


class AgentPass(_Strict):
    """An agent that produced part of the record's outputs (annotation, adjudication, analysis)."""

    role: str = Field(description="e.g. annotator pass A, adjudicator, executor")
    model: str = Field(description="Model name and version, e.g. Claude Opus 5.5")
    brief: str | None = Field(
        default=None, description="Path of the instructions it received, if kept"
    )
    separation: str | None = Field(
        default=None, description="How its inputs were bounded and audited"
    )


class Record(_Strict):
    schema_version: Literal[1] = SCHEMA_VERSION
    id: RecordId
    title: str = Field(min_length=3)
    group: str | None = Field(default=None, description="Grouping in indexes, e.g. the spike (S0)")
    package: str | None = Field(
        default=None, description="Plan package that produced it, e.g. S0-C"
    )
    finalized: dt.date
    status: Literal["current", "superseded"] = "current"
    supersedes: list[RecordRef] = Field(default_factory=list)
    superseded_by: RecordRef | None = None
    question: str = Field(min_length=3, description="Why it was investigated")
    answers: list[str] = Field(
        default_factory=list, description="Design or plan items it informs (OPEN-D1-1, ADR-0009)"
    )
    method: str = Field(min_length=3, description="How, in a sentence or two")
    commands: list[str] = Field(default_factory=list)
    agents: list[AgentPass] = Field(default_factory=list)
    inputs: list[FileRef] = Field(default_factory=list)
    outputs: list[FileRef] = Field(min_length=1)
    depends_on: list[RecordRef] = Field(
        default_factory=list, description="Records whose outputs it used"
    )
    results: list[Result] = Field(default_factory=list)
    outcome: Literal["passed", "failed", "blocked", "partial"]
    conclusion: str = Field(min_length=3)
    consumed_by: list[str] = Field(
        default_factory=list, description="Reports, plans, ADRs that rely on it"
    )

    @model_validator(mode="after")
    def _status(self) -> Record:
        if (self.status == "superseded") != (self.superseded_by is not None):
            raise ValueError("status 'superseded' and superseded_by must be set together")
        return self

    @property
    def files(self) -> list[tuple[str, FileRef]]:
        return [("input", f) for f in self.inputs] + [("output", f) for f in self.outputs]


def json_schema() -> dict:
    return Record.model_json_schema(mode="validation")
