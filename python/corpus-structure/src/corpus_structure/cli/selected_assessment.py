"""Current purpose-restricted reference authorship and selected comparison adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from corpus_structure.cli.managed import managed_operation, result_store
from corpus_structure.cli.output import JsonOpt, read_request_model, state, write_report_text
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.refusals import OperationConflict

reference_app = typer.Typer(
    help="Author independent protected references against exact source selections.",
    no_args_is_help=True,
)
evaluation_app = typer.Typer(
    help="Compare actual selected members against protected independent references.",
    no_args_is_help=True,
)


@reference_app.command("author")
def author(ctx: typer.Context, request: Annotated[Path, typer.Option()], json: JsonOpt = False):
    """Retain a typed independent reference; this does not execute its snapshot target."""
    from corpus_structure.evaluate.selected_references import author_selected_references
    from corpus_structure.semantic.data_operation_service import NativeDemandRequest
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import acquired_target

    with managed_operation(
        result_store(ctx), "golden.author", json=json, expected=(OperationConflict, OSError)
    ) as invocation:
        parsed = read_request_model(request, NativeDemandRequest)
        request_path = invocation.directory / "request.json"
        request_path.write_bytes(json_bytes(parsed.model_dump(mode="python")))
        invocation.publish("request", request_path)
        with open_runtime_engine(
            state(ctx).settings(), "ci-reference-author", purpose="evaluate"
        ) as engine:
            with engine.begin() as connection:
                prepared = open_release(connection, parsed.release_id)
                invocation.record_target(
                    acquired_target(connection, purpose="evaluate"), None, None, prepared.release_id
                )
            report = author_selected_references(engine, prepared, request=parsed)
        invocation.record_effect("authored protected reference:" + report["demand_id"])
        path = invocation.directory / "reference.json"
        path.write_bytes(json_bytes(report))
        invocation.publish("reference", path)
        invocation.settle("passed", demand_id=report["demand_id"])
        result = dict(id=invocation.id, reference=report)
    write_report_text(json_bytes(result).decode() + "\n")


@reference_app.command("snapshot")
def snapshot(
    ctx: typer.Context,
    request: Annotated[Path, typer.Option()],
    source_root: Annotated[Path, typer.Option()],
    json: JsonOpt = False,
):
    """Execute the exact protected reference snapshot; source root supplies captured code locations."""
    from corpus_structure.evaluate.selected_references import author_selected_references
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.orchestrate.source_reporting import (
        record_native_demand,
        retain_native_demand_result,
    )
    from corpus_structure.semantic.data_operation_service import (
        NativeDemandRequest,
        execute_data_demand,
    )
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import acquired_target

    with managed_operation(
        result_store(ctx), "golden.snapshot", json=json, expected=(OperationConflict, OSError)
    ) as invocation:
        parsed = read_request_model(request, NativeDemandRequest)
        request_path = invocation.directory / "request.json"
        request_path.write_bytes(json_bytes(parsed.model_dump(mode="python")))
        invocation.publish("request", request_path)
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-reference-snapshot", purpose="evaluate"
            ) as engine,
            open_runtime_engine(
                state(ctx).settings(), "ci-reference-snapshot-admit", purpose="admit"
            ) as admitted,
        ):
            with engine.begin() as connection:
                prepared = open_release(connection, parsed.release_id)
                target = acquired_target(connection, purpose="evaluate")
            authored = author_selected_references(engine, prepared, request=parsed)
            invocation.record_target(target, None, None, prepared.release_id)
            record_native_demand(invocation, {**authored, "project_id": parsed.project_id}, target)
            try:
                result = execute_data_demand(
                    engine,
                    authored["demand_id"],
                    project_id=parsed.project_id,
                    source_root=source_root,
                    purpose="evaluate",
                    admission_engine=admitted,
                )
            except NativeDemandExecutionError as error:
                retain_native_demand_result(invocation, error.result)
                raise
            native = retain_native_demand_result(invocation, result)
        invocation.settle(
            "passed", demand_id=authored["demand_id"], receipt_count=result.receipt_count
        )
        report = dict(id=invocation.id, native=native)
    write_report_text(json_bytes(report).decode() + "\n")


@evaluation_app.command("run")
def evaluate(ctx: typer.Context, request: Annotated[Path, typer.Option()], json: JsonOpt = False):
    """Retain a comparison report under explicit reference/prediction cuts; no inference."""
    from corpus_structure.evaluate.selected_references import (
        SelectedReferenceEvaluationRequest,
        evaluate_selected_references,
    )
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import acquired_target

    with managed_operation(
        result_store(ctx), "eval.selected", json=json, expected=(OperationConflict, OSError)
    ) as invocation:
        parsed = read_request_model(request, SelectedReferenceEvaluationRequest)
        request_path = invocation.directory / "request.json"
        request_path.write_bytes(json_bytes(parsed.model_dump(mode="python")))
        invocation.publish("request", request_path)
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-selected-reference-compare", purpose="evaluate"
            ) as engine,
            engine.begin() as connection,
        ):
            invocation.record_target(
                acquired_target(connection, purpose="evaluate"), None, None, None
            )
            report = evaluate_selected_references(connection, parsed)
        path = invocation.directory / "comparison.json"
        path.write_bytes(json_bytes(report))
        invocation.publish("comparison", path)
        invocation.settle(
            "passed",
            reference_cut_id=report["reference"]["cut_id"],
            prediction_cut_id=report["prediction"]["cut_id"],
        )
        result = dict(id=invocation.id, comparison=report)
    write_report_text(json_bytes(result).decode() + "\n")


def register(root: typer.Typer):
    root.add_typer(reference_app, name="golden")
    root.add_typer(evaluation_app, name="eval")


@evaluation_app.command("records")
def evaluate_records(
    ctx: typer.Context,
    request: Annotated[Path, typer.Option()],
    source_root: Annotated[Path, typer.Option()],
    json: JsonOpt = False,
):
    """Execute protected complete-record grading or exact held-out policy fitting."""
    from contextlib import nullcontext

    from corpus_structure.evaluate.declared_record_policy import author_record_policy_inputs
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.orchestrate.source_reporting import (
        record_native_demand,
        retain_native_demand_result,
    )
    from corpus_structure.semantic.data_operation_service import (
        NativeDemandRequest,
        execute_data_demand,
    )
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import acquired_target

    with managed_operation(
        result_store(ctx), "eval.records", json=json, expected=(OperationConflict, OSError)
    ) as invocation:
        parsed = read_request_model(request, NativeDemandRequest)
        if parsed.targets not in {
            ("record_policy.grade",),
            ("record_policy.fit",),
            ("record_policy.fit", "record_policy.authorize"),
        }:
            from corpus_structure.semantic.refusals import SemanticRefusal

            raise SemanticRefusal(
                "record evaluation requires exactly its protected grade or fit target"
            )
        request_path = invocation.directory / "request.json"
        request_path.write_bytes(json_bytes(parsed.model_dump(mode="python")))
        invocation.publish("request", request_path)
        settings = state(ctx).settings()
        fitter = (
            open_runtime_engine(settings, "ci-record-feature-fit", purpose="fit")
            if "record_policy.fit" in parsed.targets
            else nullcontext(None)
        )
        with (
            open_runtime_engine(
                settings, "ci-record-policy-evaluator", purpose="evaluate"
            ) as engine,
            open_runtime_engine(settings, "ci-record-policy-admit", purpose="admit") as admission,
            fitter as fitter_engine,
        ):
            with engine.begin() as connection:
                prepared = open_release(connection, parsed.release_id)
                target = acquired_target(connection, purpose="evaluate")
            authored = author_record_policy_inputs(engine, prepared, request=parsed)
            invocation.record_target(target, None, None, prepared.release_id)
            record_native_demand(invocation, {**authored, "project_id": parsed.project_id}, target)
            try:
                result = execute_data_demand(
                    engine,
                    authored["demand_id"],
                    project_id=parsed.project_id,
                    source_root=source_root,
                    purpose="evaluate",
                    admission_engine=admission,
                    fitter_engine=fitter_engine,
                )
            except NativeDemandExecutionError as error:
                retain_native_demand_result(invocation, error.result)
                raise
            native = retain_native_demand_result(invocation, result)
        invocation.settle(
            "passed", demand_id=authored["demand_id"], receipt_count=result.receipt_count
        )
        report = dict(id=invocation.id, native=native)
    write_report_text(json_bytes(report).decode() + "\n")


@evaluation_app.command("fit-features")
def fit_record_features(
    ctx: typer.Context, request: Annotated[Path, typer.Option()], json: JsonOpt = False
):
    """Fit preliminary parameters using only the restricted feature-fit capability."""
    from corpus_structure.evaluate.declared_record_policy import (
        DdoRecordFeatureFitRequest,
        prepare_record_feature_policy,
    )
    from corpus_structure.semantic.runtime import open_runtime_engine

    with managed_operation(
        result_store(ctx),
        "eval.record-feature-fit",
        json=json,
        expected=(OperationConflict, OSError),
    ) as invocation:
        parsed = read_request_model(request, DdoRecordFeatureFitRequest)
        request_path = invocation.directory / "request.json"
        request_path.write_bytes(json_bytes(parsed.model_dump(mode="json")))
        invocation.publish("request", request_path)
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-record-preliminary-fit", purpose="fit"
            ) as engine,
            engine.begin() as connection,
        ):
            report = prepare_record_feature_policy(connection, parsed)
        path = invocation.directory / "feature-fit.json"
        path.write_bytes(json_bytes(report))
        invocation.publish("feature-fit", path)
        invocation.settle("passed", standing=report["fit"]["diagnostics"]["standing"])
        result = dict(id=invocation.id, feature_fit=report)
    write_report_text(json_bytes(result).decode() + "\n")
