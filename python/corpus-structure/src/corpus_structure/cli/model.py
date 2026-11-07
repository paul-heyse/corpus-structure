"""Canonical model previews and explicit, target-bound change effects."""

from __future__ import annotations

import sys
from hashlib import sha256
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from corpus_structure.cli.output import JsonOpt, diagnostic, emit, safe_text, state
from corpus_structure.cli.schema import refusal
from corpus_structure.semantic.storage_target import StorageTarget
from corpus_structure.settings import DeploymentProfile

app = typer.Typer(help="Check the model and prepare canonical changes.")
changes = typer.Typer(help="Preview, apply and deploy exact model changes.")


class ModelResult(BaseModel):
    result_id: str
    stage: str
    revision: str
    changed: tuple[str, ...] = ()
    predecessor: str | None = None
    release: str | None = None
    target_profile: DeploymentProfile | None = None
    acquired_target: StorageTarget | None = None


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
        report = safe_text(done.stdout)
        if not json_ and report:
            typer.echo(report, nl=False)
        else:
            emit(CheckResult(exit_code=done.returncode, report=report), json=json_)
        if done.returncode:
            raise typer.Exit(done.returncode)


def _load_artifact(store, result_id: str, action: str, role: str) -> bytes:
    from corpus_structure.cli.managed import ResultError

    manifest = store.show(result_id)
    if manifest.action != action or manifest.outcome != "passed":
        raise ResultError(f"{result_id} is not a successful {action} result")
    raw = store.read_artifact(result_id, role)
    if sha256(raw).hexdigest() != manifest.details.get("sha256"):
        raise ResultError("result artifact no longer matches its settled digest")
    return raw


def _prepare_release(root, names, *, physical_sources: dict[str, bytes] | None = None):
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_change import physical_release_sources
    from corpus_structure.semantic.contracts import trusted_execution_inputs
    from corpus_structure.semantic.regeneration import prepare_packs

    if not names or any(
        not name or name in {".", ".."} or Path(name).name != name for name in names
    ):
        raise ModelError(["select one or more declared domain pack names"])
    sources = physical_release_sources(root) if physical_sources is None else physical_sources
    execution = trusted_execution_inputs(physical_sources=sources) if sources is not None else None
    return prepare_packs(tuple(root / "domains" / name for name in names), execution=execution)


