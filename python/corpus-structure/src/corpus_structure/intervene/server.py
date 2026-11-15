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

    server = build_external_server(session, project=project, demand=demand, settings=settings)
    from .demand_read_tools import register_demand_read_tools
    register_demand_read_tools(server, settings=settings or Settings(), read_engine=read_engine, project=project, demand=demand)
    return server


def serve(
    *, project: str | None = None, demand: str | None = None, settings: Settings | None = None
) -> None:
    build_server(project=project, demand=demand, settings=settings).run(
        transport="stdio", show_banner=False
    )
