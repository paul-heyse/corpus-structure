"""Pinned terminology lookup, interpretation reads and independent schema delivery."""

from pathlib import Path
from typing import Annotated

import typer

from corpus_structure.cli.output import JsonOpt, emit, state

app = typer.Typer(
    help="Inspect released terminology and source-preserving private interpretations.",
    no_args_is_help=True,
)


def register(root):
    root.add_typer(app, name="interpretations")


def snapshot(ctx):
    from contextlib import contextmanager

    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine

    @contextmanager
    def acquire():
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-interpretations", purpose="read"
            ) as engine,
            read_snapshot(engine) as conn,
        ):
            yield conn

    return acquire()


@app.command("lookup")
def lookup(
    ctx: typer.Context,
    release: str,
    field: str,
    query: str | None = None,
    browse: bool = False,
    json: JsonOpt = False,
):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.interpretations import term_lookup

    with failure_boundary(json), snapshot(ctx) as conn:
        result = term_lookup(conn, release_id=release, field=field, query=query, browse=browse)
    emit(result, json=json)


@app.command("review")
def review(
    ctx: typer.Context,
    review_run: int,
    review_cut: int,
    contribution: Annotated[list[str], typer.Option()],
    json: JsonOpt = False,
):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.interpretations import review_detail

    with failure_boundary(json), snapshot(ctx) as conn:
        result = review_detail(
            conn, review_run_id=review_run, review_cut_id=review_cut, contribution_ids=contribution
        )
    emit(result, json=json)


@app.command("records")
def records(
    ctx: typer.Context,
    source_run: int,
    review_run: int,
    review_cut: int,
    vocabulary_release: str,
    field: str,
    value: str | None = None,
    mapping_predicate: str | None = None,
    contribution: list[str] | None = None,
    cursor: str | None = None,
    limit: int = 20,
    page_bytes: int = 1024**2,
    json: JsonOpt = False,
):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.interpretation_queries import TerminologySelection
    from corpus_structure.serve.record_results import RecordRequest, serve_record_results

    with failure_boundary(json), snapshot(ctx) as conn:
        result = serve_record_results(
            conn,
            RecordRequest(
                run_id=source_run,
                terminology=TerminologySelection(
                    review_run_id=review_run,
                    review_cut_id=review_cut,
                    vocabulary_release=vocabulary_release,
                    field=field,
                    value=value,
                    mapping_predicate=mapping_predicate,
                    contribution_ids=tuple(contribution) if contribution else None,
                ),
                cursor=cursor,
                limit=limit,
                page_bytes=page_bytes,
            ),
        )
    emit(result, json=json)


@app.command("measurements")
def measurements(
    ctx: typer.Context,
    source_run: int,
    review_run: int,
    review_cut: int,
    limit: int = 100,
    json: JsonOpt = False,
):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.interpretation_queries import measurement_groups
    from corpus_structure.serve.interpretations import answer

    with failure_boundary(json), snapshot(ctx) as conn:
        result = answer(
            "measurement_groups",
            measurement_groups(
                conn,
                source_run_id=source_run,
                review_run_id=review_run,
                review_cut_id=review_cut,
                limit=limit,
            ),
        )
    emit(result, json=json)


@app.command("export-contract")
def export_contract(ctx: typer.Context, release: str, out: Path, json: JsonOpt = False):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.portable_interpretation import export_interpretation_contract
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.serve.interpretations import answer

    with failure_boundary(json), snapshot(ctx) as conn:
        result = answer(
            "portable_contract", export_interpretation_contract(open_release(conn, release), out)
        )
    emit(result, json=json)


@app.command("author")
def author(ctx: typer.Context, release: str, kind: str, input: Path, json: JsonOpt = False):
    """Complete explicitly authored reviews in a new private run under normal task custody."""
    import json as jsonlib

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.interpretation_authoring import author_interpretations
    from corpus_structure.serve.interpretations import answer

    with failure_boundary(json):
        with input.open("rb") as stream:
            content = stream.read(4 * 1024**2 + 1)
        if len(content) > 4 * 1024**2:
            raise SemanticRefusal("authored review input exceeds 4MiB")
        try:
            configuration = jsonlib.loads(content)
        except (jsonlib.JSONDecodeError, UnicodeDecodeError) as error:
            raise SemanticRefusal("authored review input must contain valid JSON") from error
        selected = state(ctx).settings()
        with open_runtime_engine(
            selected, "ci-interpretation-authoring", purpose="write"
        ) as engine:
            with read_snapshot(engine) as conn:
                prepared = open_release(conn, release)
            result = answer(
                "authored_review_result",
                author_interpretations(
                    engine, prepared, kind=kind, configuration=configuration, settings=selected
                ),
            )
    emit(result, json=json)
