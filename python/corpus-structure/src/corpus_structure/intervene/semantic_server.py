"""Retained read APIs over archived releases and genuine published source/cut custody.

The ordinary external executor is separate. This factory contains no work queue,
claims, rich submission, task release or agent-direction write protocol.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from fastmcp import Context, FastMCP
from fastmcp import __version__ as FASTMCP_VERSION
from fastmcp.server.lifespan import lifespan
from fastmcp.tools import ToolResult
from fastmcp.utilities.json_schema import compress_schema
from mcp.types import CallToolResult
from pydantic import Field
from sqlalchemy import Connection, Engine, func, select

from corpus_structure.intervene import service
from corpus_structure.semantic.operations import OperationConflict
from corpus_structure.semantic.proposals import ProposalRefused
from corpus_structure.semantic.refusals import located_failure_context, tool_refusals
from corpus_structure.serve.native_source import NativeSourceRequest, NativeSourceResponse
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin
from corpus_structure.serve.source_search import SourceSearchRequest, SourceSearchResponse
from corpus_structure.settings import Settings

from .mcp_observations import ObservationMiddleware
from .mcp_results import _stamp_mcp_result
from .mcp_results import bounded_mcp_result as _bounded_mcp_result

MCP_SERVER_NAME = "corpus-structure"


@dataclass(frozen=True)
class RetainedReaderBinding:
    engine: Engine
    run_id: int


def build_retained_reader_server(
    binding: RetainedReaderBinding | None = None,
    *,
    run_id: int | None = None,
    project: str | None = None,
    settings: Settings | None = None,
    read_engine: Engine | None = None,
) -> FastMCP:
    """Expose retained readers only."""
    bound_id = binding.run_id if binding is not None else run_id

    @lifespan
    async def open_session(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
        from corpus_structure.cli.observation_logging import child_capture

        with child_capture(run_id=bound_id) as observations:
            yield {"settings": settings or Settings(), "observation_writer": observations}

    server = FastMCP(
        MCP_SERVER_NAME,
        version=FASTMCP_VERSION,
        lifespan=open_session,
        instructions="Inspect explicit archived releases and pinned published sources/cuts. No agent queue or submission is available.",
    )
    server.add_middleware(ObservationMiddleware(bound_id))

    @contextmanager
    def reader_snapshot(ctx: Context) -> Generator[Connection]:
        from corpus_structure.semantic.query import read_snapshot
        from corpus_structure.semantic.runtime import open_runtime_engine

        injected = (
            read_engine
            if read_engine is not None
            else binding.engine
            if binding is not None
            else None
        )
        if injected is not None:
            with read_snapshot(injected) as connection:
                yield connection
        else:
            with (
                open_runtime_engine(
                    ctx.lifespan_context["settings"],
                    "ci-mcp-retained-read",
                    max_size=1,
                    purpose="read",
                ) as engine,
                read_snapshot(engine) as connection,
            ):
                yield connection

    def reader_project(ctx: Context) -> str:
        return project or ctx.lifespan_context["settings"].runtime.default_project

    @contextmanager
    def source_snapshot(ctx: Context, selected_run: int) -> Generator[Connection]:
        if bound_id is not None and selected_run != bound_id:
            raise ProposalRefused("this retained reader is bound to a different semantic run")
        with reader_snapshot(ctx) as connection:
            if bound_id is None:
                from corpus_structure.semantic.metadata import table

                runs = table("ops.run")
                if (
                    connection.scalar(
                        select(runs.c.id).where(
                            runs.c.id == selected_run, runs.c.project_id == reader_project(ctx)
                        )
                    )
                    is None
                ):
                    raise ProposalRefused("run does not belong to this retained reader project")
            yield connection

    from corpus_structure.intervene.record_tools import register_record_tools
    from corpus_structure.semantic.operation_reporting import report_schema

    register_record_tools(server, source_snapshot)
    from corpus_structure.intervene.characterization_tools import register_characterization_tools

    register_characterization_tools(server, source_snapshot, _bounded_mcp_result)
    from corpus_structure.intervene.interpretation_tools import register_interpretation_tools

    register_interpretation_tools(server, reader_snapshot, source_snapshot)

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
        dependency_detail: bool = False,
        dependency_family: str | None = None,
        dependency_output: str | None = None,
        dependency_occurrence: str | None = None,
        dependency_after: int = 0,
        dependency_limit: int = 100,
    ) -> dict:
        """Explain the exact operation contract and qualified observed prerequisites."""
        from corpus_structure.semantic.identity import canonical_bytes
        from corpus_structure.semantic.operation_reporting import explain_operation as explain
        from corpus_structure.semantic.operation_reporting import parse_operation_subject
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
        with reader_snapshot(ctx) as conn:
            prepared = open_release(conn, release)
            with located_failure_context(prepared, operation):
                reference = (
                    parse_operation_subject(prepared, operation, raw_subject, connection=conn)
                    if raw_subject is not None
                    else None
                )
                return explain(
                    prepared,
                    operation,
                    subject=reference,
                    connection=conn,
                    dependency_detail=dependency_detail,
                    dependency_family=dependency_family,
                    dependency_output=dependency_output,
                    dependency_occurrence=dependency_occurrence,
                    dependency_after=dependency_after,
                    dependency_limit=dependency_limit,
                ).model_dump(mode="json")

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=report_schema("SemanticImpactReport")
    )
    @tool_refusals(ValueError)
    def compare_semantic_releases(
        ctx: Context,
        before: str,
        after: str,
        source_run_id: int | None = None,
        review_run_id: int | None = None,
        review_cut_id: int | None = None,
        use_limit: int = 100,
        use_after: str | None = None,
        use_side: str = "before",
        dependency_detail: bool = False,
        dependency_family: str | None = None,
        dependency_output: str | None = None,
        dependency_occurrence: str | None = None,
        dependency_after: int = 0,
        dependency_limit: int = 100,
    ) -> dict:
        """Compare supported immutable releases and retain unknown impact explicitly."""
        from corpus_structure.semantic.operation_reporting import (
            compare_semantic_releases as compare,
        )
        from corpus_structure.semantic.releases import open_release

        with reader_snapshot(ctx) as conn:
            old, new = open_release(conn, before), open_release(conn, after)
            with located_failure_context(new, "compare_semantic_releases"):
                return compare(
                    old,
                    new,
                    connection=conn,
                    source_run_id=source_run_id,
                    review_run_id=review_run_id,
                    review_cut_id=review_cut_id,
                    use_limit=use_limit,
                    use_after=use_after,
                    use_side=use_side,
                    dependency_detail=dependency_detail,
                    dependency_family=dependency_family,
                    dependency_output=dependency_output,
                    dependency_occurrence=dependency_occurrence,
                    dependency_after=dependency_after,
                    dependency_limit=dependency_limit,
                ).model_dump(mode="json")

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
        """Inspect pinned source products and origins, or explicitly pinned visual candidates."""
        from corpus_structure.serve.native_source import inspect_native_source

        with source_snapshot(ctx, request.run_id) as conn:
            response = inspect_native_source(conn, request)
        return _bounded_mcp_result(response, request.max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ProposalRefused, OperationConflict, ValueError)
    def list_visual_observations(
        ctx: Context,
        source: VisualEvidencePin,
        page_no: Annotated[int, Field(gt=0)] | None = None,
        after_task: Annotated[int, Field(ge=0)] = 0,
        limit: Annotated[int, Field(ge=1, le=1000)] = 100,
        max_bytes: Annotated[int, Field(ge=1024, le=8 * 1024 * 1024)] = 1024 * 1024,
    ) -> ToolResult:
        """Discover settled page and crop observations for one pinned published PDF."""
        from corpus_structure.serve.pdf_visual_evidence import visual_observation_manifest

        with source_snapshot(ctx, source.run_id) as conn:
            manifest = visual_observation_manifest(
                conn, source, page_no=page_no, after_task=after_task, limit=limit
            )
        return _bounded_mcp_result(manifest, max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ProposalRefused, OperationConflict, ValueError)
    def visual_evidence_packet(ctx: Context, request: NativeSourceRequest) -> ToolResult:
        """Prepare an explicit source packet containing attributed visual alternatives."""
        from corpus_structure.serve.visual_evidence_packet import visual_evidence_packet as pack

        with source_snapshot(ctx, request.run_id) as conn:
            packet = pack(conn, request)
        return _bounded_mcp_result(packet, request.max_bytes)

    from corpus_structure.serve.research import register_research_tools

    register_research_tools(server, reader_snapshot, _bounded_mcp_result, tool_refusals)
    return server
