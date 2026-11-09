"""Read PM2 scope coverage from the run's authenticated worklist and task custody."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, case, cast, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH

from corpus_structure.semantic.metadata import table

if TYPE_CHECKING:
    from sqlalchemy import Connection

ScopeOutcome = Literal[
    "ineligible",
    "unscheduled",
    "pending",
    "running",
    "cancelled",
    "limited",
    "failed",
    "empty",
    "succeeded",
]


class ScopeIntent(BaseModel):
    """A bounded question on one selected source view, before task admission."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_view_id: int = Field(gt=0)
    extent: tuple[int, int]
    question: str
    operation_version: str
    disposition: Literal["scheduled", "ineligible", "unscheduled", "failed"]
    input_digest: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")
    parent_input_digest: str | None = Field(default=None, pattern="^[0-9a-f]{64}$")
    reason: str | None = None

    @model_validator(mode="after")
    def admitted_shape(self):
        if not 0 <= self.extent[0] < self.extent[1]:
            raise ValueError("invalid PM2 scope bounds")
        if self.disposition == "scheduled":
            if self.input_digest is None or self.reason is not None:
                raise ValueError("scheduled PM2 scope needs an admitted input identity")
        elif self.input_digest is not None or not self.reason:
            raise ValueError("unadmitted PM2 scope needs an explicit reason")
        return self


class ScopeCoverage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_view_id: int
    extent: tuple[int, int]
    question: str
    operation_version: str
    input_digest: str | None = None
    parent_input_digest: str | None = None
    outcome: ScopeOutcome
    provider_outcome: Literal["succeeded", "empty", "limited", "failed"] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    task_id: int | None = None
    origin_task_id: int | None = None
    inspected_count: int | None = Field(default=None, ge=0)
    emitted_count: int | None = Field(default=None, ge=0)
    reason: str | None = None


def scope_coverage(conn: Connection, run_id: int, intents: object) -> tuple[ScopeCoverage, ...]:
    """Attach task settlement without inventing an operation result for unattempted work."""
    if not isinstance(intents, list) or len(intents) > 64:
        raise ValueError("invalid PM2 scope worklist")
    worklist = [ScopeIntent.model_validate(item) for item in intents]
    hashes = [item.input_digest for item in worklist if item.input_digest is not None]
    rows = {}
    if hashes:
        task = table("ops.task")
        operation = table("kb.source_contribution_operation")
        result = table("ops.task_result")
        origin = func.coalesce(task.c.reused_task_id, task.c.id)
        # Read just the provider settlement from the lossless native report. Do not
        # hydrate complete rendered states, prompts or answer payloads for coverage.
        provider_outcome = cast(
            func.jsonb_path_query_first(
                result.c.body["parse_detail"],
                cast(
                    literal(
                        '$.fields[*] ? (@.name == "pm2_native").value.fields[*]'
                        ' ? (@.name == "native").value.fields[*] ? (@.name == "outcome").value'
                    ),
                    JSONPATH,
                ),
            ),
            JSONB,
        )["text"].astext
        task_rows = conn.execute(
            select(
                task.c.input_hash,
                task.c.id,
                task.c.unit_type,
                task.c.unit_id,
                task.c.reused_task_id,
                task.c.status,
                task.c.reason,
                task.c.trigger["pm2_split_scope"].label("split_scope"),
                operation.c.question,
                operation.c.operation_version,
                operation.c.outcome,
                case((operation.c.operation_version == "3", provider_outcome)).label(
                    "provider_outcome"
                ),
                operation.c.inspected_count.label("inspected"),
                operation.c.emitted_count.label("emitted"),
                case(
                    (
                        operation.c.outcome.in_(("limited", "failed")),
                        result.c.body["contribution_operations"][0]["reason"].astext,
                    )
                ).label("result_reason"),
            )
            .select_from(
                task.outerjoin(
                    operation,
                    and_(operation.c.task_id == origin, operation.c.position == 0),
                ).outerjoin(
                    result,
                    and_(
                        result.c.task_id == origin,
                        or_(
                            operation.c.outcome.in_(("limited", "failed")),
                            operation.c.operation_version == "3",
                        ),
                    ),
                )
            )
            .where(
                task.c.run_id == run_id,
                or_(
                    task.c.input_hash.in_(hashes),
                    task.c.trigger["pm2_split_scope"].astext.is_not(None),
                ),
            )
            .order_by(task.c.id)
            .limit(129)
        ).all()
        if len(task_rows) > 128:
            raise ValueError("PM2 scope coverage exceeds the admitted work bound")
        for row in task_rows:
            parent = None
            if row.split_scope is not None:
                item = ScopeIntent.model_validate(row.split_scope)
                parent = item.parent_input_digest
                if (
                    item.disposition != "scheduled"
                    or item.input_digest != row.input_hash
                    or not parent
                ):
                    raise ValueError("PM2 split scope differs from its admitted task")
                worklist.append(item)
            key = (row.input_hash, parent)
            if key in rows:
                raise ValueError("PM2 worklist has competing tasks for the same scope")
            rows[key] = row
    output = []
    for item in worklist:
        common = dict(
            source_view_id=item.source_view_id,
            extent=item.extent,
            question=item.question,
            operation_version=item.operation_version,
            input_digest=item.input_digest,
            parent_input_digest=item.parent_input_digest,
        )
        if item.disposition != "scheduled":
            output.append(
                ScopeCoverage(
                    **common,
                    outcome=item.disposition,
                    reason=item.reason,
                    inspected_count=0,
                    emitted_count=0,
                )
            )
            continue
        row = rows.get((item.input_digest, item.parent_input_digest))
        if row is None:
            raise ValueError("scheduled PM2 scope lacks its admitted task")
        if row.unit_type != "source_view" or row.unit_id != item.source_view_id:
            raise ValueError("PM2 scope source view differs from its admitted task")
        if row.question is not None and (
            row.question != item.question or row.operation_version != item.operation_version
        ):
            raise ValueError("PM2 result question differs from its admitted scope")
        outcome: ScopeOutcome
        if row.status == "cancelled":
            outcome = "cancelled"
        elif row.outcome in ("succeeded", "empty", "limited", "failed"):
            outcome = row.outcome
        elif row.status in ("pending", "running", "failed"):
            outcome = row.status
        else:
            raise ValueError("settled PM2 task lacks its typed operation outcome")
        output.append(
            ScopeCoverage(
                **common,
                outcome=outcome,
                provider_outcome=row.provider_outcome if outcome != "cancelled" else None,
                task_id=row.id,
                origin_task_id=row.reused_task_id or row.id if row.outcome is not None else None,
                inspected_count=row.inspected if outcome != "cancelled" else None,
                emitted_count=row.emitted if outcome != "cancelled" else None,
                reason=row.result_reason or row.reason,
            )
        )
    return tuple(output)
