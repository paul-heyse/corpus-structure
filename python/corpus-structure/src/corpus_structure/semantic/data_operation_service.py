"""Reusable operator actions over immutable native demand intent and receipts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection

from corpus_structure.semantic._data_operation_wire import (
    WireCancelDataDemandRequest,
    WireCancelDataDemandResult,
    WireReadDemandResultRequest,
    WireReadDemandResultResult,
)

from .data_operation_admission import bound_data_operation_model
from .data_operation_demands import DemandIntent, DemandPlanner, ResumedDataDemand
from .data_operation_json import DdoJsonValue as DdoJsonValue
from .data_operation_json import json_bytes
from .data_operation_storage import DataOperationStorage
from .refusals import SemanticRefusal
from .releases import load_release


class DemandRoot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    subject: str = Field(min_length=1)
    original_source: str | None = Field(min_length=1)
    analyzed_scope: dict[str, DdoJsonValue]


class DemandOperationSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    operation: str = Field(min_length=1)
    parameters: dict[str, DdoJsonValue] = Field(default_factory=dict)
    choices: dict[str, DdoJsonValue] = Field(default_factory=dict)
    selected_dependencies: tuple[str, ...] = ()
    replicate: str | None = Field(default=None, min_length=1)


class DemandDiscoverySelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    producer: str = Field(min_length=1)
    output_role: str = Field(min_length=1)
    target: str = Field(min_length=1)
    population: str = Field(min_length=1)
    target_role: str | None = None


class DemandOriginalSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reference: dict[str, DdoJsonValue]
    selectors: tuple[dict[str, DdoJsonValue], ...] = Field(min_length=1)


class NativeDemandRequest(BaseModel):
    """Operator choices compiled against one admitted model, never a runtime registry.

    Explicit targets are distinct from a source frontdoor's chosen default targets.
    Only the effective model computes dependency closure and binding readiness.
    Provider questions, candidate selections and numerical policy are operation
    parameters/choices and are frozen before registering native demand custody.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    runtime_id: str = Field(min_length=1)
    roots: tuple[DemandRoot, ...] = Field(min_length=1)
    targets: tuple[str, ...] = Field(min_length=1)
    selections: tuple[DemandOperationSelection, ...] = ()
    discovery: tuple[DemandDiscoverySelection, ...] = ()
    source_sets: dict[str, list[dict[str, DdoJsonValue]]] = Field(default_factory=dict)
    original_sources: dict[str, DemandOriginalSelection] = Field(default_factory=dict)
    inference: str = "declared"
    execution_profile: str = Field(min_length=1)
    strength: str = "value"


def freeze_native_demand(prepared, request: NativeDemandRequest) -> DemandIntent:
    """Freeze exact choices using the compiled declarations and existing validators."""
    from .data_operation_demands import (
        DiscoverySelection,
        OperationSelection,
        RootSubject,
        freeze_demand,
    )
    from .data_operation_identity import semantic_value
    from .data_operation_source_sets import read_source_sets
    from .data_operation_support import OriginalSourceSelection
    from .identity import canonical_bytes

    return freeze_demand(
        bound_data_operation_model(prepared),
        roots=tuple(
            RootSubject(value.subject, value.original_source, json_bytes(value.analyzed_scope))
            for value in request.roots
        ),
        targets=request.targets,
        selections=tuple(
            OperationSelection(
                operation=value.operation,
                parameters=json_bytes(value.parameters),
                choices=json_bytes(value.choices),
                selected_dependencies=value.selected_dependencies,
                replicate=value.replicate,
                parameter_meaning=json_bytes(semantic_value(value.parameters)),
            )
            for value in request.selections
        ),
        discovery=tuple(DiscoverySelection(**value.model_dump()) for value in request.discovery),
        source_sets=read_source_sets(request.source_sets),
        original_sources=tuple(
            OriginalSourceSelection(
                name,
                canonical_bytes(value.reference),
                canonical_bytes(list(value.selectors)),
            )
            for name, value in request.original_sources.items()
        ),
        inference=request.inference,
        execution_profile=request.execution_profile,
    )


def create_native_demand(
    connection: Connection, request: NativeDemandRequest, *, prepared=None
) -> ResumedDataDemand:
    """Authenticate retained runtime custody before admitting the compiled intent."""
    from .runtime_binding_store import runtime_binding_for_release

    prepared = load_release(connection, request.release_id) if prepared is None else prepared
    if prepared.release_id != request.release_id:
        raise SemanticRefusal("prepared source request belongs to another release")
    runtime_binding_for_release(connection, prepared, request.runtime_id)
    intent = freeze_native_demand(prepared, request)
    planner = DemandPlanner(bound_data_operation_model(prepared), DataOperationStorage(connection))
    demand = planner.register(
        intent,
        project=request.project_id,
        release=request.release_id,
        runtime=request.runtime_id,
        strength=request.strength,
    )
    return planner.resume(demand["demand_id"])


