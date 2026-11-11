"""Enriched-document reads over the existing project/purpose snapshot boundary."""

from fastmcp.utilities.json_schema import compress_schema

from corpus_structure.semantic.refusals import tool_refusals
from corpus_structure.serve.characterization import (
    CharacterizationRequest,
    CharacterizationResponse,
    inspect_characterization,
)


def register_characterization_tools(server, source_snapshot, bounded_result):
    from fastmcp import Context

    @server.tool(
        annotations={"readOnlyHint": True},
        output_schema=compress_schema(
            CharacterizationResponse.model_json_schema(mode="serialization"), prune_titles=True
        ),
    )
    @tool_refusals(ValueError)
    def inspect_enriched_document(ctx: Context, request: CharacterizationRequest):
        """Inspect a pinned enriched document without rerunning language analysis."""
        with source_snapshot(ctx, request.run_id) as conn:
            response = inspect_characterization(conn, request)
        return bounded_result(response, request.max_bytes)
