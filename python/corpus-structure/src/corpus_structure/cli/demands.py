"""Thin operator routing for native demand custody and pinned frontier inspection."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict
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
    cancel_data_demand,
    create_data_demand,
    create_native_demand,
    read_data_demand,
)
from corpus_structure.semantic.storage_target import acquired_target
from corpus_structure.settings import DeploymentProfile

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
        return DemandActionReport.model_validate({"id": invocation.id, "native": native})


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
    max_bytes: Annotated[
        int | None,
        typer.Option(min=1, max=67108864, help="Complete product-page byte bound (default 8 MiB)."),
    ] = None,
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
                max_bytes=max_bytes,
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
        Path | None,
        typer.Option(
            exists=True,
            file_okay=False,
            help="Explicit root of the retained executable source locations.",
        ),
    ] = None,
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
        ctx,
        demand=demand,
        source_root=source_root,
        project=project,
        execution_policy=execution_policy,
        limit=limit,
        max_rounds=max_rounds,
        json=json,
    )


def execute_request(
    ctx: typer.Context,
    *,
    source_root: Path | None,
    demand: str | None = None,
    request: NativeDemandRequest | None = None,
    source_request=None,
    visual_actor=None,
    required_targets: tuple[str, ...] | None = None,
    deliver: bool = True,
    project: str | None = None,
    action: str = "demands.execute",
    execution_policy: Path | None = None,
    limit: int = 100,
    max_rounds: int = 100,
    predecessor_result: str | None = None,
    json: bool = False,
) -> DemandActionReport:
    """One managed path for source creation, explicit native requests and exact resume."""
    from corpus_structure.cli.execution_context import (
        capture_execution_context,
        configured_route,
        execution_methods,
        read_execution_context,
        recovery_target,
        retain_execution_context,
    )
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.orchestrate.source_reporting import (
        record_native_demand,
        retain_native_demand_result,
    )
    from corpus_structure.semantic.refusal_types import OperationConflict

    if sum(value is not None for value in (demand, request, source_request)) != 1:
        raise typer.BadParameter("select one source request, native request or retained demand")
    settings = state(ctx).settings()
    store = result_store(ctx)
    inherited = None
    expected_target = None
    if predecessor_result is not None:
        inherited = read_execution_context(store, predecessor_result)
        predecessor_manifest = store.show(predecessor_result, role="execution_context")
        expected_target = recovery_target(predecessor_manifest)
        # Current configured credentials are resolved at acquisition. A retained URL
        # never becomes connection authority.
        from corpus_structure.cli.target import configured_selection

        current = configured_selection(ctx, settings, "development")
        if configured_route(current) != configured_route(inherited.configured_target):
            from corpus_structure.cli.managed import ResultError

            raise ResultError("configured recovery route differs from the captured target")
    methods, policy_overrides = execution_methods(settings, execution_policy, inherited=inherited)
    account = capture_execution_context(
        ctx,
        settings=settings,
        methods=methods,
        action=action,
        source_root=source_root,
        demand=demand,
        request=request,
        source_request=source_request,
        project=project,
        policy_overrides=policy_overrides,
        required_targets=required_targets,
        predecessor=predecessor_result,
        inherited=inherited,
        limit=limit,
        max_rounds=max_rounds,
    )
    with managed_operation(
        store,
        action,
        json=json,
        source=("execution_context", predecessor_result)
        if predecessor_result is not None
        else None,
        expected=(OperationConflict, OSError),
        scope={"demand_id": demand, "project": project},
    ) as invocation:
        retain_execution_context(invocation, account)
        if source_root is not None:
            invocation.manifest.details["native_source_root"] = str(source_root.resolve())
        from corpus_structure.cli.managed_stop import stoppable_invocation

        with (
            stoppable_invocation(invocation),
            ENGINE(settings, purpose="write") as engine,
            ENGINE(settings, purpose="admit") as admitted,
        ):
            from corpus_structure.orchestrate.native_execution import execute_native_intent

            def registered(snapshot, target, parsed_request):
                nonlocal demand
                demand = snapshot["demand_id"]
                if inherited is not None:
                    recorded = predecessor_manifest.details.get("observation_bindings", {})
                    selected_request = inherited.source_request or inherited.native_request
                    expected_release = recorded.get("release_id") or getattr(
                        selected_request, "release_id", None
                    )
                    expected_runtime = recorded.get("runtime_id") or getattr(
                        selected_request, "runtime_id", None
                    )
                    if (
                        expected_release is not None and snapshot["release_id"] != expected_release
                    ) or (
                        expected_runtime is not None and snapshot["runtime_id"] != expected_runtime
                    ):
                        raise OperationConflict(
                            "recovered demand differs from captured release or runtime"
                        )
                if parsed_request is not None:
                    path = invocation.directory / "request.json"
                    path.write_bytes(json_bytes(parsed_request.model_dump(mode="python")))
                    invocation.publish("request", path)
                invocation.record_target(target, None, None, snapshot["release_id"])
                record_native_demand(invocation, snapshot, target)

            try:
                result = execute_native_intent(
                    engine,
                    admitted,
                    source_root=source_root,
                    methods=methods,
                    demand=demand,
                    request=request,
                    source_request=source_request,
                    visual_actor=visual_actor,
                    project=project,
                    limit=limit,
                    max_rounds=max_rounds,
                    required_targets=required_targets,
                    registered=registered,
                    completion_draft_root=settings.paths.data_dir / "completion-drafts",
                    analytics_settings=account.analytics_settings,
                    expected_target=expected_target,
                )
            except NativeDemandExecutionError as error:
                retain_native_demand_result(invocation, error.result)
                raise
            native = retain_native_demand_result(invocation, result)
        invocation.settle("passed", demand_id=demand, receipt_count=result.receipt_count)
        report = DemandActionReport.model_validate({"id": invocation.id, "native": native})
    if deliver:
        _emit_demand(report, json=json)
    return report


@app.command("retire-draft")
def retire_draft(
    ctx: typer.Context,
    draft: Annotated[str, typer.Argument(help="Exact acknowledged draft content ID.")],
    project: Annotated[str, typer.Option(help="Exact project owning the draft.")],
    target: Annotated[DeploymentProfile, typer.Option(help="Configured PostgreSQL target.")],
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    json: JsonOpt = False,
) -> None:
    """Retire an exact private draft after native publication and producer retirement."""
    from corpus_structure.cli.characterization_options import method_settings
    from corpus_structure.cli.target import select_target
    from corpus_structure.semantic.completion_drafts import completion_draft_store
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.storage_target import verify_declared_route

    with managed_operation(
        result_store(ctx),
        "demands.retire-draft",
        json=json,
        expected=(ValueError, OSError),
        scope={"draft_id": draft, "project": project, "target": target},
    ) as invocation:
        selected, settings = select_target(ctx, target, effect=True)
        policy = method_settings(settings, execution_policy).execution_policy
        with ENGINE(settings, purpose="write") as engine, engine.begin() as connection:
            if selected == "deployment":
                verify_declared_route(connection, settings)
            binding = acquired_target(connection, purpose="write")
            invocation.record_target(binding, None, None, None)
            store = completion_draft_store(
                settings.paths.data_dir / "completion-drafts", binding, policy.max_reply_bytes
            )
            report = store.retire(
                draft,
                project_id=project,
                inspect=DataOperationStorage(connection).inspect_data_completion_draft,
            )
        if report.state == "retired":
            invocation.record_effect("private completion draft retired")
        native = asdict(report)
        path = invocation.directory / "retirement.json"
        path.write_bytes(json_bytes(native))
        invocation.publish("retirement", path)
        invocation.settle("passed", **native)
        result = DemandActionReport.model_validate({"id": invocation.id, "native": native})
    _emit_demand(result, json=json)


@app.command("plan")
def plan(
    ctx: typer.Context,
    request: Annotated[
        Path, typer.Option(help="Typed native choices to compile and freeze; '-' reads stdin.")
    ],
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
            registered = create_native_demand(connection, parsed)
            invocation.record_target(target, None, None, parsed.release_id)
        with ENGINE(state(ctx).settings(), purpose="read") as engine, engine.begin() as connection:
            native = read_data_demand(connection, registered["demand_id"], limit=1)
        from corpus_structure.orchestrate.source_reporting import record_native_demand

        record_native_demand(invocation, native, target)
        path = invocation.directory / "native.json"
        path.write_bytes(json_bytes(native))
        invocation.publish("native", path)
        invocation.settle("passed", demand_id=native["demand_id"])
        report = DemandActionReport.model_validate({"id": invocation.id, "native": native})
    _emit_demand(report, json=json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="demands")


@app.command("external")
def external(
    ctx: typer.Context,
    action: Annotated[
        Literal[
            "queue",
            "claim",
            "read",
            "renew",
            "submit",
            "inspect",
            "reconcile",
            "located",
            "release",
        ],
        typer.Argument(),
    ],
    request: Annotated[
        Path, typer.Option(help="Exact external action arguments as JSON; '-' reads stdin.")
    ],
    project: Annotated[str | None, typer.Option(help="Native project scope.")] = None,
    demand: Annotated[
        str | None, typer.Option(help="Restrict packet claims to this demand.")
    ] = None,
    json: JsonOpt = False,
) -> None:
    """Operate task-owned external packets without a parallel run/method queue."""
    from corpus_structure.semantic.data_operation_external import ExternalDataSession

    with managed_operation(
        result_store(ctx),
        "demands.external." + action,
        json=json,
        expected=(ValueError, KeyError, OSError, TypeError),
    ) as invocation:
        payload = wire_json_loads(read_request_bytes(request))
        if not isinstance(payload, dict):
            raise ValueError("external action arguments must be a JSON object")
        argument_path = invocation.directory / "request.json"
        argument_path.write_bytes(json_bytes(payload))
        invocation.publish("request", argument_path)
        settings = state(ctx).settings()
        with ENGINE(settings, purpose="write") as engine:
            with engine.begin() as connection:
                invocation.record_target(
                    acquired_target(connection, purpose="write"), None, None, None
                )
            session = ExternalDataSession(
                engine, project or settings.runtime.default_project, demand_id=demand
            )
            operation = {
                "queue": session.queue,
                "claim": session.claim,
                "read": session.read,
                "renew": session.renew,
                "submit": session.submit,
                "inspect": session.inspect,
                "reconcile": session.reconcile,
                "located": session.located,
                "release": session.release,
            }[action]
            native = operation(**payload)
        if action not in {"queue", "read", "inspect", "located"}:
            invocation.record_effect("native external " + action)
        report_path = invocation.directory / "native.json"
        report_path.write_bytes(json_bytes(native))
        invocation.publish("native", report_path)
        invocation.settle("passed", packet_id=native.get("packet_id"))
        report = DemandActionReport.model_validate({"id": invocation.id, "native": native})
    _emit_demand(report, json=json)
