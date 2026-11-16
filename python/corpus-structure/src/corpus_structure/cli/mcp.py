"""Current external-task, selected evaluator and retained-read MCP profiles."""

from __future__ import annotations

from typing import Annotated

import typer

from corpus_structure.cli.output import state

mcp_app = typer.Typer(help="Serve the MCP tools on stdio.", no_args_is_help=True)


@mcp_app.command("serve")
def serve(
    ctx: typer.Context,
    project: Annotated[str | None, typer.Option(help="Bind tools to this native project.")] = None,
    demand: Annotated[
        str | None, typer.Option(help="Restrict queue claims to this native demand.")
    ] = None,
) -> None:
    """Run the main MCP profile on stdio (one process per Claude Code session)."""
    from corpus_structure.intervene.server import serve as run

    run(project=project, demand=demand, settings=state(ctx).settings())


@mcp_app.command("evaluator")
def evaluator(
    ctx: typer.Context,
    project: Annotated[str, typer.Option(help="Exact protected evaluator project.")],
):
    """Serve selected reference comparison using the evaluator purpose on stdio."""
    from corpus_structure.intervene.selected_assessment_server import build_evaluator_server

    build_evaluator_server(project=project, settings=state(ctx).settings()).run(
        transport="stdio", show_banner=False
    )


@mcp_app.command("retained")
def retained(
    ctx: typer.Context,
    project: Annotated[
        str | None, typer.Option(help="Restrict selected reads to this project.")
    ] = None,
) -> None:
    """Serve archived source/cut/contract readers, separately from external work custody."""
    from corpus_structure.intervene.semantic_server import build_retained_reader_server

    build_retained_reader_server(project=project, settings=state(ctx).settings()).run(
        transport="stdio", show_banner=False
    )




def register(app: typer.Typer) -> None:
    app.add_typer(mcp_app, name="mcp")
