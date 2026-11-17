"""Current MCP entry point over native task-owned external demand packets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import FastMCP

from corpus_structure.settings import Settings

if TYPE_CHECKING:
    from corpus_structure.semantic.data_operation_external import ExternalDataSession


def build_server(
    session: ExternalDataSession | None = None,
    *,
    project: str | None = None,
    demand: str | None = None,
    settings: Settings | None = None,
    read_engine=None,
) -> FastMCP:
    from .external_server import build_external_server

    from .runtime_engines import McpRuntimeEngines

    selected_settings = settings or Settings()
    engines = McpRuntimeEngines(selected_settings, "ci-mcp-external", read_engine=read_engine)
    server = build_external_server(
        session, project=project, demand=demand, settings=selected_settings, engines=engines
    )
    from .demand_read_tools import register_demand_read_tools

    register_demand_read_tools(
        server,
        settings=selected_settings,
        read_engine=read_engine,
        engine_provider=lambda: engines.engine("read"),
        project=project,
        demand=demand,
    )
    from .native_render_tools import register_native_render_tools

    register_native_render_tools(
        server,
        engines=engines,
        settings=selected_settings,
        project=project
        if project is not None
        else session.project_id
        if session is not None
        else None,
        demand=demand if demand is not None else session.demand_id if session is not None else None,
    )
    return server


def serve(
    *, project: str | None = None, demand: str | None = None, settings: Settings | None = None
) -> None:
    build_server(project=project, demand=demand, settings=settings).run(
        transport="stdio", show_banner=False
    )
