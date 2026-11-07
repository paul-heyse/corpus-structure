"""Declared-scope review bundles and offline integrity inspection."""

from __future__ import annotations

import signal
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from pydantic import JsonValue, RootModel
from rich.table import Table

from corpus_structure.cli.output import (
    JsonOpt,
    diagnostic,
    emit,
    read_request_bytes,
    report_fields,
    state,
)

if TYPE_CHECKING:
    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.serve.review_bundle import ReviewSelection

app = typer.Typer(help="Export pinned evidence and verify detached review bundles.")


@contextmanager
def _capture_signals(cancellation: OperationCancellation) -> Generator[Callable[[], int | None]]:
    """Cancel the current native borrower, leaving cleanup to its execution owner."""
    received: int | None = None

    def request(number: int, _frame: object) -> None:
        nonlocal received
        if received is None:
            received = number
            cancellation.request_cancel()

    previous = {}
    try:
        if threading.current_thread() is threading.main_thread():
            for number in (signal.SIGINT, signal.SIGTERM):
                previous[number] = signal.signal(number, request)
        yield lambda: received
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def _selection_digest(body: bytes, *, exact_closure: bool) -> str:
    mode = b"exact\0" if exact_closure else b"declared\0"
    return sha256(mode + body).hexdigest()


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
    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.serve.review_bundle import export_review_bundle

    store = result_store(ctx)
    if destination is not None and (destination.exists() or destination.is_symlink()):
        raise FileExistsError(destination)
    action = "review.export" if evaluator_capture is None else "review.export-evaluated"
    body = request.model_dump_json().encode()
    selection_digest = _selection_digest(body, exact_closure=exact_closure)
    cancellation = OperationCancellation()
    with (
        _capture_signals(cancellation) as interrupted,
        store.operation(
            action,
            scope={
                "exact_closure": exact_closure,
                "selection_digest": selection_digest,
                "previous": previous,
            },
        ) as result,
    ):
        selection_path = result.directory / "selection.json"
        selection_path.write_bytes(body)
        result.publish("selection", selection_path)
        result.stage("capture")
        diagnostic(f"Review {result.id} · capture")
        bundle = result.directory / "bundle"

        def retain_binding(binding: str) -> None:
            if previous_binding is not None and binding != previous_binding:
                raise ValueError(
                    "configured database or completed review roots differ from the original"
                )
            result.manifest.scope["source_binding"] = binding
            result.stage("bound")

        try:
            manifest = export_review_bundle(
                request,
                bundle,
                state(ctx).settings(),
                cancellation=cancellation,
                evaluator_capture=evaluator_capture,
                exact_closure=exact_closure,
                retain_binding=retain_binding if evaluator_capture is None else None,
            )
        except BaseException as error:
            received = interrupted()
            database_diagnostic = getattr(error, "database_diagnostic", None)
            native = getattr(database_diagnostic, "failure", None)
            if (
                cancellation.cleanup_failures
                or getattr(error, "__notes__", ())
                or getattr(error, "adbc_cleanup_failures", ())
                or getattr(native, "invalidated", False)
            ):
                result.defer_settlement()
                raise
            if received is None:
                raise
            if evaluator_capture is not None:
                next_action = "Submit the selection again with ci review export-evaluated"
            elif result.manifest.scope.get("source_binding") is None:
                next_action = "Submit the selection again with ci review export"
            else:
                next_action = f"ci review retry {result.id}"
            result.settle(
                "interrupted",
                signal=received,
                next_action=next_action,
            )
            if json:
                emit(
                    RootModel[dict[str, JsonValue]](
                        {
                            "error": {
                                "code": "review_interrupted",
                                "message": "review capture interrupted and settled",
                                "invocation_id": result.id,
                            }
                        }
                    ),
                    json=True,
                    exit_code=128 + received,
                )
            raise typer.Exit(128 + received) from error
        result.publish("bundle", bundle)
        result.stage(
            "published",
            bundle_manifest_sha256=sha256(canonical_bytes(manifest) + b"\n").hexdigest(),
        )
    delivered = store.deliver(result.id, "bundle", destination)
    diagnostic(f"Review {result.id} · published")
    emit(
        RootModel[dict[str, JsonValue]].model_validate(
            {**manifest, "invocation_id": result.id, "destination": str(delivered)}
        ),
        json=json,
    )


