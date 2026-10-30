"""Export one completed semantic result as a detached qualified full projection."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import Annotated, Literal

import typer

from corpus_structure.cli.output import JsonOpt, state
from corpus_structure.cli.query import context, refusal
from corpus_structure.semantic.analytics import load_packet
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.serve.export import export_packet
from corpus_structure.serve.journey import bind_session


def export(
    ctx: typer.Context,
    out: Annotated[Path, typer.Option("--out")],
    format: Literal["jsonl", "parquet"] = "parquet",
    capture_mode: Annotated[
        Literal["resident", "spooled"] | None, typer.Option("--capture-mode")
    ] = None,
    run: str = "promoted",
    project: str | None = None,
    json: JsonOpt = False,
):
    from corpus_structure.semantic.runtime import connection_settings, open_runtime_engine

    settings = state(ctx).settings()
    with refusal(json), ExitStack() as resources:
        with (
            open_runtime_engine(settings, application_name="ci-export", purpose="read") as engine,
            read_snapshot(engine) as conn,
        ):
            _, rid, _ = context(
                conn,
                project or (settings.runtime.default_project if run == "promoted" else None),
                run,
            )
            session = bind_session(conn, rid)
            # The ADBC reader imports this exact native transaction snapshot.
            uri = connection_settings(settings, "read").database.url
            packet = resources.enter_context(
                load_packet(
                    session,
                    uri,
                    mode=capture_mode or settings.analytics.capture_mode,
                    batch_size=settings.analytics.batch_size,
                    resident_limit_bytes=settings.analytics.resident_limit_bytes,
                    batch_size_hint_bytes=settings.analytics.batch_size_hint_bytes,
                    scratch_path=settings.analytics.scratch_path,
                    driver_path=str(settings.analytics.adbc_driver_path)
                    if settings.analytics.adbc_driver_path
                    else None,
                )
            )
        manifest = export_packet(packet, out, format=format)
        typer.echo(
            __import__("json").dumps({"path": str(out), "manifest": manifest}) if json else str(out)
        )


def register(app: typer.Typer):
    app.command("export")(export)
