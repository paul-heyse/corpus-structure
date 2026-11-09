"""Minimal native independent-reference grading; completed knowledge output is separate."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer

from corpus_structure.cli.golden import output, reference_protocol, reference_session
from corpus_structure.cli.output import JsonOpt, emit, report_fields
from corpus_structure.semantic.operation_policy import DEFAULT_OPERATION_EVENT, OperationEvent

eval_app = typer.Typer(
    help="Grade completed knowledge against independent semantic references.", no_args_is_help=True
)


@eval_app.command("run")
def evaluate(
    ctx: typer.Context,
    run: Annotated[int, typer.Option()],
    set_id: Annotated[int, typer.Option()],
    project: str | None = None,
    json: JsonOpt = False,
    comparison_arm: Annotated[
        Literal["baseline", "revised"] | None,
        typer.Option(help="Grade the selected frozen operation comparison arm."),
    ] = None,
):
    """Grade a completed run against the exact adjudicated reference snapshot."""
    from corpus_structure.evaluate import operation_assessment, record_references, semantic

    with reference_session(ctx, project, json=json) as (conn, pid):
        protocol = reference_protocol(conn, set_id, pid)
        if protocol == operation_assessment.PROTOCOL:
            result = operation_assessment.reference_evaluate(
                conn, project_id=pid, run_id=run, set_id=set_id, comparison_arm=comparison_arm
            )
        else:
            if comparison_arm is not None:
                raise semantic.ReferenceError("comparison arms require operation references")
            evaluator = (
                record_references.reference_evaluate
                if protocol == record_references.PROTOCOL
                else semantic.reference_evaluate
            )
            result = evaluator(conn, project_id=pid, run_id=run, set_id=set_id)
    output(result, json)


@eval_app.command("record-policy-fit")
def record_policy_fit(
    ctx: typer.Context,
    run: Annotated[int, typer.Option()],
    set_id: Annotated[int, typer.Option()],
    family: Annotated[
        Literal["definition", "assertion", "measurement", "table", "formula_context"],
        typer.Option(),
    ],
    subset: Annotated[str, typer.Option()],
    assumptions: Annotated[str, typer.Option()],
    feature_evaluation: Annotated[
        int | None,
        typer.Option(help="Frozen feature-fit evaluation; selects held-out calibration."),
    ] = None,
    minimum_origin_groups: Annotated[int, typer.Option(min=1)] = 2,
    threshold: Annotated[float, typer.Option(min=0, max=1)] = 0.99,
    out: Annotated[
        Path | None, typer.Option(help="Write finite runtime parameters to a new JSON file.")
    ] = None,
    project: str | None = None,
    json: JsonOpt = False,
):
    """Fit protected whole-reading features or calibrate their complete held-out events."""
    import json as jsonlib

    from sqlalchemy import select

    from corpus_structure.evaluate.record_policy import fit_record_policy
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.record_policy import RecordAlgorithm

    if out is not None and out.exists():
        raise typer.BadParameter("runtime parameter output already exists")
    with reference_session(ctx, project, json=json) as (conn, pid):
        fitted = fit_record_policy(
            conn,
            project_id=pid,
            run_id=run,
            set_id=set_id,
            family=family,
            subset=subset,
            assumptions=assumptions,
            algorithm=(
                None
                if feature_evaluation is not None
                else RecordAlgorithm(minimum_origin_groups=minimum_origin_groups)
            ),
            feature_evaluation_id=feature_evaluation,
            threshold=threshold,
        )
        parameters = None
        report = fitted.report
        if report is not None:
            product = report.result["policy_fit"]
            parameters = {
                "feature_instances": [product["feature_instance"]],
                "record_acceptance": [],
            }
            if product.get("acceptance_instance") is not None:
                evaluations = table("eval.reference_evaluation")
                digest = conn.execute(
                    select(evaluations.c.content_digest).where(evaluations.c.id == report.id)
                ).scalar_one()
                parameters["record_acceptance"] = [
                    dict(
                        instance=product["acceptance_instance"],
                        instance_digest=product["instance_digest"],
                        instance_canonical_json=product["instance_canonical_json"],
                        evaluation_id=report.id,
                        evaluation_digest=digest,
                    )
                ]
        result = dict(
            diagnostics=dict(fitted.diagnostics),
            evaluation_id=report.id if report else None,
            runtime_policy=parameters,
        )
    if out is not None and parameters is not None:
        with out.open("x") as stream:
            stream.write(
                jsonlib.dumps(parameters, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            )
    output(result, json)


@eval_app.command("gaps")
def record_gaps(
    ctx: typer.Context,
    evaluation: Annotated[int, typer.Option()],
    project: str | None = None,
    json: JsonOpt = False,
):
    """Inspect protected source-grounded gaps and exact invocation/replay evidence."""
    from corpus_structure.evaluate.record_gaps import inspect_gaps, read_evaluation

    with reference_session(ctx, project, json=json) as (conn, pid):
        result = inspect_gaps(read_evaluation(conn, project_id=pid, evaluation_id=evaluation))
    output(result, json)


@eval_app.command("compare")
def compare_record_evaluations(
    ctx: typer.Context,
    baseline: Annotated[int, typer.Option()],
    revised: Annotated[int, typer.Option()],
    project: str | None = None,
    json: JsonOpt = False,
):
    """Compare immutable grades on one cohort; run separately for gap and regression sets."""
    from corpus_structure.evaluate.record_gaps import compare_evaluations, read_evaluation

    with reference_session(ctx, project, json=json) as (conn, pid):
        result = compare_evaluations(
            read_evaluation(conn, project_id=pid, evaluation_id=baseline),
            read_evaluation(conn, project_id=pid, evaluation_id=revised),
        )
    output(result, json)


def register(app):
    app.add_typer(eval_app, name="eval")


@eval_app.command("operation-compare")
def compare_operation_evaluations(
    ctx: typer.Context,
    baseline: Annotated[int, typer.Option()],
    revised: Annotated[int, typer.Option()],
    project: str | None = None,
    json: JsonOpt = False,
):
    """Compare case facets only on the same frozen operation/source/reference frames."""
    from corpus_structure.evaluate.operation_assessment import compare_assessments, read_evaluation

    with reference_session(ctx, project, json=json) as (conn, pid):
        result = compare_assessments(
            read_evaluation(conn, project_id=pid, evaluation_id=baseline),
            read_evaluation(conn, project_id=pid, evaluation_id=revised),
        )
    output(result, json)


@eval_app.command("operation-export")
def export_operation_review(
    ctx: typer.Context,
    set_id: Annotated[int, typer.Option()],
    project: str | None = None,
    json: JsonOpt = False,
):
    """Export development judgments; protected cohorts expose sealed inventory only."""
    from corpus_structure.evaluate.operation_assessment import review_export

    with reference_session(ctx, project, json=json) as (conn, pid):
        result = review_export(conn, project_id=pid, set_id=set_id)
    output(result, json)


@eval_app.command("operation-event-availability")
def operation_event_availability(
    ctx: typer.Context,
    run: Annotated[int, typer.Argument(metavar="RUN")],
    evaluation: Annotated[int | None, typer.Option()] = None,
    project: str | None = None,
    event: Annotated[OperationEvent, typer.Option()] = DEFAULT_OPERATION_EVENT,
    json: JsonOpt = False,
):
    """Inspect exact emitted events and a selected protected evaluation before fitting."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import state
    from corpus_structure.evaluate.operation_fitting import operation_event_availability as inspect

    with failure_boundary(json):
        settings = state(ctx).settings()
        result = inspect(
            settings,
            project_id=project or settings.runtime.default_project,
            run_id=run,
            evaluation_id=evaluation,
            event=event,
        )
    if json:
        output(result, json)
        return
    emit(
        result,
        json=False,
        render=lambda report: report_fields(
            ("Fitting availability", report.status),
            ("Event", report.event),
            ("Project", report.project_id),
            ("Run / cut", f"{report.run_id} / {report.cut_id}"),
            ("Release", report.release_id),
            ("Compatible events", report.compatible_events),
            ("Feature unavailable", report.feature_unavailable),
            (
                "Evaluation",
                report.evaluation_id if report.evaluation_id is not None else "unselected",
            ),
            ("Next action", report.next_action),
        ),
    )


