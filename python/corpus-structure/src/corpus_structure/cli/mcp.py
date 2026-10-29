"""`ci mcp serve` and `ci direct` (agent interface §3.5; D8 §1, §4).

- `ci mcp serve` runs the main MCP profile on stdio (registered in `.mcp.json`); nothing reaches
  stdout before the protocol handshake.
- `ci direct "TEXT" [--scope S] [--project NAME]` records an operator direction through the same
  function as the `record_direction` tool.
"""

from __future__ import annotations

from typing import Annotated

import typer

from corpus_structure.cli.output import JsonOpt, emit, state, stderr_console

mcp_app = typer.Typer(help="Serve the MCP tools on stdio.", no_args_is_help=True)


@mcp_app.command("serve")
def serve(
    ctx: typer.Context,
    semantic_run: Annotated[
        int | None, typer.Option(help="Bind tools to this semantic run.")
    ] = None,
) -> None:
    """Run the main MCP profile on stdio (one process per Claude Code session)."""
    from corpus_structure.intervene.server import serve as run

    run(semantic_run=semantic_run, settings=state(ctx).settings())


def direct(
    ctx: typer.Context,
    text: Annotated[str, typer.Argument(help="The direction.")],
    scope: Annotated[str | None, typer.Option(help="What it applies to.")] = None,
    project: Annotated[
        str | None, typer.Option(help="The project (default: the only one).")
    ] = None,
    json: JsonOpt = False,
) -> None:
    """Record operator guidance in the semantic operation log."""
    from corpus_structure.cli import orchestrate
    from corpus_structure.intervene.directions import record_direction
    from corpus_structure.intervene.service import ToolFailure
    from corpus_structure.orchestrate.commands import CommandError

    try:
        with orchestrate.ENGINE(state(ctx).settings()) as engine:
            report = record_direction(
                engine,
                text,
                scope,
                actor="human:operator",
                project=project or state(ctx).settings().runtime.default_project,
            )
    except (ToolFailure, CommandError) as error:
        stderr_console().print(f"refused: {error}")
        raise typer.Exit(code=1) from None
    emit(report, json=json)


def register(app: typer.Typer) -> None:
    app.add_typer(mcp_app, name="mcp")
    app.command("direct")(direct)
