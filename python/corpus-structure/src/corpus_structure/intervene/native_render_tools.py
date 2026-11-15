"""Explicit source-region demand execution on the current command server."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.data_operation_service import NativeDemandRequest
from corpus_structure.semantic.native_requests import TARGET


class NativeRenderRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    project_id: str = Field(min_length=1)
    demand_id: str | None = Field(default=None, min_length=1)
    request: NativeDemandRequest | None = None
    source_root: Path | None = None
    limit: int = Field(default=100, strict=True, ge=1, le=1000)
    max_rounds: int = Field(default=100, strict=True, ge=1, le=1000)

    @model_validator(mode="after")
    def explicit_intent(self):
        if (self.demand_id is None) == (self.request is None):
            raise ValueError("render requires one explicit request or retained demand")
        if self.request is not None and (
            self.request.targets != (TARGET,) or self.request.project_id != self.project_id
        ):
            raise ValueError(
                "render requires its exact project and source.pdf_region/render target"
            )
        return self


class NativeRenderResponse(BaseModel):
    format: Literal["native-render-exact-json-v1"] = "native-render-exact-json-v1"
    demand_id: str
    exact_json: str


def execute_native_render(selection: NativeRenderRequest, *, settings, project, demand=None):
    from corpus_structure.orchestrate.native_execution import execute_native_intent
    from corpus_structure.orchestrate.source_reporting import native_demand_result
    from corpus_structure.orchestrate.source_request import method_settings
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.runtime import open_runtime_engine

    if selection.project_id != project:
        raise ValueError("render belongs to another server project")
    if demand is not None and (selection.request is not None or selection.demand_id != demand):
        raise ValueError("render belongs to another server demand")
    with (
        open_runtime_engine(settings, "ci-mcp-native-render", purpose="write") as engine,
        open_runtime_engine(settings, "ci-mcp-native-render-admit", purpose="admit") as admitted,
    ):
        result = execute_native_intent(
            engine,
            admitted,
            source_root=selection.source_root,
            methods=method_settings(settings),
            project=project,
            demand=selection.demand_id,
            request=selection.request,
            limit=selection.limit,
            max_rounds=selection.max_rounds,
            required_targets=(TARGET,),
        )
    return NativeRenderResponse(
        demand_id=result.demand_id, exact_json=json_bytes(native_demand_result(result)).decode()
    )


def register_native_render_tools(server, *, settings, project=None, demand=None):
    from fastmcp import Context

    from corpus_structure.intervene.mcp_results import bounded_mcp_result
    from corpus_structure.semantic.refusals import tool_refusals

    @server.tool(annotations={"readOnlyHint": False})
    @tool_refusals(ValueError, KeyError, OSError)
    def render_source_region(ctx: Context, request: NativeRenderRequest):
        """Execute or resume only the explicit source.pdf_region/render demand.

        The current native effect/claim/publication owners retain image custody.
        This command never chooses a latest source or accepts private task aliases.
        """
        return bounded_mcp_result(
            execute_native_render(
                request,
                settings=settings,
                project=project or settings.runtime.default_project,
                demand=demand,
            ),
            8 * 1024 * 1024,
        )