def execute_data_demand(
    engine,
    demand_id: str,
    *,
    source_root: Path | None = None,
    purpose: Literal["write", "evaluate"] = "write",
    policy=None,
    project_id: str | None = None,
    admission_engine=None,
    fitter_engine=None,
    nemotron_endpoint: str | None = None,
    database_capacity: int | None = None,
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

    if purpose not in {"write", "evaluate"}:
        raise SemanticRefusal("native execution purpose must be write or evaluate")
    with engine.begin() as connection:
        if admission_engine is not None:
            from .storage_target import acquired_target

            target = acquired_target(connection, purpose=purpose)
            with admission_engine.begin() as admitted:
                if acquired_target(admitted, purpose="admit") != target.model_copy(
                    update={"purpose": "admit"}
                ):
                    raise SemanticRefusal("demand admission belongs to another PostgreSQL target")
        snapshot = read_data_demand(connection, demand_id, limit=1)
        if project_id is not None and snapshot["project_id"] != project_id:
            raise SemanticRefusal("retained demand belongs to another project")
        bundle, dependencies, _, prepared = load_release_inputs(connection, snapshot["release_id"])
        runtime = runtime_binding_for_release(connection, prepared, snapshot["runtime_id"])
        captured = read_data_operation_inputs(dependencies)
        if captured is None:
            raise SemanticRefusal("demand execution requires its captured operation declarations")
        if captured[1] is None:
            from .data_operation_admission import bound_data_operation_model
            from .python_operation_sources import PythonSourceCollection

            if any(
                operation.external is None
                for operation in bound_data_operation_model(prepared).operations
            ):
                raise SemanticRefusal("Python operations require their captured source context")
            sources = PythonSourceCollection(())
        else:
            sources = captured[1]
    if source_root is None and sources.sources:
        raise SemanticRefusal("captured Python execution requires an explicit source root")
    root = source_root.resolve() if source_root is not None else None
    locations = {}
    for source in sources.sources:
        assert root is not None
        path = root / source.filename
        if not path.resolve().is_relative_to(root):
            raise SemanticRefusal("runtime source location escapes its explicit root")
        locations[source.module] = path
    executor = NativeDemandExecutor(
        engine,
        prepared,
        runtime,
        sources,
        runtime_locations=locations,
        schema=bundle,
        declarations=captured[0],
        captured_contracts=dependencies.artifacts,
        policy=policy,
        nemotron_endpoint=nemotron_endpoint,
        admission_engine=admission_engine,
        fitter_engine=fitter_engine,
        database_capacity=database_capacity,
    )
    return executor.run(demand_id, limit=limit, max_rounds=max_rounds)


class CreateDataDemand(BaseModel):
    """The caller supplies already frozen meaning, with explicit release/runtime custody."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    release_id: str
    runtime_id: str
    intent: dict[str, DdoJsonValue]
    strength: str = "value"


def create_data_demand(connection: Connection, request: CreateDataDemand) -> ResumedDataDemand:
    prepared = load_release(connection, request.release_id)
    planner = DemandPlanner(bound_data_operation_model(prepared), DataOperationStorage(connection))
    demand = planner.register(
        DemandIntent(json_bytes(request.intent)),
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
    continuation: Mapping[str, Any] | None = None,
    limit: int | None = None,
    max_bytes: int | None = None,
    view: Literal["frontier", "products"] | None = None,
) -> WireReadDemandResultResult:
    """Preserve all native continuation pins; new bounds and view are explicit overrides."""
    payload = dict(continuation) if continuation is not None else {"demand_id": demand_id}
    if payload.get("demand_id") != demand_id:
        raise SemanticRefusal("continuation belongs to another demand")
    if limit is not None:
        payload["limit"] = limit
    if max_bytes is not None:
        payload["max_bytes"] = max_bytes
    if view is not None:
        if continuation is not None and payload.get("view", view) != view:
            raise SemanticRefusal("continuation view differs from the explicit requested view")
        payload["view"] = view
    return DataOperationStorage(connection).read_demand_result(
        cast(WireReadDemandResultRequest, payload)
    )


def cancel_data_demand(
    connection: Connection, demand_id: str, *, reason: str
) -> WireCancelDataDemandResult:
    """Native cancellation retains shared producers and never asserts physical retirement."""
    return DataOperationStorage(connection).cancel_data_demand(
        cast(
            WireCancelDataDemandRequest,
            {
                "demand_id": demand_id,
                "reason": reason,
            },
        )
    )
