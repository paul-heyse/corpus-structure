"""Reusable operator actions over immutable native demand intent and receipts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import Connection

from .data_operation_admission import bound_data_operation_model
from .data_operation_demands import DemandIntent, DemandPlanner
from .data_operation_storage import DataOperationStorage
from .identity import canonical_bytes
from .releases import load_release


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
