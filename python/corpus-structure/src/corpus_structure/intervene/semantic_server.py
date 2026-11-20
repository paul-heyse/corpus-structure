"""Retained read APIs over archived releases and genuine published source/cut custody.

The ordinary external executor is separate. This factory contains no work queue,
claims, rich submission, task release or agent-direction write protocol.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from contextlib import contextmanager
from typing import Annotated, Any, Literal

from fastmcp import Context, FastMCP
from fastmcp import __version__ as FASTMCP_VERSION
from fastmcp.server.lifespan import lifespan
from fastmcp.tools import ToolResult
from pydantic import Field, JsonValue
from sqlalchemy import Connection, Engine

from corpus_structure.semantic.proposals import ProposalRefused
from corpus_structure.semantic.refusal_types import OperationConflict
from corpus_structure.semantic.refusals import located_failure_context, tool_refusals
from corpus_structure.serve.native_source import NativeSourceRequest
from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference
from corpus_structure.settings import Settings

from .mcp_observations import ObservationMiddleware
from .mcp_results import bounded_mcp_result as _bounded_mcp_result

MCP_SERVER_NAME = "corpus-structure"


def build_retained_reader_server(
    *,
    project: str | None = None,
    settings: Settings | None = None,
    read_engine: Engine | None = None,
) -> FastMCP:
    """Expose current pinned readers and explicit captured contract inspection."""

    from .runtime_engines import McpRuntimeEngines

    effective_settings = settings or Settings()
    engines = McpRuntimeEngines(effective_settings, "ci-mcp-retained", read_engine=read_engine)

    @lifespan
    async def open_session(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
        from corpus_structure.analytics import configure as configure_analytics
        from corpus_structure.caches import configure
        from corpus_structure.cli.observation_logging import child_capture

        configure(effective_settings.cache)
        configure_analytics(effective_settings.analytics)
        with child_capture() as observations, engines.lifespan():
            yield {"settings": effective_settings, "observation_writer": observations}

    server = FastMCP(
        MCP_SERVER_NAME,
        version=FASTMCP_VERSION,
        lifespan=open_session,
        instructions="Inspect explicit archived releases and pinned published sources/cuts. No agent queue or submission is available.",
    )
    server.add_middleware(ObservationMiddleware(None))

    @server.tool(annotations={"readOnlyHint": True})
    def inspect_cache(
        max_bytes: Annotated[int, Field(ge=1024, le=1048576)] = 262144,
    ) -> ToolResult:
        """Inspect retention and counters of this running server process."""
        from corpus_structure.caches import snapshot

        return _bounded_mcp_result(snapshot(owner="mcp-retained-reader"), max_bytes)

    @contextmanager
    def reader_snapshot(ctx: Context) -> Generator[Connection]:
        from corpus_structure.semantic.read_snapshot import read_snapshot

        with read_snapshot(engines.engine("read")) as connection:
            yield connection

    def reader_project(ctx: Context) -> str:
        return project or ctx.lifespan_context["settings"].runtime.default_project

    @contextmanager
    def selected_source_snapshot(ctx: Context, project_id: str) -> Generator[Connection]:
        from corpus_structure.semantic.demand_results import selected_read_snapshot

        if project_id != reader_project(ctx):
            raise ProposalRefused("selected source belongs to another reader project")
        with selected_read_snapshot(engines.engine("read")) as connection:
            yield connection

    from corpus_structure.intervene.demand_read_tools import register_demand_read_tools
    from corpus_structure.semantic.operation_reporting import report_schema

    register_demand_read_tools(
        server,
        settings=effective_settings,
        read_engine=read_engine,
        engine_provider=lambda: engines.engine("read"),
        project=project or effective_settings.runtime.default_project,
    )

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=report_schema("ContractInspection")
    )
    @tool_refusals(ValueError, KeyError)
    def inspect_contract(
        ctx: Context,
        release: str,
        subject_kind: Literal["class", "property", "operation"],
        subject_id: str,
        property: str | None = None,
        view: Literal["summary", "detail"] = "summary",
        after: str | None = None,
        limit: int = 20,
        input_json: str | None = None,
        validation_purpose: Literal["structural", "accepted"] | None = None,
        correction_detail: bool = False,
        raw_evidence: bool = False,
        max_errors: int = 100,
        max_depth: int = 8,
        max_bytes: int = 262144,
    ) -> ToolResult:
        """Inspect an explicit release and optional class input without authorizing effects."""
        from corpus_structure.semantic.contract_inspection import inspect_contract as inspect
        from corpus_structure.semantic.releases import open_release

        with reader_snapshot(ctx) as conn:
            prepared = open_release(conn, release)
            report = inspect(
                prepared,
                subject_kind,
                subject_id,
                property=property,
                view=view,
                after=after,
                limit=limit,
                input_json=input_json,
                validation_purpose=validation_purpose,
                correction_detail=correction_detail,
                raw_evidence=raw_evidence,
                max_errors=max_errors,
                max_depth=max_depth,
                max_bytes=max_bytes,
            )
        presentation = None
        if correction_detail:
            data = report.model_dump(mode="json", exclude_none=True)
            validation = data.get("validation_report")
            if validation is not None:
                from corpus_structure.cli.correction_rendering import correction_text
                from corpus_structure.semantic.diagnostic_selection import select_diagnostic

                try:
                    selected = select_diagnostic(
                        dict(version=1, report=validation, members=[]),
                        "correction",
                        max_errors=max_errors,
                        max_depth=max_depth,
                        max_bytes=max_bytes,
                        raw_evidence=raw_evidence,
                    )
                    presentation = correction_text(selected)
                except Exception as presentation_error:
                    # Optional readable text cannot replace a successful native inspection.
                    presentation = (
                        "Correction presentation unavailable: " + type(presentation_error).__name__
                    )

        return _bounded_mcp_result(report, 8 * 1024 * 1024, presentation=presentation)

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=report_schema("OperationExplanation")
    )
    @tool_refusals(ValueError)
    def explain_operation(
        ctx: Context,
        release: str,
        operation: str,
        demand_id: str | None = None,
        project_id: str | None = None,
        cursor: str | None = None,
        limit: int = 100,
    ) -> dict:
        """Explain the captured DDO contract and optional exact selected native frontier."""
        from corpus_structure.semantic.demand_queries import DemandQueryRequest
        from corpus_structure.semantic.operation_reporting import explain_operation as explain
        from corpus_structure.semantic.releases import open_release

        if (demand_id is None) != (project_id is None) or (
            cursor is not None and demand_id is None
        ):
            raise ValueError("operation observation requires explicit native demand and project")
        request = (
            None
            if demand_id is None or project_id is None
            else DemandQueryRequest(
                demand_id=demand_id,
                project_id=project_id,
                view="operations",
                operation_id=operation,
                cursor=cursor,
                limit=limit,
            )
        )
        with (
            selected_source_snapshot(ctx, project_id)
            if project_id is not None
            else reader_snapshot(ctx)
        ) as conn:
            prepared = open_release(conn, release)
            with located_failure_context(prepared, operation):
                return explain(
                    prepared, operation, connection=conn, observation=request
                ).model_dump(mode="json")

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=report_schema("SemanticImpactReport")
    )
    @tool_refusals(ValueError)
    def compare_semantic_releases(ctx: Context, before: str, after: str) -> dict:
        """Compare exact declared models; selected retained impact is a separate tool."""
        from corpus_structure.semantic.operation_reporting import (
            compare_semantic_releases as compare,
        )
        from corpus_structure.semantic.releases import open_release

        with reader_snapshot(ctx) as conn:
            old, new = open_release(conn, before), open_release(conn, after)
            with located_failure_context(new, "compare_declared_models"):
                return compare(old, new).model_dump(mode="json")

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ProposalRefused, OperationConflict, ValueError)
    def list_visual_observations(
        ctx: Context,
        source: SelectedPdfSourceReference,
        page_no: Annotated[int, Field(gt=0)] | None = None,
        continuation: dict[str, JsonValue] | None = None,
        limit: Annotated[int, Field(ge=1, le=1000)] = 100,
        max_bytes: Annotated[int, Field(ge=1024, le=8 * 1024 * 1024)] = 1024 * 1024,
    ) -> ToolResult:
        """Discover selected raw and mapped candidates in the same source cut."""
        from corpus_structure.serve.pdf_visual_evidence import visual_observation_manifest

        with selected_source_snapshot(ctx, source.project_id) as conn:
            manifest = visual_observation_manifest(
                conn,
                source,
                page_no=page_no,
                continuation=continuation,
                limit=limit,
                max_bytes=max_bytes,
            )
        return _bounded_mcp_result(manifest, max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ProposalRefused, OperationConflict, ValueError)
    def visual_evidence_packet(ctx: Context, request: NativeSourceRequest) -> ToolResult:
        """Prepare an explicit source packet containing attributed visual alternatives."""
        from corpus_structure.serve.visual_evidence_packet import visual_evidence_packet as pack

        with selected_source_snapshot(ctx, request.project_id) as conn:
            packet = pack(conn, request)
        return _bounded_mcp_result(packet, request.max_bytes)

    return server
