"""Pinned terminology lookup, interpretation reads and independent schema delivery."""

from pathlib import Path
from typing import Annotated, Literal

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


@app.command(
    "lookup",
    epilog=(
        "Example: ci interpretations lookup RELEASE FIELD --query term "
        "--json\n\nDomain contract: [domain "
        "reader](docs/design/D8-agent-and-query-interfaces.md)"
    ),
)
def lookup(
    ctx: typer.Context,
    release: Annotated[
        str, typer.Argument(metavar="RELEASE", help="Archived semantic release ID.")
    ],
    field: Annotated[str, typer.Argument(metavar="FIELD", help="Released field identifier.")],
    query: Annotated[
        str | None,
        typer.Option(
            help="Lexical terminology query; mutually exclusive with --browse.",
            rich_help_panel="Inputs",
        ),
    ] = None,
    browse: Annotated[
        bool,
        typer.Option(
            "--browse/--no-browse",
            help="Explicitly browse the released field vocabulary instead of supplying --query.",
            rich_help_panel="Inputs",
        ),
    ] = False,
    json: JsonOpt = False,
):
    """Look up released terminology for a field; choose query or explicit browse."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.interpretations import term_lookup

    with failure_boundary(json), snapshot(ctx) as conn:
        result = term_lookup(conn, release_id=release, field=field, query=query, browse=browse)
    emit(result, json=json)


@app.command(
    "review",
    epilog=(
        "Example: ci interpretations review REVIEW_RUN REVIEW_CUT "
        "--contribution CONTRIBUTION --json\n\nDomain contract: [domain "
        "reader](docs/design/D8-agent-and-query-interfaces.md)"
    ),
)
def review(
    ctx: typer.Context,
    review_run: Annotated[
        int, typer.Argument(metavar="REVIEW_RUN", help="Pinned private review run ID.")
    ],
    review_cut: Annotated[int, typer.Argument(metavar="REVIEW_CUT", help="Pinned review cut ID.")],
    contribution: Annotated[
        list[str],
        typer.Option(
            "--contribution",
            help="Pinned contribution ID; repeat to select several.",
            rich_help_panel="Inputs",
        ),
    ],
    json: JsonOpt = False,
):
    """Read pinned review contributions without changing their selection."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.interpretations import review_detail

    with failure_boundary(json), snapshot(ctx) as conn:
        result = review_detail(
            conn, review_run_id=review_run, review_cut_id=review_cut, contribution_ids=contribution
        )
    emit(result, json=json)


@app.command(
    "records",
    epilog=(
        "Example: ci interpretations records SOURCE_RUN REVIEW_RUN "
        "REVIEW_CUT VOCABULARY_RELEASE FIELD --limit 20 --json\n\nDomain "
        "contract: [domain reader](docs/design/D8-agent-and-query-interfac"
        "es.md)"
    ),
)
def records(
    ctx: typer.Context,
    source_run: Annotated[int, typer.Argument(metavar="SOURCE_RUN", help="Pinned source run ID.")],
    review_run: Annotated[
        int, typer.Argument(metavar="REVIEW_RUN", help="Pinned private review run ID.")
    ],
    review_cut: Annotated[int, typer.Argument(metavar="REVIEW_CUT", help="Pinned review cut ID.")],
    vocabulary_release: Annotated[
        str, typer.Argument(metavar="VOCABULARY_RELEASE", help="Pinned released vocabulary ID.")
    ],
    field: Annotated[str, typer.Argument(metavar="FIELD", help="Released field identifier.")],
    value: Annotated[
        str | None, typer.Option(help="Released vocabulary value filter.", rich_help_panel="Inputs")
    ] = None,
    mapping_predicate: Annotated[
        str | None,
        typer.Option(help="Exact mapping predicate IRI filter.", rich_help_panel="Inputs"),
    ] = None,
    contribution: Annotated[
        list[str] | None,
        typer.Option(
            "--contribution",
            help="Contribution ID filter; repeat to select several.",
            rich_help_panel="Inputs",
        ),
    ] = None,
    cursor: Annotated[
        str | None,
        typer.Option(
            help="Opaque continuation from the previous records page.", rich_help_panel="Delivery"
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(min=1, max=100, help="Maximum records per page.", rich_help_panel="Delivery"),
    ] = 20,
    page_bytes: Annotated[
        int,
        typer.Option(
            min=1,
            max=32 * 1024**2,
            help="Maximum serialized page bytes.",
            rich_help_panel="Delivery",
        ),
    ] = 1024**2,
    json: JsonOpt = False,
):
    """Read source records using an explicitly pinned terminology review and vocabulary."""
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


@app.command(
    "measurements",
    epilog=(
        "Example: ci interpretations measurements SOURCE_RUN REVIEW_RUN "
        "REVIEW_CUT --json\n\nDomain contract: [domain "
        "reader](docs/design/D8-agent-and-query-interfaces.md)"
    ),
)
def measurements(
    ctx: typer.Context,
    source_run: Annotated[int, typer.Argument(metavar="SOURCE_RUN", help="Pinned source run ID.")],
    review_run: Annotated[
        int, typer.Argument(metavar="REVIEW_RUN", help="Pinned private review run ID.")
    ],
    review_cut: Annotated[int, typer.Argument(metavar="REVIEW_CUT", help="Pinned review cut ID.")],
    limit: Annotated[
        int,
        typer.Option(
            min=1, max=1000, help="Maximum measurement groups.", rich_help_panel="Delivery"
        ),
    ] = 100,
    json: JsonOpt = False,
):
    """Read grouped measurement interpretations under a pinned review cut."""
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


@app.command(
    "export-contract",
    epilog=(
        "Example: ci interpretations export-contract RELEASE "
        "build/interpretation-contract --json\n\nDomain contract: [domain "
        "reader](docs/design/D8-agent-and-query-interfaces.md)"
    ),
)
def export_contract(
    ctx: typer.Context,
    release: Annotated[
        str, typer.Argument(metavar="RELEASE", help="Archived semantic release ID.")
    ],
    out: Annotated[
        Path, typer.Argument(metavar="OUT", help="Destination for the portable contract.")
    ],
    json: JsonOpt = False,
):
    """Write the portable interpretation contract for the archived release."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.portable_interpretation import export_interpretation_contract
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.serve.interpretations import answer

    with failure_boundary(json), snapshot(ctx) as conn:
        result = answer(
            "portable_contract", export_interpretation_contract(open_release(conn, release), out)
        )
    emit(result, json=json)


@app.command(
    "author",
    epilog=(
        "Example: ci interpretations author RELEASE terminology "
        "review.json --json\n\nDomain contract: [domain "
        "reader](docs/design/D8-agent-and-query-interfaces.md)"
    ),
)
def author(
    ctx: typer.Context,
    release: Annotated[
        str, typer.Argument(metavar="RELEASE", help="Archived semantic release ID.")
    ],
    kind: Annotated[
        Literal["terminology", "measurement", "source_records"],
        typer.Argument(metavar="KIND", help="Authored private contribution kind."),
    ],
    input: Annotated[
        Path,
        typer.Argument(
            metavar="INPUT",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Supplied JSON configuration, bounded to 4 MiB.",
        ),
    ],
    json: JsonOpt = False,
):
    """Complete supplied reviews in a new private run under normal task custody.

    First inspect the released input contract with `schema inspect`, or export the
    portable contract with `interpretations export-contract`. Structural validation
    checks shape; accepted validation checks the released constraints. Authoring
    retains private knowledge; selecting it is a separate explicit operation.
    """
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