@changes.command("preview")
def preview(
    ctx: typer.Context,
    request: Annotated[
        str, typer.Argument(help="A change request file, '-' for stdin, or a managed ID.")
    ],
    json_: JsonOpt = False,
) -> None:
    """Validate and stage an inspectable patch without changing tracked or native state."""
    import re

    import yaml

    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.cli.recipes import checkout
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_change import (
        ChangePreview,
        ChangeRequest,
        physical_release_sources,
        prepare_preview,
    )
    from corpus_structure.schema.model_deployment import (
        capture_target,
        deployment_settings,
        target_fingerprint,
        verify_predecessor,
    )

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
                raw = (
                    sys.stdin.read()
                    if request == "-"
                    else Path(request).read_text(encoding="utf-8")
                )
                bound = ChangeRequest.model_validate(yaml.safe_load(raw))
            target = None
            profile: DeploymentProfile = "development"
            authoring_target = None
            target_identity = None
            authoring_identity = None
            if bound.native_predecessor or bound.deployment:
                settings = state(ctx).settings()
                profile, destination = deployment_settings(settings, bound.deployment_profile)
                target = target_fingerprint(destination)
                if bound.native_predecessor:
                    authoring_target = target_fingerprint(settings)
                    authoring_identity = verify_predecessor(
                        settings, authoring_target, bound.native_predecessor
                    )
                target_identity = (
                    authoring_identity
                    if profile == "development" and authoring_identity is not None
                    else capture_target(destination, purpose="maintenance")
                )
            impact = None
            local = None
            release = None
            physical_id = None
            if bound.archive_release or target is not None:
                from corpus_structure.semantic.metadata import physical_sources_id

                physical_sources = physical_release_sources(root, bound.physical)
                if physical_sources is not None:
                    physical_id = physical_sources_id(physical_sources)
                _, _, _, local = _prepare_release(
                    root, bound.packs, physical_sources=physical_sources
                )
                release = local.release_id
            if bound.archive_release:
                from corpus_structure.semantic.operation_reporting import compare_semantic_releases
                from corpus_structure.semantic.query import read_snapshot
                from corpus_structure.semantic.releases import open_release
                from corpus_structure.semantic.runtime import open_runtime_engine

                assert local is not None
                with (
                    open_runtime_engine(
                        state(ctx).settings(), "ci-model-compare", purpose="read"
                    ) as engine,
                    read_snapshot(engine) as connection,
                ):
                    before = open_release(connection, bound.archive_release)
                    impact = compare_semantic_releases(before, local).model_dump(mode="json")
            result.stage("validate and stage")
            staged = prepare_preview(
                root,
                bound,
                target=target,
                target_profile=profile,
                authoring_target=authoring_target,
                target_identity=target_identity,
                authoring_identity=authoring_identity,
                comparison=impact,
                local_release=release,
                expected_physical=physical_id,
                release_manifest_sha256=sha256(local.manifest).hexdigest()
                if local is not None
                else None,
            )
            artifact = result.directory / "preview.json"
            artifact.write_text(staged.model_dump_json(), encoding="utf-8")
            patch = result.directory / "model.patch"
            patch.write_text(staged.patch, encoding="utf-8")
            result.publish("preview", artifact)
            result.publish("patch", patch)
            result.settle(
                sha256=sha256(artifact.read_bytes()).hexdigest(), revision=staged.revision
            )
        emit(
            ModelResult(
                result_id=result.id,
                stage="preview",
                revision=staged.revision,
                changed=tuple(file.path for file in staged.files),
                predecessor=bound.native_predecessor,
                release=release,
                target_profile=staged.target_profile,
                acquired_target=staged.target_identity,
            ),
            json=json_,
        )


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
        with store.recovery_operation("model.apply", change, source_role="preview") as result:
            staged = ChangePreview.model_validate_json(
                _load_artifact(store, change, "model.preview", "preview")
            )

            native = None
            if staged.effects.native:
                if (
                    not staged.authoring_target
                    or staged.authoring_identity is None
                    or not staged.request.native_predecessor
                ):
                    raise ModelError(["preview lacks the bound development authoring target"])
                native = predecessor_fence(
                    state(ctx).settings(),
                    staged.authoring_target,
                    staged.request.native_predecessor,
                    staged.authoring_identity,
                )

            settled: list[str] = []

            def report(path: str) -> None:
                settled.append(path)
                result.stage(f"applied {path}", settled_paths=settled)

            result.stage("verify exact preview")
            try:
                apply_preview(checkout(ctx), staged, native_fence=native, report=report)
            except BaseException as error:
                outcome = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
                details = (
                    {"next_action": f"ci model change apply {change}"}
                    if outcome == "interrupted"
                    else {}
                )
                result.settle(
                    outcome, settled_paths=settled, error_type=type(error).__name__, **details
                )
                raise
            result.settle(settled_paths=settled, revision=staged.revision)
        emit(
            ModelResult(
                result_id=result.id,
                stage="applied",
                revision=staged.revision,
                changed=tuple(settled),
                predecessor=staged.request.native_predecessor,
            ),
            json=json_,
        )


@changes.command("candidate")
def candidate(ctx: typer.Context, change: str, json_: JsonOpt = False) -> None:
    """Author a rollback-only candidate for an applied preview on its bound database."""
    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.cli.recipes import checkout
    from corpus_structure.cli.schema import author_native_candidate, publish_native_candidate
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_change import (
        ChangePreview,
        approved_physical_metadata,
        check_preview,
        native_intent,
    )
    from corpus_structure.schema.model_deployment import (
        Candidate,
        migration_wrapper,
        target_fingerprint,
    )
    from corpus_structure.schema.preparation import writer_lock
    from corpus_structure.semantic.native_objects import NativeAuthoringError
    from corpus_structure.semantic.prepared_sql import SQLSyntaxError

    with refusal(
        json_, expected=(ModelError, ResultError, NativeAuthoringError, SQLSyntaxError, OSError)
    ):
        root = checkout(ctx)
        store = result_store(ctx)
        with (
            store.lease(change),
            store.operation("model.candidate", scope={"preview": change}) as result,
        ):
            staged = ChangePreview.model_validate_json(
                _load_artifact(store, change, "model.preview", "preview")
            )
            record = staged.request.change
            revision = staged.request.native_revision or (
                record.alembic_revision if record else None
            )
            if (
                not staged.effects.admission
                or not staged.target
                or not staged.target_profile
                or staged.target_identity is None
            ):
                raise ModelError(["preview does not authorize a target-bound candidate"])
            with writer_lock(root):
                check_preview(root, staged, applied=True)
                _, _, _, prepared = _prepare_release(root, staged.request.packs)
                if (
                    prepared.release_id != staged.local_release
                    or sha256(prepared.manifest).hexdigest() != staged.release_manifest_sha256
                ):
                    raise ModelError(
                        ["prepared release identity differs from the reviewed preview"]
                    )
                products: dict[str, bytes] = {}
                if staged.effects.native:
                    settings = state(ctx).settings()
                    if (
                        staged.authoring_identity is None
                        or target_fingerprint(settings) != staged.authoring_target
                    ):
                        raise ModelError(["development authoring target differs from the preview"])
                    retired, recreated = native_intent(
                        staged.request.retire, staged.request.recreate
                    )
                    result.stage("rollback-only authoring")
                    native, products = author_native_candidate(
                        settings,
                        None,
                        None,
                        expected_predecessor=staged.request.native_predecessor,
                        expected_target=staged.authoring_identity,
                        target_metadata=approved_physical_metadata(root, staged),
                        retire=retired,
                        recreate=recreated,
                    )
                    report = publish_native_candidate(result, native, products)
                else:
                    report = ModelResult(
                        result_id=result.id,
                        stage="release candidate",
                        revision=staged.revision,
                        release=prepared.release_id,
                        target_profile=staged.target_profile,
                    )
                binding = Candidate.from_preview(staged, revision, prepared.release_id, products)
                if revision:
                    wrapper = result.directory / "migration.py"
                    wrapper.write_bytes(migration_wrapper(binding))
                    result.publish("wrapper", wrapper)
            artifact = result.directory / "deployment.json"
            artifact.write_text(binding.model_dump_json(), encoding="utf-8")
            result.publish("deployment", artifact)
            result.settle(
                sha256=sha256(artifact.read_bytes()).hexdigest(),
                target=binding.target,
                target_profile=binding.target_profile,
                authoring_target=binding.authoring_target,
                release=binding.release,
                predecessor=binding.predecessor,
            )
        emit(report, json=json_)


