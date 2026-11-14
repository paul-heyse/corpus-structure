"""Reusable operator actions over immutable native demand intent and receipts."""

from __future__ import annotations

from typing import Any, Literal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import Connection

from .data_operation_admission import bound_data_operation_model
from .data_operation_demands import DemandIntent, DemandPlanner
from .data_operation_storage import DataOperationStorage
from .identity import canonical_bytes
from .releases import load_release


def execute_data_demand(
    engine,
    demand_id: str,
    *,
    source_root: Path,
    policy=None,
    limit: int = 100,
    max_rounds: int = 100,
):
    """Resume exact retained intent with acquired source/runtime custody.

    Source locations are physical acquisition hints. All executable bytes and
    semantic selections remain authenticated by the retained release and runtime.
    No connection survives preparation into provider execution or capacity waits.
    """
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutor

    from .composed import read_data_operation_inputs
    from .releases import load_release_inputs
    from .runtime_binding_store import runtime_binding_for_release

    with engine.begin() as connection:
        snapshot = read_data_demand(connection, demand_id, limit=1)
        bundle, dependencies, _, prepared = load_release_inputs(connection, snapshot["release_id"])
        runtime = runtime_binding_for_release(connection, prepared, snapshot["runtime_id"])
        captured = read_data_operation_inputs(dependencies)
        if captured is None or captured[1] is None:
            raise ValueError("demand execution requires its captured Python source context")
        sources = captured[1]
    root = source_root.resolve()
    locations = {}
    for source in sources.sources:
        path = root / source.filename
        if Path(source.filename).is_absolute() or not path.resolve().is_relative_to(root):
            raise ValueError("runtime source location escapes its explicit root")
        locations[source.module] = path
    executor = NativeDemandExecutor(
        engine,
        prepared,
        runtime,
        sources,
        runtime_locations=locations,
        schema=bundle,
        policy=policy,
    )
    return executor.run(demand_id, limit=limit, max_rounds=max_rounds)


class CreateDataDemand(BaseModel):
    """The caller supplies already frozen meaning, with explicit release/runtime custody."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    release_id: str
    runtime_id: str
    intent: dict[str, JsonValue]
    strength: str = "value"


def create_data_demand(connection: Connection, request: CreateDataDemand) -> dict[str, Any]:
    prepared = load_release(connection, request.release_id)
    planner = DemandPlanner(bound_data_operation_model(prepared), DataOperationStorage(connection))
    demand = planner.register(
        DemandIntent(canonical_bytes(request.intent)),
        project=request.project_id,
        release=request.release_id,
        runtime=request.runtime_id,
        strength=request.strength,
    )
    return planner.resume(demand["demand_id"])


def read_data_demand(
    connection: Connection,
    demand_id: str,
    *,
    continuation: dict[str, Any] | None = None,
    limit: int | None = None,
    view: Literal["frontier", "products"] | None = None,
) -> dict[str, Any]:
    """Preserve all native continuation pins; new bounds and view are explicit overrides."""
    payload = dict(continuation) if continuation is not None else {"demand_id": demand_id}
    if payload.get("demand_id") != demand_id:
        raise ValueError("continuation belongs to another demand")
    if limit is not None:
        payload["limit"] = limit
    if view is not None:
        if continuation is not None and payload.get("view", view) != view:
            raise ValueError("continuation view differs from the explicit requested view")
        payload["view"] = view
    return DataOperationStorage(connection).invoke("read_demand_result", payload)


def cancel_data_demand(connection: Connection, demand_id: str, *, reason: str) -> dict[str, Any]:
    """Native cancellation retains shared producers and never asserts physical retirement."""
    return DataOperationStorage(connection).invoke(
        "cancel_data_demand",
        {
            "demand_id": demand_id,
            "reason": reason,
        },
    )
