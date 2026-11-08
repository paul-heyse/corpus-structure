"""Read deterministic Chandra routing nominations without starting inference."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, emit, state


def visual_route(
    ctx: typer.Context,
    run: int,
    producing_task: int = typer.Option(...),
    product: str = typer.Option(...),
    native_digest: str = typer.Option(...),
    first: int = 1,
    limit: int = 32,
    json: JsonOpt = False,
) -> None:
    """Evaluate a bounded physical-page range of an exact published integrated PDF."""
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.visual_routing import read_visual_routes
    from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

    with (
        failure_boundary(json, expected=(ValueError,)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-visual-route", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        source = VisualEvidencePin(
            run_id=run, task_id=producing_task, product_key=product, content_digest=native_digest
        )
        report = read_visual_routes(conn, source, first=first, limit=limit)
    emit(report, json=json)


class VisualDispatchMode(StrEnum):
    SELECTIVE = "selective"
    ALL_PAGE = "all-page"


def visual_dispatch(
    ctx: typer.Context,
    run: int,
    producing_task: Annotated[int, typer.Option()],
    product: Annotated[str, typer.Option()],
    native_digest: Annotated[str, typer.Option()],
    source_cut: Annotated[int, typer.Option()],
    semantic_release: Annotated[str, typer.Option()],
    realization: Annotated[str, typer.Option()],
    mode: Annotated[VisualDispatchMode, typer.Option()],
    artifacts: Annotated[Path, typer.Option(file_okay=False)],
    first: int = 1,
    limit: int = 32,
    retry_failed: Annotated[
        bool, typer.Option(help="Retry a failed group once after resolving a transient failure.")
    ] = False,
    nomination_run_id: Annotated[int | None, typer.Option("--nomination-run")] = None,
    json: JsonOpt = False,
) -> None:
    """Dispatch candidate-only visual work for a committed source-ready page range."""
    from corpus_structure.cli.managed import managed_operation, result_store
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.visual_dispatch import dispatch_visual_work
    from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

    with managed_operation(
        result_store(ctx), "source.visual-dispatch", json=json, expected=(ValueError, OSError)
    ) as managed:
        source = VisualEvidencePin(
            run_id=run, task_id=producing_task, product_key=product, content_digest=native_digest
        )
        settings = state(ctx).settings()
        with open_runtime_engine(
            settings, application_name="ci-visual-dispatch", purpose="write"
        ) as engine:
            result = dispatch_visual_work(
                engine,
                source=source,
                source_cut=source_cut,
                semantic_release=semantic_release,
                realization=realization,
                mode=mode.value,
                first=first,
                limit=limit,
                artifacts=artifacts,
                receipts=settings.nemotron.receipts,
                nemotron_endpoint=settings.nemotron.endpoint,
                retry_failed=retry_failed,
                nomination_run_id=nomination_run_id,
                report_progress=managed.record_routing,
            )
        failed = any(group.status == "failed" for group in result.groups)
        managed.settle("failed" if failed else "passed")
    account = managed.manifest.operation_account
    emit(
        result.model_copy(
            update={
                "result_id": managed.id,
                "operation_account": account.model_dump(mode="json") if account else None,
            }
        ),
        json=json,
        exit_code=int(failed),
    )
    if failed:
        raise typer.Exit(1)
