"""Regeneration creates a new native demand; recovery resumes only demand IDs."""

from pathlib import Path
from typing import Annotated, Literal

import typer

from corpus_structure.cli.output import JsonOpt


def regenerate(
    ctx: typer.Context,
    source_root: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    demand: Annotated[
        str | None, typer.Option(help="Exact retained native demand to resume.")
    ] = None,
    request: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    project: Annotated[str | None, typer.Option()] = None,
    semantic_release: Annotated[str | None, typer.Option()] = None,
    runtime: Annotated[str | None, typer.Option(help="Exact admitted runtime profile.")] = None,
    domain: Annotated[str | None, typer.Option()] = None,
    slice: Annotated[str | None, typer.Option()] = None,
    scope: Annotated[str | None, typer.Option()] = None,
    whole_document: Annotated[bool, typer.Option()] = False,
    source_membership: Annotated[Literal["direct", "descendants"], typer.Option()] = "descendants",
    document: Annotated[list[str] | None, typer.Option()] = None,
    source: Annotated[list[Path] | None, typer.Option(exists=True, dir_okay=False)] = None,
    target: Annotated[list[str] | None, typer.Option()] = None,
    operation_options: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    json: JsonOpt = False,
) -> None:
    """Execute declared source work against an explicit admitted release/runtime.

    Project/original registration is ci project init. Model admission, deployment,
    activation and answer selection retain their separate owning operations.
    """
    if demand is not None:
        if (
            request is not None
            or any(
                value is not None
                for value in (
                    semantic_release,
                    runtime,
                    domain,
                    slice,
                    scope,
                    operation_options,
                )
            )
            or whole_document
            or document
            or source
            or target
            or source_membership != "descendants"
        ):
            raise typer.BadParameter("a retained demand owns its source and workflow selections")
        from .demands import execute_request

        execute_request(
            ctx,
            demand=demand,
            source_root=source_root,
            project=project,
            execution_policy=execution_policy,
            action="regenerate",
            json=json,
        )
        return
    from .orchestrate import execute_source_choices

    execute_source_choices(
        ctx,
        action="regenerate",
        workflow="phase0",
        source_root=source_root,
        request=request,
        project=project,
        semantic_release=semantic_release,
        runtime=runtime,
        domain=domain,
        slice=slice,
        scope=scope,
        whole_document=whole_document,
        source_membership=source_membership,
        document=document,
        source=source,
        target=target,
        operation_options=operation_options,
        execution_policy=execution_policy,
        json=json,
    )


def register(app: typer.Typer) -> None:
    app.command("regenerate")(regenerate)
