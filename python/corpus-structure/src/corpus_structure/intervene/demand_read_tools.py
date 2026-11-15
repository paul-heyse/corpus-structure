"""Actual current MCP tools/resources over the shared selected result owner."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Literal

from fastmcp import Context
from pydantic import BaseModel

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.serve.demand_journey import DemandQueryRequest, _decode, serve_demand_query


class ExactSelectedResult(BaseModel):
    format: Literal["demand-result-exact-json-v1"] = "demand-result-exact-json-v1"
    cut_id: str
    exact_json: str
    resource: str


def register_demand_read_tools(server, *, settings, read_engine=None, project=None, demand=None):
    from corpus_structure.intervene.mcp_results import bounded_mcp_result
    from corpus_structure.semantic.refusals import tool_refusals

    @contextmanager
    def reader():
        if read_engine is not None:
            with read_engine.begin() as connection:
                yield connection
        else:
            from corpus_structure.semantic.runtime import open_runtime_engine
            with open_runtime_engine(settings, "ci-mcp-selected-read", purpose="read", max_size=1) as engine, engine.begin() as connection:
                yield connection

    def selected(request):
        if project is not None and request.project_id != project:
            raise ValueError("selected result belongs to another server project")
        if demand is not None and request.demand_id != demand:
            raise ValueError("selected result belongs to another server demand")
        with reader() as connection:
            report = serve_demand_query(connection, request)
        return ExactSelectedResult(cut_id=report["cut_id"], exact_json=json_bytes(report).decode(), resource="corpus://selected-result/" + report["resource_handle"])

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def read_result(ctx: Context, request: DemandQueryRequest):
        """Read selected members/operations/source/support with explicit demand/project pins.

        exact_json is authoritative for Decimal, context JSON and semantic tags.
        Protected reference answers require evaluator purpose and cannot be read here.
        """
        return bounded_mcp_result(selected(request), request.max_bytes)

    @server.resource("corpus://selected-result/{handle}")
    def selected_result(handle: str) -> str:
        """Replay an exact pinned page; never reinterpret it using a newer release."""
        request = DemandQueryRequest.model_validate(_decode(handle))
        response = selected(request)
        # Resource delivery has one text body; validate its own actual byte bound.
        content = response.model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise ValueError("complete selected resource exceeds max_bytes")
        return content
