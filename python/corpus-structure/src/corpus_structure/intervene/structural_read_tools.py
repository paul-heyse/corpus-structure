"""Actual MCP frontdoors for selected structural reads and pinned resources."""

from fastmcp import Context

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_queries import _cursor
from corpus_structure.semantic.refusals import tool_refusals
from corpus_structure.serve.rich_queries import decode_rich_cursor
from corpus_structure.serve.source_decision_journey import (
    SelectedSourceDecisionJourneyRequest, inspect_selected_source_journey,
)
from corpus_structure.serve.structural_gaps import SelectedGapRequest, inspect_selected_gap
from corpus_structure.serve.structural_products import (
    SelectedDossierRequest, SelectedStructuralRequest,
    inspect_selected_dossier, inspect_selected_structures,
)

from .demand_read_tools import ExactSelectedResult
from .mcp_results import bounded_mcp_result


def register_structural_read_tools(server, reader, *, project=None, demand=None):
    def execute(request, operation, name):
        if project is not None and request.project_id != project:
            raise ValueError("structural read belongs to another server project")
        if demand is not None and request.demand_id != demand:
            raise ValueError("structural read belongs to another server demand")
        with reader() as connection:
            report = operation(connection, request)
        pinned = request.model_copy(update=dict(read_id=report["cut"]["read_id"], expected_cut=report["cut_id"], implementation=report["implementation"]))
        handle = _cursor(pinned.model_dump(mode="python"))
        return ExactSelectedResult(cut_id=report["cut_id"], exact_json=json_bytes(report).decode(),
                                   resource="corpus://" + name + "/" + handle)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_structures(ctx: Context, request: SelectedStructuralRequest):
        """Read explicit selected structural roots with original use and support custody."""
        return bounded_mcp_result(execute(request, inspect_selected_structures, "selected-structures"), request.max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_dossier(ctx: Context, request: SelectedDossierRequest):
        """Page exact immutable membership or its display; private standing stays explicit."""
        return bounded_mcp_result(execute(request, inspect_selected_dossier, "selected-dossier"), request.max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_structural_gap(ctx: Context, request: SelectedGapRequest):
        """Read recorded decisions and premises. Missing data establishes no absence."""
        return bounded_mcp_result(execute(request, inspect_selected_gap, "selected-structural-gap"), request.max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_source_journey(ctx: Context, request: SelectedSourceDecisionJourneyRequest):
        """Follow one native source opportunity through explicit roots in the same read."""
        return bounded_mcp_result(execute(request, inspect_selected_source_journey, "selected-source-journey"), request.max_bytes)

    def resource(handle, contract, operation, name):
        request = contract.model_validate(decode_rich_cursor(handle))
        content = execute(request, operation, name).model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise ValueError("complete structural resource exceeds max_bytes")
        return content

    @server.resource("corpus://selected-structures/{handle}")
    def structures_resource(handle: str) -> str:
        return resource(handle, SelectedStructuralRequest, inspect_selected_structures, "selected-structures")

    @server.resource("corpus://selected-dossier/{handle}")
    def dossier_resource(handle: str) -> str:
        return resource(handle, SelectedDossierRequest, inspect_selected_dossier, "selected-dossier")

    @server.resource("corpus://selected-structural-gap/{handle}")
    def gap_resource(handle: str) -> str:
        return resource(handle, SelectedGapRequest, inspect_selected_gap, "selected-structural-gap")

    @server.resource("corpus://selected-source-journey/{handle}")
    def journey_resource(handle: str) -> str:
        return resource(handle, SelectedSourceDecisionJourneyRequest, inspect_selected_source_journey, "selected-source-journey")
