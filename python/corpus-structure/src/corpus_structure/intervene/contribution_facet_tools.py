"""Current exact composite read transport over real selected native cuts."""

from typing import Literal

from fastmcp import Context
from pydantic import BaseModel, Field, ValidationError

from corpus_structure.semantic.continuation_codec import decode_rich_cursor
from corpus_structure.semantic.data_operation_json import FiniteJsonValue, finite_result_record
from corpus_structure.semantic.refusal_types import InvalidContinuation, RichQueryRefused
from corpus_structure.semantic.refusals import tool_refusals
from corpus_structure.semantic.selected_graph_budget import SelectedGraphBudgetExceeded
from corpus_structure.serve.contribution_facets import (
    ContributionFacetsRequest,
    serve_contribution_facets,
)
from corpus_structure.serve.identity_exclusion_comparison import (
    ExclusionComparisonRequest,
    compare_selected_exclusions,
)

from .mcp_results import bounded_structured_result


class SelectedCompositeRead(BaseModel):
    format: Literal["selected-composite-structured-v2"] = "selected-composite-structured-v2"
    cut_ids: tuple[str, ...] = Field(min_length=1, max_length=2)
    result: dict[str, FiniteJsonValue]
    resource: str


def register_contribution_facet_tools(server, reader, *, project=None, demand=None):
    def allowed(selected):
        if project is not None and selected.project_id != project:
            raise RichQueryRefused("composite read belongs to another server project")
        if demand is not None and selected.demand_id != demand:
            raise RichQueryRefused("composite read belongs to another server demand")

    def facets(request):
        allowed(request)
        with reader() as connection:
            report = serve_contribution_facets(connection, request)
        return SelectedCompositeRead(
            cut_ids=(report["cut_id"],),
            result=finite_result_record(report),
            resource="corpus://contribution-facets/" + report["resource_handle"],
        )

    def comparison(request):
        allowed(request.before)
        allowed(request.after)
        report = compare_selected_exclusions(reader, request)
        return SelectedCompositeRead(
            cut_ids=(report["before"]["pin"]["cut_id"], report["after"]["pin"]["cut_id"]),
            result=finite_result_record(report),
            resource="corpus://identity-exclusion-comparison/" + report["resource_handle"],
        )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(
        ValidationError, RichQueryRefused, InvalidContinuation, SelectedGraphBudgetExceeded
    )
    def inspect_contributions(ctx: Context, request: ContributionFacetsRequest):
        """Join actual selected contributions with typed interpretation and captured judgments.

        Private proposal/consolidation standing stays explicit. Missing assessment or
        unsupported nominal facets remain unknown.
        """
        return bounded_structured_result(facets(request), request.max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(
        ValidationError, RichQueryRefused, InvalidContinuation, SelectedGraphBudgetExceeded
    )
    def compare_identity_exclusions(ctx: Context, request: ExclusionComparisonRequest):
        """Compare two exact whole roots/read/use/product/derivation pins.

        Declaration matches use original product/member addresses. Unmatched or
        incomparable observations establish no source absence or source change.
        """
        return bounded_structured_result(comparison(request), request.max_bytes)

    @server.resource("corpus://contribution-facets/{handle}")
    def contribution_facets_resource(handle: str) -> str:
        request = ContributionFacetsRequest.model_validate(decode_rich_cursor(handle))
        content = facets(request).model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise RichQueryRefused("complete contribution resource exceeds max_bytes")
        return content

    @server.resource("corpus://identity-exclusion-comparison/{handle}")
    def exclusion_comparison_resource(handle: str) -> str:
        request = ExclusionComparisonRequest.model_validate(decode_rich_cursor(handle))
        content = comparison(request).model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise RichQueryRefused("complete comparison resource exceeds max_bytes")
        return content
