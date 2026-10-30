"""Restricted semantic reference-set, split, pass and status commands."""

from __future__ import annotations

import json as jsonlib
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy import select

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, state
from corpus_structure.evaluate import semantic as references
from corpus_structure.semantic.metadata import table

golden_app = typer.Typer(
    help="Independent references on an immutable semantic release.", no_args_is_help=True
)


@contextmanager
def reference_session(ctx, project=None, *, json=False):
    from corpus_structure.semantic.runtime import open_runtime_engine

    with failure_boundary(json, expected=(references.ReferenceError,)):
        settings = state(ctx).settings()
        with (
            open_runtime_engine(
                settings, application_name="ci-reference", purpose="evaluate"
            ) as engine,
            engine.begin() as conn,
        ):
            project = project or settings.runtime.default_project
            if project is None:
                candidates = list(
                    conn.execute(select(table("data.project").c.project_id)).scalars()
                )
                if len(candidates) != 1:
                    raise references.ReferenceError("select --project explicitly")
                project = candidates[0]
            if not conn.scalar(
                select(table("data.project").c.project_id).where(
                    table("data.project").c.project_id == project
                )
            ):
                raise references.ReferenceError("unknown semantic project")
            yield conn, project


def output(result, json):
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json")
    if json:
        typer.echo(jsonlib.dumps(result, ensure_ascii=False, allow_nan=False, default=str))
    else:
        from rich.pretty import Pretty

        from corpus_structure.cli.output import stdout_console

        stdout_console().print(Pretty(result))


@golden_app.command("split")
def split_command(
    ctx: typer.Context, seed: int | None = None, project: str | None = None, json: JsonOpt = False
):
    """Assign registered source documents immutably to development/test splits."""
    with reference_session(ctx, project, json=json) as (conn, pid):
        result = references.split_documents(conn, pid, seed=seed)
    output(result, json)


@golden_app.command("create")
def create_command(
    ctx: typer.Context,
    split: Annotated[str, typer.Option()],
    label: Annotated[str, typer.Option()],
    size: int | None = None,
    seed: int | None = None,
    from_run: int | None = None,
    project: str | None = None,
    json: JsonOpt = False,
):
    """Sample independent reference units from a completed result's frozen source cut."""
    with reference_session(ctx, project, json=json) as (conn, pid):
        run = from_run or conn.scalar(
            select(table("data.project").c.selected_result_run_id).where(
                table("data.project").c.project_id == pid
            )
        )
        if run is None:
            raise references.ReferenceError("choose --from-run or select a completed result")
        result = references.create_reference_set(
            conn, project_id=pid, source_run_id=run, label=label, split=split, size=size, seed=seed
        )
    output(result, json)


@golden_app.command("status")
def status_command(
    ctx: typer.Context, label: str | None = None, project: str | None = None, json: JsonOpt = False
):
    """Show counts and bindings, without exposing reference answers."""
    with reference_session(ctx, project, json=json) as (conn, pid):
        s = table("eval.reference_set")
        q = select(s).where(s.c.project_id == pid)
        if label is not None:
            q = q.where(s.c.label == label)
        result = [
            {
                **references.golden_set_status(conn, row.id),
                "label": row.label,
                "split": row.split,
                "release_id": row.release_id,
                "source_run_id": row.source_run_id,
            }
            for row in conn.execute(q.order_by(s.c.id))
        ]
        if label is not None and not result:
            raise references.ReferenceError(f"no reference set {label!r}")
    output(result, json)


@golden_app.command("submit")
def submit_command(
    ctx: typer.Context,
    unit: Annotated[int, typer.Option()],
    pass_kind: Annotated[str, typer.Option("--pass")],
    actor: Annotated[str, typer.Option()],
    authored: Annotated[Path, typer.Option(exists=True, dir_okay=False, readable=True)],
    frame: Annotated[Path, typer.Option(exists=True, dir_okay=False, readable=True)],
    project: str | None = None,
    json: JsonOpt = False,
):
    """Store an automated independent pass and its exact source citation frame."""
    from corpus_structure.semantic.proposals import ProposalFrame, ProposalSentence

    with reference_session(ctx, project, json=json) as (conn, pid):
        if references._unit(conn, unit)["project_id"] != pid:
            raise references.ReferenceError("reference unit belongs to another project")
        try:
            raw = jsonlib.loads(frame.read_bytes())
            source = ProposalFrame(
                raw["unit_ref"], raw["text"], tuple(ProposalSentence(**s) for s in raw["sentences"])
            )
        except (jsonlib.JSONDecodeError, KeyError, TypeError) as error:
            raise references.ReferenceError("invalid authored citation frame") from error
        identity = references.record_pass(
            conn,
            unit_id=unit,
            pass_kind=pass_kind,
            actor=actor,
            authored=authored.read_bytes(),
            frame=source,
        )
    output({"pass_id": identity, "unit_id": unit, "pass_kind": pass_kind}, json)


def register(app):
    app.add_typer(golden_app, name="golden")
