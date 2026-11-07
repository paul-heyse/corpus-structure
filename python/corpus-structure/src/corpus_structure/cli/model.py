"""Canonical model previews and explicit, target-bound change effects."""

from __future__ import annotations

import sys
from hashlib import sha256
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from corpus_structure.cli.output import JsonOpt, diagnostic, emit, state
from corpus_structure.cli.schema import refusal

app = typer.Typer(help="Check the model and prepare canonical changes.")
changes = typer.Typer(help="Preview, apply and deploy exact model changes.")


class ModelResult(BaseModel):
    result_id: str
    stage: str
    revision: str
    changed: tuple[str, ...] = ()
    predecessor: str | None = None
    release: str | None = None


class CheckResult(BaseModel):
    exit_code: int
    report: str


@app.command()
def check(json_: JsonOpt = False) -> None:
    """Check canonical declarations, generated output and revision log."""
    from corpus_structure.cli.recipes import RecipeError, run_recipe

    with refusal(json_, expected=(RecipeError, OSError)):
        done = run_recipe("model", "check")
        if done.stderr:
            diagnostic(done.stderr)
        if not json_ and done.stdout:
            typer.echo(done.stdout, nl=False)
        else:
            emit(CheckResult(exit_code=done.returncode, report=done.stdout), json=json_)
        if done.returncode:
            raise typer.Exit(done.returncode)


def _load_artifact(store, result_id: str, action: str, role: str) -> bytes:
    from corpus_structure.cli.managed import ResultError

    manifest = store.show(result_id)
    if manifest.action != action or manifest.outcome != "passed":
        raise ResultError(f"{result_id} is not a successful {action} result")
    raw = store.artifact(result_id, role).read_bytes()
    if sha256(raw).hexdigest() != manifest.details.get("sha256"):
        raise ResultError("result artifact no longer matches its settled digest")
    return raw


def _prepare_release(root, names):
    from corpus_structure.schema.model import ModelError
    from corpus_structure.semantic.regeneration import prepare_packs

    if not names or any(not name or name in {".", ".."} or Path(name).name != name for name in names):
        raise ModelError(["select one or more declared domain pack names"])
    return prepare_packs(tuple(root / "domains" / name for name in names))


@changes.command("preview")
def preview(
    ctx: typer.Context,
    request: Annotated[str, typer.Argument(help="A change request file, '-' for stdin, or a managed ID.")],
    json_: JsonOpt = False,
) -> None:
    """Validate and stage an inspectable patch without changing tracked or native state."""
    import re

    import yaml

    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.cli.recipes import checkout
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_change import ChangePreview, ChangeRequest, prepare_preview
    from corpus_structure.schema.model_deployment import target_fingerprint, verify_predecessor

    with refusal(json_, expected=(ModelError, ResultError, OSError, yaml.YAMLError)):
        store = result_store(ctx)
        root = checkout(ctx)
        with store.operation("model.preview") as result:
            result.stage("resolve request")
            if re.fullmatch(r"[a-f0-9]{32}", request) and not Path(request).is_file():
                with store.lease(request):
                    bound = ChangePreview.model_validate_json(
                        _load_artifact(store, request, "model.preview", "preview")
                    ).request
            else:
                raw = sys.stdin.read() if request == "-" else Path(request).read_text(encoding="utf-8")
                bound = ChangeRequest.model_validate(yaml.safe_load(raw))
            if bound.archive_release and (bound.core is not None or bound.system is not None):
                raise ModelError([
                    "compare an archived release against local pack inputs, "
                    "then stage declaration edits separately"
                ])
            target = None
            if bound.native_predecessor or bound.deployment:
                settings = state(ctx).settings()
                target = target_fingerprint(settings)
                if bound.native_predecessor:
                    verify_predecessor(settings, target, bound.native_predecessor)
            impact = None
            release = None
            if bound.archive_release:
                from corpus_structure.semantic.operation_reporting import compare_semantic_releases
                from corpus_structure.semantic.query import read_snapshot
                from corpus_structure.semantic.releases import open_release
                from corpus_structure.semantic.runtime import open_runtime_engine

                _, _, _, local = _prepare_release(root, bound.packs)
                with (
                    open_runtime_engine(state(ctx).settings(), "ci-model-compare", purpose="read") as engine,
                    read_snapshot(engine) as connection,
                ):
                    before = open_release(connection, bound.archive_release)
                    impact = compare_semantic_releases(before, local).model_dump(mode="json")
                release = local.release_id
            result.stage("validate and stage")
            staged = prepare_preview(root, bound, target=target, comparison=impact, local_release=release)
            artifact = result.directory / "preview.json"
            artifact.write_text(staged.model_dump_json(), encoding="utf-8")
            patch = result.directory / "model.patch"
            patch.write_text(staged.patch, encoding="utf-8")
            result.publish("preview", artifact)
            result.publish("patch", patch)
            result.settle(sha256=sha256(artifact.read_bytes()).hexdigest(), revision=staged.revision)
        emit(ModelResult(
            result_id=result.id, stage="preview", revision=staged.revision,
            changed=tuple(file.path for file in staged.files), predecessor=bound.native_predecessor,
            release=release,
        ), json=json_)


