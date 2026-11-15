"""Pinned terminology lookup, interpretation reads and independent schema delivery."""

from pathlib import Path
from typing import Annotated

import typer

from corpus_structure.cli.output import JsonOpt, emit, state, write_report_text
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads

app = typer.Typer(
    help="Inspect released terminology and source-preserving private interpretations.",
    no_args_is_help=True,
)


def register(root):
    root.add_typer(app, name="interpretations")


def _emit(result, *, json):
    if json:
        write_report_text(json_bytes(result.model_dump(mode="python")).decode() + "\n")
    else:
        emit(result, json=False)


def snapshot(ctx):
    from contextlib import contextmanager

    from corpus_structure.semantic.demand_results import selected_read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine

    @contextmanager
    def acquire():
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-interpretations", purpose="read"
            ) as engine,
            selected_read_snapshot(engine) as conn,
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
    _emit(result, json=json)


@app.command("review")
def review(ctx: typer.Context, request: Annotated[Path, typer.Argument(help="SelectedProposalRequest JSON with explicit demand/project and optional product/member pins.")], json: JsonOpt = False):
    """Inspect genuine selected private proposal members; no accepted standing follows."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import read_request_bytes
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.serve.interpretations import SelectedProposalRequest, inspect_selected_proposals

    with failure_boundary(json, expected=(ValueError, OSError)), snapshot(ctx) as connection:
        selected = SelectedProposalRequest.model_validate(json_loads(read_request_bytes(request)))
        result = inspect_selected_proposals(connection, selected)
    _emit(result, json=json)


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
    _emit(result, json=json)


@app.command(
    "author",
    epilog=(
        "Example: ci interpretations author RELEASE "
        "review.json --json\n\nDomain contract: [domain "
        "reader](docs/design/D8-agent-and-query-interfaces.md)"
    ),
)
def author(
    ctx: typer.Context,
    release: Annotated[
        str, typer.Argument(metavar="RELEASE", help="Archived semantic release ID.")
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
    """Retain typed authored facts frozen with an explicit native demand request.

    INPUT is a NativeDemandRequest containing authored-fact original selections,
    their actual kind contracts, complete root contexts and downstream targets.
    Authoring admits those facts without running downstream inference or selecting
    them as an active result. Inspect the admitted kind contract before authoring.
    """
    from pydantic import ValidationError

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.data_operation_service import NativeDemandRequest
    from corpus_structure.semantic.demand_results import selected_read_snapshot
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
            request = NativeDemandRequest.model_validate(json_loads(content))
        except ValidationError as error:
            raise SemanticRefusal(
                "authored input must match the native demand request contract"
            ) from error
        selected = state(ctx).settings()
        with open_runtime_engine(
            selected, "ci-interpretation-authoring", purpose="write"
        ) as engine:
            with selected_read_snapshot(engine) as conn:
                prepared = open_release(conn, release)
            result = answer(
                "authored_review_result",
                author_interpretations(engine, prepared, request=request),
            )
    _emit(result, json=json)
