"""Thin operator routing for native demand custody and pinned frontier inspection."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import BaseModel, RootModel

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.managed import managed_operation, result_store
from corpus_structure.cli.output import JsonOpt, emit, read_request_bytes, state, write_report_text
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads, wire_json_loads
from corpus_structure.semantic.data_operation_service import (
    CreateDataDemand,
    DdoJsonValue,
    cancel_data_demand,
    create_data_demand,
    read_data_demand,
)
from corpus_structure.semantic.storage_target import acquired_target

app = typer.Typer(help="Create, inspect and cancel immutable native demands.", no_args_is_help=True)


@contextmanager
def _open_engine(settings, *, purpose: Literal["read", "write"]) -> Generator:
    from corpus_structure.semantic.runtime import open_runtime_engine

    with open_runtime_engine(settings, "ci-demands", purpose=purpose) as engine:
        yield engine


ENGINE = _open_engine


class DemandActionReport(BaseModel):
    id: str
    native: dict[str, DdoJsonValue]


class DemandSnapshot(RootModel[dict[str, DdoJsonValue]]):
    pass


def _emit_demand(report, *, json):
    if json:
        write_report_text(json_bytes(report.model_dump(mode="python")).decode() + "\n")
    else:
        emit(report, json=False)


def _mutation(
    ctx: typer.Context, action: Literal["create", "cancel"], request: dict, *, json: bool
) -> DemandActionReport:
    with managed_operation(
        result_store(ctx), "demands." + action, json=json, expected=(ValueError, KeyError, OSError)
    ) as invocation:
        request_path = invocation.directory / "request.json"
        request_path.write_bytes(json_bytes(request))
        invocation.publish("request", request_path)
        with ENGINE(state(ctx).settings(), purpose="write") as engine, engine.begin() as connection:
            target = acquired_target(connection, purpose="write")
            invocation.record_target(target, None, None, request.get("release_id"))
            if action == "create":
                native = create_data_demand(connection, CreateDataDemand.model_validate(request))
            else:
                native = cancel_data_demand(
                    connection,
                    request["demand_id"],
                    reason=request["reason"],
                )
        invocation.record_effect("native demand " + action + ":" + native["demand_id"])
        native_path = invocation.directory / "native.json"
        native_path.write_bytes(json_bytes(native))
        invocation.publish("native", native_path)
        invocation.settle("passed", demand_id=native["demand_id"])
        return DemandActionReport(id=invocation.id, native=native)


@app.command("create")
def create(
    ctx: typer.Context,
    request: Annotated[
        Path,
        typer.Option(
            help="Service request with frozen intent/release/runtime; '-' reads stdin.",
        ),
    ],
    json: JsonOpt = False,
) -> None:
    """Create or resume the deterministic demand for an existing frozen intent."""
    with failure_boundary(json, expected=(ValueError, OSError)):
        parsed = CreateDataDemand.model_validate(json_loads(read_request_bytes(request)))
        report = _mutation(ctx, "create", parsed.model_dump(mode="python"), json=json)
    _emit_demand(report, json=json)


@app.command("read")
def read(
    ctx: typer.Context,
    demand: Annotated[str, typer.Argument(help="Exact immutable native demand ID.")],
    continuation: Annotated[
        Path | None,
        typer.Option(
            help="Complete native continuation JSON; '-' reads stdin.",
        ),
    ] = None,
    limit: Annotated[int | None, typer.Option(min=1, max=1000)] = None,
    view: Annotated[Literal["frontier", "products"] | None, typer.Option()] = None,
    json: JsonOpt = False,
) -> None:
    """Inspect the native frontier, preserving source, read and pagination pins."""
    with failure_boundary(json, expected=(ValueError, OSError)):
        pins = None if continuation is None else wire_json_loads(read_request_bytes(continuation))
        if pins is not None and not isinstance(pins, dict):
            raise ValueError("continuation must be a complete native JSON object")
        with ENGINE(state(ctx).settings(), purpose="read") as engine, engine.begin() as connection:
            snapshot = read_data_demand(
                connection,
                demand,
                continuation=pins,
                limit=limit,
                view=view,
            )
    _emit_demand(DemandSnapshot(snapshot), json=json)


@app.command("cancel")
def cancel(
    ctx: typer.Context,
    demand: Annotated[str, typer.Argument(help="Exact immutable native demand ID.")],
    reason: Annotated[str, typer.Option(help="Reason retained by native cancellation.")],
    json: JsonOpt = False,
) -> None:
    """Detach this demand while retaining independent shared producer interest."""
    report = _mutation(ctx, "cancel", {"demand_id": demand, "reason": reason}, json=json)
    _emit_demand(report, json=json)


@app.command("execute")
def execute(
    ctx: typer.Context,
    demand: Annotated[
        str, typer.Argument(help="Exact retained native demand ID to execute or resume.")
    ],
    source_root: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            help="Explicit root of the retained executable source locations.",
        ),
    ],
    project: Annotated[
        str | None, typer.Option(help="Require the retained demand to belong to this project.")
    ] = None,
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
    max_rounds: Annotated[int, typer.Option(min=1)] = 100,
    json: JsonOpt = False,
) -> None:
    """Execute the frozen native frontier; repeat this action to resume the same intent."""
    from corpus_structure.cli.characterization_options import method_settings
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.semantic.data_operation_service import execute_data_demand

    settings = state(ctx).settings()
    methods = method_settings(settings, execution_policy)
    with managed_operation(
        result_store(ctx),
        "demands.execute",
        json=json,
        expected=(ValueError, KeyError, OSError),
        scope={"demand_id": demand},
    ) as invocation:
        with (
            ENGINE(settings, purpose="write") as engine,
            ENGINE(settings, purpose="admit") as admitted,
        ):
            with engine.begin() as connection:
                target = acquired_target(connection, purpose="write")
                invocation.record_target(target, None, None, None)

            def retain(result):
                native = wire_json_loads(result.snapshot)
                report = {
                    "demand_id": result.demand_id,
                    "snapshot": native,
                    "snapshot_standing": result.snapshot_standing,
                    "receipt_count": result.receipt_count,
                    "receipts_truncated": result.receipts_truncated,
                    "receipts": [wire_json_loads(value) for value in result.receipts],
                }
                path = invocation.directory / "native.json"
                path.write_bytes(json_bytes(report))
                invocation.publish("native", path)
                return report

            try:
                result = execute_data_demand(
                    engine,
                    demand,
                    source_root=source_root,
                    limit=limit,
                    max_rounds=max_rounds,
                    policy=methods.execution_policy,
                    project_id=project,
                    nemotron_endpoint=methods.nemotron_endpoint,
                    admission_engine=admitted,
                )
            except NativeDemandExecutionError as error:
                retain(error.result)
                raise
            native = retain(result)
        invocation.settle("passed", demand_id=demand, receipt_count=result.receipt_count)
        report = DemandActionReport(id=invocation.id, native=native)
    _emit_demand(report, json=json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="demands")
