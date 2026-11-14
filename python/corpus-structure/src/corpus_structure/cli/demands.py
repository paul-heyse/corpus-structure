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
    NativeDemandRequest,
    create_native_demand,
    cancel_data_demand,
    create_data_demand,
    read_data_demand,
)
from corpus_structure.semantic.storage_target import acquired_target

app = typer.Typer(help="Create, inspect and cancel immutable native demands.", no_args_is_help=True)


@contextmanager
def _open_engine(settings, *, purpose: Literal["read", "write", "admit"]) -> Generator:
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
    execute_request(
        ctx, demand=demand, source_root=source_root, project=project,
        execution_policy=execution_policy, limit=limit, max_rounds=max_rounds, json=json,
    )


def execute_request(
    ctx: typer.Context, *, source_root: Path, demand: str | None = None,
    request: NativeDemandRequest | None = None, source_request=None,
    project: str | None = None, action: str = "demands.execute",
    execution_policy: Path | None = None, limit: int = 100, max_rounds: int = 100,
    json: bool = False,
) -> None:
    """One managed path for source creation, explicit native requests and exact resume."""
    from corpus_structure.cli.characterization_options import method_settings
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.orchestrate.source_reporting import (
        record_native_demand, retain_native_demand_result,
    )
    from corpus_structure.semantic.data_operation_service import execute_data_demand

    if sum(value is not None for value in (demand, request, source_request)) != 1:
        raise typer.BadParameter("select one source request, native request or retained demand")
    settings = state(ctx).settings()
    methods = method_settings(settings, execution_policy)
    with managed_operation(
        result_store(ctx), action, json=json, expected=(ValueError, KeyError, OSError),
        scope={"demand_id": demand, "project": project},
    ) as invocation:
        invocation.manifest.details["native_source_root"] = str(source_root.resolve())
        with ENGINE(settings, purpose="write") as engine, ENGINE(settings, purpose="admit") as admitted:
            with engine.begin() as connection:
                target = acquired_target(connection, purpose="write")
                if source_request is not None:
                    from corpus_structure.orchestrate.source_operation import prepare_source_demand

                    request = prepare_source_demand(connection, source_request)
                if request is not None:
                    if project is not None and request.project_id != project:
                        raise ValueError("request belongs to another project")
                    path = invocation.directory / "request.json"
                    path.write_bytes(json_bytes(request.model_dump(mode="python")))
                    invocation.publish("request", path)
                    snapshot = create_native_demand(connection, request)
                    demand = snapshot["demand_id"]
                else:
                    assert demand is not None
                    snapshot = read_data_demand(connection, demand, limit=1)
                    if project is not None and snapshot["project_id"] != project:
                        raise ValueError("retained demand belongs to another project")
                invocation.record_target(target, None, None, snapshot["release_id"])
            record_native_demand(invocation, snapshot, target)
            assert demand is not None
            try:
                result = execute_data_demand(
                    engine, demand, source_root=source_root, limit=limit, max_rounds=max_rounds,
                    policy=methods.execution_policy, project_id=project,
                    nemotron_endpoint=methods.nemotron_endpoint, admission_engine=admitted,
                )
            except NativeDemandExecutionError as error:
                retain_native_demand_result(invocation, error.result)
                raise
            native = retain_native_demand_result(invocation, result)
        invocation.settle("passed", demand_id=demand, receipt_count=result.receipt_count)
        report = DemandActionReport(id=invocation.id, native=native)
    _emit_demand(report, json=json)


@app.command("plan")
def plan(
    ctx: typer.Context,
    request: Annotated[Path, typer.Option(help="Typed native choices to compile and freeze; '-' reads stdin.")],
    json: JsonOpt = False,
) -> None:
    """Freeze declared operation choices and register the exact native demand."""
    with failure_boundary(json, expected=(ValueError, KeyError, OSError)):
        parsed = NativeDemandRequest.model_validate(json_loads(read_request_bytes(request)))
    with managed_operation(
        result_store(ctx), "demands.plan", json=json, expected=(ValueError, KeyError, OSError)
    ) as invocation:
        request_path = invocation.directory / "request.json"
        request_path.write_bytes(json_bytes(parsed.model_dump(mode="python")))
        invocation.publish("request", request_path)
        with ENGINE(state(ctx).settings(), purpose="write") as engine, engine.begin() as connection:
            target = acquired_target(connection, purpose="write")
            native = create_native_demand(connection, parsed)
            invocation.record_target(target, None, None, parsed.release_id)
        from corpus_structure.orchestrate.source_reporting import record_native_demand

        record_native_demand(invocation, native, target)
        path = invocation.directory / "native.json"
        path.write_bytes(json_bytes(native))
        invocation.publish("native", path)
        invocation.settle("passed", demand_id=native["demand_id"])
        report = DemandActionReport(id=invocation.id, native=native)
    _emit_demand(report, json=json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="demands")
