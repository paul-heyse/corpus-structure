"""The existing extraction tool names over explicitly selected semantic runs."""

from __future__ import annotations

import secrets
import threading
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Annotated, Literal

from fastmcp import Context, FastMCP
from fastmcp import __version__ as FASTMCP_VERSION
from fastmcp.exceptions import ToolError
from fastmcp.server.lifespan import lifespan
from fastmcp.tools import ToolResult
from fastmcp.utilities.json_schema import compress_schema
from mcp.types import CallToolResult, Implementation
from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, ValidationError
from sqlalchemy import Engine, func, select

from corpus_structure.intervene import service, submission
from corpus_structure.intervene.semantic import ProposalSession, RefusedProposal
from corpus_structure.semantic.operation_results import MethodConfigId, RunId
from corpus_structure.semantic.operations import OperationConflict
from corpus_structure.semantic.proposals import ProposalIssue, ProposalRefused
from corpus_structure.semantic.refusals import located_failure_context, tool_refusals
from corpus_structure.semantic.types import PreparedRelease
from corpus_structure.serve.native_source import NativeSourceRequest, NativeSourceResponse
from corpus_structure.serve.source_search import SourceSearchRequest, SourceSearchResponse
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


def _require_queue_mode(mode: str) -> None:
    """The current proposal queue executes extraction, not reference adjudication."""
    if mode != "extract":
        raise ProposalRefused(f"unsupported proposal queue mode: {mode!r}; expected 'extract'")


MCP_SERVER_NAME = "corpus-structure"
QUEUE_ACK_MAX_BYTES = 8 * 1024 * 1024
READ_UNIT_MAX_BYTES = 8 * 1024 * 1024


def _stamp_mcp_result(wire: CallToolResult) -> CallToolResult:
    """Include SDK delivery metadata before admitting any bounded tool result."""
    meta = dict(wire.meta or {})
    key = "io.modelcontextprotocol/serverInfo"
    if meta.get(key) is None:
        meta[key] = Implementation(name=MCP_SERVER_NAME, version=FASTMCP_VERSION).model_dump(
            mode="json", by_alias=True, exclude_none=True
        )
    return wire.model_copy(update={"meta": meta})