@changes.command("apply")
def apply(ctx: typer.Context, change: str, json_: JsonOpt = False) -> None:
    """Apply exactly the reviewed change; repeat with the same ID to resume."""
    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.cli.recipes import checkout
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_change import ChangePreview, apply_preview
    from corpus_structure.schema.model_deployment import predecessor_fence

    with refusal(json_, expected=(ModelError, ResultError, OSError)):
        store = result_store(ctx)
        with store.lease(change), store.operation("model.apply", scope={"preview": change}) as result:
            staged = ChangePreview.model_validate_json(
                _load_artifact(store, change, "model.preview", "preview")
            )

            native = None
            if staged.request.native_predecessor:
                assert staged.target
                native = predecessor_fence(
                    state(ctx).settings(), staged.target, staged.request.native_predecessor
                )

            settled: list[str] = []

            def report(path: str) -> None:
                settled.append(path)
                result.stage(f"applied {path}")

            result.stage("verify exact preview")
            try:
                apply_preview(checkout(ctx), staged, native_fence=native, report=report)
            except BaseException as error:
                outcome = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
                result.settle(outcome, settled_paths=settled, error_type=type(error).__name__)
                raise
            result.settle(settled_paths=settled, revision=staged.revision)
        emit(ModelResult(
            result_id=result.id, stage="applied", revision=staged.revision, changed=tuple(settled),
            predecessor=staged.request.native_predecessor,
        ), json=json_)


@changes.command("candidate")
def candidate(ctx: typer.Context, change: str, json_: JsonOpt = False) -> None:
    """Author a rollback-only candidate for an applied preview on its bound database."""
    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.cli.recipes import checkout
    from corpus_structure.cli.schema import author_native_candidate, publish_native_candidate
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_change import ChangePreview, check_preview
    from corpus_structure.schema.model_deployment import Candidate, target_fingerprint
    from corpus_structure.schema.preparation import writer_lock
    from corpus_structure.semantic.native_objects import NativeAuthoringError
    from corpus_structure.semantic.prepared_sql import SQLSyntaxError

    with refusal(json_, expected=(ModelError, ResultError, NativeAuthoringError, SQLSyntaxError, OSError)):
        root = checkout(ctx)
        store = result_store(ctx)
        settings = state(ctx).settings()
        with store.lease(change), store.operation("model.candidate", scope={"preview": change}) as result:
            staged = ChangePreview.model_validate_json(
                _load_artifact(store, change, "model.preview", "preview")
            )
            record = staged.request.change
            revision = staged.request.native_revision or (record.alembic_revision if record else None)
            if not staged.target:
                raise ModelError(["preview does not authorize a target-bound candidate"])
            if target_fingerprint(settings) != staged.target:
                raise ModelError(["native authoring target differs from the preview"])
            with writer_lock(root):
                check_preview(root, staged, applied=True)
                _, _, _, prepared = _prepare_release(root, staged.request.packs)
                products: dict[str, bytes] = {}
                if revision:
                    result.stage("rollback-only authoring")
                    native, products = author_native_candidate(
                        settings, None, None, expected_predecessor=staged.request.native_predecessor,
                    )
                    report = publish_native_candidate(result, native, products)
                else:
                    report = ModelResult(
                        result_id=result.id, stage="release candidate",
                        revision=staged.revision, release=prepared.release_id,
                    )
                binding = Candidate.from_preview(staged, revision, prepared.release_id, products)
            artifact = result.directory / "deployment.json"
            artifact.write_text(binding.model_dump_json(), encoding="utf-8")
            result.publish("deployment", artifact)
            result.settle(sha256=sha256(artifact.read_bytes()).hexdigest(), target=binding.target)
        emit(report, json=json_)


@changes.command("deploy")
def deploy(ctx: typer.Context, candidate: str, json_: JsonOpt = False) -> None:
    """Deploy a registered native candidate on its exact configured target."""
    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.cli.recipes import checkout
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_deployment import Candidate, deploy_candidate
    from corpus_structure.schema.preparation import writer_lock
    from corpus_structure.semantic.authored_sql import SQLAdmissionError
    from corpus_structure.semantic.migrations import MigrationPredecessorError
    from corpus_structure.semantic.publication import PublicationConflict

    with refusal(json_, expected=(ModelError, ResultError, SQLAdmissionError, MigrationPredecessorError,
                                   PublicationConflict, OSError)):
        store = result_store(ctx)
        with store.lease(candidate), store.operation("model.deploy", scope={"candidate": candidate}) as result:
            binding = Candidate.model_validate_json(
                _load_artifact(store, candidate, "model.candidate", "deployment")
            )
            root = checkout(ctx)
            with writer_lock(root):
                deployment = _prepare_release(root, binding.packs)
                applied: list[str] = []

                def report(effect: str) -> None:
                    applied.append(effect)
                    result.stage(effect)

                try:
                    deploy_candidate(root, state(ctx).settings(), binding, deployment, report=report)
                except BaseException as error:
                    outcome = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
                    result.settle(outcome, settled_effects=applied, error_type=type(error).__name__)
                    raise
            result.settle(settled_effects=applied, release=binding.release)
        emit(ModelResult(
            result_id=result.id, stage="deployed", revision=binding.model_revision,
            predecessor=binding.predecessor, release=binding.release,
        ), json=json_)


def register(root: typer.Typer) -> None:
    app.add_typer(changes, name="change")
    root.add_typer(app, name="model")
