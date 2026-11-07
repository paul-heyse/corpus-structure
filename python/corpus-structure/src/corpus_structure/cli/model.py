"""Canonical model previews and explicit, target-bound change effects."""

from __future__ import annotations

import re
from hashlib import sha256
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

import typer
from pydantic import BaseModel, JsonValue
from rich.console import Group
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.output import (
    JsonOpt,
    diagnostic,
    emit,
    read_request_bytes,
    report_fields,
    safe_text,
    state,
    write_report_bytes,
    write_report_text,
)
from corpus_structure.cli.schema import model_stage, refusal
from corpus_structure.semantic.storage_target import StorageTarget
from corpus_structure.settings import DeploymentProfile

if TYPE_CHECKING:
    from corpus_structure.schema.model_change import ChangePreview

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


class EffectGuidance(BaseModel):
    next_command: str | None = None
    action_detail: str | None = None
    action_conditions: tuple[str, ...] = ()


class PreviewEffectsReport(EffectGuidance):
    preview_id: str
    revision: str
    baseline: str
    head: str
    workspace: str
    target: str | None
    target_profile: DeploymentProfile | None
    acquired_target: StorageTarget | None
    authoring_target: StorageTarget | None
    predecessor: str | None
    release: str | None
    changed_paths: tuple[str, ...]
    effects: dict[str, JsonValue]
    comparison_status: Literal["available", "unavailable", "not_applicable"]
    comparison: dict[str, JsonValue] | None
    discovery_status: Literal["available", "unavailable"]
    dependency_available: bool


class PreviewDiscoveryReport(BaseModel):
    preview_id: str
    status: Literal["available", "unavailable"]
    discovery: dict[str, JsonValue] | None


class PatchHunk(BaseModel):
    ordinal: int
    path: str
    patch_line: int
    excerpt: str
    truncated: bool


class PreviewPatchReport(BaseModel):
    preview_id: str
    target: str | None
    target_profile: DeploymentProfile | None
    acquired_target: StorageTarget | None
    changed_paths: tuple[str, ...]
    total_hunks: int
    hunks: list[PatchHunk]
    next_after_hunk: int | None


class CandidateInspection(EffectGuidance):
    candidate_id: str
    preview_id: str | None
    workspace: str
    model_revision: str
    native_revision: str | None
    predecessor: str | None
    release: str
    target: str
    target_profile: DeploymentProfile
    acquired_target: StorageTarget | None
    authoring_target: StorageTarget | None
    registration: Literal["verified", "unverified", "not_applicable"]
    registration_detail: str | None
    dependency_available: bool


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
            write_report_text(report, exit_code=done.returncode)
        else:
            emit(
                CheckResult(exit_code=done.returncode, report=report),
                json=json_,
                exit_code=done.returncode,
            )
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


_HUNK = re.compile(r"@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@[^\n]*\n")
_NO_FINAL_NEWLINE = "\\ No newline at end of file\n"
_PATCH_STREAM_LIMIT = 8 * 1024 * 1024
_HUNK_LINES = 40
_HUNK_CHARS = 3000


