"""The ordinary MCP external executor, using native demand packet custody only."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.lifespan import lifespan
from fastmcp.tools import ToolResult
from pydantic import RootModel
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_external import ExternalDataSession
from corpus_structure.settings import Settings


class ExternalReport(RootModel[dict[str, Any]]):
    pass


def build_external_server(session: ExternalDataSession | None = None, *, project: str | None = None,
                          demand: str | None = None, settings: Settings | None = None) -> FastMCP:
    @lifespan
    async def open_session(server: FastMCP) -> AsyncIterator[dict]:
        from corpus_structure.cli.observation_logging import child_capture
        from corpus_structure.semantic.runtime import open_runtime_engine

        with child_capture() as observations:
            if session is not None:
                yield {"external": session, "observation_writer": observations}
                return
            selected = settings or Settings()
            with open_runtime_engine(selected, "ci-mcp-external", max_size=4, purpose="write") as engine:
                yield {"external": ExternalDataSession(engine, project or selected.runtime.default_project,
                                                       demand_id=demand), "observation_writer": observations}

    server = FastMCP("corpus-structure", lifespan=open_session, instructions=(
        "Execute only authored native external packets. List packets with queue_next, claim one exact "
        "packet, then read its complete immutable packet with read_packet. Follow its protocol.instructions "
        "and declared-inputs-only reference scope; protected evaluator data is unavailable. Return only "
        "outcome and outputs (each output has role and body). Supply honest actor/model assertions matching "
        "the packet protocol. Renew the exact claim while working. submit_result retains the result and "
        "publishes through native authority; packet delivery alone is never fulfillment. After uncertainty, "
        "inspect_result and replay the same result, or reconcile_result under a native takeover claim; never repeat external work. "
        "release_packet relinquishes logical permission without asserting a remote process stopped."
    ))

    from .mcp_observations import ObservationMiddleware

    server.add_middleware(ObservationMiddleware())

    def current(ctx: Context) -> ExternalDataSession:
        return ctx.lifespan_context["external"]

    def report(action) -> ToolResult:
        # The shared transport bound includes SDK metadata and text plus structured
        # content; it has no legacy extraction queue or task-policy dependency.
        from .mcp_results import bounded_mcp_result

        try:
            result = action()
            return bounded_mcp_result(ExternalReport(result), 32 * 1024 * 1024)
        except (ValueError, KeyError, DBAPIError) as error:
            raise ToolError(str(error)) from error

    @server.tool(annotations={"readOnlyHint": True})
    def queue_next(ctx: Context, limit: int = 1) -> ToolResult:
        """List at most 64 claimable packet headers in the bound project/demand."""
        return report(lambda: current(ctx).queue(limit=limit))

    @server.tool()
    def claim_packet(ctx: Context, packet_id: str, lease_seconds: int = 300) -> ToolResult:
        """Acquire an exact native packet/task attempt; preserve the returned fence."""
        return report(lambda: current(ctx).claim(packet_id, lease_seconds=lease_seconds))

    @server.tool(annotations={"readOnlyHint": True})
    def read_packet(ctx: Context, packet_id: str, claim: dict[str, Any]) -> ToolResult:
        """Read the complete bounded packet under this exact claim, including its result schema."""
        return report(lambda: current(ctx).read(packet_id, claim))

    @server.tool()
    def renew_packet(ctx: Context, claim: dict[str, Any], lease_seconds: int = 300) -> ToolResult:
        """Renew permission only if the complete original native fence remains active."""
        return report(lambda: current(ctx).renew(claim, lease_seconds=lease_seconds))

    @server.tool()
    def submit_result(ctx: Context, packet_id: str, claim: dict[str, Any], result: dict[str, Any],
                      actor_assertion: str, model_assertion: str | None) -> ToolResult:
        """Admit the exact typed result with genuine native receipt and atomic publication."""
        return report(lambda: current(ctx).submit(packet_id, claim, result,
                                                actor_assertion=actor_assertion, model_assertion=model_assertion))

    @server.tool()
    def reconcile_result(ctx: Context, packet_id: str, claim: dict[str, Any]) -> ToolResult:
        """Adopt and publish this packet's retained result under an actual takeover claim."""
        return report(lambda: current(ctx).reconcile(packet_id, claim))

    @server.tool(annotations={"readOnlyHint": True})
    def inspect_result(ctx: Context, packet_id: str) -> ToolResult:
        """Resolve retained/committed/cancelled/superseded standing after uncertainty."""
        return report(lambda: current(ctx).inspect(packet_id))

    @server.tool()
    def release_packet(ctx: Context, packet_id: str, claim: dict[str, Any], reason: str) -> ToolResult:
        """Relinquish only this exact packet claim; never assert remote physical retirement."""
        return report(lambda: current(ctx).release(packet_id, claim, reason=reason))

    return server
