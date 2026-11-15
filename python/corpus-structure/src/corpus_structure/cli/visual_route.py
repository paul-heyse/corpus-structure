"""Read Chandra diagnostics and retained dispatch results."""

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, state

if TYPE_CHECKING:
    from corpus_structure.cli.managed import Manifest


def visual_route(
    ctx: typer.Context,
    demand: str,
    project: str = typer.Option(...),
    first: int = 1,
    limit: int = 32,
    continuation: Path | None = None,
    json: JsonOpt = False,
) -> None:
    """Assess selected visual products under their explicit native demand cut."""
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.visual_routing import read_demand_visual_routes

    with (
        failure_boundary(json, expected=(ValueError,)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-visual-route", purpose="read"
        ) as engine,
        engine.begin() as conn,
    ):
        from corpus_structure.semantic.data_operation_json import wire_json_loads

        cursor = None if continuation is None else wire_json_loads(continuation.read_bytes())
        report = read_demand_visual_routes(
            conn, demand, project_id=project, first=first, limit=limit, continuation=cursor
        )
    from corpus_structure.cli.demands import DemandSnapshot, _emit_demand

    _emit_demand(DemandSnapshot.model_validate(report), json=json)


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
