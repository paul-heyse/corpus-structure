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

from corpus_structure.cli.observations import Bindings, ObservationPage, ObservationSelection


class NextAction(BaseModel):
    kind: Literal["watch", "inspect", "resume_run", "recover_result", "native_status"]
    command: str
    owner: Literal["managed_result", "semantic_run"]


class NativeInspection(BaseModel):
    availability: Literal["available", "unavailable"] = "unavailable"
    reason: str | None = None
    assurance: Literal["native"] = "native"
    run: dict[str, Any] | None = None
    task: dict[str, Any] | None = None
    receipt_observations: tuple[int, ...] | None = None
    counts: dict[str, int] | None = None
    denominator: int | None = None
    detail_omissions: tuple[str, ...] = ()


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
    next_actions: tuple[NextAction, ...] = ()
    correlation: Literal["recorded_bindings_only"] = "recorded_bindings_only"
    timeline_ordering: Literal[
        "parent_journal_sequence; timestamps do not establish cross-process causality"
    ] = "parent_journal_sequence; timestamps do not establish cross-process causality"
    provider_receipts: tuple[str, ...] = ()
    provider_receipts_omitted: int = 0


def native_inspection(
    ctx: typer.Context, manifest: Any, selection: ObservationSelection, page: ObservationPage
) -> NativeInspection:
    """Join only an exact recorded run on the same acquired storage target, with reader purpose."""
    from psycopg import Error as PsycopgError
    from sqlalchemy import select
    from sqlalchemy.exc import SQLAlchemyError

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.output import state
    from corpus_structure.orchestrate import commands
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.storage_target import StorageTarget, verify_target

    bindings = manifest.details.get("observation_bindings", {})
    run_id = bindings.get("run_id")
    target = manifest.details.get("observation_target")
    if run_id is None:
        return NativeInspection(reason="No native run binding was acquired by this invocation.")
    if target is None:
        return NativeInspection(
            reason="The native storage binding is unavailable; no lookup was inferred."
        )
    try:
        expected = StorageTarget.model_validate(target)
        with orchestrate.READ_ENGINE(state(ctx).settings()) as engine, engine.connect() as conn:
            verify_target(conn, expected, purpose="read")
            progress = commands.bound_status(conn, run_id)
            run = progress.run
            if run is None:
                return NativeInspection(reason="The exact native run is unavailable.")
            counts: dict[str, int] = {}
            for group in run.stages:
                counts[group.status] = counts.get(group.status, 0) + group.count
            task_value = None
            receipt_observations = None
            if selection.task is not None:
                tasks = table("ops.task")
                task = (
                    conn.execute(
                        select(
                            tasks.c.id,
                            tasks.c.run_id,
                            tasks.c.stage,
                            tasks.c.status,
                            tasks.c.attempt,
                        ).where(tasks.c.id == selection.task, tasks.c.run_id == run_id)
                    )
                    .mappings()
                    .one_or_none()
                )
                if task is not None:
                    task_value = dict(task)
                    task_value["selected_attempt_standing"] = (
                        "current"
                        if selection.attempt is None or selection.attempt == task["attempt"]
                        else "historical; current native task does not establish its receipt"
                    )
                # Native observation IDs are checked through the native reader; reported IDs
                # remain provider evidence until this independent join succeeds.
                ids: set[int] = set()
                for row in page.rows:
                    receipt = row.fields.get("receipt")
                    if row.bindings.task_id == selection.task and isinstance(receipt, dict):
                        reported_ids = receipt.get("observation_ids", [])
                        if isinstance(reported_ids, list):
                            ids.update(value for value in reported_ids if type(value) is int)
                if ids:
                    observations = table("kb.observation")
                    receipt_observations = tuple(
                        conn.execute(
                            select(observations.c.id)
                            .where(
                                observations.c.task_id == selection.task,
                                observations.c.id.in_(sorted(ids)[:32]),
                            )
                            .order_by(observations.c.id)
                        ).scalars()
                    )
            return NativeInspection(
                availability="available",
                run=run.model_dump(
                    mode="json",
                    include={
                        "run_id",
                        "kind",
                        "status",
                        "release_id",
                        "output_realization_id",
                        "readiness",
                        "supervisor",
                        "unresolved_agent_tasks",
                    },
                ),
                task=task_value,
                receipt_observations=receipt_observations,
                counts=counts,
                denominator=sum(counts.values()),
                detail_omissions=(
                    "run.stages: selected aggregate counts",
                    "run.pm2_scope_coverage: inspect native status for detail",
                ),
            )
    except (
        SQLAlchemyError,
        PsycopgError,
        SemanticRefusal,
        commands.CommandError,
        ValueError,
    ) as error:
        return NativeInspection(reason="Native reader unavailable: " + type(error).__name__)


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
        native = native_inspection(ctx, manifest, selection, page)
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
        if bindings.run_id is not None:
            actions.append(
                NextAction(
                    kind="native_status",
                    command=f"ci status {bindings.run_id}",
                    owner="semantic_run",
                )
            )
            if (
                native.availability == "available"
                and native.run is not None
                and native.run.get("readiness") == "source_ready"
                and bindings.project is not None
            ):
                command = shlex.join(
                    ["ci", "run", "resume", str(bindings.run_id), "--project", bindings.project]
                )
                actions.append(NextAction(kind="resume_run", command=command, owner="semantic_run"))
        if manifest.action in {"test", "test.retry"} and not manifest.custody_settled():
            actions.append(
                NextAction(
                    kind="recover_result",
                    command=f"ci results recover {result}",
                    owner="managed_result",
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
            next_actions=tuple(actions),
            provider_receipts=receipts,
            provider_receipts_omitted=len(all_receipts) - len(receipts),
        )
        # Bound the complete joined envelope, including zero-row filtered pages. Detail
        # omission never changes recorded operation outcome or claims unknown counts are zero.
        if len(report.model_dump_json().encode()) > selection.max_bytes:
            report.provider_receipts_omitted += len(report.provider_receipts)
            report.provider_receipts = ()
            if report.native.run is not None:
                retained = {
                    key: value
                    for key, value in report.native.run.items()
                    if key in {"run_id", "status", "readiness", "supervisor"}
                }
                report.native = report.native.model_copy(
                    update={
                        "run": retained,
                        "counts": None,
                        "detail_omissions": (
                            *report.native.detail_omissions,
                            "native detail: response byte limit",
                        ),
                    }
                )
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
    if report.native.availability == "available":
        parts.append(
            Text(
                f"Native task counts: {report.native.counts}; "
                f"denominator {report.native.denominator}"
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
    parts.extend(Text(action.command) for action in report.next_actions)
    return Group(*parts)
