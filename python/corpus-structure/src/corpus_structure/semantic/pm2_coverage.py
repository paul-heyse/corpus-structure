"""Read PM2 scope coverage from the run's authenticated worklist and task custody."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, case, cast, func, literal, or_, select, true
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH

from corpus_structure.core.vocab import TaskStatus
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.refusals import SemanticRefusal

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


class ScopeSettlement(BaseModel):
    """Selected task custody and the first, scope-level operation result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int = Field(gt=0)
    input_hash: str = Field(pattern="^[0-9a-f]{64}$")
    unit_type: str
    unit_id: int
    reused_task_id: int | None
    status: TaskStatus
    reason: str | None
    split_scope: ScopeIntent | None
    question: str | None
    operation_version: str | None
    outcome: Literal["succeeded", "empty", "limited", "failed"] | None
    provider_outcome: Literal["succeeded", "empty", "limited", "failed"] | None
    inspected: int | None = Field(ge=0)
    emitted: int | None = Field(ge=0)
    result_reason: str | None
    cut_origin: int | None = None


class ScopeWorklist(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    intents: tuple[ScopeIntent, ...] = Field(max_length=64)
    settlements: tuple[ScopeSettlement, ...] = Field(max_length=128)

    def select(self, source_view_id: int | None, task_id: int | None) -> ScopeWorklist:
        """Retain only the selected population and any split ancestors."""
        if task_id is None:
            return ScopeWorklist(
                intents=tuple(
                    intent
                    for intent in self.intents
                    if source_view_id is None or intent.source_view_id == source_view_id
                ),
                settlements=tuple(
                    row
                    for row in self.settlements
                    if source_view_id is None or row.unit_id == source_view_id
                ),
            )
        by_digest = {row.input_hash: row for row in self.settlements}
        row = next(
            (
                row
                for row in self.settlements
                if row.id == task_id and (source_view_id is None or source_view_id == row.unit_id)
            ),
            None,
        )
        keep = set()
        while row is not None:
            if row.input_hash in keep:
                raise ValueError("PM2 split worklist has a cycle")
            keep.add(row.input_hash)
            if row.split_scope is None:
                break
            parent = row.split_scope.parent_input_digest
            row = by_digest.get(parent) if parent is not None else None
            if row is None:
                raise ValueError("PM2 split worklist is missing its parent")
        return ScopeWorklist(
            intents=tuple(intent for intent in self.intents if intent.input_digest in keep),
            settlements=tuple(row for row in self.settlements if row.input_hash in keep),
        )


def read_scope_worklist(
    conn: Connection,
    run_id: int,
    intents: object,
    *,
    cut_id: int | None = None,
    source_view_id: int | None = None,
    question: str | None = None,
    operation_version: str | None = None,
    resident_intents: bool = False,
) -> ScopeWorklist:
    """Collect bounded source-task receipts in the caller's snapshot."""
    if not isinstance(intents, list) or len(intents) > 64:
        raise ValueError("invalid PM2 scope worklist")
    worklist = [ScopeIntent.model_validate(item) for item in intents]
    worklist = [
        item
        for item in worklist
        if (source_view_id is None or item.source_view_id == source_view_id)
        and (question is None or item.question == question)
        and (operation_version is None or item.operation_version == operation_version)
    ]
    hashes = [item.input_digest for item in worklist if item.input_digest is not None]
    settlements = ()
    if hashes:
        task = table("ops.task")
        operation = table("kb.source_contribution_operation")
        result = table("ops.task_result")
        # Completed reads derive hashes from the retained resident declaration. Live
        # pre-persistence callers can still supply their bounded initial intents.
        run = table("ops.run")
        root_source = (
            run.c.options["pm2_scope_intents"]
            if resident_intents
            else literal([item.model_dump(mode="json") for item in worklist], type_=JSONB)
        )
        root_rows = func.jsonb_array_elements(root_source).table_valued("value")
        seed = select(root_rows.c.value.op("->>")("input_digest").label("input_hash")).where(
            root_rows.c.value.op("->>")("input_digest").is_not(None)
        )
        if resident_intents:
            seed = seed.select_from(run.join(root_rows, true())).where(run.c.id == run_id)
            for field, value in (
                ("source_view_id", source_view_id),
                ("question", question),
                ("operation_version", operation_version),
            ):
                if value is not None:
                    seed = seed.where(root_rows.c.value.op("->>")(field) == str(value))
        # UNION terminates even malformed cycles; shared custody validation refuses them.
        selected_hashes = seed.cte("selected_scope_hashes", recursive=True)
        selected_hashes = selected_hashes.union(
            select(task.c.input_hash)
            .join(
                selected_hashes,
                task.c.trigger["pm2_split_scope"]["parent_input_digest"].astext
                == selected_hashes.c.input_hash,
            )
            .where(task.c.run_id == run_id)
        )
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
        query = (
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
                task.c.input_hash.in_(select(selected_hashes.c.input_hash)),
            )
            .order_by(task.c.id)
            .limit(129)
        )
        if cut_id is not None:
            member = table("ops.cut_task")
            query = query.outerjoin(
                member, and_(member.c.cut_id == cut_id, member.c.task_id == task.c.id)
            ).add_columns(member.c.origin_task_id.label("cut_origin"))
        task_rows = conn.execute(query).mappings().all()
        if len(task_rows) > 128:
            raise ValueError("PM2 scope coverage exceeds the admitted work bound")
        settlements = tuple(ScopeSettlement.model_validate(row) for row in task_rows)
    return ScopeWorklist(intents=tuple(worklist), settlements=settlements)