@app.command("export-evaluated")
def export_evaluated_review(
    ctx: typer.Context,
    selection: Annotated[str, typer.Argument(help="A JSON selection path or '-' for stdin.")],
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
        request = ReviewSelection.model_validate_json(read_request_bytes(selection))
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
    selection: Annotated[str, typer.Argument(help="A JSON selection path or '-' for stdin.")],
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
        request = ReviewSelection.model_validate_json(read_request_bytes(selection))
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
            if previous.settled is None or previous.details.get("custody_unsettled"):
                raise ValueError("retry requires proof that the previous capture settled")
            binding = previous.scope.get("source_binding")
            if not isinstance(binding, str):
                raise ValueError(
                    "original export acquired no source binding; submit its selection explicitly"
                )
            body = store.read_artifact(result_id, "selection")
            exact_closure = previous.scope.get("exact_closure") is True
            if _selection_digest(body, exact_closure=exact_closure) != previous.scope.get(
                "selection_digest"
            ):
                raise ValueError("retained review selection differs from the original")
            request = ReviewSelection.model_validate_json(body)
            _deliver_review(
                ctx,
                request,
                destination,
                exact_closure=exact_closure,
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


def _inspection_view(report: RootModel[dict[str, JsonValue]], subject: str) -> Table:
    body = report.root
    fields: list[tuple[str, object]] = [
        ("Verified review", subject),
        ("Coverage", body["completeness"]),
        ("Source completeness", body["original_source_completeness"]),
        ("Assessment scope", body["assessment_scope"]),
    ]
    selections = body["selection"]
    selected_bindings = body["selected_bindings"]
    cuts = (
        {
            (binding.get("kind"), binding.get("index")): binding.get("cut_id")
            for binding in selected_bindings
            if isinstance(binding, dict)
        }
        if isinstance(selected_bindings, list)
        else {}
    )
    if isinstance(selections, dict):
        visible = []
        total = 0
        for kind, key in (
            ("Contribution", "selections"),
            ("Structural", "structural_selections"),
        ):
            requests = selections.get(key)
            if not isinstance(requests, list):
                continue
            total += len(requests)
            for index, request in enumerate(requests[: 8 - len(visible)]):
                if isinstance(request, dict):
                    item = f"{kind} · Run {request['run_id']}"
                    if (cut := cuts.get((kind.lower(), index))) is not None:
                        item += f" · Cut {cut}"
                    elif (cut := request.get("cut_id")) is not None:
                        item += f" · Requested cut {cut}"
                    if (task := request.get("selected_task_id")) is not None:
                        item += f" · Task {task}"
                    visible.append(item)
        if total > len(visible):
            visible.append(f"… {total - len(visible)} more selections")
        fields.append(("Selection", "\n".join(visible)))
    relations = body["relations"]
    if isinstance(relations, dict):
        for label, name in (
            ("Witness rows", "structural_public_assertions"),
            ("Evaluator authority rows", "assessment_authority"),
            ("Assessment history rows", "assessment_history"),
            ("Omission rows", "omissions"),
        ):
            fields.append((label, relations.get(name, "none retained")))
        names = sorted(relations)
        visible = [f"{name}: {relations[name]}" for name in names[:12]]
        if len(names) > len(visible):
            visible.append(f"… {len(names) - len(visible)} more relations")
        fields.append(("Relation rows", "\n".join(visible) or "none retained"))
    return report_fields(*fields)


@app.command("inspect")
def inspect_review(
    ctx: typer.Context,
    bundle: Annotated[Path | None, typer.Argument()] = None,
    result_id: Annotated[str | None, typer.Option("--result", metavar="RESULT_ID")] = None,
    json: JsonOpt = False,
):
    """Verify a detached bundle or managed result and summarize its coverage."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.serve.review_bundle import inspect_review_bundle

    if (bundle is None) == (result_id is None):
        raise typer.BadParameter("supply a detached bundle path or --result, exactly one")
    with failure_boundary(json, expected=(OSError, ValueError, ResultError)):
        if bundle is not None:
            report = inspect_review_bundle(bundle)
            subject = str(bundle)
        else:
            assert result_id is not None
            store = result_store(ctx)
            with store.lease(result_id):
                manifest = store.show(result_id)
                if manifest.action not in {"review.export", "review.export-evaluated"}:
                    raise ResultError("result is not a managed review export")
                if manifest.outcome != "passed" or manifest.details.get("custody_unsettled"):
                    raise ResultError("a successful, settled review export is required")
                digest = manifest.details.get("bundle_manifest_sha256")
                if not isinstance(digest, str):
                    raise ResultError(
                        "review result has no bound bundle digest; export the selection again "
                        "or verify an intentional detached copy"
                    )
                with store.open_artifact(result_id, "bundle") as (_, descriptor):
                    report = {
                        "result_id": result_id,
                        **inspect_review_bundle(descriptor, manifest_digest=digest),
                    }
            subject = result_id

    emit(
        RootModel[dict[str, JsonValue]].model_validate(report),
        json=json,
        render=lambda value: _inspection_view(value, subject),
    )


def register(root: typer.Typer):
    root.add_typer(app, name="review")
