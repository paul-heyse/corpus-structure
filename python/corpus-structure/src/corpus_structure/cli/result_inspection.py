"""One selection for retained result inspection, replay, and useful headless progress."""

from __future__ import annotations

import shlex
from contextlib import ExitStack
from typing import Any, Literal

import typer
from pydantic import BaseModel
from rich.console import Group
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.observations import (
    Bindings,
    Observation,
    ObservationPage,
    ObservationSelection,
)
from corpus_structure.cli.operation_observation import (
    OperationalObservation,
    operational_observation,
)
from corpus_structure.semantic._data_operation_wire import WireReadDemandResultRequest
from corpus_structure.semantic.code_reuse import ReuseExplanationReport
from corpus_structure.semantic.data_operation_storage import NativeKernelObservation
from corpus_structure.semantic.demand_queries import DemandQueryRequest
from corpus_structure.semantic.storage_target import StorageTarget


class NextAction(BaseModel):
    kind: Literal[
        "watch",
        "inspect",
        "resume_demand",
        "resume_result",
        "recover_result",
        "replay_native_read",
        "query",
        "successor_admission",
        "resume_deployment",
    ]
    command: str | None = None
    owner: Literal["managed_result", "native_demand", "model_deployment"]
    result_id: str | None = None
    demand_id: str | None = None
    required_inputs: tuple[str, ...] = ()
    target_profile: str | None = None
    standing: Literal["recorded", "conditional", "observed"] = "recorded"
    reason: str | None = None
    expected_target: StorageTarget | None = None
    query: DemandQueryRequest | None = None
    retained_read: WireReadDemandResultRequest | None = None
    read_scope: Literal["fresh_current", "retained_frontier"] | None = None


class NativeInspection(BaseModel):
    availability: Literal["available", "unavailable"] = "unavailable"
    reason: str | None = None
    assurance: Literal["native"] = "native"
    demand: dict[str, Any] | None = None
    execution_receipts: tuple[dict[str, Any], ...] = ()
    detail_omissions: tuple[str, ...] = ()
    observed_at: str | None = None
    configured_selection: dict[str, Any] | None = None
    expected_target: dict[str, Any] | None = None
    kernel: NativeKernelObservation | None = None
    retained_read: WireReadDemandResultRequest | None = None


class DeploymentObservation(BaseModel):
    """Recorded deployment effects retain their owner and target across interruption."""

    standing: Literal["retained"] = "retained"
    candidate_id: str
    settled_effects: tuple[str, ...] | None
    acquired_target: StorageTarget | None = None
    predecessor: str | None = None
    reached_revision: str | None = None
    release_id: str | None = None


class ResultInspection(BaseModel):
    version: Literal[1] = 1
    id: str
    view: Literal["summary", "observations", "timeline"] = "summary"
    action: str
    outcome: str
    stage: str
    custody: Literal["settled", "unsettled"]
    cleanup: str
    bindings: Bindings
    native: NativeInspection
    observations: ObservationPage
    activity: OperationalObservation | None = None
    execution_context: dict[str, Any] | None = None
    recovery_unavailable_reason: str | None = None
    reuse_explanation: ReuseExplanationReport | None = None
    preparation_refusal: Observation | None = None
    recovery_observation: Observation | None = None
    deployment: DeploymentObservation | None = None
    owner_observations_omitted: bool = False
    next_actions: tuple[NextAction, ...] = ()
    correlation: Literal["recorded_bindings_only"] = "recorded_bindings_only"
    timeline_ordering: Literal[
        "parent_journal_sequence; timestamps do not establish cross-process causality"
    ] = "parent_journal_sequence; timestamps do not establish cross-process causality"
    provider_receipts: tuple[str, ...] = ()
    provider_receipts_omitted: int = 0


def _kernel_observation(connection, release_id):
    """Observe archived kernel correspondence without admitting the archived release."""
    from sqlalchemy.exc import SQLAlchemyError

    from corpus_structure.semantic.data_operation_storage import observe_native_kernel
    from corpus_structure.semantic.refusal_types import SemanticRefusal
    from corpus_structure.semantic.releases import open_release

    with connection.begin_nested() as observation:
        try:
            return observe_native_kernel(connection, open_release(connection, release_id))
        except SQLAlchemyError, SemanticRefusal, ValueError:
            observation.rollback()
    return None


