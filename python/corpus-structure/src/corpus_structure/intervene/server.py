"""The main MCP profile (agent interface §3.5; D8 §1-§3; ADR-0015): `ci mcp serve` runs it on stdio,
one process per Claude Code session, registered in `.mcp.json`.

The lifespan builds settings once, opens the store (a small pool), mints the instance id and holds
the `Session`; tools are synchronous, run on FastMCP's worker threads and call `service` and
`submission`. Nothing is printed at import or lifespan time; logs go to stderr. The profile
registers no golden tools and imports nothing that imports the math grammar.

`ToolFailure` and database errors become `ToolError` (`isError`); content problems are typed
results.
`ResponseLimitingMiddleware` is a byte backstop well above the 24,000-character pages.
"""

from __future__ import annotations

import functools
from collections.abc import AsyncIterator, Callable
from typing import Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.lifespan import lifespan
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
from fastmcp.tools import ToolResult
from sqlalchemy.exc import DBAPIError

from corpus_structure.intervene import service, submission
from corpus_structure.intervene.service import Session, ToolFailure
from corpus_structure.settings import Settings

INSTRUCTIONS = (
    "The corpus-structure work queue. Follow the work-queue skill: lease a unit with queue_next, "
    "read the instruction parts once per run with read_instructions, read every part of the unit "
    "with read_unit, and submit one batch with propose_claims. A first submission with problems "
    "stays open for one corrected resubmission."
)
BACKSTOP_BYTES = 200_000


def _tool_errors[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except ToolFailure as error:
            raise ToolError(str(error)) from None
        except DBAPIError as error:
            raise ToolError(
                f"database failure: {type(error.orig).__name__}: {error.orig}"
            ) from None

    return wrapped


def _session(ctx: Context) -> Session:
    return ctx.lifespan_context["session"]


def build_server(session: Session | None = None, *, semantic_run: int | None = None,
                 settings: Settings | None = None) -> FastMCP:
    """The main profile; `session` is injected by tests (the lifespan then opens no store)."""

    if semantic_run is not None:
        from corpus_structure.intervene.semantic_server import build_semantic_server
        return build_semantic_server(run_id=semantic_run, settings=settings)

    @lifespan
    async def open_session(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
        if session is not None:
            yield {"session": session}
            return
        from corpus_structure.core.db.store import open_store
        from corpus_structure.settings import Settings

        with open_store(settings if settings is not None else Settings(), "ci-mcp", max_size=4) as store:
            yield {"session": Session(store.engine)}

    mcp = FastMCP(
        "corpus-structure",
        INSTRUCTIONS,
        lifespan=open_session,
        middleware=[ResponseLimitingMiddleware(max_size=BACKSTOP_BYTES)],
    )

    @mcp.tool
    @_tool_errors
    def queue_status(ctx: Context, run: int | None = None) -> service.QueueStatus:
        """Counts of awaiting agent.opus tasks by run, mode and stage."""
        return service.queue_status(_session(ctx), run)

    @mcp.tool
    @_tool_errors
    def queue_next(
        ctx: Context,
        mode: Literal["extract", "adjudicate"] = "extract",
        run: int | None = None,
        max_units: int | None = None,
    ) -> service.QueueNext:
        """Lease the next unit (30-minute lease, renewed by every call on the task). Without `run`,
        the newest run with awaiting units. Returns task ids, unit keys and packet sizes."""
        return service.queue_next(_session(ctx), mode, run, max_units)

    @mcp.tool
    @_tool_errors
    def read_unit(ctx: Context, task_id: int, part: int = 1) -> ToolResult:
        """One part of the unit's packet as text; the structured content gives the part count,
        the packet hash and the part's sentence map. Read every part before submitting."""
        packet, unit = service.read_unit(_session(ctx), task_id, part)
        return ToolResult(content=packet, structured_content=unit.model_dump(mode="json"))

    @mcp.tool
    @_tool_errors
    def read_instructions(
        ctx: Context, task_id: int, part: str | None = None, page: int = 1
    ) -> service.Instructions:
        """Without `part`: the instruction parts (system, guideline, reference, format, schema)
        with sizes and hashes. With `part`: one page of it (24,000 characters). The parts are the
        same for every task of a run; read them once per run. The schema part is optional: the
        reference states every shape."""
        return service.read_instructions(_session(ctx), task_id, part, page)

    @mcp.tool
    @_tool_errors
    def propose_claims(
        ctx: Context,
        task_id: int,
        batch: dict[str, Any],
        schema_hash: str | None = None,
        rationale: str | None = None,
    ) -> submission.SubmissionResult:
        """Submit the unit's ClaimProposalBatch (model-facing form, see the format part). The
        result lists rejected items with paths, unlocated quotes and guideline warnings per item.
        A first submission with any of them stays open (`task_open: true`): fix and resubmit once,
        or resubmit with a `rationale` saying why a warning does not apply."""
        return submission.propose_claims(_session(ctx), task_id, batch, schema_hash, rationale)

    @mcp.tool
    @_tool_errors
    def release(ctx: Context, task_id: int, reason: str) -> service.Released:
        """Give a leased unit back to the queue, with the reason."""
        return service.release(_session(ctx), task_id, reason)

    @mcp.tool
    @_tool_errors
    def record_direction(
        ctx: Context, text: str, scope: str | None = None
    ) -> service.DirectionRecorded:
        """Record an operator direction (an intervention and an entry in the pack's
        directions.md); it is outside the guideline's hash."""
        s = _session(ctx)
        return service.record_direction(
            s.engine, text, scope, actor="agent:session", session_ref=s.instance, domains=s.domains
        )

    return mcp


def serve(*, semantic_run: int | None = None, settings: Settings | None = None) -> None:
    """`ci mcp serve`: the main profile on stdio, no banner."""
    build_server(semantic_run=semantic_run, settings=settings).run(show_banner=False)