def _bounded_mcp_result(value: BaseModel, max_bytes: int) -> ToolResult:
    """Admit the actual full text-plus-structured result, retaining its exact wire form."""
    from corpus_structure.semantic.query import ReadLimit

    encoded = ToolResult(content=value, structured_content=value.model_dump(mode="json"))
    # The pinned SDK stamps this identity after dispatch on modern protocols. Author
    # that same SDK-shaped metadata here so admission includes the final stamp, and
    # the runner preserves it. Legacy protocols can carry this optional metadata;
    # their serializer may omit resultType, so this complete-result bound remains safe.
    wire = _stamp_mcp_result(
        CallToolResult(
            content=encoded.content,
            structured_content=encoded.structured_content,
        )
    )
    if len(wire.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")) > max_bytes:
        raise ReadLimit("complete MCP response exceeds byte budget", reason="oversized_item")
    return ToolResult.from_mcp_result(wire)


def _invocation_event(task_id, attempt, holder, binding, event, **details):
    """Link the actual leased attempt and native receipt to the automation's retained invocation."""
    import json
    import os
    from pathlib import Path
    from uuid import uuid4

    directory = os.environ.get("CORPUS_AGENT_RECEIPTS")
    invocation = os.environ.get("CORPUS_AGENT_INVOCATION_ID")
    if directory is None or invocation is None:
        return
    path = Path(directory) / f"task-{task_id}-attempt-{attempt}-{event}-{uuid4().hex}.json"
    with path.open("x") as stream:
        json.dump(
            {
                "invocation_id": invocation,
                "task_id": task_id,
                "attempt": attempt,
                "holder": holder,
                "producer_binding": binding,
                "event": event,
                "assurance": "provider_reported",
                **details,
            },
            stream,
            sort_keys=True,
        )
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _rendered_artifact_result(engine, result, max_bytes):
    """Bound inline MCP delivery after durable rendering, before artifact materialization."""
    from dataclasses import asdict

    from fastmcp.utilities.types import Image
    from mcp.types import ImageContent, TextContent

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.query import read_snapshot

    if type(max_bytes) is not int or not 1024 <= max_bytes <= 8 * 1024 * 1024:
        raise ValueError("inline image max_bytes must be between 1024 and 8388608")
    if result.artifact_digest is None:
        raise ValueError("rendered source has no retained artifact reference")
    structured = asdict(result)
    artifact = table("kb.source_artifact")

    def wire(content, body, *, refused=False):
        return _stamp_mcp_result(
            CallToolResult(content=content, structured_content=body, is_error=refused)
        )

    def size(response):
        return len(response.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8"))

    def refusal(raw_bytes, required):
        body = dict(
            structured,
            inline_image=dict(
                disposition="refused",
                reason="oversized_item",
                media_type="image/png",
                artifact_bytes=raw_bytes,
                required_bytes=required,
                max_bytes=max_bytes,
            ),
        )
        response = wire(
            [
                TextContent(
                    type="text",
                    text=(
                        "Rendered artifact is committed; inline image exceeds max_bytes. "
                        "Use the retained artifact reference."
                    ),
                )
            ],
            body,
            refused=True,
        )
        if size(response) > max_bytes:
            # The minimum supported budget is sized for a reference-only refusal,
            # independently of any potentially large optional native result detail.
            body = {
                key: structured[key]
                for key in ("run_id", "task_id", "source_view_id", "artifact_digest")
            }
            body["inline_image"] = {"disposition": "refused", "reason": "oversized_item"}
            response = wire(
                [TextContent(type="text", text="Inline image refused; artifact retained.")],
                body,
                refused=True,
            )
            if size(response) > max_bytes:
                raise ValueError("retained artifact reference exceeds inline response budget")
        return ToolResult.from_mcp_result(response)

    with read_snapshot(engine) as conn:
        length = conn.execute(
            select(func.octet_length(artifact.c.content)).where(
                artifact.c.artifact_digest == result.artifact_digest
            )
        ).scalar_one()
        body = dict(
            structured,
            inline_image=dict(
                disposition="included",
                media_type="image/png",
                artifact_bytes=length,
                max_bytes=max_bytes,
            ),
        )
        empty = wire([ImageContent(type="image", data="", mime_type="image/png")], body)
        required = size(empty) + 4 * ((length + 2) // 3)
        if required > max_bytes:
            return refusal(length, required)
        content = bytes(
            conn.execute(
                select(artifact.c.content).where(
                    artifact.c.artifact_digest == result.artifact_digest
                )
            ).scalar_one()
        )
    response = wire([Image(data=content, format="png").to_image_content()], body)
    actual = size(response)
    if actual > max_bytes:
        return refusal(length, actual)
    return ToolResult.from_mcp_result(response)


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
        from corpus_structure.semantic.releases import open_release

        with self.lock:
            if self.prepared is None:
                with self.engine.connect() as conn:
                    runs = table("ops.run")
                    release_id = conn.execute(
                        select(runs.c.release_id).where(runs.c.id == self.run_id)
                    ).scalar_one()
                    self.prepared = open_release(conn, release_id)
            return self.prepared

    def active(self, task_id: int) -> ProposalSession:

        with self.lock:
            session = self.sessions.get(task_id)
            if session is None:
                raise ProposalTaskNotOpen(
                    "task is not leased by this session or has already finished"
                )
            with self.engine.begin() as conn:
                from corpus_structure.semantic.operations import renew_claim

                try:
                    renew_claim(
                        conn,
                        task_id=session.task_id,
                        attempt=session.attempt,
                        holder=self.holder,
                    )
                except OperationConflict as error:
                    raise ProposalTaskNotOpen(str(error)) from error
                from corpus_structure.semantic.metadata import table
                from corpus_structure.semantic.operations import lock_input_snapshot

                lock_input_snapshot(conn, self.run_id)
                tasks = table("ops.task")
                packet_hash = conn.execute(
                    select(tasks.c.packet_hash).where(
                        tasks.c.id == task_id,
                        tasks.c.run_id == self.run_id,
                        tasks.c.release_id == session.prepared.release_id,
                    )
                ).scalar_one_or_none()
                if packet_hash != session.packet.hash:
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
        _require_queue_mode(mode)
        from corpus_structure.methods.llm.producer import SUPPORTED_PRODUCERS, producer_binding
        from corpus_structure.orchestrate.semantic import agent_packet
        from corpus_structure.semantic.metadata import table
        from corpus_structure.semantic.operations import claim_tasks

        configs, methods = table("ops.method_config"), table("ops.method")
        prepared = self.interpretation()
        if max_units is not None and max_units < 1:
            raise ProposalRefused("max_units must be positive")
        from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget

        read_budget = PublishedReadBudget(max_rows=10000, max_bytes=8 * 1024 * 1024)
        out = []
        admitted_events = []
        pending_sessions: dict[int, ProposalSession] = {}
        with self.lock, self.engine.begin() as conn:
            rows = conn.execute(
                select(
                    configs.c.id,
                    configs.c.params,
                    methods.c.name.label("method"),
                    methods.c.version.label("method_version"),
                )
                .join(methods, methods.c.id == configs.c.method_id)
                .join(table("ops.task"), table("ops.task").c.method_config_id == configs.c.id)
                .where(
                    methods.c.name.in_(SUPPORTED_PRODUCERS),
                    table("ops.task").c.run_id == self.run_id,
                    table("ops.task").c.status == "awaiting_agent",
                )
                .distinct()
                .order_by(configs.c.id)
            ).mappings()
            for row in rows:
                preparation = {}
                binding = producer_binding(
                    row["method"], row["params"], method_version=row["method_version"]
                )
                if binding.mode != mode:
                    continue
                limit = min(max_units or 1, row["params"].get("max_units", 1))
                leased = claim_tasks(
                    conn,
                    run_id=RunId(self.run_id),
                    config_id=MethodConfigId(row["id"]),
                    holder=self.holder,
                    limit=limit,
                    agent=True,
                    prepared=prepared,
                )
                for task in leased:
                    packet = agent_packet(
                        conn,
                        self.run_id,
                        task.task_id,
                        prepared,
                        preparation=preparation,
                        read_budget=read_budget,
                    )
                    if packet.hash != task.packet_hash:
                        raise ProposalRefused(
                            "queued task does not match its recorded source packet"
                        )
                    session = ProposalSession(
                        prepared, packet, task.task_id, task.attempt, self.holder
                    )
                    pending_sessions[task.task_id] = session
                    admitted_events.append((task, binding, packet.hash))
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
            response = service.QueueNext(tasks=out)
            # A refused ACK must roll back the claim, not strand a committed lease
            # that the client never received. Packet work has its separate budget.
            _bounded_mcp_result(response, QUEUE_ACK_MAX_BYTES)
        self.sessions.update(pending_sessions)
        for task, binding, packet_hash in admitted_events:
            _invocation_event(
                task.task_id,
                task.attempt,
                self.holder,
                binding.values(),
                "leased",
                packet_hash=packet_hash,
            )
        return response


@dataclass
class SemanticProjectSession:
    """Dynamic project queue; each leased task retains its immutable run interpretation."""

    engine: Engine
    project_id: str
    instance: str = field(default_factory=lambda: "mcp-semantic-" + secrets.token_hex(6))
    runs: dict[int, SemanticAgentSession] = field(default_factory=dict)
    sessions: dict[int, ProposalSession] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def for_run(self, run_id: int) -> SemanticAgentSession:
        from corpus_structure.semantic.metadata import table

        with self.lock:
            if run_id not in self.runs:
                runs = table("ops.run")
                with self.engine.connect() as conn:
                    exists = conn.execute(
                        select(runs.c.id).where(
                            runs.c.id == run_id, runs.c.project_id == self.project_id
                        )
                    ).scalar_one_or_none()
                if exists is None:
                    raise ProposalRefused("run does not belong to this semantic project")
                self.runs[run_id] = SemanticAgentSession(
                    self.engine, run_id, instance=self.instance, sessions=self.sessions
                )
            return self.runs[run_id]

    def pending_runs(self) -> tuple[int, ...]:
        from corpus_structure.semantic.metadata import table

        runs, tasks = table("ops.run"), table("ops.task")
        with self.engine.connect() as conn:
            return tuple(
                conn.execute(
                    select(runs.c.id)
                    .join(tasks, tasks.c.run_id == runs.c.id)
                    .where(
                        runs.c.project_id == self.project_id,
                        runs.c.status.in_(("created", "running")),
                        tasks.c.status == "awaiting_agent",
                    )
                    .distinct()
                    .order_by(runs.c.id.desc())
                ).scalars()
            )

    def status(self) -> service.QueueStatus:
        return service.QueueStatus(
            queues=[
                queue for run in self.pending_runs() for queue in self.for_run(run).status().queues
            ]
        )

    def next(self, mode: str, max_units: int | None) -> service.QueueNext:
        _require_queue_mode(mode)
        if max_units is not None and max_units < 1:
            raise ProposalRefused("max_units must be positive")
        for run in self.pending_runs():
            result = self.for_run(run).next(mode, max_units)
            if result.tasks:
                return result
        return service.QueueNext(tasks=[])

    def active(self, task_id: int) -> ProposalSession:
        from corpus_structure.semantic.metadata import table

        tasks = table("ops.task")
        with self.engine.connect() as conn:
            run = conn.execute(
                select(tasks.c.run_id).where(tasks.c.id == task_id)
            ).scalar_one_or_none()
        if run is None:
            raise ProposalTaskNotOpen("unknown semantic task")
        return self.for_run(run).active(task_id)


SemanticSession = SemanticAgentSession | SemanticProjectSession


def build_semantic_server(
    session: SemanticSession | None = None,
    *,
    run_id: int | None = None,
    settings: Settings | None = None,
    read_engine: Engine | None = None,
) -> FastMCP:
    @lifespan
    async def open_session(server: FastMCP) -> AsyncIterator[dict[str, SemanticSession | Settings]]:
        if session is not None:
            yield {"session": session}
            return
        from corpus_structure.semantic.runtime import open_runtime_engine
        from corpus_structure.settings import Settings

        selected = settings if settings is not None else Settings()
        with open_runtime_engine(
            selected, "ci-mcp-semantic", max_size=4, purpose="write"
        ) as engine:
            active: SemanticSession = (
                SemanticAgentSession(engine, run_id)
                if run_id is not None
                else SemanticProjectSession(engine, selected.runtime.default_project)
            )
            yield {"session": active, "settings": selected}

    server = FastMCP(
        MCP_SERVER_NAME,
        version=FASTMCP_VERSION,
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

    def current(ctx: Context) -> SemanticSession:
        return ctx.lifespan_context["session"]

    def bound_run(ctx: Context, run: int | None) -> SemanticSession:
        found = current(ctx)
        if isinstance(found, SemanticProjectSession):
            return found.for_run(run) if run is not None else found
        if run is not None and run != found.run_id:
            raise ToolError("this server is bound to a different semantic run")
        return found

    @contextmanager
    def source_snapshot(ctx: Context, selected_run: int):
        """Open source reads under the reader purpose and retain the server scope."""
        from corpus_structure.semantic.metadata import table
        from corpus_structure.semantic.query import read_snapshot
        from corpus_structure.semantic.runtime import open_runtime_engine

        active = current(ctx)
        if isinstance(active, SemanticAgentSession) and selected_run != active.run_id:
            raise ProposalRefused("this server is bound to a different semantic run")

        @contextmanager
        def engine_for_source() -> Iterator[Engine]:
            if read_engine is not None:
                yield read_engine
            elif session is not None:
                # A caller-supplied session owns its engine and compatibility.
                yield active.engine
            else:
                with open_runtime_engine(
                    ctx.lifespan_context["settings"],
                    "ci-mcp-source",
                    max_size=1,
                    purpose="read",
                ) as reader:
                    yield reader

        with engine_for_source() as engine, read_snapshot(engine) as conn:
            if isinstance(active, SemanticProjectSession):
                runs = table("ops.run")
                belongs = conn.scalar(
                    select(runs.c.id).where(
                        runs.c.id == selected_run, runs.c.project_id == active.project_id
                    )
                )
                if belongs is None:
                    raise ProposalRefused("run does not belong to this semantic project")
            yield conn

    from corpus_structure.intervene.record_tools import register_record_tools
    from corpus_structure.semantic.operation_reporting import report_schema

    register_record_tools(server, bound_run)

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=report_schema("OperationExplanation")
    )
    @tool_refusals(ValueError)
    def explain_operation(
        ctx: Context,
        release: str,
        operation: str,
        task_id: int | None = None,
        product_key: str | None = None,
        content_digest: str | None = None,
        realization_id: str | None = None,
        data_revision: int | None = None,
        capture_id: str | None = None,
        run_id: int | None = None,
        section_pointer: str | None = None,
        pointer: str | None = None,
        region_index: int | None = None,
    ) -> dict:
        """Explain the exact operation contract and qualified observed prerequisites."""
        from corpus_structure.semantic.identity import canonical_bytes
        from corpus_structure.semantic.operation_reporting import explain_operation as explain
        from corpus_structure.semantic.operation_reporting import parse_operation_subject
        from corpus_structure.semantic.query import read_snapshot
        from corpus_structure.semantic.releases import open_release

        raw_subject = None
        if any(v is not None for v in (task_id, product_key, content_digest)):
            if task_id is None or product_key is None or content_digest is None:
                raise ValueError("product subject requires all three pin fields")
            raw_subject = canonical_bytes(
                dict(task_id=task_id, product_key=product_key, content_digest=content_digest)
                | {
                    name: value
                    for name, value in dict(
                        run_id=run_id,
                        section_pointer=section_pointer,
                        pointer=pointer,
                        region_index=region_index,
                    ).items()
                    if value is not None
                }
            )
        elif any(v is not None for v in (run_id, section_pointer, pointer, region_index)):
            raise ValueError("document context requires its exact product pin")
        if any(v is not None for v in (realization_id, data_revision, capture_id)):
            if raw_subject is not None:
                raise ValueError("select a product or snapshot subject")
            if realization_id is None or data_revision is None or capture_id is None:
                raise ValueError("snapshot subject requires realization, revision and capture")
            raw_subject = canonical_bytes(
                dict(
                    release_id=release,
                    realization_id=realization_id,
                    data_revision=data_revision,
                    capture_id=capture_id,
                )
            )
        with read_snapshot(current(ctx).engine) as conn:
            prepared = open_release(conn, release)
            with located_failure_context(prepared, operation):
                reference = (
                    parse_operation_subject(prepared, operation, raw_subject, connection=conn)
                    if raw_subject is not None
                    else None
                )
                return explain(prepared, operation, subject=reference, connection=conn).model_dump(
                    mode="json"
                )

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=report_schema("SemanticImpactReport")
    )
    @tool_refusals(ValueError)
    def compare_semantic_releases(ctx: Context, before: str, after: str) -> dict:
        """Compare supported immutable releases and retain unknown impact explicitly."""
        from corpus_structure.semantic.operation_reporting import (
            compare_semantic_releases as compare,
        )
        from corpus_structure.semantic.query import read_snapshot
        from corpus_structure.semantic.releases import open_release

        with read_snapshot(current(ctx).engine) as conn:
            old, new = open_release(conn, before), open_release(conn, after)
            with located_failure_context(new, "compare_semantic_releases"):
                return compare(old, new).model_dump(mode="json")

    @server.tool(
        annotations={"readOnlyHint": True},
        output_schema=compress_schema(
            SourceSearchResponse.model_json_schema(mode="serialization"), prune_titles=True
        ),
    )
    @tool_refusals(ProposalRefused, OperationConflict, ValueError)
    def find(ctx: Context, request: SourceSearchRequest) -> ToolResult:
        """Find selected PDF source sections, with exact retrievable source handles."""
        from corpus_structure.serve.source_search import search_source

        with source_snapshot(ctx, request.run_id) as conn:
            response = search_source(conn, request)
        return _bounded_mcp_result(response, request.max_bytes)

    @server.tool(
        annotations={"readOnlyHint": True},
        output_schema=compress_schema(
            NativeSourceResponse.model_json_schema(mode="serialization"), prune_titles=True
        ),
    )
    @tool_refusals(ProposalRefused, OperationConflict, ValueError)
    def inspect_source(ctx: Context, request: NativeSourceRequest) -> ToolResult:
        """Inspect pinned source products and qualified origins without interpretation."""
        from corpus_structure.serve.native_source import inspect_native_source

        with source_snapshot(ctx, request.run_id) as conn:
            response = inspect_native_source(conn, request)
        return _bounded_mcp_result(response, request.max_bytes)

    @server.tool(annotations={"readOnlyHint": False})
    @tool_refusals(ProposalRefused, OperationConflict, ValueError)
    def render_source_region(
        ctx: Context,
        run_id: int,
        source_view_id: int,
        pointer: str,
        region_index: int = 0,
        scale: float = 2,
        max_bytes: Annotated[int, Field(ge=1024, le=8 * 1024 * 1024)] = 1024 * 1024,
    ) -> ToolResult:
        """Retain a source-qualified region and deliver inline imagery within max_bytes."""
        from corpus_structure.semantic.native_requests import request_source_view

        active = bound_run(ctx, run_id)
        result = request_source_view(
            active.engine,
            source_run_id=run_id,
            source_view_id=source_view_id,
            demand="render",
            pointer=pointer,
            region_index=region_index,
            scale=scale,
            code_commit="native-source-mcp-v4",
        )
        if result.status == "failed":
            raise ValueError(result.error or "native region render failed")
        return _rendered_artifact_result(active.engine, result, max_bytes)

    @server.tool
    @tool_refusals(ProposalRefused, OperationConflict)
    def queue_status(ctx: Context, run: int | None = None) -> service.QueueStatus:
        return bound_run(ctx, run).status()

    @server.tool(
        output_schema=compress_schema(
            service.QueueNext.model_json_schema(mode="serialization"), prune_titles=True
        )
    )
    @tool_refusals(ProposalRefused, OperationConflict)
    def queue_next(
        ctx: Context,
        mode: Literal["extract"] = "extract",
        run: int | None = None,
        max_units: int | None = None,
    ) -> ToolResult:
        active = bound_run(ctx, run)
        if isinstance(active, SemanticAgentSession):
            with located_failure_context(active.interpretation(), "claim"):
                response = active.next(mode, max_units)
        else:
            response = active.next(mode, max_units)
        return _bounded_mcp_result(response, QUEUE_ACK_MAX_BYTES)

    @server.tool
    @tool_refusals(ProposalRefused, OperationConflict)
    def read_unit(ctx: Context, task_id: int, part: int = 1) -> ToolResult:
        active = current(ctx).active(task_id)
        with located_failure_context(active.prepared, "make_packet", scope="mcp/read_unit"):
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
            from mcp.types import TextContent

            from corpus_structure.semantic.query import ReadLimit

            wire = _stamp_mcp_result(
                CallToolResult(
                    content=[TextContent(type="text", text=body)],
                    structured_content=structured.model_dump(mode="json"),
                )
            )
            if (
                len(wire.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8"))
                > READ_UNIT_MAX_BYTES
            ):
                raise ReadLimit(
                    "complete read_unit envelope exceeds byte budget", reason="oversized_item"
                )
            return ToolResult.from_mcp_result(wire)

    @server.tool
    @tool_refusals(ProposalRefused, OperationConflict)
    def read_instructions(
        ctx: Context, task_id: int, part: str | None = None, page: int = 1
    ) -> service.Instructions:
        active = current(ctx).active(task_id)
        with located_failure_context(active.prepared, "make_packet", scope="mcp/read_instructions"):
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

    @server.tool
    @tool_refusals(ProposalRefused, OperationConflict)
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
            _invocation_event(
                task_id,
                active.attempt,
                active.holder,
                result.producer_binding,
                "completed",
                receipt=result.completion.receipt.model_dump(mode="json"),
            )
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
    @tool_refusals(ProposalRefused, OperationConflict)
    def release(ctx: Context, task_id: int, reason: str) -> service.Released:
        active = current(ctx).active(task_id)
        with located_failure_context(active.prepared, "release_claim"):
            from corpus_structure.semantic.operations import release_claim

            with current(ctx).engine.begin() as conn:
                release_claim(
                    conn,
                    task_id=active.task_id,
                    attempt=active.attempt,
                    holder=active.holder,
                    reason=reason,
                )
            current(ctx).sessions.pop(task_id, None)
            return service.Released(task_id=task_id, released=True, reason=reason)

    @server.tool
    @tool_refusals(ProposalRefused, OperationConflict)
    def record_direction(
        ctx: Context, text: str, scope: str | None = None
    ) -> service.DirectionRecorded:
        from corpus_structure.intervene.directions import record_direction as record

        active = current(ctx)
        return record(
            active.engine,
            text,
            scope,
            actor="agent:session",
            session_ref=active.instance,
            project=active.project_id if isinstance(active, SemanticProjectSession) else None,
            run_id=active.run_id if isinstance(active, SemanticAgentSession) else None,
        )

    return server
