"""Thin MCP adapters for the shared archived interpretation application."""

from __future__ import annotations

from fastmcp import Context

from corpus_structure.semantic.refusals import tool_refusals
from corpus_structure.serve.interpretations import InterpretationAnswer


def register_interpretation_tools(server, reader_snapshot, source_snapshot):
    from corpus_structure.intervene.semantic_server import _bounded_mcp_result
    from corpus_structure.semantic.interpretation_queries import measurement_groups
    from corpus_structure.serve.interpretations import answer, review_detail, term_lookup

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=InterpretationAnswer.model_json_schema()
    )
    @tool_refusals(ValueError)
    def lookup_terminology(
        ctx: Context,
        release: str,
        field: str,
        query: str | None = None,
        browse: bool = False,
        max_bytes: int = 1024**2,
    ):
        with reader_snapshot(ctx) as conn:
            result = term_lookup(
                conn,
                release_id=release,
                field=field,
                query=query,
                browse=browse,
                max_bytes=max_bytes,
            )
        return _bounded_mcp_result(result, max_bytes)

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=InterpretationAnswer.model_json_schema()
    )
    @tool_refusals(ValueError)
    def inspect_terminology_review(
        ctx: Context,
        review_run: int,
        review_cut: int,
        contribution_ids: list[str],
        max_bytes: int = 1024**2,
    ):
        with source_snapshot(ctx, review_run) as conn:
            result = review_detail(
                conn,
                review_run_id=review_run,
                review_cut_id=review_cut,
                contribution_ids=contribution_ids,
                max_bytes=max_bytes,
            )
        return _bounded_mcp_result(result, max_bytes)

    @server.tool(
        annotations={"readOnlyHint": True}, output_schema=InterpretationAnswer.model_json_schema()
    )
    @tool_refusals(ValueError)
    def group_measurement_interpretations(
        ctx: Context,
        source_run: int,
        review_run: int,
        review_cut: int,
        limit: int = 100,
        max_bytes: int = 1024**2,
    ):
        with source_snapshot(ctx, source_run) as conn:
            result = answer(
                "measurement_groups",
                measurement_groups(
                    conn,
                    source_run_id=source_run,
                    review_run_id=review_run,
                    review_cut_id=review_cut,
                    limit=limit,
                ),
                max_bytes,
            )
        return _bounded_mcp_result(result, max_bytes)