def native_inspection(
    ctx: typer.Context, manifest: Any, selection: ObservationSelection
) -> NativeInspection:
    """Join an exact recorded demand on its acquired storage target, with reader purpose."""
    from psycopg import Error as PsycopgError
    from sqlalchemy.exc import SQLAlchemyError

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.output import state
    from corpus_structure.semantic.refusal_types import SemanticRefusal
    from corpus_structure.semantic.storage_target import StorageTarget, verify_target

    bindings = manifest.details.get("observation_bindings", {})
    target = manifest.details.get("observation_target")
    demand_id = bindings.get("demand_id")
    if demand_id is None:
        return NativeInspection(reason="No native demand binding was acquired.")
    if target is None:
        return NativeInspection(
            reason="The native storage binding is unavailable; no lookup was inferred."
        )
    from datetime import UTC, datetime

    from corpus_structure.cli.target import configured_selection

    configured = configured_selection(ctx, state(ctx).settings(), "development").model_dump(
        mode="json"
    )
    observed_at = datetime.now(UTC).isoformat()
    kernel = None
    try:
        from corpus_structure.semantic.demand_results import selected_read_snapshot

        expected = StorageTarget.model_validate(target)
        with (
            orchestrate.READ_ENGINE(state(ctx).settings()) as engine,
            selected_read_snapshot(engine) as conn,
        ):
            verify_target(conn, expected, purpose="read")
            if bindings.get("release_id") is not None:
                kernel = _kernel_observation(conn, bindings["release_id"])
            from corpus_structure.semantic.data_operation_service import read_data_demand

            limit = min(selection.limit, 16)
            snapshot = read_data_demand(
                conn, demand_id, limit=limit, max_bytes=selection.max_bytes, view="frontier"
            )
            for recorded, native in (
                ("project", "project_id"),
                ("release_id", "release_id"),
                ("runtime_id", "runtime_id"),
            ):
                if bindings.get(recorded) is not None and bindings[recorded] != snapshot[native]:
                    return NativeInspection(
                        reason="Recorded demand custody differs from the native demand."
                    )
            if kernel is None:
                kernel = _kernel_observation(conn, snapshot["release_id"])
            return NativeInspection(
                availability="available",
                observed_at=observed_at,
                configured_selection=configured,
                expected_target=target,
                kernel=kernel,
                retained_read={
                    "demand_id": snapshot["demand_id"],
                    "read_id": snapshot["read_id"],
                    "scope": snapshot["scope"],
                    "view": "frontier",
                    "limit": limit,
                    "max_bytes": selection.max_bytes,
                },
                demand={
                    key: snapshot[key]
                    for key in (
                        "demand_id",
                        "project_id",
                        "release_id",
                        "runtime_id",
                        "state",
                        "read_id",
                        "read_snapshot",
                        "frontier_at",
                        "trust_snapshot",
                        "obligations",
                        "uses",
                        "continuation",
                    )
                    if key in snapshot
                },
                detail_omissions=(
                    "demand: bounded native frontier page; counts are not a whole-demand denominator",
                ),
            )
    except (
        SQLAlchemyError,
        PsycopgError,
        SemanticRefusal,
        ValueError,
    ) as error:
        return NativeInspection(
            reason="Native reader unavailable: " + type(error).__name__,
            observed_at=observed_at,
            configured_selection=configured,
            expected_target=target,
            kernel=kernel,
        )


