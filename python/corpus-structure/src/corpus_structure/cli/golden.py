"""Named sealed reference packet/status readers; original addresses remain intact."""

from __future__ import annotations

import json as jsonlib
from contextlib import contextmanager
from typing import Annotated

import typer

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, state


@contextmanager
def reference_session(ctx, project=None, *, json=False):
    from sqlalchemy import select

    from corpus_structure.evaluate import semantic as references
    from corpus_structure.semantic.metadata import table
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
        from corpus_structure.cli.output import write_report_text

        write_report_text(
            jsonlib.dumps(result, ensure_ascii=False, allow_nan=False, default=str) + "\n"
        )
    else:
        from rich.pretty import Pretty

        from corpus_structure.cli.output import stdout_console

        stdout_console().print(Pretty(result))

def reference_protocol(conn, set_id, project_id):
    """Route only from a stored, project-bound reference-set declaration."""
    from sqlalchemy import select

    from corpus_structure.evaluate import operation_assessment, record_references, semantic
    from corpus_structure.semantic.metadata import table

    sets = table("eval.reference_set")
    definition = conn.execute(select(sets).where(sets.c.id == set_id)).mappings().one_or_none()
    if definition is None:
        raise semantic.ReferenceError(f"unknown reference set {set_id}")
    if definition["project_id"] != project_id:
        raise semantic.ReferenceError("reference set belongs to another project")
    protocol = definition["sampling"].get("operation_protocol") or definition["sampling"].get(
        "record_protocol"
    )
    if protocol not in (None, record_references.PROTOCOL, operation_assessment.PROTOCOL):
        raise semantic.ReferenceError("unsupported stored reference protocol")
    return protocol








def record_packet_command(
    ctx: typer.Context,
    unit: Annotated[int, typer.Option()],
    pass_kind: Annotated[str, typer.Option("--pass")],
    project: str | None = None,
    json: JsonOpt = False,
):
    """Read source-only A/B inputs or the separate retained A/B adjudication packet for C."""
    from corpus_structure.evaluate import record_references as references

    with reference_session(ctx, project, json=json) as (conn, pid):
        bound = references._unit(conn, unit)
        if bound["project_id"] != pid:
            raise references.ReferenceError("reference unit belongs to another project")
        if reference_protocol(conn, bound["set_id"], pid) != references.PROTOCOL:
            raise references.ReferenceError("reference set does not declare the record protocol")
        if pass_kind in {"A", "B"}:
            result = references.author_packet(conn, unit)
        elif pass_kind == "C":
            result = references.adjudication_packet(conn, unit)
            result = dict(
                result,
                authors=[
                    dict(author, authored=author["authored"].decode("utf-8"))
                    for author in result["authors"]
                ],
            )
        else:
            raise references.ReferenceError("record packet --pass must be A, B or C")
    output(result, json)




def operation_packet_command(
    ctx: typer.Context,
    unit: Annotated[int, typer.Option()],
    pass_kind: Annotated[str, typer.Option("--pass")],
    project: str | None = None,
    json: JsonOpt = False,
):
    """Read independent source-only A/B input or retained A/B adjudication input for C."""
    from corpus_structure.evaluate import operation_assessment as references

    with reference_session(ctx, project, json=json) as (conn, pid):
        bound = references._unit(conn, unit)
        if (
            bound["project_id"] != pid
            or reference_protocol(conn, bound["set_id"], pid) != references.PROTOCOL
        ):
            raise references.ReferenceError("unit is outside selected operation reference project")
        if pass_kind in {"A", "B"}:
            result = references.author_packet(conn, unit)
        elif pass_kind == "C":
            result = references.adjudication_packet(conn, unit)
        else:
            raise references.ReferenceError("operation packet --pass must be A, B or C")
    output(result, json)



def status_command(
    ctx: typer.Context, label: str | None = None, project: str | None = None, json: JsonOpt = False
):
    """Show counts and bindings, without exposing reference answers."""
    from sqlalchemy import select

    from corpus_structure.evaluate import semantic as references
    from corpus_structure.semantic.metadata import table

    with reference_session(ctx, project, json=json) as (conn, pid):
        provenance = references.split_provenance_summary(conn, pid)
        s = table("eval.reference_set")
        q = select(s).where(s.c.project_id == pid)
        if label is not None:
            q = q.where(s.c.label == label)
        result = [
            {
                **references.golden_set_status(conn, row.id),
                "split_provenance": provenance,
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



def register(app):
    # Preserved original packets/status are named sealed readers. Current authoring
    # uses protected declared reference facts; old create/submit mutators are absent.
    retained = typer.Typer(help="Read original sealed reference inventories without regrading.")
    retained.command("status")(status_command)
    retained.command("record-packet")(record_packet_command)
    retained.command("operation-packet")(operation_packet_command)
    app.add_typer(retained, name="retained-golden")
