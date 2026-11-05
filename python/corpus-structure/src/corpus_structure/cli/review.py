"""Declared-scope review bundles and offline integrity inspection."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import JsonValue, RootModel

from corpus_structure.cli.output import JsonOpt, emit, state

app = typer.Typer(help="Export pinned evidence and verify detached review bundles.")


@app.command("export-evaluated")
def export_evaluated_review(
    ctx: typer.Context,
    selection: Path,
    destination: Path,
    project: Annotated[str, typer.Option()],
    assessment_set: Annotated[list[int] | None, typer.Option("--assessment-set")] = None,
    group_set: Annotated[list[int] | None, typer.Option("--group-assessment-set")] = None,
    group_project: Annotated[str | None, typer.Option()] = None,
    authorization_basis: Annotated[str | None, typer.Option()] = None,
    json: JsonOpt = False,
):
    """Use evaluator authority for selected development history; record exposure first."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.evaluate.review_assessments import (
        AssessmentReviewSelection,
        assessment_review_capture,
        record_review_exposure,
    )
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle

    with failure_boundary(json, expected=(OSError, ValueError)):
        request = ReviewSelection.model_validate_json(selection.read_bytes())
        settings = state(ctx).settings()
        cohorts = tuple((False, project, value) for value in assessment_set or ()) + tuple(
            (True, group_project or project, value) for value in group_set or ()
        )
        if not cohorts or len(set(cohorts)) != len(cohorts):
            raise ValueError("assessment sets must be nonempty and distinct")
        with (
            open_runtime_engine(settings, "ci-review-exposure", purpose="evaluate") as engine,
            engine.begin() as conn,
        ):
            receipts = {
                (group, owner, set_id): record_review_exposure(
                    conn,
                    project_id=owner,
                    set_id=set_id,
                    purpose="portable_review",
                    recipient_class="external_reviewer",
                    group=group,
                    authorization_basis=None if group else authorization_basis,
                )
                for group, owner, set_id in cohorts
            }
        capture = assessment_review_capture(
            tuple(
                AssessmentReviewSelection(
                    project_id=owner,
                    set_id=set_id,
                    exposure_receipt_id=receipts[group, owner, set_id],
                    group=group,
                )
                for group, owner, set_id in cohorts
            )
        )
        result = export_review_bundle(request, destination, settings, evaluator_capture=capture)
    emit(RootModel[dict[str, JsonValue]].model_validate(result), json=json)


@app.command("export")
def export_review(ctx: typer.Context, selection: Path, destination: Path, json: JsonOpt = False):
    """Export an explicit JSON selection using ordinary reader authority."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle

    with failure_boundary(json, expected=(OSError, ValueError)):
        request = ReviewSelection.model_validate_json(selection.read_bytes())
        result = export_review_bundle(request, destination, state(ctx).settings())
    emit(RootModel[dict[str, JsonValue]].model_validate(result), json=json)


@app.command("verify")
def verify_review(bundle: Path, json: JsonOpt = False):
    """Check manifest, bodies and relation agreement without a database or model."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.review_bundle import verify_review_bundle

    with failure_boundary(json, expected=(OSError, ValueError)):
        result = verify_review_bundle(bundle)
    emit(RootModel[dict[str, JsonValue]].model_validate(result), json=json)


@app.command("inspect")
def inspect_review(bundle: Path, json: JsonOpt = False):
    """Verify a detached bundle and summarize its declared coverage."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.review_bundle import inspect_review_bundle

    with failure_boundary(json, expected=(OSError, ValueError)):
        result = inspect_review_bundle(bundle)
    emit(RootModel[dict[str, JsonValue]].model_validate(result), json=json)


def register(root: typer.Typer):
    root.add_typer(app, name="review")