def inspect_result(
    ctx: typer.Context,
    store: Any,
    result: str,
    selection: ObservationSelection,
    *,
    after: str | None = None,
    view: Literal["summary", "observations", "timeline"] = "summary",
    page: ObservationPage | None = None,
) -> ResultInspection:
    from corpus_structure.cli.managed import ResultError

    with store.lease(result), ExitStack() as reading:
        reader = None
        manifest = store.show(result, role="observations")
        if page is None:
            if manifest.observations is None or "observations" not in manifest.artifacts:
                page = ObservationPage(
                    result=result,
                    availability="unavailable",
                    standing="unavailable",
                    coverage="unavailable",
                    unavailable_reason="No observations were retained for this invocation.",
                )
            else:
                reader = reading.enter_context(store.open_observations(result))
                page = reader.read(
                    selection,
                    after=after,
                    running=manifest.settled is None,
                    journal=manifest.observations,
                )
        try:
            bindings = Bindings.model_validate(
                {"invocation_id": result, **manifest.details.get("observation_bindings", {})}
            )
        except ValueError as error:
            raise ResultError("recorded observation bindings are invalid") from error
        native = native_inspection(ctx, manifest, selection)
        captured = None
        unavailable_reason = None
        has_context = "execution_context" in manifest.artifacts
        if has_context and manifest.settled is not None:
            from .execution_context import read_execution_context

            account = read_execution_context(store, result)
            captured = account.model_dump(mode="json", exclude={"native_request", "source_request"})
            captured["selection"] = (
                "demand"
                if account.demand_id is not None
                else "source_request"
                if account.source_request is not None
                else "native_request"
            )
        elif has_context:
            unavailable_reason = (
                "Captured recovery inputs become available when this invocation settles."
            )
        elif manifest.action in {"run", "run.resume", "ingest", "demands.execute"}:
            unavailable_reason = "No execution context was captured; exact source root and execution policy are required for direct demand recovery."
        actions = [
            NextAction(
                kind="inspect",
                command=f"ci results inspect {result} --view observations",
                owner="managed_result",
            )
        ]
        if manifest.settled is None:
            actions.append(
                NextAction(
                    kind="watch", command=f"ci results watch {result}", owner="managed_result"
                )
            )
        if (
            captured is not None
            and native.kernel is not None
            and native.kernel.standing == "mismatch"
        ):
            actions.append(
                NextAction(
                    kind="successor_admission",
                    owner="native_demand",
                    result_id=result,
                    demand_id=bindings.demand_id,
                    standing="observed",
                    required_inputs=("reviewed_successor_release", "current_execution_admission"),
                    reason=(
                        "The captured release's kernel differs from the current descriptor. "
                        "Prepare and admit a reviewed successor before attempting compatible recovery."
                    ),
                )
            )
        elif captured is not None:
            actions.append(
                NextAction(
                    kind="resume_result",
                    command=shlex.join(["ci", "run", "resume", "--result", result]),
                    owner="managed_result",
                    result_id=result,
                    demand_id=bindings.demand_id,
                    required_inputs=() if captured.get("source_root") else ("source_root",),
                    target_profile=captured["configured_target"]["profile"],
                    standing="conditional",
                    reason=(
                        "The recorded release/runtime and policy will be resumed. Current "
                        "execution admission, support, claim and retained-file custody must "
                        "be acquired before recorded work can be used."
                    ),
                    expected_target=StorageTarget.model_validate(native.expected_target)
                    if native.expected_target is not None
                    else None,
                )
            )
        if bindings.demand_id is not None:
            source_root = manifest.details.get("native_source_root")
            if isinstance(source_root, str) and not has_context:
                actions.append(
                    NextAction(
                        kind="resume_demand",
                        command=shlex.join(
                            [
                                "ci",
                                "demands",
                                "execute",
                                bindings.demand_id,
                                "--source-root",
                                source_root,
                            ]
                        ),
                        owner="native_demand",
                        demand_id=bindings.demand_id,
                        required_inputs=("execution_policy",),
                        standing="conditional",
                        reason="Current execution admission, support and recovery custody require observation.",
                    )
                )
            if manifest.settled is not None and "native" in manifest.artifacts:
                from corpus_structure.semantic.data_operation_json import wire_json_loads

                retained = wire_json_loads(store.read_artifact(result, "native"))
                if retained.get("demand_id") == bindings.demand_id:
                    native.execution_receipts = tuple(retained.get("receipts", ()))
        if (
            native.availability == "available"
            and native.demand is not None
            and native.expected_target is not None
            and native.demand.get("project_id") is not None
        ):
            query = DemandQueryRequest(
                demand_id=native.demand["demand_id"],
                project_id=native.demand["project_id"],
                view="operations",
                limit=min(selection.limit, 16),
                max_bytes=selection.max_bytes,
            )
            target = StorageTarget.model_validate(native.expected_target)
            if native.retained_read is not None:
                from corpus_structure.semantic.data_operation_json import finite_json_bytes

                actions.append(
                    NextAction(
                        kind="replay_native_read",
                        command=shlex.join(
                            [
                                "ci",
                                "demands",
                                "read",
                                query.demand_id,
                                "--project",
                                query.project_id,
                                "--continuation-json",
                                finite_json_bytes(native.retained_read).decode(),
                                "--expected-target",
                                target.model_dump_json(),
                                "--json",
                            ]
                        ),
                        owner="native_demand",
                        demand_id=query.demand_id,
                        standing="conditional",
                        reason="Reopen the recorded frontier on the recorded target with current disclosure authority.",
                        expected_target=target,
                        retained_read=native.retained_read,
                        read_scope="retained_frontier",
                    )
                )
            actions.append(
                NextAction(
                    kind="query",
                    command=shlex.join(
                        [
                            "ci",
                            "query",
                            query.view,
                            "--demand",
                            query.demand_id,
                            "--project",
                            query.project_id,
                            "--limit",
                            str(query.limit),
                            "--max-bytes",
                            str(query.max_bytes),
                            "--expected-target",
                            target.model_dump_json(),
                            "--json",
                        ]
                    ),
                    owner="native_demand",
                    demand_id=query.demand_id,
                    standing="conditional",
                    reason="Acquire a fresh current read on the recorded target with current disclosure authority.",
                    expected_target=target,
                    query=query,
                    read_scope="fresh_current",
                )
            )
        if manifest.action in {"test", "test.retry"} and not manifest.custody_settled():
            actions.append(
                NextAction(
                    kind="recover_result",
                    command=f"ci results recover {result}",
                    owner="managed_result",
                )
            )
        deployment = None
        candidate = manifest.scope.get("candidate")
        account = manifest.operation_account
        if manifest.action == "model.deploy" and isinstance(candidate, str) and account is not None:
            deployment = DeploymentObservation(
                candidate_id=candidate,
                settled_effects=account.known_effects,
                acquired_target=account.acquired_target,
                predecessor=account.predecessor,
                reached_revision=account.reached_revision,
                release_id=account.release,
            )
            if manifest.outcome != "passed":
                actions.append(
                    NextAction(
                        kind="resume_deployment",
                        owner="model_deployment",
                        command=shlex.join(["ci", "model", "change", "deploy", candidate]),
                        result_id=result,
                        standing="conditional",
                        expected_target=account.acquired_target,
                        reason=(
                            "Reconcile this candidate's recorded effects on its exact target. "
                            "The deployment owner checks current migration, archive and admission standing."
                        ),
                    )
                )
        receipts = tuple(
            dict.fromkeys(
                row.fields["provider_receipt"]
                for row in page.rows
                if isinstance(row.fields.get("provider_receipt"), str)
            )
        )
        all_receipts = receipts
        receipts = tuple(
            path
            for index, path in enumerate(all_receipts)
            if index < 16 and sum(len(item.encode()) for item in all_receipts[: index + 1]) <= 4096
        )
        reuse = None
        if "reuse_explanation" in manifest.artifacts:
            reuse = ReuseExplanationReport.model_validate_json(
                store.read_artifact(result, "reuse_explanation")
            )
        report = ResultInspection(
            id=result,
            view=view,
            action=manifest.action,
            outcome=manifest.outcome,
            stage=manifest.stage,
            custody="settled" if manifest.custody_settled() else "unsettled",
            cleanup=manifest.operation_account.cleanup
            if manifest.operation_account is not None
            else "established"
            if manifest.custody_settled()
            else "unknown",
            bindings=bindings,
            native=native,
            observations=page,
            activity=operational_observation(page, native, running=manifest.settled is None),
            execution_context=captured,
            recovery_unavailable_reason=unavailable_reason,
            reuse_explanation=reuse,
            preparation_refusal=next(
                (
                    row
                    for row in page.rows
                    if row.message == "native_demand.prepared_acquisition_refused"
                ),
                None,
            ),
            recovery_observation=next(
                (
                    row
                    for row in reversed(page.rows)
                    if row.message == "native_demand.recovery_selected"
                ),
                None,
            ),
            deployment=deployment,
            next_actions=tuple(actions),
            provider_receipts=receipts,
            provider_receipts_omitted=len(all_receipts) - len(receipts),
        )
        # Bound the complete joined envelope, including zero-row filtered pages. Detail
        # omission never changes recorded operation outcome or claims unknown counts are zero.
        if (
            len(report.model_dump_json().encode()) > selection.max_bytes
            and report.native.demand is not None
        ):
            report.native = report.native.model_copy(
                update={
                    "demand": {
                        key: value
                        for key, value in report.native.demand.items()
                        if key
                        in {
                            "demand_id",
                            "project_id",
                            "release_id",
                            "runtime_id",
                            "state",
                            "read_id",
                            "read_snapshot",
                            "frontier_at",
                        }
                    },
                    "execution_receipts": (),
                    "detail_omissions": (
                        *report.native.detail_omissions,
                        "demand frontier, continuation and physical receipts: response byte limit; inspect ci demands read and retained native artifact",
                    ),
                }
            )
        if len(report.model_dump_json().encode()) > selection.max_bytes:
            report.owner_observations_omitted = (
                report.preparation_refusal is not None or report.recovery_observation is not None
            )
            report.preparation_refusal = None
            report.recovery_observation = None
            report.provider_receipts_omitted += len(report.provider_receipts)
            report.provider_receipts = ()
        while (
            len(report.model_dump_json().encode()) > selection.max_bytes
            and report.observations.rows
        ):
            keep = len(report.observations.rows) - 1
            if reader is not None:
                report.observations = reader.withhold_rows(report.observations, keep)
            else:
                report.observations = report.observations.model_copy(
                    update={
                        "rows": report.observations.rows[1:],
                        "selected_count": keep,
                        "response_omitted": report.observations.response_omitted + 1,
                        "window_budget_evicted": report.observations.window_budget_evicted
                        + (1 if report.observations.selection_kind == "latest_window" else 0),
                        "returned_sequence_range": (
                            report.observations.rows[1].sequence,
                            report.observations.rows[-1].sequence,
                        )
                        if keep
                        else None,
                    }
                )
        if len(report.model_dump_json().encode()) > selection.max_bytes:
            raise ResultError("inspection identity/outcome envelope exceeds response byte budget")
        return report