@eval_app.command("operation-event-features")
def operation_event_features(
    ctx: typer.Context,
    run: Annotated[int, typer.Argument(metavar="RUN")],
    cut: Annotated[int, typer.Option()],
    task: Annotated[int, typer.Option()],
    contribution: Annotated[str, typer.Option()],
    project: Annotated[str, typer.Option()],
    json: JsonOpt = False,
):
    """Read the exact defining-text features with ordinary reader authority."""
    from dataclasses import asdict

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import state
    from corpus_structure.semantic.operation_policy import (
        ATTACHMENT_EVENT_VERSION,
        ATTACHMENT_FEATURE_NAMES,
        read_defining_text_features,
    )
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine

    with (
        failure_boundary(json),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-event-features", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        result = read_defining_text_features(
            conn,
            project_id=project,
            run_id=run,
            cut_id=cut,
            task_id=task,
            contribution_id=contribution,
        )
    output(
        {
            "event": "defining_text_attachment_correctness",
            "event_version": ATTACHMENT_EVENT_VERSION,
            "feature_names": ATTACHMENT_FEATURE_NAMES,
            **asdict(result),
        },
        json,
    )


@eval_app.command("operation-event-fit")
def operation_event_fit(
    ctx: typer.Context,
    evaluation: Annotated[int | None, typer.Option()] = None,
    project: Annotated[str | None, typer.Option()] = None,
    run: Annotated[
        int | None, typer.Option(help="Check an exact completed event population.")
    ] = None,
    out: Annotated[Path | None, typer.Option()] = None,
    event: Annotated[OperationEvent, typer.Option()] = DEFAULT_OPERATION_EVENT,
    json: JsonOpt = False,
):
    """Persist same-corpus development fit of independently graded emitted events."""
    import json as jsonlib

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import state
    from corpus_structure.evaluate.operation_fitting import fit_native_operation_event
    from corpus_structure.evaluate.operation_fitting import operation_event_availability as inspect
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.runtime import open_runtime_engine

    if out is not None and out.exists():
        raise typer.BadParameter("runtime parameter output already exists")
    with failure_boundary(json):
        settings = state(ctx).settings()
        project = project or settings.runtime.default_project
        if run is not None:
            availability = inspect(
                settings, project_id=project, run_id=run, evaluation_id=evaluation, event=event
            )
            if availability.status != "ready":
                output(availability, json)
                return
        if evaluation is None:
            raise SemanticRefusal("select --run to inspect availability or --evaluation to fit")
        with open_runtime_engine(settings, "ci-event-fit", purpose="fit") as engine:
            result = fit_native_operation_event(
                engine, project_id=project, evaluation_id=evaluation, event=event
            )
    parameters = result["result"]["parameters"]
    if out is not None and parameters is not None:
        with out.open("x") as stream:
            jsonlib.dump(parameters, stream, indent=2, allow_nan=False)
            stream.write("\n")
    output(result, json)


@eval_app.command("operation-event-read")
def operation_event_read(
    ctx: typer.Context,
    fit: Annotated[int, typer.Option()],
    project: Annotated[str, typer.Option()],
    diagnostics: Annotated[
        bool, typer.Option(help="Protected evaluator labels and diagnostics.")
    ] = False,
    json: JsonOpt = False,
):
    """Read finite runtime parameters, or explicitly protected fit diagnostics."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import state
    from corpus_structure.evaluate.operation_fitting import read_native_fit
    from corpus_structure.semantic.runtime import open_runtime_engine

    with (
        failure_boundary(json),
        open_runtime_engine(
            state(ctx).settings(),
            application_name="ci-event-fit-read",
            purpose="evaluate" if diagnostics else "read",
        ) as engine,
        engine.begin() as conn,
    ):
        result = read_native_fit(conn, project_id=project, fit_id=fit, protected=diagnostics)
    output(result, json)
