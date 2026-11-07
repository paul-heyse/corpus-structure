"""Prepare and apply an exact, worktree-bound canonical model change."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from difflib import unified_diff
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from pydantic import BaseModel, ConfigDict

from corpus_structure.schema import change, model, preparation
from corpus_structure.schema.change import ChangeRecord
from corpus_structure.settings import DeploymentProfile


class ChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline: str = "HEAD"
    core: str | None = None
    system: str | None = None
    change: ChangeRecord | None = None
    archive_release: str | None = None
    packs: tuple[str, ...] = ()
    native_predecessor: str | None = None
    native_revision: str | None = None
    deployment: bool = False
    deployment_profile: DeploymentProfile | None = None


class FileEffect(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    before: str | None
    after: str


class ChangePreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace: str
    head: str
    baseline: str
    revision: str
    compilers: dict[str, str]
    python: str
    generator: str
    inputs: dict[str, str | None]
    files: tuple[FileEffect, ...]
    patch: str
    source_diff: str
    request: ChangeRequest
    target: str | None
    target_profile: DeploymentProfile | None = None
    authoring_target: str | None = None
    comparison: dict | None = None
    local_release: str | None = None
    discovery: dict | None = None


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ("git", "-C", str(root), *args), capture_output=True, timeout=30, check=False
    )
    if done.returncode:
        raise model.ModelError([f"git {' '.join(args[:1])} could not resolve the model input"])
    return done.stdout.decode()


def _ref(root: Path, name: str) -> str:
    return _git(root, "rev-parse", "--verify", "--end-of-options", f"{name}^{{commit}}").strip()


def checked_path(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.is_relative_to(root) or path.resolve() != path:
        raise model.ModelError([f"unsafe model path {relative}"])
    return path


def _read(root: Path, relative: str) -> str | None:
    path = checked_path(root, relative)
    return path.read_bytes().decode() if path.exists() else None


def generator_fingerprint(root: Path) -> str:
    digest = sha256()
    directory = root / preparation.PACKAGE_PATH / "schema"
    for path in sorted(directory.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _digest(content: str | None) -> str | None:
    return sha256(content.encode()).hexdigest() if content is not None else None


def _diff(path: str, before: str | None, after: str) -> str:
    return "".join(
        unified_diff(
            (before or "").splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}" if before is not None else "/dev/null",
            tofile=f"b/{path}",
        )
    )


def prepare_preview(
    root: Path,
    request: ChangeRequest,
    *,
    target: str | None = None,
    target_profile: DeploymentProfile = "development",
    authoring_target: str | None = None,
    comparison: dict | None = None,
    local_release: str | None = None,
) -> ChangePreview:
    root = root.resolve()
    baseline = _ref(root, request.baseline)
    head = _ref(root, "HEAD")
    core, system, log = (
        (preparation.MODEL_PATH / name).as_posix()
        for name in ("core.yaml", "system.yaml", "revisions.yaml")
    )
    original = {path: _git(root, "show", f"{baseline}:{path}") for path in (core, system, log)}
    current = {path: _read(root, path) for path in original}
    if current[log] != original[log]:
        raise model.ModelError(["worktree revision log differs from the requested baseline"])
    source = {
        core: request.core if request.core is not None else current[core],
        system: request.system if request.system is not None else current[system],
    }
    if any(value is None for value in source.values()):
        raise model.ModelError(["both canonical declarations are required"])
    with TemporaryDirectory(prefix="cs-model-preview-") as directory:
        before, after = Path(directory) / "before", Path(directory) / "after"
        before.mkdir()
        after.mkdir()
        for path in (core, system):
            name = Path(path).name
            (before / name).write_text(original[path], encoding="utf-8")
            content = source[path]
            assert content is not None
            (after / name).write_text(content, encoding="utf-8")
        (before / "revisions.yaml").write_text(original[log], encoding="utf-8")
        old = model.load(before / "core.yaml", before / "system.yaml")
        new = model.load(after / "core.yaml", after / "system.yaml")
        revision = model.revision(new)
        changed = change.diff(old, new)
        native = request.native_predecessor
        if bool(native or request.deployment) != bool(target):
            raise model.ModelError(["a deployment preview requires a configured target binding"])
        if request.deployment_profile and (
            not target or request.deployment_profile != target_profile
        ):
            raise model.ModelError(["deployment profile differs from the requested target"])
        if bool(native) != bool(authoring_target):
            raise model.ModelError(["a native preview requires its development authoring target"])
        migration = request.change.alembic_revision if request.change else None
        if request.native_revision and migration and migration != request.native_revision:
            raise model.ModelError(["native revision conflicts with the declared model change"])
        if bool(native) != bool(migration or request.native_revision):
            raise model.ModelError(
                ["a native change requires an exact predecessor and Alembic revision"]
            )
        if model.revision(old).content_hash == revision.content_hash and request.change is None:
            problems = model.check(new) + model.check_log(
                revision, model.read_log(before / "revisions.yaml")
            )
            if problems:
                raise model.ModelError(problems)
            generated: dict[str, str] = {}
        else:
            generated = preparation.prepare(
                new, model.read_log(before / "revisions.yaml"), before=old, record=request.change
            )
    staged = {path: content for path, content in source.items() if content is not None} | generated
    prior = {path: _read(root, path) for path in staged}
    files = tuple(
        FileEffect(path=path, before=_digest(prior[path]), after=content)
        for path, content in staged.items()
        if prior[path] != content
    )
    if any(_read(root, path) != content for path, content in current.items()):
        raise model.ModelError(["canonical inputs changed during preview"])
    from corpus_structure.schema.model_discovery import locate_consumers

    identifiers = {
        name
        for item in changed
        for name in item.element.split(":")[-1].replace("#", ".").split(".")
        if name.isidentifier()
    }
    return ChangePreview(
        workspace=str(root),
        head=head,
        baseline=baseline,
        revision=revision.content_hash,
        compilers=dict(revision.compilers),
        python=sys.version,
        generator=generator_fingerprint(root),
        inputs={path: _digest(content) for path, content in current.items()},
        files=files,
        patch="".join(_diff(file.path, prior[file.path], file.after) for file in files),
        source_diff="".join(
            _diff(path, original[path], content)
            for path, content in source.items()
            if content is not None and content != original[path]
        ),
        request=request,
        target=target,
        target_profile=target_profile if target else None,
        authoring_target=authoring_target,
        comparison=comparison,
        local_release=local_release,
        discovery=locate_consumers(root, head, identifiers) if identifiers else None,
    )


def check_preview(root: Path, preview: ChangePreview, *, applied: bool = False) -> None:
    """Check every affected file before writes, accepting only exact prior/settled bytes."""
    if str(root) != preview.workspace:
        raise model.ModelError(["preview belongs to another workspace"])
    if not applied and _ref(root, "HEAD") != preview.head:
        raise model.ModelError(["worktree HEAD changed after preview"])
    if (
        model.compilers() != preview.compilers
        or sys.version != preview.python
        or generator_fingerprint(root) != preview.generator
    ):
        raise model.ModelError(["model toolchain changed after preview"])
    effects = {file.path: file for file in preview.files}
    for path, before in preview.inputs.items():
        if path not in effects and _digest(_read(root, path)) != before:
            raise model.ModelError([f"stale model input {path}"])
    for effect in preview.files:
        actual = _digest(_read(root, effect.path))
        if actual != _digest(effect.after) and (applied or actual != effect.before):
            raise model.ModelError([f"stale model input {effect.path}"])


def apply_preview(
    root: Path,
    preview: ChangePreview,
    *,
    native_fence: AbstractContextManager[None] | None = None,
    report: Callable[[str], None] | None = None,
) -> list[str]:
    """Apply only the approved files. Exact after-bytes make interrupted work retryable."""
    root = root.resolve()
    settled: list[str] = []
    with preparation.writer_lock(root):
        check_preview(root, preview)
        if preview.request.native_predecessor and native_fence is None:
            raise model.ModelError(["native predecessor has not been checked"])
        with native_fence or nullcontext():
            for effect in preview.files:
                actual = _digest(_read(root, effect.path))
                if actual != _digest(effect.after):
                    if actual != effect.before:
                        raise model.ModelError([f"concurrent edit to {effect.path}"])
                    path = checked_path(root, effect.path)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
                    with NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
                        staged = Path(temporary.name)
                        try:
                            temporary.write(effect.after.encode())
                            temporary.flush()
                            os.fchmod(temporary.fileno(), mode)
                            if _digest(_read(root, effect.path)) != effect.before:
                                raise model.ModelError([f"concurrent edit to {effect.path}"])
                            os.replace(staged, path)
                        finally:
                            staged.unlink(missing_ok=True)
                settled.append(effect.path)
                if report is not None:
                    report(effect.path)
    return settled
