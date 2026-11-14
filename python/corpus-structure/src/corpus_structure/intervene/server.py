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
) -> FastMCP:
    from .external_server import build_external_server

    return build_external_server(session, project=project, demand=demand, settings=settings)


def serve(
    *, project: str | None = None, demand: str | None = None, settings: Settings | None = None
) -> None:
    build_server(project=project, demand=demand, settings=settings).run(
        transport="stdio", show_banner=False
    )