def _patch_hunks(
    patch: str, paths: tuple[str, ...], after: int, limit: int
) -> tuple[int, list[PatchHunk]]:
    from corpus_structure.cli.managed import ResultError

    hunks: list[PatchHunk] = []
    total = 0
    path = None
    bound_paths = iter(paths)
    lines = iter(enumerate(StringIO(patch), 1))
    for patch_line, line in lines:
        if line == _NO_FINAL_NEWLINE:
            continue
        if line.startswith("--- "):
            path = next(bound_paths, None)
            if (
                path is None
                or line not in (f"--- a/{path}\n", "--- /dev/null\n")
                or next(lines, (0, ""))[1] != f"+++ b/{path}\n"
            ):
                raise ResultError("patch headers differ from the bound changed paths")
            continue
        header = _HUNK.fullmatch(line)
        if header is None or path is None:
            raise ResultError("patch hunk is missing its bound file or has an invalid header")
        total += 1
        selected = after < total <= after + limit
        old, new = (int(count) if count is not None else 1 for count in header.groups())
        excerpt = safe_text(line) if selected else ""
        line_count = 0
        truncated = len(excerpt) > _HUNK_CHARS
        excerpt = excerpt[:_HUNK_CHARS]
        while old or new:
            _, body = next(lines, (0, ""))
            if body == _NO_FINAL_NEWLINE:
                continue
            if not body:
                # Older producers could leave the final changed line unterminated.
                truncated = True
                break
            kind = body[:1]
            if kind not in {" ", "+", "-"}:
                raise ResultError("patch hunk body differs from its declared range")
            old -= kind != "+"
            new -= kind != "-"
            if min(old, new) < 0:
                raise ResultError("patch hunk body differs from its declared range")
            if selected and line_count < _HUNK_LINES and not truncated:
                rendered = safe_text(body)
                remaining = _HUNK_CHARS - len(excerpt)
                excerpt += rendered[:remaining]
                truncated = len(rendered) > remaining
            line_count += 1
        if selected:
            hunks.append(
                PatchHunk(
                    ordinal=total,
                    path=path,
                    patch_line=patch_line,
                    excerpt=excerpt,
                    truncated=truncated or line_count > _HUNK_LINES,
                )
            )
    if next(bound_paths, None) is not None:
        raise ResultError("patch does not contain every bound changed path")
    return total, hunks


def _path_summary(paths: tuple[str, ...]) -> str:
    listed = "\n".join(paths[:8])
    if len(paths) > 8:
        return f"{listed}\n… {len(paths) - 8} more"
    return listed or "none"


def _target_summary(profile: DeploymentProfile | None, target: StorageTarget | None) -> str:
    if target is not None:
        return (
            f"{profile or 'bound'} · {target.database} at "
            f"{target.host}:{target.port} ({target.purpose})"
        )
    return f"{profile} · acquired identity unavailable" if profile else "unbound"


def _guidance_fields(guidance: EffectGuidance) -> tuple[tuple[str, object], ...]:
    fields: list[tuple[str, object]] = [
        ("Review before", guidance.next_command or "no effect command proposed")
    ]
    if guidance.action_detail:
        fields.append(("Action detail", guidance.action_detail))
    if guidance.action_conditions:
        fields.append(("Still required", "\n".join(guidance.action_conditions)))
    return tuple(fields)


def _preview_guidance(
    ctx: typer.Context, staged: ChangePreview, preview_id: str, dependency_available: bool
) -> EffectGuidance:
    from corpus_structure.cli.recipes import RecipeError, checkout
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_change import check_preview

    if not dependency_available:
        return EffectGuidance(action_detail="the managed preview is unavailable as a dependency")
    if not staged.files and not staged.effects.admission:
        return EffectGuidance()
    try:
        root = checkout(ctx)
        if staged.effects.admission:
            try:
                check_preview(root, staged, applied=True)
            except ModelError:
                if not staged.files:
                    raise
            else:
                if not staged.target or not staged.target_profile or staged.target_identity is None:
                    return EffectGuidance(
                        action_detail="the candidate requires an exact target binding"
                    )
                conditions = ["verify the prepared release identity"]
                if staged.effects.native:
                    conditions.append("verify the bound development target and native predecessor")
                return EffectGuidance(
                    next_command=f"ci model change candidate {preview_id}",
                    action_conditions=tuple(conditions),
                )
        check_preview(root, staged)
        if staged.request.native_predecessor and (
            not staged.authoring_target or staged.authoring_identity is None
        ):
            return EffectGuidance(action_detail="the native authoring target is unavailable")
        conditions = (
            ("verify the bound development target and native predecessor",)
            if staged.request.native_predecessor
            else ()
        )
        return EffectGuidance(
            next_command=f"ci model change apply {preview_id}",
            action_conditions=conditions,
        )
    except (ModelError, OSError, RecipeError) as error:
        return EffectGuidance(action_detail=safe_text(str(error)))


