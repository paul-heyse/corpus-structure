"""Minimal native independent-reference grading; completed knowledge output is separate."""

from __future__ import annotations

from typing import Annotated

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


def register(app):
    app.add_typer(eval_app, name="eval")