def derive_scope_coverage(
    evidence: ScopeWorklist, *, completed: bool = False
) -> tuple[ScopeCoverage, ...]:
    """Derive the same ordered outcome rows for live reads and detached replay."""
    worklist = list(evidence.intents)
    intents = {item.input_digest: item for item in worklist if item.input_digest is not None}
    if len(intents) != sum(item.input_digest is not None for item in worklist):
        raise ValueError("PM2 worklist has competing scope intents")
    if any(item.parent_input_digest is not None for item in worklist):
        raise ValueError("initial PM2 worklist cannot declare split parents")
    rows: dict[str, ScopeSettlement] = {}
    previous = 0
    for row in evidence.settlements:
        if row.id <= previous:
            raise ValueError("PM2 task worklist is not in admission order")
        previous = row.id
        parent = None
        if row.split_scope is not None:
            item = row.split_scope
            parent = item.parent_input_digest
            parent_intent = intents.get(parent) if parent is not None else None
            parent_row = rows.get(parent) if parent is not None else None
            if (
                item.disposition != "scheduled"
                or item.input_digest != row.input_hash
                or parent_intent is None
                or parent_row is None
                or parent_row.outcome != "limited"
                or (
                    parent_intent.source_view_id,
                    parent_intent.question,
                    parent_intent.operation_version,
                )
                != (item.source_view_id, item.question, item.operation_version)
                or not (
                    parent_intent.extent[0]
                    <= item.extent[0]
                    < item.extent[1]
                    <= parent_intent.extent[1]
                )
                or item.extent == parent_intent.extent
            ):
                raise ValueError("PM2 split scope differs from its admitted parent")
            if row.input_hash in intents:
                raise ValueError("PM2 worklist has competing scope intents")
            intents[row.input_hash] = item
            worklist.append(item)
        if row.input_hash in rows:
            raise ValueError("PM2 worklist has competing tasks for the same scope")
        rows[row.input_hash] = row
    if set(rows) != set(intents):
        raise ValueError("PM2 scope worklist differs from its admitted task population")
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
        row = rows.get(item.input_digest) if item.input_digest is not None else None
        if row is None:
            raise ValueError("scheduled PM2 scope lacks its admitted task")
        if row.unit_type != "source_view" or row.unit_id != item.source_view_id:
            raise ValueError("PM2 scope source view differs from its admitted task")
        if row.question is not None and (
            row.question != item.question or row.operation_version != item.operation_version
        ):
            raise ValueError("PM2 result question differs from its admitted scope")
        if completed:
            if row.status in {"pending", "running", "awaiting_agent"}:
                raise ValueError("completed PM2 worklist has an unsettled task")
            if (row.status == "reused") != (row.reused_task_id is not None):
                raise ValueError("PM2 reused task lacks matching origin custody")
            if row.status == "cancelled" and row.outcome is not None:
                raise ValueError("cancelled PM2 task cannot claim an operation result")
            expected_origin = (
                row.reused_task_id or row.id if row.status in {"done", "empty", "reused"} else None
            )
            if row.cut_origin != expected_origin:
                raise ValueError("PM2 task origin differs from its completed cut custody")
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


def scope_coverage(conn: Connection, run_id: int, intents: object) -> tuple[ScopeCoverage, ...]:
    """Attach task settlement without inventing an operation result for unattempted work."""
    return derive_scope_coverage(read_scope_worklist(conn, run_id, intents))


def completed_scope_worklist(
    conn: Connection,
    *,
    run_id: int,
    cut_id: int,
    release_id: str,
    source_view_id: int | None = None,
    question: str | None = None,
    operation_version: str | None = None,
) -> ScopeWorklist:
    """Capture from the immutable final run and its exact completed cut."""
    run, cut, result = (table("ops.run"), table("ops.input_cut"), table("ops.completed_result"))
    options = conn.scalar(
        select(run.c.options["pm2_scope_intents"])
        .join(cut, and_(cut.c.run_id == run.c.id, cut.c.release_id == run.c.release_id))
        .join(
            result,
            and_(
                result.c.run_id == run.c.id,
                result.c.cut_id == cut.c.id,
                result.c.release_id == run.c.release_id,
            ),
        )
        .where(
            run.c.id == run_id,
            run.c.release_id == release_id,
            run.c.sealed,
            run.c.status == "finished",
            cut.c.id == cut_id,
            cut.c.final,
        )
    )
    if options is None:
        raise SemanticRefusal(
            "detached PM2 coverage requires a completed run with a retained worklist"
        )
    worklist = read_scope_worklist(
        conn,
        run_id,
        options,
        cut_id=cut_id,
        source_view_id=source_view_id,
        question=question,
        operation_version=operation_version,
        resident_intents=True,
    )
    derive_scope_coverage(worklist, completed=True)
    return worklist