def _effects_view(report: PreviewEffectsReport) -> Table:
    changes = (report.comparison or {}).get("changes")
    impact = report.comparison_status
    if isinstance(changes, list):
        visible = [
            f"{item.get('kind', 'change')} {item.get('model_ref', '')}"
            for item in changes[:8]
            if isinstance(item, dict)
        ]
        impact = "\n".join((f"{len(changes)} declared changes", *visible))
    routes = report.effects.get("routes")
    route_summary = (
        "\n".join(f"{kind} → {route}" for kind, route in list(routes.items())[:8])
        if isinstance(routes, dict)
        else ""
    )
    return report_fields(
        ("Preview", report.preview_id),
        ("Revision", report.revision),
        ("Target", _target_summary(report.target_profile, report.acquired_target)),
        ("Target fingerprint", report.target or "unbound"),
        ("Authoring target", _target_summary(None, report.authoring_target)),
        ("Predecessor", report.predecessor or "not applicable"),
        ("Release", report.release or "unavailable"),
        ("Changed paths", _path_summary(report.changed_paths)),
        ("Native authoring", "required" if report.effects["native"] else "not required"),
        ("Release admission", "planned" if report.effects["admission"] else "not planned"),
        ("Compatibility routes", route_summary or "none declared"),
        ("Semantic comparison", impact),
        ("Discovery", report.discovery_status),
        ("Dependency", "available" if report.dependency_available else "unavailable"),
        *_guidance_fields(report),
    )


def _patch_view(report: PreviewPatchReport) -> Group:
    summary = report_fields(
        ("Preview", report.preview_id),
        ("Target", _target_summary(report.target_profile, report.acquired_target)),
        ("Target fingerprint", report.target or "unbound"),
        ("Changed paths", _path_summary(report.changed_paths)),
        ("Selected hunks", f"{len(report.hunks)} of {report.total_hunks}"),
        (
            "Next page",
            f"--after-hunk {report.next_after_hunk}"
            if report.next_after_hunk is not None
            else "none",
        ),
    )
    parts: list[Table | Text | Syntax] = [summary]
    for hunk in report.hunks:
        suffix = " (excerpt truncated)" if hunk.truncated else ""
        parts.append(Text(safe_text(f"Hunk {hunk.ordinal} · {hunk.path}{suffix}"), style="bold"))
        parts.append(
            Syntax(
                hunk.excerpt, "diff", line_numbers=True, start_line=hunk.patch_line, word_wrap=True
            )
        )
    return Group(*parts)


def _discovery_view(report: PreviewDiscoveryReport) -> Table:
    discovery = report.discovery
    if discovery is None:
        return report_fields(("Preview", report.preview_id), ("Discovery", report.status))
    hits = discovery.get("ast")
    selected = []
    if isinstance(hits, list):
        selected = [
            f"{item.get('name', '')} · {item.get('path', '')}:{item.get('line', '')}"
            for item in hits[:8]
            if isinstance(item, dict)
        ]
    coverage = discovery.get("semantic_coverage")
    return report_fields(
        ("Preview", report.preview_id),
        ("Discovery", report.status),
        ("Source head", discovery.get("head", "unavailable")),
        ("Unscanned files", discovery.get("unscanned_files", "unknown")),
        (
            "AST candidates",
            f"{len(selected)} displayed of {len(hits)} recorded"
            if isinstance(hits, list)
            else "unknown",
        ),
        ("Candidate examples", "\n".join(selected) or "none displayed"),
        ("AST-grep", discovery.get("ast_grep_status", "unknown")),
        (
            "Semantic coverage",
            coverage.get("status", "unknown") if isinstance(coverage, dict) else "unknown",
        ),
    )


