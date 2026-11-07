"""MCP registration of the common pinned record journey."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager

from fastmcp import Context, FastMCP
from fastmcp.tools import ToolResult
from sqlalchemy import Connection

from corpus_structure.semantic.proposals import ProposalRefused
from corpus_structure.semantic.refusals import tool_refusals
from corpus_structure.serve.contributions import ContributionPage, ContributionRequest
from corpus_structure.serve.record_results import RecordPage, RecordRequest
from corpus_structure.serve.record_support import RecordSupportPage
from corpus_structure.serve.structural_products import (
    DossierRepresentationPage,
    DossierRepresentationRequest,
    StructuralPage,
    StructuralRequest,
)


def register_record_tools(
    server: FastMCP, snapshot: Callable[[Context, int], AbstractContextManager[Connection]]
) -> None:
    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=StructuralPage.model_json_schema()
    )
    @tool_refusals(ProposalRefused, ValueError)
    def structural_products(ctx: Context, request: StructuralRequest) -> ToolResult:
        """Read pinned cross-source proposals with original citations and explicit unknowns."""
        from corpus_structure.intervene.semantic_server import _bounded_mcp_result
        from corpus_structure.serve.structural_products import serve_structural_products

        with snapshot(ctx, request.run_id) as conn:
            page = serve_structural_products(conn, request)
        return _bounded_mcp_result(page, request.max_bytes)

    @server.tool(
        annotations={"readOnlyHint": True},
        output_schema=DossierRepresentationPage.model_json_schema(),
    )
    @tool_refusals(ProposalRefused, ValueError)
    def dossier_representation(ctx: Context, request: DossierRepresentationRequest) -> ToolResult:
        """Page selected dossier members with exact membership-bound continuation."""
        from corpus_structure.intervene.semantic_server import _bounded_mcp_result
        from corpus_structure.serve.structural_products import serve_dossier_representation

        with snapshot(ctx, request.run_id) as conn:
            page = serve_dossier_representation(conn, request)
        return _bounded_mcp_result(page, request.max_bytes)

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=ContributionPage.model_json_schema()
    )
    @tool_refusals(ProposalRefused, ValueError)
    def contributions(ctx: Context, request: ContributionRequest) -> ToolResult:
        """Inspect pinned private contributions and zero-output operations without a record.

        Inventory paging establishes neither source completeness nor public eligibility.
        """
        from corpus_structure.intervene.semantic_server import _bounded_mcp_result
        from corpus_structure.serve.contributions import serve_contributions

        with snapshot(ctx, request.run_id) as conn:
            page = serve_contributions(conn, request)
        return _bounded_mcp_result(page, request.page_bytes)

    @server.tool(annotations={"readOnlyHint": True}, output_schema=RecordPage.model_json_schema())
    @tool_refusals(ProposalRefused, ValueError)
    def records(ctx: Context, request: RecordRequest) -> ToolResult:
        """Read pinned records, field evidence, alternatives and candidate admission.

        Use record_id/interpretation_id for inspection. Source handles keep the same
        completed run. A complete page population does not establish source coverage.
        """
        from corpus_structure.intervene.semantic_server import _bounded_mcp_result
        from corpus_structure.serve.record_results import serve_record_results

        with snapshot(ctx, request.run_id) as conn:
            page = serve_record_results(conn, request)
        return _bounded_mcp_result(page, request.page_bytes)

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=RecordSupportPage.model_json_schema()
    )
    @tool_refusals(ProposalRefused, ValueError)
    def record_support(ctx: Context, request: RecordRequest) -> ToolResult:
        """Inspect pinned source-reading field facts, actual support/custody and assessments.

        Scientific proposition support/opposition is explicitly unmodeled; source
        polarity/modality and repeated windows do not establish independent votes.
        """
        from corpus_structure.intervene.semantic_server import _bounded_mcp_result
        from corpus_structure.serve.record_support import serve_record_support

        with snapshot(ctx, request.run_id) as conn:
            ledger = serve_record_support(conn, request)
        return _bounded_mcp_result(ledger, request.page_bytes)
