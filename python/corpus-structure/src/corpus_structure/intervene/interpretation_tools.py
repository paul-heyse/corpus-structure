"""Current terminology and selected private proposal read tools."""

from typing import Literal

from fastmcp import Context
from pydantic import BaseModel

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.grouped_record_interpretations import GroupedInterpretationRequest
from corpus_structure.semantic.refusals import tool_refusals
from corpus_structure.serve.interpretations import (
    SelectedProposalRequest,
    group_selected_interpretations,
    inspect_selected_proposals,
    term_lookup,
)


class ExactInterpretationResult(BaseModel):
    format: Literal["interpretation-exact-json-v1"] = "interpretation-exact-json-v1"
    exact_json: str


def register_interpretation_tools(
    server, metadata_reader, selected_reader, *, project=None, demand=None
):
    from corpus_structure.intervene.mcp_results import bounded_mcp_result

    def present(result, max_bytes):
        return bounded_mcp_result(
            ExactInterpretationResult(
                exact_json=json_bytes(result.model_dump(mode="python")).decode()
            ),
            max_bytes,
        )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def lookup_terminology(
        ctx: Context,
        release: str,
        field: str,
        query: str | None = None,
        browse: bool = False,
        max_bytes: int = 1024**2,
    ):
        """Look up real released field vocabulary metadata."""
        with metadata_reader(ctx) as connection:
            result = term_lookup(
                connection,
                release_id=release,
                field=field,
                query=query,
                browse=browse,
                max_bytes=max_bytes,
            )
        return present(result, max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_private_proposals(ctx: Context, request: SelectedProposalRequest):
        """Inspect actual selected private proposal kinds under native read authority."""
        if project is not None and request.project_id != project:
            raise ValueError("private proposal selection belongs to another server project")
        if demand is not None and request.demand_id != demand:
            raise ValueError("private proposal selection belongs to another server demand")
        with selected_reader(ctx, request.project_id) as connection:
            result = inspect_selected_proposals(connection, request)
        return present(result, request.max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def group_source_record_interpretations(ctx: Context, request: GroupedInterpretationRequest):
        """Read complete private SourceRecord alternatives under exact candidate product pins."""
        if project is not None and request.project_id != project:
            raise ValueError("interpretation selection belongs to another server project")
        if demand is not None and request.demand_id != demand:
            raise ValueError("interpretation selection belongs to another server demand")
        with selected_reader(ctx, request.project_id) as connection:
            result = group_selected_interpretations(connection, request)
        return present(result, request.max_bytes)