@changes.command("inspect")
def inspect_preview(
    ctx: typer.Context,
    preview_id: Annotated[str, typer.Argument(metavar="PREVIEW_ID")],
    view: Annotated[Literal["effects", "patch", "discovery"], typer.Option()] = "effects",
    limit: Annotated[int | None, typer.Option(min=1, max=20, help="Maximum hunks.")] = None,
    after_hunk: Annotated[int, typer.Option(min=0, help="Continue after this hunk ordinal.")] = 0,
    stdout: Annotated[
        bool, typer.Option(help="Write the exact safe patch bytes to stdout.")
    ] = False,
    json_: JsonOpt = False,
) -> None:
    """Inspect a settled preview by ID without applying it."""
    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_change import ChangePreview

    if stdout and (view != "patch" or json_ or limit is not None or after_hunk):
        raise typer.BadParameter("--stdout requires --view patch without JSON or hunk selection")
    if view != "patch" and (limit is not None or after_hunk):
        raise typer.BadParameter("hunk selection requires --view patch")
    with refusal(json_, expected=(ResultError, ModelError, OSError)):
        store = result_store(ctx)
        with store.lease(preview_id):
            staged = ChangePreview.model_validate_json(
                _load_artifact(store, preview_id, "model.preview", "preview")
            )
            dependency_available = store.dependency_available(preview_id)
            if stdout:
                patch = staged.patch.encode("utf-8")
                if len(patch) > _PATCH_STREAM_LIMIT:
                    raise ResultError("patch exceeds the 8 MiB stream limit")
                if safe_text(staged.patch) != staged.patch:
                    raise ResultError(
                        "patch cannot be delivered unchanged; use the bounded patch view"
                    )
                write_report_bytes(patch)
                return
        paths = tuple(file.path for file in staged.files)
        if view == "patch":
            total, hunks = _patch_hunks(staged.patch, paths, after_hunk, limit or 8)
            emit(
                PreviewPatchReport(
                    preview_id=preview_id,
                    target=staged.target,
                    target_profile=staged.target_profile,
                    acquired_target=staged.target_identity,
                    changed_paths=paths,
                    total_hunks=total,
                    hunks=hunks,
                    next_after_hunk=hunks[-1].ordinal
                    if hunks and hunks[-1].ordinal < total
                    else None,
                ),
                json=json_,
                render=_patch_view,
            )
            return
        discovery_status: Literal["available", "unavailable"] = (
            "available" if staged.discovery is not None else "unavailable"
        )
        if view == "discovery":
            emit(
                PreviewDiscoveryReport(
                    preview_id=preview_id, status=discovery_status, discovery=staged.discovery
                ),
                json=json_,
                render=_discovery_view,
            )
            return
        emit(
            PreviewEffectsReport(
                preview_id=preview_id,
                revision=staged.revision,
                baseline=staged.baseline,
                head=staged.head,
                workspace=staged.workspace,
                target=staged.target,
                target_profile=staged.target_profile,
                acquired_target=staged.target_identity,
                authoring_target=staged.authoring_identity,
                predecessor=staged.request.native_predecessor,
                release=staged.local_release,
                changed_paths=paths,
                effects=staged.effects.model_dump(mode="json"),
                comparison_status="available"
                if staged.comparison is not None
                else "not_applicable"
                if staged.effects.release == "not_applicable"
                else "unavailable",
                comparison=staged.comparison,
                discovery_status=discovery_status,
                dependency_available=dependency_available,
                **_preview_guidance(ctx, staged, preview_id, dependency_available).model_dump(),
            ),
            json=json_,
            render=_effects_view,
        )


def _candidate_view(report: CandidateInspection) -> Table:
    return report_fields(
        ("Candidate", report.candidate_id),
        ("Preview", report.preview_id or "unavailable"),
        ("Target", _target_summary(report.target_profile, report.acquired_target)),
        ("Target fingerprint", report.target),
        ("Authoring target", _target_summary(None, report.authoring_target)),
        ("Release", report.release),
        ("Native revision", report.native_revision or "not applicable"),
        ("Predecessor", report.predecessor or "not applicable"),
        ("Registration", report.registration),
        ("Registration detail", report.registration_detail or "none"),
        ("Dependency", "available" if report.dependency_available else "unavailable"),
        *_guidance_fields(report),
    )


