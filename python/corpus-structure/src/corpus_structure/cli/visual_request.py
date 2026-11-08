"""Explicit local Chandra recognition and raw replay for a pinned source."""

from pathlib import Path
from typing import Annotated

import typer

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, emit, state


def visual_request(
    ctx: typer.Context,
    run: int,
    producing_task: Annotated[int, typer.Option()],
    product: Annotated[str, typer.Option()],
    native_digest: Annotated[str, typer.Option()],
    page: Annotated[int, typer.Option()],
    semantic_release: Annotated[str, typer.Option()],
    realization: Annotated[str, typer.Option()],
    artifacts: Annotated[Path | None, typer.Option(file_okay=False)] = None,
    pointer: str | None = None,
    region_index: int | None = None,
    rotation: Annotated[
        int | None, typer.Option(help="Clockwise crop rotation in degrees.")
    ] = None,
    replay_run: int | None = None,
    replay_task: int | None = None,
    replay_product: str | None = None,
    replay_digest: str | None = None,
    json: JsonOpt = False,
) -> None:
    """Recognize one exact PDF page or crop, or replay its retained raw observation."""
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.visual_requests import (
        VisualSelection,
        request_visual_observation,
    )
    from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

    with failure_boundary(json, expected=(ValueError, KeyError)):
        selection = VisualSelection.model_validate(
            {
                "source": dict(
                    run_id=run,
                    task_id=producing_task,
                    product_key=product,
                    content_digest=native_digest,
                ),
                "page_no": page,
                "pointer": pointer,
                "region_index": region_index,
                "rotation": rotation,
            }
        )
        supplied = dict(
            run_id=replay_run,
            task_id=replay_task,
            product_key=replay_product,
            content_digest=replay_digest,
        )
        replay = (
            VisualEvidencePin.model_validate(supplied)
            if any(value is not None for value in supplied.values())
            else None
        )
        settings = state(ctx).settings()
        with open_runtime_engine(
            settings, application_name="ci-visual-request", purpose="write"
        ) as engine:
            result = request_visual_observation(
                engine,
                selection=selection,
                semantic_release=semantic_release,
                realization=realization,
                receipts=settings.nemotron.receipts,
                artifacts=artifacts,
                replay=replay,
                nemotron_endpoint=settings.nemotron.endpoint,
            )
        failed = result.status == "failed"
        emit(result, json=json, exit_code=int(failed))
        if failed:
            raise typer.Exit(1)


def visual_group(
    ctx: typer.Context,
    run: int,
    producing_task: Annotated[int, typer.Option()],
    product: Annotated[str, typer.Option()],
    native_digest: Annotated[str, typer.Option()],
    semantic_release: Annotated[str, typer.Option()],
    realization: Annotated[str, typer.Option()],
    artifacts: Annotated[Path, typer.Option(file_okay=False)],
    selections: Annotated[Path, typer.Option(dir_okay=False)],
    json: JsonOpt = False,
) -> None:
    """Recognize up to four pages or crops from a JSON list of source selections."""
    from json import loads

    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.visual_requests import VisualSelection, request_visual_group
    from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

    with failure_boundary(json, expected=(ValueError, KeyError, OSError)):
        source = VisualEvidencePin(
            run_id=run, task_id=producing_task, product_key=product, content_digest=native_digest
        )
        rows = loads(selections.read_bytes())
        if not isinstance(rows, list) or any(
            not isinstance(row, dict) or "source" in row for row in rows
        ):
            raise ValueError("expected a JSON list of page or crop selections without source pins")
        batch = tuple(VisualSelection.model_validate(dict(row, source=source)) for row in rows)
        settings = state(ctx).settings()
        with open_runtime_engine(
            settings, application_name="ci-visual-group", purpose="write"
        ) as engine:
            result = request_visual_group(
                engine,
                selections=batch,
                semantic_release=semantic_release,
                realization=realization,
                receipts=settings.nemotron.receipts,
                artifacts=artifacts,
                nemotron_endpoint=settings.nemotron.endpoint,
            )
        failed = result.status == "failed"
        emit(result, json=json, exit_code=int(failed))
        if failed:
            raise typer.Exit(1)