@changes.command("register")
def register_native(ctx: typer.Context, candidate: str, json_: JsonOpt = False) -> None:
    """Register the candidate's frozen Alembic revision in the selected checkout."""
    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.cli.recipes import checkout
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_deployment import (
        Candidate,
        migration_wrapper,
        register_candidate,
    )
    from corpus_structure.schema.preparation import writer_lock

    with refusal(json_, expected=(ModelError, ResultError, OSError)):
        store = result_store(ctx)
        with store.recovery_operation(
            "model.register", candidate, source_role="candidate"
        ) as result:
            binding = Candidate.model_validate_json(
                _load_artifact(store, candidate, "model.candidate", "deployment")
            )
            if store.read_artifact(candidate, "wrapper") != migration_wrapper(binding):
                raise ModelError(["managed migration wrapper differs from the reviewed candidate"])
            root = checkout(ctx)
            with (
                writer_lock(root),
                store.open_artifact(candidate, "candidate") as (_, directory_fd),
            ):
                paths = register_candidate(root, binding, directory_fd)
            store.hold(candidate, _registration_hold(candidate))
            result.settle(paths=paths, revision=binding.revision)
        emit(
            ModelResult(
                result_id=result.id,
                stage="registered",
                revision=binding.model_revision,
                predecessor=binding.predecessor,
                changed=paths,
            ),
            json=json_,
        )


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

    with refusal(
        json_,
        expected=(
            ModelError,
            ResultError,
            SQLAdmissionError,
            MigrationPredecessorError,
            PublicationConflict,
            OSError,
        ),
    ):
        store = result_store(ctx)
        with store.recovery_operation("model.deploy", candidate, source_role="candidate") as result:
            binding = Candidate.model_validate_json(
                _load_artifact(store, candidate, "model.candidate", "deployment")
            )
            root = checkout(ctx)
            with writer_lock(root):
                deployment = _prepare_release(root, binding.packs)
                applied: list[str] = []

                def report(effect: str) -> None:
                    applied.append(effect)
                    result.stage(effect, settled_effects=applied)

                try:
                    deploy_candidate(
                        root, state(ctx).settings(), binding, deployment, report=report
                    )
                except BaseException as error:
                    outcome = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
                    details = (
                        {"next_action": f"ci model change deploy {candidate}"}
                        if outcome == "interrupted"
                        else {}
                    )
                    result.settle(
                        outcome, settled_effects=applied, error_type=type(error).__name__, **details
                    )
                    raise
            store.release(candidate, _registration_hold(candidate))
            result.settle(settled_effects=applied, release=binding.release)
        emit(
            ModelResult(
                result_id=result.id,
                stage="deployed",
                revision=binding.model_revision,
                predecessor=binding.predecessor,
                release=binding.release,
                target_profile=binding.target_profile,
                acquired_target=binding.target_identity,
            ),
            json=json_,
        )


def _registration_hold(candidate: str) -> str:
    return sha256(f"registered:{candidate}".encode()).hexdigest()[:32]


def register(root: typer.Typer) -> None:
    app.add_typer(changes, name="change")
    root.add_typer(app, name="model")
