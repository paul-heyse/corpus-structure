"""Selected PDF source tools on the ordinary current server's read purpose."""

from hashlib import sha256
from typing import Literal

from fastmcp import Context
from pydantic import BaseModel

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.serve.native_source import NativeSourceRequest
from corpus_structure.serve.source_catalog import SourceCatalogRequest
from corpus_structure.serve.source_search import SourceSearchRequest


class ExactSourceCatalog(BaseModel):
    format: Literal["selected-source-catalog-exact-json-v1"] = (
        "selected-source-catalog-exact-json-v1"
    )
    cut_id: str
    exact_json: str


class ExactSourceSearch(BaseModel):
    format: Literal["selected-source-search-exact-json-v1"] = "selected-source-search-exact-json-v1"
    cut_id: str
    exact_json: str


def exact_source_search(response):
    """Keep native JSON numbers in the cut and score through MCP's JSON transport."""
    return ExactSourceSearch(
        cut_id="cut-selection:" + sha256(json_bytes(response.cut)).hexdigest(),
        exact_json=json_bytes(response.model_dump(mode="python")).decode(),
    )


def register_native_source_tools(server, reader, *, project=None, demand=None):
    from corpus_structure.intervene.mcp_results import bounded_mcp_result
    from corpus_structure.semantic.refusals import tool_refusals
    from corpus_structure.serve.native_source import inspect_native_source
    from corpus_structure.serve.source_catalog import read_source_catalog
    from corpus_structure.serve.source_search import search_source

    def scope(request):
        if project is not None and request.project_id != project:
            raise ValueError("source selection belongs to another server project")
        if demand is not None and request.demand_id != demand:
            raise ValueError("source selection belongs to another server demand")

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_source(ctx: Context, request: NativeSourceRequest):
        """Inspect one exact demand/read/use/product/derivation source selection."""
        scope(request)
        with reader() as connection:
            response = inspect_native_source(connection, request)
        return bounded_mcp_result(response, request.max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def find(ctx: Context, request: SourceSearchRequest):
        """Search only the explicitly selected native source population."""
        scope(request)
        with reader() as connection:
            response = search_source(connection, request)
        return bounded_mcp_result(exact_source_search(response), request.max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def list_source_catalog(ctx: Context, request: SourceCatalogRequest):
        """Discover checked publication/source-view kinds in an actual selected cut.

        exact_json preserves all native scope numbers and unknown/partial standing.
        """
        scope(request)
        with reader() as connection:
            response = read_source_catalog(connection, request)
        return bounded_mcp_result(
            ExactSourceCatalog(
                cut_id="cut-selection:" + sha256(json_bytes(response.cut)).hexdigest(),
                exact_json=json_bytes(response.model_dump(mode="python")).decode(),
            ),
            request.max_bytes,
        )
