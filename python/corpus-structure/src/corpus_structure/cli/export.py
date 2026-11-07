"""Export one completed semantic result as a detached qualified full projection."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import Annotated, Literal

import typer

from corpus_structure.cli.output import JsonOpt, state
from corpus_structure.cli.query import refusal, result_context


def export(
    ctx: typer.Context,
    out: Annotated[Path, typer.Option("--out")],
    format: Literal["jsonl", "parquet"] = "parquet",
    capture_mode: Annotated[
        Literal["resident", "spooled"] | None, typer.Option("--capture-mode")
    ] = None,
    run: str = "promoted",
    project: str | None = None,
    include_records: bool = False,
    include_record_diagnostics: bool = False,
    json: JsonOpt = False,
):
    from corpus_structure.semantic.analytics import load_packet
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import connection_settings, open_runtime_engine
    from corpus_structure.serve.export import export_packet
    from corpus_structure.serve.journey import bind_session

    settings = state(ctx).settings()
    with refusal(json), ExitStack() as resources:
        with (
            open_runtime_engine(settings, application_name="ci-export", purpose="read") as engine,
            read_snapshot(engine) as conn,
        ):
            _, rid = result_context(
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
            records = None
            if include_records:
                from corpus_structure.semantic.record_queries import (
                    read_completed_record_projection,
                )

                records = read_completed_record_projection(
                    conn,
                    run_id=rid,
                    project_id=project,
                    include_diagnostics=include_record_diagnostics,
                )
        manifest = export_packet(
            packet,
            out,
            format=format,
            records=records,
            include_record_diagnostics=include_record_diagnostics,
        )
        from corpus_structure.cli.output import write_report_text

        report = (
            __import__("json").dumps({"path": str(out), "manifest": manifest}) if json else str(out)
        )
        write_report_text(report + "\n")


def register(app: typer.Typer):
    app.command("export")(export)
