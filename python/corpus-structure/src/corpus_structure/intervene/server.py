"""Current extraction MCP entry point, using admitted semantic project/run bindings."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from corpus_structure.settings import Settings


def build_server(
    session: Any = None,
    *,
    semantic_run: int | None = None,
    settings: Settings | None = None,
) -> FastMCP:
    """The current profile always uses semantic source and proposal contracts."""
    from corpus_structure.intervene.semantic_server import build_semantic_server

    return build_semantic_server(session=session, run_id=semantic_run, settings=settings)


def serve(*, semantic_run: int | None = None, settings: Settings | None = None) -> None:
    """Run the semantic project queue over stdio without a banner."""
    build_server(semantic_run=semantic_run, settings=settings).run(
        transport="stdio", show_banner=False
    )
