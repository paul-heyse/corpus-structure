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
    kind: Literal["watch", "inspect", "resume_demand", "recover_result", "native_status"]
    command: str
    owner: Literal["managed_result", "native_demand"]


class NativeInspection(BaseModel):
    availability: Literal["available", "unavailable"] = "unavailable"
    reason: str | None = None
    assurance: Literal["native"] = "native"
    demand: dict[str, Any] | None = None
    execution_receipts: tuple[dict[str, Any], ...] = ()
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
    ctx: typer.Context, manifest: Any, selection: ObservationSelection
) -> NativeInspection:
    """Join an exact recorded demand on its acquired storage target, with reader purpose."""
    from psycopg import Error as PsycopgError
    from sqlalchemy.exc import SQLAlchemyError

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.output import state
    from corpus_structure.semantic.refusals import SemanticRefusal
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
    try:
        from corpus_structure.semantic.demand_results import selected_read_snapshot

        expected = StorageTarget.model_validate(target)
        with (
            orchestrate.READ_ENGINE(state(ctx).settings()) as engine,
            selected_read_snapshot(engine) as conn,
        ):
            verify_target(conn, expected, purpose="read")
            from corpus_structure.semantic.data_operation_service import read_data_demand

            snapshot = read_data_demand(conn, demand_id, limit=min(selection.limit, 16))
            for recorded, native in (
                ("project", "project_id"),
                ("release_id", "release_id"),
                ("runtime_id", "runtime_id"),
            ):
                if (
                    bindings.get(recorded) is not None
                    and bindings[recorded] != snapshot[native]
                ):
                    return NativeInspection(
                        reason="Recorded demand custody differs from the native demand."
                    )
            return NativeInspection(
                availability="available",
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
        native = native_inspection(ctx, manifest, selection)
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
        if bindings.demand_id is not None:
            actions.append(
                NextAction(
                    kind="native_status",
                    command=shlex.join(["ci", "demands", "read", bindings.demand_id]),
                    owner="native_demand",
                )
            )
            source_root = manifest.details.get("native_source_root")
            if isinstance(source_root, str):
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
                    )
                )
            if "native" in manifest.artifacts:
                from corpus_structure.semantic.data_operation_json import wire_json_loads

                retained = wire_json_loads(store.read_artifact(result, "native"))
                if retained.get("demand_id") == bindings.demand_id:
                    native.execution_receipts = tuple(retained.get("receipts", ()))
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
    parts.extend(Text(action.command) for action in report.next_actions)
    return Group(*parts)