@changes.command("inspect-candidate")
def inspect_candidate(
    ctx: typer.Context,
    candidate_id: Annotated[str, typer.Argument(metavar="CANDIDATE_ID")],
    json_: JsonOpt = False,
) -> None:
    """Inspect a settled candidate and its registration in the bound checkout."""
    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.cli.recipes import RecipeError, checkout
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_deployment import (
        Candidate,
        MigrationNotRegistered,
        _verify_installed_revision,
        candidate_registration_files,
        check_candidate_files,
        migration_wrapper,
    )

    with refusal(json_, expected=(ResultError, OSError)):
        store = result_store(ctx)
        status: Literal["verified", "unverified", "not_applicable"] = "unverified"
        detail = None
        guidance = EffectGuidance()
        with store.lease(candidate_id):
            binding = Candidate.model_validate_json(
                _load_artifact(store, candidate_id, "model.candidate", "deployment")
            )
            scope = store.show(candidate_id).scope
            dependency_available = store.dependency_available(candidate_id)
            try:
                root = checkout(ctx)
                if str(root) != binding.workspace:
                    raise ModelError(["candidate is bound to a different checkout"])
                status = "not_applicable" if binding.revision is None else "unverified"
                try:
                    _verify_installed_revision(root, binding)
                except MigrationNotRegistered as error:
                    detail = safe_text(str(error))
                    if dependency_available:
                        if store.read_artifact(candidate_id, "wrapper") != migration_wrapper(
                            binding
                        ):
                            raise ModelError(
                                ["managed migration wrapper differs from the reviewed candidate"]
                            ) from None
                        with store.open_artifact(candidate_id, "candidate") as (_, descriptor):
                            candidate_registration_files(root, binding, descriptor)
                        guidance = EffectGuidance(
                            next_command=f"ci model change register {candidate_id}"
                        )
                else:
                    if binding.revision is not None:
                        status = "verified"
                    if dependency_available:
                        check_candidate_files(root, binding)
                        if binding.target_identity is None:
                            raise ModelError(
                                ["candidate lacks the approved acquired PostgreSQL target"]
                            )
                        guidance = EffectGuidance(
                            next_command=f"ci model change deploy {candidate_id}",
                            action_conditions=(
                                "verify the configured and acquired target",
                                "verify purpose roles and the applicable native predecessor",
                                "verify the prepared release identity",
                            ),
                        )
            except (ModelError, ResultError, OSError, RecipeError) as error:
                if status == "unverified":
                    detail = safe_text(str(error))
                guidance = EffectGuidance(action_detail=safe_text(str(error)))
            if not dependency_available:
                guidance = EffectGuidance(
                    action_detail="the managed candidate is unavailable as a dependency"
                )
        preview_id = scope.get("preview")
        emit(
            CandidateInspection(
                candidate_id=candidate_id,
                preview_id=preview_id if isinstance(preview_id, str) else None,
                workspace=binding.workspace,
                model_revision=binding.model_revision,
                native_revision=binding.revision,
                predecessor=binding.predecessor,
                release=binding.release,
                target=binding.target,
                target_profile=binding.target_profile,
                acquired_target=binding.target_identity,
                authoring_target=binding.authoring_identity,
                registration=status,
                registration_detail=detail,
                dependency_available=dependency_available,
                **guidance.model_dump(),
            ),
            json=json_,
            render=_candidate_view,
        )


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

    with refusal(json_, expected=(ModelError, ResultError, OSError, ValueError, yaml.YAMLError)):
        store = result_store(ctx)
        root = checkout(ctx)
        with store.operation("model.preview") as result:
            model_stage(result, "resolve request")
            if re.fullmatch(r"[a-f0-9]{32}", request) and not Path(request).is_file():
                with store.lease(request):
                    bound = ChangePreview.model_validate_json(
                        _load_artifact(store, request, "model.preview", "preview")
                    ).request
            else:
                raw = read_request_bytes(request)
                bound = ChangeRequest.model_validate(yaml.safe_load(raw.decode("utf-8")))
            target = None
            profile: DeploymentProfile = "development"
            authoring_target = None
            target_identity = None
            authoring_identity = None
            if bound.native_predecessor or bound.deployment:
                model_stage(result, "bind deployment target")
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
                model_stage(result, "compare archived release")
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
            model_stage(result, "validate and stage")
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

            model_stage(result, "verify exact preview")
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
                model_stage(result, "verify preview and prepare release")
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
                    model_stage(result, "rollback-only authoring")
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
                model_stage(result, "bind and publish candidate")
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
            model_stage(result, "verify and register frozen migration")
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
                model_stage(result, "prepare bound release")
                deployment = _prepare_release(root, binding.packs)
                applied: list[str] = []

                def report(effect: str) -> None:
                    applied.append(effect)
                    model_stage(result, effect, settled_effects=applied)

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
