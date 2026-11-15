"""Exact-JSON MCP transport for actual selected rich knowledge queries."""

from __future__ import annotations

from fastmcp import Context

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.refusals import tool_refusals
from corpus_structure.serve.rich_queries import (
    RichQueryRequest,
    decode_rich_cursor,
    serve_rich_query,
)

from .demand_read_tools import ExactSelectedResult
from .mcp_results import bounded_mcp_result


def register_rich_query_tools(server, reader, *, project=None, demand=None):
    def execute(request):
        if project is not None and request.project_id != project:
            raise ValueError("rich query belongs to another server project")
        if demand is not None and request.demand_id != demand:
            raise ValueError("rich query belongs to another server demand")
        with reader() as connection:
            report = serve_rich_query(connection, request)
        return ExactSelectedResult(
            cut_id=report["cut_id"],
            exact_json=json_bytes(report).decode(),
            resource="corpus://rich-query/" + report["resource_handle"],
        )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def query_knowledge(ctx: Context, request_json: str):
        """Query one explicit demand/project/product. Supply exact RichQueryRequest JSON.

        Required keys: demand_id, project_id, product_id and query (with name).
        Query fields: entity(key?, class_name?); claims(subject?, predicate?,
        object_entity?, fact_id?); statement(product_id, member_id including null);
        evidence(fact_id?, occurrence_id?); source_readings(record_id?);
        family_profile/transformations_of(family); construction_profile(construction);
        parameter_mapping(family, construction); families_where(predicate, value?);
        relations_between(a, b, depth<=4, max_edges?, max_frontier?, max_state_bytes?).
        Common query options: population=selected|retained, include_suppositions.
        The JSON string preserves Decimal literals. Returned exact_json is authoritative;
        source readings never establish scientific truth. Cursors retain exact native
        selection and installed query meaning; use the returned resource to replay a page.
        """
        request = RichQueryRequest.model_validate(json_loads(request_json))
        return bounded_mcp_result(execute(request), request.max_bytes)

    @server.resource("corpus://rich-query/{handle}")
    def rich_query(handle: str) -> str:
        request = RichQueryRequest.model_validate(decode_rich_cursor(handle))
        result = execute(request)
        content = result.model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise ValueError("complete rich query resource exceeds max_bytes")
        return content
