"""Current read comparisons over two explicit selected native roots."""

from contextlib import nullcontext
from hashlib import sha256
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from corpus_structure.cli.output import JsonOpt, read_request_json, state, write_report_text
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_results import selected_read_snapshot
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.semantic.rich_queries import RichQueryRefused
from corpus_structure.semantic.selected_graph_budget import SelectedGraphBudgetExceeded

app = typer.Typer(help="Compare explicitly pinned current research inputs.", no_args_is_help=True)


@app.command("compare-exclusions")
def compare_exclusions(
    ctx: typer.Context,
    request: Annotated[
        Path,
        typer.Option(
            help="ExclusionComparisonRequest JSON with exact before/after read/cut/use/product/derivation pins."
        ),
    ],
    retain: bool = False,
    json: JsonOpt = False,
):
    """Compare materialized source constraints; unmatched declarations establish no absence."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.managed import result_store
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.identity_exclusion_comparison import (
        ExclusionComparisonRequest,
        compare_selected_exclusions,
    )

    with failure_boundary(
        json,
        expected=(
            ValidationError,
            RichQueryRefused,
            InvalidContinuation,
            SelectedGraphBudgetExceeded,
        ),
    ):
        try:
            incoming = read_request_json(request)
        except OSError as error:
            raise RichQueryRefused("comparison request could not be read") from error
        selected = ExclusionComparisonRequest.model_validate(incoming)
        store = result_store(ctx) if retain else None
        with (
            store.operation("research.exclusion-comparison", scope=selected.selection())
            if store is not None
            else nullcontext(None) as operation
        ):
            with (
                open_runtime_engine(
                    state(ctx).settings(), "ci-identity-exclusion-comparison", purpose="read"
                ) as engine,
                selected_read_snapshot(engine) as connection,
            ):
                report = compare_selected_exclusions(connection, selected)
            if operation is not None:
                # Settle only after the native acquisition transaction succeeded.
                content = json_bytes(report)
                path = operation.directory / "comparison.json"
                path.write_bytes(content)
                operation.publish("comparison", path)
                operation.settle(
                    "passed",
                    scope="explicit-selected-root-observations",
                    sha256=sha256(content).hexdigest(),
                )
                report = dict(
                    report,
                    retained=dict(
                        result_id=operation.id,
                        role="comparison",
                        sha256=sha256(content).hexdigest(),
                    ),
                )
    write_report_text(json_bytes(report).decode() + "\n")


def register(root):
    root.add_typer(app, name="research")
