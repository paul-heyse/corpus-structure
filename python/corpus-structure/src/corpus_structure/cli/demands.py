"""Thin operator routing for native demand custody and pinned frontier inspection."""

from __future__ import annotations

import json as jsonlib
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import BaseModel, JsonValue, RootModel

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.managed import managed_operation, result_store
from corpus_structure.cli.output import JsonOpt, emit, read_request_bytes, state
from corpus_structure.semantic.data_operation_service import (
    CreateDataDemand,
    cancel_data_demand,
    create_data_demand,
    read_data_demand,
)
from corpus_structure.semantic.identity import canonical_bytes
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
    native: dict[str, JsonValue]


class DemandSnapshot(RootModel[dict[str, JsonValue]]):
    pass


def _mutation(ctx: typer.Context, action: Literal["create", "cancel"], request: dict,
              *, json: bool) -> DemandActionReport:
    with managed_operation(result_store(ctx), "demands." + action, json=json,
                           expected=(ValueError, KeyError, OSError)) as invocation:
        request_path = invocation.directory / "request.json"
        request_path.write_bytes(canonical_bytes(request))
        invocation.publish("request", request_path)
        with ENGINE(state(ctx).settings(), purpose="write") as engine, engine.begin() as connection:
            target = acquired_target(connection, purpose="write")
            invocation.record_target(target, None, None, request.get("release_id"))
            if action == "create":
                native = create_data_demand(connection, CreateDataDemand.model_validate(request))
            else:
                native = cancel_data_demand(
                    connection, request["demand_id"], reason=request["reason"],
                )
        invocation.record_effect("native demand " + action + ":" + native["demand_id"])
        native_path = invocation.directory / "native.json"
        native_path.write_bytes(canonical_bytes(native))
        invocation.publish("native", native_path)
        invocation.settle("passed", demand_id=native["demand_id"])
        return DemandActionReport(id=invocation.id, native=native)


@app.command("create")
def create(
    ctx: typer.Context,
    request: Annotated[Path, typer.Option(
        help="Service request with frozen intent/release/runtime; '-' reads stdin.",
    )],
    json: JsonOpt = False,
) -> None:
    """Create or resume the deterministic demand for an existing frozen intent."""
    with failure_boundary(json, expected=(ValueError, OSError)):
        parsed = CreateDataDemand.model_validate_json(read_request_bytes(request))
        report = _mutation(ctx, "create", parsed.model_dump(mode="json"), json=json)
    emit(report, json=json)


@app.command("read")
def read(
    ctx: typer.Context,
    demand: Annotated[str, typer.Argument(help="Exact immutable native demand ID.")],
    continuation: Annotated[Path | None, typer.Option(
        help="Complete native continuation JSON; '-' reads stdin.",
    )] = None,
    limit: Annotated[int | None, typer.Option(min=1, max=1000)] = None,
    view: Annotated[Literal["frontier", "products"] | None, typer.Option()] = None,
    json: JsonOpt = False,
) -> None:
    """Inspect the native frontier, preserving source, read and pagination pins."""
    with failure_boundary(json, expected=(ValueError, OSError)):
        pins = None if continuation is None else jsonlib.loads(read_request_bytes(continuation))
        if pins is not None and not isinstance(pins, dict):
            raise ValueError("continuation must be a complete native JSON object")
        with ENGINE(state(ctx).settings(), purpose="read") as engine, engine.begin() as connection:
            snapshot = read_data_demand(
                connection, demand, continuation=pins, limit=limit, view=view,
            )
    emit(DemandSnapshot(snapshot), json=json)


@app.command("cancel")
def cancel(
    ctx: typer.Context,
    demand: Annotated[str, typer.Argument(help="Exact immutable native demand ID.")],
    reason: Annotated[str, typer.Option(help="Reason retained by native cancellation.")],
    json: JsonOpt = False,
) -> None:
    """Detach this demand while retaining independent shared producer interest."""
    report = _mutation(ctx, "cancel", {"demand_id": demand, "reason": reason}, json=json)
    emit(report, json=json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="demands")