def render_inspection(report: ResultInspection) -> Group:
    parts: list[Any] = [
        Text(f"Result {report.id} · {report.outcome} · {report.stage} · custody {report.custody}"),
        Text(
            f"Observations: {report.observations.standing}; "
            f"coverage {report.observations.coverage}; "
            f"collection minimum {report.observations.collection_threshold}"
        ),
    ]
    if report.reuse_explanation is not None:
        from .reuse_explanation import render_reuse_explanation

        parts.append(render_reuse_explanation(report.reuse_explanation))
    if report.activity is not None:
        phases = Table("Phase", "Standing", "Observed", "Source")
        for phase in report.activity.phases:
            phases.add_row(
                phase.phase,
                phase.standing,
                phase.observed_at or "unavailable",
                phase.source or "unavailable",
            )
        parts.append(phases)
    if report.execution_context is not None:
        parts.append(
            Text("Execution policy and source custody captured for exact managed recovery.")
        )
    elif report.recovery_unavailable_reason:
        parts.append(Text(report.recovery_unavailable_reason))
    if report.native.demand is not None:
        parts.append(
            Text(
                f"Native demand {report.native.demand['demand_id']}: {report.native.demand.get('state', 'unknown')}; bounded frontier, no inferred task denominator"
            )
        )
    else:
        parts.append(Text(report.native.reason or "Native evidence unavailable"))
    if report.view != "summary":
        table = Table("seq", "severity", "stage", "message", "binding / assurance", expand=True)
        for row in report.observations.rows:
            binding = row.bindings.model_dump(exclude_none=True)
            table.add_row(
                str(row.sequence),
                row.severity,
                Text(row.stage or ""),
                Text(row.message),
                Text(f"{binding} / {row.assurance}"),
            )
            if row.exception is not None:
                from corpus_structure.cli.correction_rendering import render_exception

                parts.append(
                    render_exception(
                        row.exception, invocation=row.bindings.invocation_id, stage=row.stage
                    )
                )
        parts.insert(2, table)
    if report.observations.selection_kind == "latest_window":
        parts.append(
            Text(
                f"Latest window: limit {report.observations.window_limit}; "
                f"returned sequences {report.observations.returned_sequence_range}; "
                f"older window evictions {report.observations.window_evicted}; "
                f"byte-budget evictions {report.observations.window_budget_evicted}. "
                "Cursor and byte extents describe scan progress; "
                "read earlier events with ordinary results inspect."
            )
        )
    if report.observations.continuation:
        parts.append(Text(f"Continue observations with --after {report.observations.next_after}"))
    if report.observations.collection_omitted:
        parts.append(Text(f"Collection omitted {report.observations.collection_omitted} events."))
    for observation in (report.preparation_refusal, report.recovery_observation):
        if observation is not None:
            parts.append(
                Text(f"{observation.message} · retained observation at {observation.timestamp}")
            )
            parts.append(Text(str(observation.fields)))
    if report.deployment is not None:
        parts.append(
            Text(
                f"Candidate {report.deployment.candidate_id} · retained settled effects: "
                + (
                    "unavailable"
                    if report.deployment.settled_effects is None
                    else ", ".join(report.deployment.settled_effects) or "none recorded"
                )
            )
        )
    if report.owner_observations_omitted:
        parts.append(Text("Owner observation detail omitted by response byte limit."))
    for action in report.next_actions:
        if action.command is not None:
            parts.append(Text(action.command))
        if action.reason:
            parts.append(Text(f"{action.standing}: {action.reason}"))
    return Group(*parts)
