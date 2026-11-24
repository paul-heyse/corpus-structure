"""Explicit evaluator-purpose MCP comparison; protected labels stay off the public profile."""

from contextlib import contextmanager
from typing import Annotated, Literal

from fastmcp import Context, FastMCP
from pydantic import BaseModel, BeforeValidator

from corpus_structure.evaluate.declared_record_policy import (
    DdoRecordFeatureFitRequest,
    prepare_record_feature_policy,
)
from corpus_structure.evaluate.selected_references import (
    SelectedReferenceEvaluationRequest,
    evaluate_selected_references,
)
from corpus_structure.intervene.mcp_results import bounded_structured_result
from corpus_structure.semantic.continuation_codec import decode_resource_handle
from corpus_structure.semantic.continuation_codec import encode_cursor as _cursor
from corpus_structure.semantic.data_operation_json import (
    FiniteJsonValue,
    finite_result_record,
    json_bytes,
)
from corpus_structure.semantic.refusals import tool_refusals
from corpus_structure.settings import Settings


def _feature_fit_json(value):
    if isinstance(value, DdoRecordFeatureFitRequest):
        return value
    # MCP has already decoded JSON arrays to Python lists. Re-enter through the
    # domain DTO's JSON boundary so its strict immutable tuple fields stay strict.
    return DdoRecordFeatureFitRequest.model_validate_json(json_bytes(value))


class RecordFeatureFitResult(BaseModel):
    format: Literal["record-feature-fit-structured-v2"] = "record-feature-fit-structured-v2"
    result: dict[str, FiniteJsonValue]


class ReferenceComparisonResult(BaseModel):
    format: Literal["selected-reference-comparison-structured-v2"] = (
        "selected-reference-comparison-structured-v2"
    )
    result: dict[str, FiniteJsonValue]
    resource: str


def build_evaluator_server(
    *, project: str, settings: Settings | None = None, evaluator_engine=None, fitter_engine=None
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

    @contextmanager
    def fitter():
        if fitter_engine is not None:
            with fitter_engine.begin() as connection:
                yield connection
        else:
            from corpus_structure.semantic.runtime import open_runtime_engine

            with (
                open_runtime_engine(
                    settings, "ci-mcp-record-fitter", purpose="fit", max_size=1
                ) as engine,
                engine.begin() as connection,
            ):
                yield connection

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def fit_complete_record_features(
        ctx: Context,
        request: Annotated[DdoRecordFeatureFitRequest, BeforeValidator(_feature_fit_json)],
    ):
        """Fit preliminary whole-reading parameters through the dedicated protected fitter; no policy authority."""
        if request.selection.project_id != project:
            raise ValueError("record feature fitting belongs to another evaluator project")
        with fitter() as connection:
            report = prepare_record_feature_policy(connection, request)
        return bounded_structured_result(
            RecordFeatureFitResult(result=finite_result_record(report)), 8388608
        )

    def compare(request):
        if request.project_id != project:
            raise ValueError("reference comparison belongs to another evaluator project")
        report = evaluate_selected_references(evaluator, request)
        replay = request.model_copy(
            update=dict(
                reference_cut=report["reference"]["cut"],
                prediction_cut=report["prediction"]["cut"],
            )
        )
        return ReferenceComparisonResult(
            result=finite_result_record(report),
            resource="corpus://selected-reference-comparison/"
            + _cursor(replay.model_dump(mode="python")),
        )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def compare_selected_reference(ctx: Context, request: SelectedReferenceEvaluationRequest):
        """Compare independent protected reference and prediction under distinct exact cuts; no inference."""
        return bounded_structured_result(compare(request), request.max_bytes)

    @server.resource("corpus://selected-reference-comparison/{handle}")
    def reference_comparison(handle: str) -> str:
        request = decode_resource_handle(handle, SelectedReferenceEvaluationRequest)
        content = compare(request).model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise ValueError("complete selected reference comparison resource exceeds max_bytes")
        return content

    return server
