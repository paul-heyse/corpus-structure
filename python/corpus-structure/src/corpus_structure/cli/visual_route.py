"""Read Chandra diagnostics and retained dispatch results."""

from typing import TYPE_CHECKING

import typer

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, emit, state

if TYPE_CHECKING:
    from corpus_structure.cli.managed import Manifest


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


def inspect_visual_dispatch(ctx: typer.Context, manifest: Manifest) -> None:
    """Read current exact native progress without rewriting the managed receipt."""
    from sqlalchemy.exc import SQLAlchemyError

    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import StorageTargetError, verify_target
    from corpus_structure.semantic.visual_dispatch import read_visual_dispatch_progress

    account = manifest.operation_account
    if account is None or account.routing is None:
        return
    target = account.acquired_target
    routing = account.routing
    if target is not None:
        try:
            with (
                open_runtime_engine(
                    state(ctx).settings(), "ci-visual-dispatch-inspect", purpose="read"
                ) as engine,
                read_snapshot(engine) as conn,
            ):
                verify_target(conn, target, purpose="read")
                progress = read_visual_dispatch_progress(conn, routing.nomination_run_id)
        except SQLAlchemyError, StorageTargetError, OperationConflict, OSError:
            pass
        else:
            account.routing = routing.model_copy(
                update={"native_status": "verified", "projection": progress.model_dump(mode="json")}
            )
            return
    account.routing = routing.model_copy(update={"native_status": "unavailable"})
