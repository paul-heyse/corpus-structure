"""Named sealed grade readers and comparisons without native regrading."""

from __future__ import annotations

from typing import Annotated, Literal

import typer

from corpus_structure.cli.golden import output, reference_session
from corpus_structure.cli.output import JsonOpt





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
    # Original immutable grades and their explicit comparisons retain their own
    # read route. No old run/frame dispatch performs current authoring or regrading.
    retained = typer.Typer(help="Inspect or compare original sealed grades without regrading.")
    retained.command("gaps")(record_gaps)
    retained.command("compare")(compare_record_evaluations)
    retained.command("operation-compare")(compare_operation_evaluations)
    retained.command("operation-export")(export_operation_review)
    retained.command("operation-inspect")(inspect_operation_evaluation)
    retained.command("operation-event-read")(operation_event_read)
    app.add_typer(retained, name="retained-eval")

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

def inspect_operation_evaluation(
    ctx: typer.Context,
    evaluation: Annotated[int, typer.Argument(min=1)],
    view: Annotated[Literal["summary", "coverage", "cases", "errors"], typer.Option()] = "summary",
    facet: str | None = None,
    direction: Literal["source_first", "output_first"] | None = None,
    cursor: str | None = None,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
    max_bytes: Annotated[int, typer.Option(min=1024, max=8388608)] = 1048576,
    project: str | None = None,
    json: JsonOpt = False,
):
    """Inspect bounded protected operation cases, coverage and errors without regrading."""
    from corpus_structure.evaluate.operation_assessment import inspect_evaluation

    with reference_session(ctx, project, json=json) as (conn, pid):
        result = inspect_evaluation(
            conn,
            project_id=pid,
            evaluation_id=evaluation,
            view=view,
            facet=facet,
            direction=direction,
            cursor=cursor,
            limit=limit,
            max_bytes=max_bytes,
        )
    output(result, json)
