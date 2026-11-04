"""Minimal native independent-reference grading; completed knowledge output is separate."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer

from corpus_structure.cli.golden import output, reference_protocol, reference_session
from corpus_structure.cli.output import JsonOpt

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
):
    """Persist core, qualified-full and evidence P/R/F1 with exact pass-C snapshots."""
    from corpus_structure.evaluate import record_references, semantic

    with reference_session(ctx, project, json=json) as (conn, pid):
        protocol = reference_protocol(conn, set_id, pid)
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


def register(app):
    app.add_typer(eval_app, name="eval")
