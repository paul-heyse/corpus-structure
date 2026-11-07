"""Declared-scope review bundles and offline integrity inspection."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from pydantic import JsonValue, RootModel

from corpus_structure.cli.output import JsonOpt, emit, state

if TYPE_CHECKING:
    from corpus_structure.serve.review_bundle import ReviewSelection

app = typer.Typer(help="Export pinned evidence and verify detached review bundles.")


def _deliver_review(
    ctx: typer.Context,
    request: ReviewSelection,
    destination: Path | None,
    *,
    exact_closure: bool,
    json: bool,
    evaluator_capture: Callable[[Any], Any] | None = None,
    previous: str | None = None,
    previous_binding: str | None = None,
) -> None:
    from corpus_structure.cli.managed import result_store
    from corpus_structure.serve.review_bundle import export_review_bundle

    store = result_store(ctx)
    if destination is not None and (destination.exists() or destination.is_symlink()):
        raise FileExistsError(destination)
    action = "review.export" if evaluator_capture is None else "review.export-evaluated"
    with store.operation(
        action, scope={"exact_closure": exact_closure, "previous": previous}
    ) as result:
        selection_path = result.directory / "selection.json"
        selection_path.write_text(request.model_dump_json())
        result.publish("selection", selection_path)
        result.stage("capture")
        bundle = result.directory / "bundle"

        def retain_binding(binding: str) -> None:
            if previous_binding is not None and binding != previous_binding:
                raise ValueError(
                    "configured database or completed review roots differ from the original"
                )
            result.manifest.scope["source_binding"] = binding
            result.stage("bound")

        manifest = export_review_bundle(
            request,
            bundle,
            state(ctx).settings(),
            evaluator_capture=evaluator_capture,
            exact_closure=exact_closure,
            retain_binding=retain_binding if evaluator_capture is None else None,
        )
        result.publish("bundle", bundle)
        result.stage("published")
    delivered = store.deliver(result.id, "bundle", destination)
    emit(
        RootModel[dict[str, JsonValue]].model_validate(
            {**manifest, "invocation_id": result.id, "destination": str(delivered)}
        ),
        json=json,
    )


@app.command("export-evaluated")
def export_evaluated_review(
    ctx: typer.Context,
    selection: Path,
    destination: Annotated[Path | None, typer.Argument()] = None,
    *,
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
    from corpus_structure.serve.review_bundle import ReviewSelection

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
        _deliver_review(
            ctx, request, destination, exact_closure=False, json=json, evaluator_capture=capture
        )


@app.command("export")
def export_review(
    ctx: typer.Context,
    selection: Path,
    destination: Annotated[Path | None, typer.Argument()] = None,
    exact_closure: Annotated[
        bool, typer.Option(help="Include only exact retained predecessors.")
    ] = False,
    json: JsonOpt = False,
):
    """Export an explicit JSON selection using ordinary reader authority."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.review_bundle import ReviewSelection

    with failure_boundary(json, expected=(OSError, ValueError)):
        request = ReviewSelection.model_validate_json(selection.read_bytes())
        _deliver_review(ctx, request, destination, exact_closure=exact_closure, json=json)


@app.command("retry")
def retry_review(
    ctx: typer.Context, result_id: str, destination: Path | None = None, json: JsonOpt = False
):
    """Retry an ordinary export against the same completed selection."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.managed import result_store
    from corpus_structure.serve.review_bundle import ReviewSelection

    with failure_boundary(json, expected=(OSError, ValueError)):
        store = result_store(ctx)
        with store.lease(result_id):
            previous = store.show(result_id)
            if previous.action != "review.export":
                raise ValueError("retry requires an ordinary review export result")
            binding = previous.scope.get("source_binding")
            if not isinstance(binding, str):
                raise ValueError(
                    "original export acquired no source binding; submit its selection explicitly"
                )
            request = ReviewSelection.model_validate_json(
                store.artifact(result_id, "selection").read_bytes()
            )
            _deliver_review(
                ctx,
                request,
                destination,
                exact_closure=previous.scope.get("exact_closure") is True,
                previous=result_id,
                previous_binding=binding,
                json=json,
            )


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
