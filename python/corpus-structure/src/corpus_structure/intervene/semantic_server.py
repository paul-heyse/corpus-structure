"""The existing extraction tool names over explicitly selected semantic runs."""

from __future__ import annotations

import secrets
import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.lifespan import lifespan
from fastmcp.tools import ToolResult
from pydantic import BaseModel, ConfigDict, JsonValue, TypeAdapter, ValidationError
from sqlalchemy import Engine, func, select

from corpus_structure.intervene import service, submission
from corpus_structure.intervene.semantic import ProposalSession, RefusedProposal
from corpus_structure.semantic.operations import OperationConflict
from corpus_structure.semantic.proposals import ProposalIssue, ProposalRefused
from corpus_structure.semantic.types import PreparedRelease
from corpus_structure.settings import Settings


class SemanticUnitPart(BaseModel):
    """One exact fragment; concatenate all numbered parts before decoding the unit JSON."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    task_id: int
    part: int
    parts: int
    hash: str
    text: str


class ProposalTaskNotOpen(ProposalRefused):
    """The submitted attempt cannot append source results."""


@dataclass
class SemanticAgentSession:
    engine: Engine
    run_id: int
    instance: str = field(default_factory=lambda: "mcp-semantic-" + secrets.token_hex(6))
    prepared: PreparedRelease | None = None
    sessions: dict[int, ProposalSession] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    @property
    def holder(self) -> str:
        return "agent:" + self.instance

    def interpretation(self) -> PreparedRelease:
        from corpus_structure.semantic.metadata import table
        from corpus_structure.semantic.releases import load_release

        with self.lock:
            if self.prepared is None:
                with self.engine.connect() as conn:
                    runs = table("ops.run")
                    release_id = conn.execute(
                        select(runs.c.release_id).where(runs.c.id == self.run_id)
                    ).scalar_one()
                    self.prepared = load_release(conn, release_id)
            return self.prepared

    def active(self, task_id: int) -> ProposalSession:
        from corpus_structure.orchestrate.semantic import agent_packet

        with self.lock:
            session = self.sessions.get(task_id)
            if session is None:
                raise ProposalTaskNotOpen(
                    "task is not leased by this session or has already finished"
                )
            with self.engine.begin() as conn:
                from corpus_structure.semantic.operations import renew_claim

                try:
                    renew_claim(conn, task_id=task_id, attempt=session.attempt, holder=self.holder)
                except OperationConflict as error:
                    raise ProposalTaskNotOpen(str(error)) from error
                packet = agent_packet(conn, self.run_id, task_id, self.interpretation())
            if packet.hash != session.packet.hash:
                raise ProposalRefused("recorded source packet changed after it was served")
            return session

    def status(self) -> service.QueueStatus:
        from corpus_structure.semantic.metadata import table

        tasks, configs = table("ops.task"), table("ops.method_config")
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(tasks.c.stage, configs.c.params, func.count().label("n"))
                .join(configs, configs.c.id == tasks.c.method_config_id)
                .where(tasks.c.run_id == self.run_id, tasks.c.status == "awaiting_agent")
                .group_by(tasks.c.stage, configs.c.params)
            ).mappings()
            return service.QueueStatus(
                queues=[
                    service.QueueCount(
                        run_id=self.run_id,
                        stage=row["stage"],
                        mode=row["params"].get("mode", "extract"),
                        awaiting=row["n"],
                    )
                    for row in rows
                ]
            )

    def next(self, mode: str, max_units: int | None) -> service.QueueNext:
        from corpus_structure.orchestrate.semantic import agent_packet
        from corpus_structure.semantic.metadata import table
        from corpus_structure.semantic.operations import claim_tasks

        configs, methods = table("ops.method_config"), table("ops.method")
        prepared = self.interpretation()
        if max_units is not None and max_units < 1:
            raise ProposalRefused("max_units must be positive")
        out = []
        with self.lock, self.engine.begin() as conn:
            rows = conn.execute(
                select(configs.c.id, configs.c.params)
                .join(methods, methods.c.id == configs.c.method_id)
                .where(methods.c.name == "agent.opus")
            ).mappings()
            for row in rows:
                if row["params"].get("mode", "extract") != mode:
                    continue
                limit = min(max_units or 1, row["params"].get("max_units", 1))
                leased = claim_tasks(
                    conn,
                    run_id=self.run_id,
                    config_id=row["id"],
                    holder=self.holder,
                    limit=limit,
                    agent=True,
                )
                for task in leased:
                    packet = agent_packet(conn, self.run_id, task.task_id, prepared)
                    if packet.hash != task.packet_hash:
                        raise ProposalRefused(
                            "queued task does not match its recorded source packet"
                        )
                    session = ProposalSession(
                        prepared, packet, task.task_id, task.attempt, self.holder
                    )
                    self.sessions[task.task_id] = session
                    pages = packet.part_pages(
                        next(part for part in packet.parts() if part.name == "unit")
                    )
                    out.append(
                        service.LeasedTask(
                            task_id=task.task_id,
                            run_id=self.run_id,
                            unit_key=packet.frame.unit_ref,
                            parts=len(pages),
                            chars=sum(map(len, pages)),
                            previous_issues=TypeAdapter(tuple[ProposalIssue, ...]).validate_python(
                                task.held_progress.result.get("issues", ())
                                if task.held_progress
                                else ()
                            ),
                        )
                    )
                if out:
                    break
        return service.QueueNext(tasks=out)


def build_semantic_server(
    session: SemanticAgentSession | None = None,
    *,
    run_id: int | None = None,
    settings: Settings | None = None,
) -> FastMCP:
    if session is None and run_id is None:
        raise ValueError("semantic MCP requires an explicit run")

    @lifespan
    async def open_session(server: FastMCP) -> AsyncIterator[dict[str, SemanticAgentSession]]:
        if session is not None:
            yield {"session": session}
            return
        from corpus_structure.core.db.store import open_store
        from corpus_structure.settings import Settings

        selected = settings if settings is not None else Settings()
        assert run_id is not None
        with open_store(selected, "ci-mcp-semantic", max_size=4) as store:
            yield {"session": SemanticAgentSession(store.engine, run_id)}

    server = FastMCP(
        "corpus-structure",
        instructions=(
            "Automated extraction for a release-bound run. Lease a unit using queue_next, "
            "read every "
            "instruction page (including schema) with read_instructions and every unit part with "
            "read_unit. Concatenate numbered unit text fragments and parse their JSON after every "
            "part is read, then submit the rich authored batch with propose_claims. "
            "A first uncertain or content-refused submission is held for automated correction; "
            "the second is retained as a terminal source report with its uncertainty or refusal. "
            "Packet, schema-hash and unread-part errors do not consume that content retry. "
            "On a reclaimed lease, previous_issues contains the stored feedback to correct. "
            "Source issues require "
            "automated correction; no human grading is required."
        ),
        lifespan=open_session,
    )

    def current(ctx: Context) -> SemanticAgentSession:
        return ctx.lifespan_context["session"]

    def bound_run(ctx: Context, run: int | None) -> SemanticAgentSession:
        found = current(ctx)
        if run is not None and run != found.run_id:
            raise ToolError("this server is bound to a different semantic run")
        return found

    @server.tool
    def queue_status(ctx: Context, run: int | None = None) -> service.QueueStatus:
        return bound_run(ctx, run).status()

    @server.tool
    def queue_next(
        ctx: Context,
        mode: Literal["extract", "adjudicate"] = "extract",
        run: int | None = None,
        max_units: int | None = None,
    ) -> service.QueueNext:
        try:
            return bound_run(ctx, run).next(mode, max_units)
        except (ProposalRefused, OperationConflict) as error:
            raise ToolError(str(error)) from None

    @server.tool
    def read_unit(ctx: Context, task_id: int, part: int = 1) -> ToolResult:
        try:
            active = current(ctx).active(task_id)
            body = active.read("unit", part)
            pages = active.packet.part_pages(
                next(item for item in active.packet.parts() if item.name == "unit")
            )
            structured = SemanticUnitPart(
                task_id=task_id,
                part=part,
                parts=len(pages),
                hash=active.packet.hash,
                text=body,
            )
            return ToolResult(content=body, structured_content=structured.model_dump(mode="json"))
        except (ProposalRefused, OperationConflict) as error:
            raise ToolError(str(error)) from None

    @server.tool
    def read_instructions(
        ctx: Context, task_id: int, part: str | None = None, page: int = 1
    ) -> service.Instructions:
        try:
            active = current(ctx).active(task_id)
            instructions = [item for item in active.packet.parts() if item.name != "unit"]
            infos = [
                service.PartInfo(
                    name=item.name,
                    chars=len(item.text),
                    pages=len(active.packet.part_pages(item)),
                    hash=item.hash,
                )
                for item in instructions
            ]
            if part is None:
                return service.Instructions(task_id=task_id, parts=infos)
            item = next((item for item in instructions if item.name == part), None)
            if item is None:
                raise ProposalRefused("unknown instruction part")
            return service.Instructions(
                task_id=task_id,
                parts=infos,
                part=part,
                page=page,
                page_count=len(active.packet.part_pages(item)),
                text=active.read(part, page),
            )
        except (ProposalRefused, OperationConflict) as error:
            raise ToolError(str(error)) from None

    @server.tool
    def propose_claims(
        ctx: Context,
        task_id: int,
        batch: dict[str, JsonValue],
        schema_hash: str | None = None,
        rationale: str | None = None,
    ) -> submission.SubmissionResult:
        from corpus_structure.semantic.operations import OperationConflict

        session = current(ctx)
        try:
            active = session.active(task_id)
            checked = active.check(
                batch,
                packet_hash=active.packet.hash,
                schema_hash=schema_hash or active.packet.schema_hash,
            )
            with session.engine.begin() as conn:
                result = active.commit(conn, checked)
            if result.disposition == "held":
                return submission.SubmissionResult(
                    task_id=task_id,
                    status="held",
                    submission_disposition="held",
                    task_open=True,
                    rejected=[
                        submission.ItemIssue(
                            path=issue.path, category="parse", code=issue.code, message=issue.detail
                        )
                        for issue in checked.issues
                    ],
                )
            session.sessions.pop(task_id, None)
            data = {} if isinstance(checked, RefusedProposal) else checked.stored.model_dump()
            return submission.SubmissionResult(
                task_id=task_id,
                status="done",
                task_open=False,
                submission_disposition=result.disposition,
                observation_id=result.completion.receipt.observation_ids[0],
                rejected=[
                    submission.ItemIssue(
                        path=issue.path, category="parse", code=issue.code, message=issue.detail
                    )
                    for issue in checked.issues
                ],
                accepted={
                    name: len(data.get(name, ()))
                    for name in ("entities", "statements", "claims", "alternatives", "unsupported")
                },
            )
        except (OperationConflict, ProposalTaskNotOpen) as error:
            return submission.SubmissionResult(
                task_id=task_id,
                status="not_open",
                submission_disposition="refused_context",
                task_open=False,
                reason=str(error),
            )
        except (ProposalRefused, ValidationError) as error:
            return submission.SubmissionResult(
                task_id=task_id,
                status="held",
                submission_disposition="refused_context",
                task_open=True,
                rejected=[
                    submission.ItemIssue(
                        path="$", category="envelope", code="proposal_invalid", message=str(error)
                    )
                ],
            )

    @server.tool
    def release(ctx: Context, task_id: int, reason: str) -> service.Released:
        try:
            active = current(ctx).active(task_id)
            from corpus_structure.semantic.operations import release_claim

            with current(ctx).engine.begin() as conn:
                release_claim(
                    conn,
                    task_id=task_id,
                    attempt=active.attempt,
                    holder=active.holder,
                    reason=reason,
                )
            current(ctx).sessions.pop(task_id, None)
            return service.Released(task_id=task_id, released=True, reason=reason)
        except (ProposalRefused, OperationConflict) as error:
            raise ToolError(str(error)) from None

    return server
