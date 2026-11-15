"""Explicit operator source inspection using the existing model command family."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from corpus_structure.cli.output import JsonOpt, emit, state
from corpus_structure.semantic.source_navigation import NavigationRequest, NavigationSnapshot

app = typer.Typer(help="Inspect captured source interfaces, navigation and selected change impact.")


class NavigationInput(BaseModel):
    snapshot: NavigationSnapshot
    request: NavigationRequest


def register(root):
    from corpus_structure.cli.model import app as model_app

    model_app.add_typer(app, name="source")


@app.command("navigate")
def navigate(
    ctx: typer.Context,
    input: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    json: JsonOpt = False,
):
    """Navigate an explicitly supplied immutable source snapshot through public ty LSP."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.source_navigation import inspect_source_navigation

    with failure_boundary(json, expected=(ValueError, OSError)):
        with input.open("rb") as stream:
            content = stream.read(16 * 1024 * 1024 + 1)
        if len(content) > 16 * 1024 * 1024:
            raise ValueError("navigation input exceeds16MiB")
        request = NavigationInput.model_validate_json(content)
        result = inspect_source_navigation(request.snapshot, request.request)
    emit(result, json=json)


@app.command("interfaces")
def interfaces(
    ctx: typer.Context,
    release: str,
    operation: str | None = None,
    cursor: str | None = None,
    limit: int = 100,
    max_bytes: int = 262144,
    json: JsonOpt = False,
):
    """Read bounded prepared facts from an explicit archived release."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.source_interface_read import (
        SourceInterfaceRequest,
        read_source_interface_page,
    )

    with (
        failure_boundary(json, expected=(ValueError, KeyError)),
        open_runtime_engine(
            state(ctx).settings(), "ci-source-interfaces", purpose="read"
        ) as engine,
        engine.begin() as connection,
    ):
        result = read_source_interface_page(
            open_release(connection, release),
            SourceInterfaceRequest(
                release_id=release,
                operation_id=operation,
                cursor=cursor,
                limit=limit,
                max_bytes=max_bytes,
            ),
        )
    emit(result, json=json)


@app.command("impact")
def impact(
    ctx: typer.Context,
    input: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    json: JsonOpt = False,
):
    """Explain change relative to explicit before/target demand and release pins."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.change_impact import ChangeImpactRequest, inspect_change_impact
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    with failure_boundary(json, expected=(ValueError, KeyError)):
        request = ChangeImpactRequest.model_validate_json(input.read_bytes())
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-source-impact", purpose="read"
            ) as engine,
            engine.begin() as connection,
        ):
            target = open_release(connection, request.target_release_id)
            result = inspect_change_impact(connection, request, target_prepared=target)
    emit(result, json=json)
