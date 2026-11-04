"""MCP registration of the common pinned record journey."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.tools import ToolResult

from corpus_structure.semantic.refusals import tool_refusals
from corpus_structure.serve.record_results import RecordPage, RecordRequest


def register_record_tools(server: FastMCP, bound_run: Callable[[Context, int], Any]) -> None:
    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=RecordPage.model_json_schema()
    )
    @tool_refusals(ValueError)
    def records(ctx: Context, request: RecordRequest) -> ToolResult:
        """Read pinned records, field evidence, alternatives and candidate admission.

        Use record_id/interpretation_id for inspection. Source handles keep the same
        completed run. A complete page population does not establish source coverage.
        """
        from corpus_structure.intervene.semantic_server import _bounded_mcp_result
        from corpus_structure.semantic.query import read_snapshot
        from corpus_structure.serve.record_results import serve_record_results

        active = bound_run(ctx, request.run_id)
        with read_snapshot(active.engine) as conn:
            page = serve_record_results(conn, request)
        return _bounded_mcp_result(page, request.page_bytes)
