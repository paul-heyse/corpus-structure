"""Actual current MCP tools/resources over the shared selected result owner."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Literal

from fastmcp import Context
from pydantic import BaseModel

from corpus_structure.semantic.continuation_codec import decode_resource_handle
from corpus_structure.semantic.data_operation_json import FiniteJsonValue, finite_result_record
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.serve.characterization import (
    DemandCharacterizationRequest,
    DemandDefinitionRequest,
    inspect_demand_characterization,
    inspect_demand_definition,
)
from corpus_structure.serve.demand_context import DemandContextRequest, inspect_demand_context
from corpus_structure.serve.selected_neighborhood import (
    DemandNeighborhoodRequest,
    inspect_demand_neighborhood,
)


class SelectedResult(BaseModel):
    format: Literal["demand-result-structured-v2"] = "demand-result-structured-v2"
    cut_id: str
    result: dict[str, FiniteJsonValue]
    resource: str | None = None


def register_demand_read_tools(
    server, *, settings, read_engine=None, engine_provider=None, project=None, demand=None
):
    from corpus_structure.intervene.mcp_results import bounded_structured_result
    from corpus_structure.semantic.refusals import tool_refusals

    if read_engine is None and engine_provider is None:
        raise ValueError("selected MCP tools require their lifespan-owned read engine")

    @contextmanager
    def reader():
        engine = engine_provider() if engine_provider is not None else read_engine
        if engine is None:
            raise RuntimeError("MCP read engine is unavailable")
        with engine.begin() as connection:
            yield connection

    from .interpretation_tools import register_interpretation_tools

    register_interpretation_tools(
        server,
        lambda ctx: reader(),
        lambda ctx, project_id: reader(),
        project=project,
        demand=demand,
    )
    from .native_source_tools import register_native_source_tools

    @contextmanager
    def search_reader():
        from corpus_structure.semantic.pdf_source_search import search_source_snapshot

        engine = engine_provider() if engine_provider is not None else read_engine
        if engine is None:
            raise RuntimeError("MCP search engine is unavailable")
        with search_source_snapshot(engine) as connection:
            yield connection

    register_native_source_tools(
        server, reader, search_reader=search_reader, project=project, demand=demand
    )
    from .source_inspection_tools import register_source_inspection_tools

    register_source_inspection_tools(server, reader, project=project, demand=demand)

    from .rich_query_tools import register_rich_query_tools

    register_rich_query_tools(server, reader, project=project, demand=demand)

    from .contribution_facet_tools import register_contribution_facet_tools

    register_contribution_facet_tools(server, reader, project=project, demand=demand)

    from .structural_read_tools import register_structural_read_tools

    register_structural_read_tools(server, reader, project=project, demand=demand)

    def selected(request, projection=None, *, scheme="selected-result"):
        projection = serve_demand_query if projection is None else projection
        if project is not None and request.project_id != project:
            raise ValueError("selected result belongs to another server project")
        if demand is not None and request.demand_id != demand:
            raise ValueError("selected result belongs to another server demand")
        with reader() as connection:
            report = projection(connection, request)
        return SelectedResult(
            cut_id=report["cut_id"],
            result=finite_result_record(report),
            resource="corpus://" + scheme + "/" + report["resource_handle"]
            if report.get("resource_handle") is not None
            else None,
        )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def read_result(ctx: Context, request: DemandQueryRequest):
        """Read selected members/operations/source/support with explicit demand/project pins.

        The structured result carries its native cut identity and selected data.
        Protected reference answers require evaluator purpose and cannot be read here.
        """
        return bounded_structured_result(selected(request), request.max_bytes)

    @server.resource("corpus://selected-result/{handle}")
    def selected_result(handle: str) -> str:
        """Replay an exact pinned page; never reinterpret it using a newer release."""
        request = decode_resource_handle(handle, DemandQueryRequest)
        response = selected(request)
        # Resource delivery has one text body; validate its own actual byte bound.
        content = response.model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise ValueError("complete selected resource exceeds max_bytes")
        return content

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_characterization(ctx: Context, request: DemandCharacterizationRequest):
        """Inspect selected nominal annotations/terms/choices and explicit source coverage."""
        return bounded_structured_result(
            selected(request, inspect_demand_characterization), request.max_bytes
        )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_definition(ctx: Context, request: DemandDefinitionRequest):
        """Read actual definition components/applicability/location with private standing."""
        return bounded_structured_result(
            selected(request, inspect_demand_definition), request.max_bytes
        )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_query_context(ctx: Context, request: DemandContextRequest):
        """Project one exact frame/referent/discourse recipe; no recognition or inference."""
        return bounded_structured_result(
            selected(request, inspect_demand_context, scheme="selected-context"), request.max_bytes
        )

    @server.resource("corpus://selected-context/{handle}")
    def selected_context(handle: str) -> str:
        request = decode_resource_handle(handle, DemandContextRequest)
        content = selected(
            request, inspect_demand_context, scheme="selected-context"
        ).model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise ValueError("complete selected query context resource exceeds max_bytes")
        return content

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_neighborhood(ctx: Context, request: DemandNeighborhoodRequest):
        """Read actual selected mutual neighbors and their producing use/derivation references.

        The result carries the finite distance values. Reading performs no encoding,
        ranking or relationship inference.
        """
        return bounded_structured_result(
            selected(request, inspect_demand_neighborhood, scheme="selected-neighborhood"),
            request.max_bytes,
        )

    @server.resource("corpus://selected-neighborhood/{handle}")
    def selected_neighborhood(handle: str) -> str:
        request = decode_resource_handle(handle, DemandNeighborhoodRequest)
        content = selected(
            request, inspect_demand_neighborhood, scheme="selected-neighborhood"
        ).model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise ValueError("complete selected neighborhood resource exceeds max_bytes")
        return content
