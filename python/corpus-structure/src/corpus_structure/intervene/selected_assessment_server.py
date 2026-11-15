"""Explicit evaluator-purpose MCP comparison; protected labels stay off the public profile."""

from contextlib import contextmanager
from typing import Literal

from fastmcp import Context, FastMCP
from pydantic import BaseModel

from corpus_structure.evaluate.selected_references import (
    SelectedReferenceEvaluationRequest,
    evaluate_selected_references,
)
from corpus_structure.intervene.mcp_results import bounded_mcp_result
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_queries import _cursor, _decode
from corpus_structure.semantic.refusals import tool_refusals
from corpus_structure.settings import Settings


class ExactReferenceComparison(BaseModel):
    format: Literal["selected-reference-comparison-exact-json-v1"] = (
        "selected-reference-comparison-exact-json-v1"
    )
    exact_json: str
    resource: str


def build_evaluator_server(
    *, project: str, settings: Settings | None = None, evaluator_engine=None
):
    settings = Settings() if settings is None else settings
    server = FastMCP("corpus-structure selected reference evaluator")

    @contextmanager
    def evaluator():
        if evaluator_engine is not None:
            with evaluator_engine.begin() as connection:
                yield connection
        else:
            from corpus_structure.semantic.runtime import open_runtime_engine

            with (
                open_runtime_engine(
                    settings, "ci-mcp-selected-evaluator", purpose="evaluate", max_size=1
                ) as engine,
                engine.begin() as connection,
            ):
                yield connection

    def compare(request):
        if request.project_id != project:
            raise ValueError("reference comparison belongs to another evaluator project")
        with evaluator() as connection:
            report = evaluate_selected_references(connection, request)
        replay = request.model_copy(
            update=dict(
                reference_read_id=report["reference"]["cut"]["read_id"],
                reference_cut_id=report["reference"]["cut_id"],
                prediction_read_id=report["prediction"]["cut"]["read_id"],
                prediction_cut_id=report["prediction"]["cut_id"],
            )
        )
        return ExactReferenceComparison(
            exact_json=json_bytes(report).decode(),
            resource="corpus://selected-reference-comparison/"
            + _cursor(replay.model_dump(mode="python")),
        )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def compare_selected_reference(ctx: Context, request: SelectedReferenceEvaluationRequest):
        """Compare independent protected reference and prediction under distinct exact cuts; no inference."""
        return bounded_mcp_result(compare(request), request.max_bytes)

    @server.resource("corpus://selected-reference-comparison/{handle}")
    def reference_comparison(handle: str) -> str:
        request = SelectedReferenceEvaluationRequest.model_validate(_decode(handle))
        content = compare(request).model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise ValueError("complete selected reference comparison resource exceeds max_bytes")
        return content

    return server
