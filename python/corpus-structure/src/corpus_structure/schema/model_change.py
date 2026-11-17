"""Prepare and apply an exact, worktree-bound canonical model change."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import asdict
from difflib import unified_diff
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.schema import change, model, preparation
from corpus_structure.schema.change import ChangeRecord
from corpus_structure.schema.data_steps import (
    DataStepRequest,
    FrozenDataStep,
    prepare_data_steps,
)
from corpus_structure.schema.physical import (
    PHYSICAL_ROOT,
    compile_physical,
    physical_source_closure,
    physical_sources_id,
)
from corpus_structure.schema.source_migrations import (
    SourceMigration,
    SourceMigrationPreview,
    check_source_migration,
    prepare_source_migration,
)
from corpus_structure.semantic.migration_chain import NativeMigrationBase
from corpus_structure.semantic.projection_analysis_products import ProjectionAnalysisComparison
from corpus_structure.semantic.source_comparison import EffectiveChangeComparison
from corpus_structure.semantic.storage_target import StorageTarget
from corpus_structure.semantic.types import PreparedRelease
from corpus_structure.settings import DeploymentProfile

if TYPE_CHECKING:
    from corpus_structure.semantic.data_operation_runtime import RuntimeBinding


_PHYSICAL_DIR = preparation.MODEL_PATH / "semantic"
_PHYSICAL = (_PHYSICAL_DIR / PHYSICAL_ROOT).as_posix()
_SOURCE_CALLS_OUTPUT = "semantic/_source_admission_calls.py"
_TYPED_COLUMNS_OUTPUT = "semantic/_typed_columns.py"


class NativeEffect(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, serialize_by_alias=True)

    kind: Literal["function", "view", "trigger"]
    schema_name: str = Field(alias="schema")
    name: str
    arguments: tuple[str, ...] = ()
    relation: str | None = None

    def identity(self):
        from corpus_structure.semantic.native_objects import NativeIdentity

        if (self.kind == "trigger") != bool(self.relation) or (
            self.kind != "function" and self.arguments
        ):
            raise model.ModelError(["native effect has inconsistent arguments or trigger relation"])
        if not self.schema_name or not self.name:
            raise model.ModelError(["native effect requires a schema and name"])
        return NativeIdentity.from_payload(self.model_dump(by_alias=True))


class NativeIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    retire: tuple[NativeEffect, ...] = ()
    recreate: tuple[NativeEffect, ...] = ()


class RuntimeCustody(BaseModel):
    """Exact reviewed runtime bytes; a logical profile establishes no execution outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_profile: str
    runtime_id: str
    manifest_sha256: str
    archive_sha256: str

    @classmethod
    def from_binding(cls, binding: RuntimeBinding) -> RuntimeCustody:
        return cls(
            execution_profile=json.loads(binding.manifest)["execution_profile"],
            runtime_id=binding.runtime_id,
            manifest_sha256=sha256(binding.manifest).hexdigest(),
            archive_sha256=sha256(binding.archive).hexdigest(),
        )

    def verify(self, binding: RuntimeBinding, prepared: PreparedRelease) -> None:
        from corpus_structure.semantic.data_operation_runtime import (
            RuntimeBindingError,
            validate_data_operation_runtime,
        )

        if (
            binding.release_id != prepared.release_id
            or binding.runtime_id != self.runtime_id
            or sha256(binding.manifest).hexdigest() != self.manifest_sha256
            or sha256(binding.archive).hexdigest() != self.archive_sha256
        ):
            raise model.ModelError(["runtime differs from exact reviewed custody"])
        try:
            validate_data_operation_runtime(binding, prepared)
        except RuntimeBindingError as error:
            raise model.ModelError(["reviewed runtime is invalid: " + str(error)]) from error
        if json.loads(binding.manifest)["execution_profile"] != self.execution_profile:
            raise model.ModelError(["runtime execution profile differs from reviewed selection"])


class ChangeRequest(NativeIntent):
    baseline: str = "HEAD"
    core: str | None = None
    system: str | None = None
    physical: str | None = None
    change: ChangeRecord | None = None
    archive_release: str | None = None
    packs: tuple[str, ...] = ()
    data_operations: str | None = None
    execution_profile: str | None = None
    native_predecessor: str | None = None
    native_revision: str | None = None
    deployment: bool = False
    deployment_profile: DeploymentProfile | None = None
    source_migrations: tuple[SourceMigration, ...] = ()
    data_steps: tuple[DataStepRequest, ...] = ()

    @model_validator(mode="after")
    def explicit_application_runtime(self):
        if self.data_steps and not self.native_requested:
            raise ValueError("revision data steps require explicit native authoring")
        if len({step.name for step in self.data_steps}) != len(self.data_steps):
            raise ValueError("duplicate revision data step")
        executable = bool(self.data_operations and (self.deployment or self.native_requested))
        if executable and (self.execution_profile is None or not self.execution_profile.strip()):
            raise ValueError("DDO application deployment requires an explicit execution_profile")
        if not executable and self.execution_profile is not None:
            raise ValueError("execution_profile requires an actual DDO application deployment")
        return self

    @property
    def declared_native_revision(self) -> str | None:
        return self.native_revision or (self.change.alembic_revision if self.change else None)

    @property
    def native_requested(self) -> bool:
        return self.native_predecessor is not None or self.declared_native_revision is not None


class FileEffect(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    before: str | None
    after: str


class ChangeEffects(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    compatibility: dict[str, tuple[str, ...]]
    routes: dict[str, str]
    generated: tuple[str, ...]
    physical: tuple[str, str] | None
    native: bool
    native_basis: tuple[str, ...]
    admission: bool
    admission_applicable: bool
    release: Literal["unchanged", "changed", "uncompared", "not_applicable"]
    checks: tuple[str, ...]


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
    target_identity: StorageTarget | None = None
    authoring_identity: StorageTarget | None = None
    native_base: NativeMigrationBase | None = None
    deployment_base: NativeMigrationBase | None = None
    effects: ChangeEffects
    comparison: dict | None = None
    local_release: str | None = None
    release_manifest_sha256: str | None = None
    release_artifacts_sha256: str | None = None
    runtime: RuntimeCustody | None = None
    discovery: dict | None = None
    source_migrations: tuple[SourceMigrationPreview, ...] = ()
    data_steps: tuple[FrozenDataStep, ...] = ()
    source_comparison: EffectiveChangeComparison | None = None
    query_analysis: ProjectionAnalysisComparison | None = None
    preparation_fingerprint: str | None = None
    inspection_sha256: str | None = None

    @model_validator(mode="after")
    def runtime_matches_application(self):
        if self.runtime is not None and (
            not self.effects.admission
            or not self.request.data_operations
            or self.request.execution_profile != self.runtime.execution_profile
        ):
            raise ValueError("runtime custody requires its reviewed DDO application/profile")
        return self

    def verify_runtime(self, binding: RuntimeBinding | None, prepared: PreparedRelease) -> None:
        if self.request.data_operations and self.effects.admission:
            if self.runtime is None or binding is None:
                raise model.ModelError(["application preview lacks exact reviewed runtime custody"])
            self.runtime.verify(binding, prepared)
        elif self.runtime is not None or binding is not None:
            raise model.ModelError(["preview has no DDO runtime admission intent"])

    @model_validator(mode="after")
    def query_analysis_matches_release_pair(self):
        if self.query_analysis is not None and (
            not self.request.data_operations
            or self.query_analysis.before_release != self.request.archive_release
            or self.query_analysis.after_release != self.local_release
        ):
            raise ValueError(
                "retained query analysis comparison differs from the preview release pair"
            )
        return self

    def verify_release(self, prepared: PreparedRelease) -> None:
        verify_release_products(
            prepared,
            release=self.local_release,
            manifest_sha256=self.release_manifest_sha256,
            artifacts_sha256=self.release_artifacts_sha256,
            binding="the reviewed preview",
        )


def verify_release_products(
    prepared: PreparedRelease,
    *,
    release: str | None,
    manifest_sha256: str | None,
    artifacts_sha256: str | None,
    binding: str,
) -> None:
    if not artifacts_sha256 or not manifest_sha256:
        raise model.ModelError(
            [f"{binding} lacks exact release product digests; prepare a fresh preview"]
        )
    if prepared.release_id != release or sha256(prepared.manifest).hexdigest() != manifest_sha256:
        raise model.ModelError([f"prepared release identity differs from {binding}"])
    if prepared.artifacts_sha256 != artifacts_sha256:
        raise model.ModelError([f"prepared release artifacts differ from {binding}"])


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


def compilation_fingerprint(
    root: Path,
    request: ChangeRequest,
    *,
    proposed: dict[str, bytes] | None = None,
    native_base: NativeMigrationBase | None = None,
    deployment_base: NativeMigrationBase | None = None,
) -> str:
    """Identify acquired compilation inputs, not compiled or admitted products.

    A fresh acquisition also detects changed input membership and optional additions.
    Generator-owned output paths are excluded from implementation hashing: their
    authored inputs and exact reviewed output bytes have separate owners.
    """
    from corpus_structure.schema.generate import generated_output_paths
    from corpus_structure.semantic.determinants import (
        ANALYSIS_LIBRARIES,
        BYTE_LIBRARIES,
        DEPLOYMENT_LIBRARIES,
        determinant_version,
    )
    from corpus_structure.semantic.identity import canonical_bytes

    physical = physical_release_sources(root, request.physical)
    acquired = None
    acquired_files = ()
    if request.data_operations:
        from corpus_structure.semantic.data_operation_preparation import (
            acquire_data_operation_inputs,
        )

        try:
            inputs = acquire_data_operation_inputs(root, request.data_operations, proposed=proposed)
        except ValueError as error:
            raise model.ModelError(
                [f"compilation inputs changed; prepare a fresh preview: {error}"]
            ) from error
        acquired = (inputs.bundle, inputs.dependencies, inputs.profile)
        acquired_files = tuple(
            (name, sha256(content).hexdigest()) for name, content in inputs.files
        )
    elif request.packs:
        from corpus_structure.semantic.regeneration import acquire_packs

        if any(
            not name or name in {".", ".."} or Path(name).name != name for name in request.packs
        ):
            raise model.ModelError(["select declared domain pack names"])
        acquired = acquire_packs(
            tuple(root / "domains" / name for name in request.packs), physical_sources=physical
        )
    input_facts = None
    if acquired is not None:
        bundle, dependencies, profile = acquired
        input_facts = {
            "root": bundle.root,
            "sources": sorted((item.name, item.digest) for item in bundle.sources),
            "dependencies": sorted((item.name, item.digest) for item in dependencies.artifacts),
            "vocabularies": [asdict(item) for item in dependencies.vocabularies],
            "ontology_sources": list(dependencies.ontology_sources),
            "profile": asdict(profile),
        }
    generated = generated_output_paths() | {_SOURCE_CALLS_OUTPUT, _TYPED_COLUMNS_OUTPUT}
    implementation = []
    selected_package = root / preparation.PACKAGE_PATH
    running_package = Path(__file__).resolve().parents[1]
    for label, directory in (("selected", selected_package), ("running", running_package)):
        paths = {
            path.relative_to(directory).as_posix(): path
            for path in directory.rglob("*")
            if path.is_file()
            and path.suffix in {".py", ".sql", ".yaml", ".json", ".lark", ".jinja", ".j2"}
            and "__pycache__" not in path.parts
        }
        if directory == selected_package and proposed:
            for name in proposed:
                path = root / name
                if path.is_relative_to(directory):
                    paths[path.relative_to(directory).as_posix()] = path
        for relative, path in sorted(paths.items()):
            if relative in generated or relative.startswith("model/"):
                continue
            selected_name = (preparation.PACKAGE_PATH / relative).as_posix()
            content = (
                proposed[selected_name]
                if directory == selected_package and proposed and selected_name in proposed
                else path.read_bytes()
            )
            implementation.append((label, relative, sha256(content).hexdigest()))
    # These are production compiler, Python-source extraction, projection-analysis
    # and native authoring dependencies, rather than unrelated environment tools.
    libraries = (
        set(BYTE_LIBRARIES)
        | set(ANALYSIS_LIBRARIES)
        | set(DEPLOYMENT_LIBRARIES)
        | {
            "ruff",
            "pyyaml",
            "networkx",
            "astroid",
            "griffe",
            "libcst",
            "ast-grep-py",
            "ty",
        }
    )
    facts = {
        "version": "model-compilation-inputs-v1",
        "request": request.model_dump(mode="json"),
        "native_base": native_base.model_dump(mode="json") if native_base is not None else None,
        "deployment_base": deployment_base.model_dump(mode="json")
        if deployment_base is not None
        else None,
        "canonical": {
            name: value
            if value is not None
            else _read(root, (preparation.MODEL_PATH / (name + ".yaml")).as_posix())
            for name, value in (("core", request.core), ("system", request.system))
        },
        "inputs": input_facts,
        "acquired_files": acquired_files,
        "physical": sorted(
            (name, sha256(value).hexdigest()) for name, value in (physical or {}).items()
        ),
        "implementation": implementation,
        "python": sys.version,
        "compilers": model.compilers(),
        "libraries": {name: determinant_version(name) for name in sorted(libraries)},
    }
    return sha256(canonical_bytes(facts)).hexdigest()


def _digest(content: str | None) -> str | None:
    return sha256(content.encode()).hexdigest() if content is not None else None


def _diff(path: str, before: str | None, after: str) -> str:
    lines = unified_diff(
        (before or "").splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}" if before is not None else "/dev/null",
        tofile=f"b/{path}",
    )
    return "".join(
        line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines
    )


def native_intent(retire: tuple[NativeEffect, ...], recreate: tuple[NativeEffect, ...]):
    removed = frozenset(item.identity() for item in retire)
    replaced = frozenset(item.identity() for item in recreate)
    if len(removed) != len(retire) or len(replaced) != len(recreate) or removed & replaced:
        raise model.ModelError(["native retirement and recreation must be unique and disjoint"])
    return removed, replaced


def _physical_closure(root: Path, content: str, *, baseline: str | None = None) -> dict[str, bytes]:
    def read(name: str) -> bytes | None:
        if name == PHYSICAL_ROOT:
            return content.encode()
        relative = (_PHYSICAL_DIR / name).as_posix()
        value = _git(root, "show", f"{baseline}:{relative}") if baseline else _read(root, relative)
        return None if value is None else value.encode()

    return physical_source_closure(PHYSICAL_ROOT, read)


def _physical_worktree_files(sources: dict[str, bytes]) -> dict[str, str]:
    return {(_PHYSICAL_DIR / name).as_posix(): value.decode() for name, value in sources.items()}


def physical_release_sources(root: Path, proposed: str | None = None) -> dict[str, bytes] | None:
    content = _read(root, _PHYSICAL) if proposed is None else proposed
    return None if content is None else _physical_closure(root, content)


def approved_physical_metadata(root: Path, preview: ChangePreview):
    source = _read(root, _PHYSICAL)
    if source is None or preview.effects.physical is None:
        raise model.ModelError(["native candidate lacks the approved physical declaration"])
    sources = _physical_closure(root, source)
    if physical_sources_id(sources) != preview.effects.physical[1]:
        raise model.ModelError(["applied physical inputs differ from the approved preview"])
    return compile_physical(sources)


def prepare_preview(
    root: Path,
    request: ChangeRequest,
    *,
    target: str | None = None,
    target_profile: DeploymentProfile = "development",
    authoring_target: str | None = None,
    target_identity: StorageTarget | None = None,
    authoring_identity: StorageTarget | None = None,
    native_base: NativeMigrationBase | None = None,
    deployment_base: NativeMigrationBase | None = None,
    comparison: dict | None = None,
    source_comparison: EffectiveChangeComparison | None = None,
    query_analysis: ProjectionAnalysisComparison | None = None,
    local_release: str | None = None,
    release_manifest_sha256: str | None = None,
    release_artifacts_sha256: str | None = None,
    expected_physical: str | None = None,
    prepared_application: PreparedRelease | None = None,
) -> ChangePreview:
    root = root.resolve()
    if request.source_migrations and not request.data_operations:
        raise model.ModelError(["source migrations require explicit data-operation inputs"])
    comparison_model = None
    migrations = tuple(prepare_source_migration(root, item) for item in request.source_migrations)
    proposed: dict[str, str] = {}
    for migration in migrations:
        for path, content in migration.after.items():
            if path in proposed and proposed[path] != content:
                raise model.ModelError([f"competing source migrations for {path}"])
            proposed[path] = content
    baseline = _ref(root, request.baseline)
    head = _ref(root, "HEAD")
    core, system, log = (
        (preparation.MODEL_PATH / name).as_posix()
        for name in ("core.yaml", "system.yaml", "revisions.yaml")
    )
    original = {path: _git(root, "show", f"{baseline}:{path}") for path in (core, system, log)}
    current = {path: _read(root, path) for path in original}
    acquired = None
    captured_paths: set[str] = set()
    if request.data_operations is not None:
        if request.packs:
            raise model.ModelError(["target inputs and legacy domain packs are exclusive"])
        from corpus_structure.semantic.data_operation_preparation import (
            acquire_data_operation_inputs,
        )

        acquired = acquire_data_operation_inputs(root, request.data_operations)
        captured_paths = {path for path, _ in acquired.files}
        if any(
            change.path not in captured_paths
            for intent in request.source_migrations
            for change in intent.sources
        ):
            raise model.ModelError(
                ["authored source migration input is outside the acquired operation source closure"]
            )
        current.update({path: content.decode() for path, content in acquired.files})
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
        native = request.native_requested
        if request.physical is not None or request.retire or request.recreate:
            if not native:
                raise model.ModelError(
                    ["physical and native object effects require a native revision request"]
                )
            native_intent(request.retire, request.recreate)
        if (native or request.deployment) != bool(target):
            raise model.ModelError(["a deployment preview requires a configured target binding"])
        if request.deployment_profile and (
            not target or request.deployment_profile != target_profile
        ):
            raise model.ModelError(["deployment profile differs from the requested target"])
        if native != bool(authoring_target):
            raise model.ModelError(["a native preview requires its development authoring target"])
        migration = request.change.alembic_revision if request.change else None
        if request.native_revision and migration and migration != request.native_revision:
            raise model.ModelError(["native revision conflicts with the declared model change"])
        if native != bool(migration or request.native_revision):
            raise model.ModelError(
                [
                    "a native change requires an Alembic revision; None predecessor explicitly requests an empty root"
                ]
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
        compatibility: dict[str, list[str]] = {}
        for (element, _, _), classification in change.derived(
            old, new, request.change.name_map if request.change else {}
        ).items():
            compatibility.setdefault(classification, []).append(element)
    physical = None
    if native:
        physical_input = _read(root, _PHYSICAL)
        if physical_input is None:
            raise model.ModelError(["native preview requires the trusted physical declaration"])
        original_physical = _physical_closure(
            root, _git(root, "show", f"{baseline}:{_PHYSICAL}"), baseline=baseline
        )
        requested_physical = _physical_closure(
            root, physical_input if request.physical is None else request.physical
        )
        target_metadata = compile_physical(requested_physical)
        physical = (physical_sources_id(original_physical), physical_sources_id(requested_physical))
        if expected_physical is not None and expected_physical != physical[1]:
            raise model.ModelError(["physical release inputs changed during preview"])
        original_files = _physical_worktree_files(original_physical)
        requested_files = _physical_worktree_files(requested_physical)
        original.update(original_files)
        current.update(
            {path: _read(root, path) for path in original_files.keys() | requested_files.keys()}
        )
        source.update(requested_files)
        from corpus_structure.semantic.original_document_contracts import generated_source_calls
        from corpus_structure.semantic.typed_generation import generated_source

        generated.update(
            {
                (
                    preparation.PACKAGE_PATH / _SOURCE_CALLS_OUTPUT
                ).as_posix(): generated_source_calls(target_metadata=target_metadata),
                (preparation.PACKAGE_PATH / _TYPED_COLUMNS_OUTPUT).as_posix(): generated_source(
                    target_metadata
                ),
            }
        )
        for path in _git(
            root, "ls-files", "-z", "--", str(preparation.PACKAGE_PATH / "semantic")
        ).split("\0"):
            if path.endswith((".py", ".sql")):
                current[path] = _read(root, path)
        from corpus_structure.semantic.migrations import ALEMBIC_DIR

        migration_directory = preparation.PACKAGE_PATH.parents[1] / ALEMBIC_DIR.name
        for name in ("env.py", "script.py.mako"):
            path = (migration_directory / name).as_posix()
            current[path] = _read(root, path)
            if current[path] is None:
                raise model.ModelError(
                    ["native preview requires its current migration environment: " + path]
                )
    for migration in migrations:
        for path, digest in migration.inputs.items():
            content = _read(root, path)
            if _digest(content) != digest:
                raise model.ModelError([f"source changed during preview: {path}"])
            current[path] = content
    previous = None
    if migrations and request.data_operations:
        assert acquired is not None
        from corpus_structure.semantic.data_operation_preparation import (
            prepare_data_operation_inputs,
        )

        prepared_source = prepared_application
        if prepared_source is None:
            _, _, _, prepared_source = prepare_data_operation_inputs(
                root,
                request.data_operations,
                proposed={path: value.encode() for path, value in proposed.items()},
            )
        if local_release is not None and prepared_source.release_id != local_release:
            raise model.ModelError(["proposed-source release differs from reviewed release"])
        from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

        effective = bound_data_operation_model(prepared_source)
        comparison_model = effective
        owners = {operation.semantic_id for operation in effective.operations}
        if any((item.new_owner or item.owner) not in owners for item in request.source_migrations):
            raise model.ModelError(
                ["source migration owner is absent from the proposed effective model"]
            )
        from corpus_structure.semantic.prepare import prepare_release

        previous = bound_data_operation_model(
            prepare_release(acquired.bundle, acquired.dependencies, acquired.profile)
        )
        from corpus_structure.semantic.source_comparison import compare_data_operation_models

        for intent, migration in zip(request.source_migrations, migrations, strict=True):
            if intent.owner not in {op.semantic_id for op in previous.operations}:
                raise model.ModelError(
                    ["source migration owner is absent from the acquired effective model"]
                )
            if intent.kind in {"symbol_move", "call_context"}:
                before_names = {
                    surface.declaration
                    for surface in previous.operation(intent.owner).callable_surfaces
                }
                after_names = {
                    surface.declaration
                    for surface in effective.operation(
                        intent.new_owner or intent.owner
                    ).callable_surfaces
                }
                after_operation = effective.operation(intent.new_owner or intent.owner)
                selection = getattr(after_operation, "consumer_selection", None)
                if selection is not None:
                    after_names.add(selection.entrypoint)
                assert intent.old_name is not None and intent.new_name is not None
                before_operation = previous.operation(intent.owner)
                class_move = (
                    intent.kind == "symbol_move"
                    and before_operation.implementation_root == "python:" + intent.old_name
                    and after_operation.implementation_root == "python:" + intent.new_name
                    and bool(before_operation.callable_surfaces)
                    and all(
                        surface.exposed.startswith(intent.old_name + ".")
                        for surface in before_operation.callable_surfaces
                    )
                    and all(
                        surface.exposed.startswith(intent.new_name + ".")
                        for surface in after_operation.callable_surfaces
                    )
                )
                if class_move:

                    def class_contract(operation, prefix):
                        return {
                            surface.exposed.removeprefix(prefix + "."): (
                                surface.declaration.removeprefix(prefix + ".")
                                if surface.declaration.startswith(prefix + ".")
                                else surface.declaration,
                                surface.parameters,
                                surface.returns,
                                surface.overloads,
                            )
                            for surface in operation.callable_surfaces
                        }

                    if class_contract(before_operation, intent.old_name) != class_contract(
                        after_operation, intent.new_name
                    ):
                        raise model.ModelError(
                            [
                                "symbol_move cannot change the callable contract of its operation class"
                            ]
                        )
                    continue
                proof = next(
                    (
                        item
                        for item in migration.call_proofs
                        if item.owner == intent.owner
                        and item.callable == intent.old_name
                        and item.path in captured_paths
                    ),
                    None,
                )
                if intent.old_name not in before_names and not (
                    intent.kind == "call_context" and proof is not None
                ):
                    raise model.ModelError(
                        ["source migration correspondence differs from its owned callable"]
                    )
                if intent.new_name not in after_names:
                    raise model.ModelError(
                        ["source migration correspondence differs from its owned callable"]
                    )
                if intent.kind == "call_context":
                    continue
                before_surface = next(
                    surface
                    for surface in previous.operation(intent.owner).callable_surfaces
                    if surface.declaration == intent.old_name
                )
                after_surface = next(
                    surface
                    for surface in effective.operation(
                        intent.new_owner or intent.owner
                    ).callable_surfaces
                    if surface.declaration == intent.new_name
                )
                if intent.kind == "symbol_move" and (
                    before_surface.parameters,
                    before_surface.returns,
                    before_surface.overloads,
                ) != (after_surface.parameters, after_surface.returns, after_surface.overloads):
                    raise model.ModelError(
                        [
                            "symbol_move cannot change the callable contract; use a separately supported interface migration"
                        ]
                    )

        for intent in request.source_migrations:
            if intent.kind == "authored_update":

                def surfaces(operation):
                    return tuple(
                        (surface.exposed, surface.parameters, surface.returns, surface.overloads)
                        for surface in operation.callable_surfaces
                    )

                if surfaces(previous.operation(intent.owner)) != surfaces(
                    effective.operation(intent.owner)
                ):
                    raise model.ModelError(
                        [
                            "authored_update preserves callable contracts; use an explicit caller migration for interface changes"
                        ]
                    )

        if comparison is None:
            from corpus_structure.semantic.model_comparison import compare_declared_models

            comparison = compare_declared_models(
                previous,
                effective,
                after_release=prepared_source.release_id,
            ).model_dump(mode="json")
        if source_comparison is None:
            source_comparison = compare_data_operation_models(previous, effective)
        elif source_comparison.after_digest != sha256(effective.content).hexdigest():
            raise model.ModelError(["source comparison differs from the proposed effective model"])

        local_release = prepared_source.release_id
        release_manifest_sha256 = sha256(prepared_source.manifest).hexdigest()
        release_artifacts_sha256 = prepared_source.artifacts_sha256
    if (
        (source_comparison is not None or comparison is not None)
        and request.data_operations
        and not migrations
    ):
        assert acquired is not None
        from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
        from corpus_structure.semantic.prepare import prepare_release

        compiled = bound_data_operation_model(
            prepare_release(acquired.bundle, acquired.dependencies, acquired.profile)
        )
        comparison_model = compiled
        if (
            source_comparison is not None
            and source_comparison.after_digest != sha256(compiled.content).hexdigest()
        ):
            raise model.ModelError(["source comparison differs from the proposed effective model"])
    if comparison is not None and request.data_operations:
        from corpus_structure.semantic.model_comparison import DeclaredModelComparison

        checked_comparison = DeclaredModelComparison.model_validate(comparison)
        assert comparison_model is not None
        if checked_comparison.after_digest != sha256(comparison_model.content).hexdigest():
            raise model.ModelError(
                ["declared model comparison differs from the proposed effective model"]
            )
        if source_comparison is not None and (
            checked_comparison.before_digest != source_comparison.before_digest
            or checked_comparison.after_digest != source_comparison.after_digest
        ):
            raise model.ModelError(
                ["declared and source comparisons refer to different model pairs"]
            )
        comparison = checked_comparison.model_dump(mode="json")
    staged = {path: content for path, content in source.items() if content is not None} | generated
    if proposed.keys() & staged.keys():
        raise model.ModelError(["source migration overlaps a generated or canonical effect"])
    staged.update(proposed)
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
    identifiers.update(item.name for item in (*request.retire, *request.recreate))
    for item in (comparison or {}).get("changes", ()):
        for ref in (item["model_ref"], *item.get("consumers", ())):
            identifiers.update(
                token for token in ref.replace(":", ".").split(".") if token.isidentifier()
            )
    if migrations:
        assert previous is not None
        identifiers.update(
            surface.declaration.rsplit(".", 1)[-1]
            for intent in request.source_migrations
            for surface in previous.operation(intent.owner).callable_surfaces
        )
    discovery_sources = None
    if migrations:
        discovery_sources = {}
        for path in sorted({path for migration in migrations for path in migration.membership}):
            content = current[path]
            if content is None:
                raise model.ModelError([f"acquired source is unavailable: {path}"])
            discovery_sources[path] = proposed.get(path, content).encode()
    release_effect = (
        ("unchanged" if request.archive_release == local_release else "changed")
        if comparison
        else "uncompared"
        if local_release
        else "not_applicable"
    )
    admission = bool(target and local_release)
    native_basis = tuple(
        reason
        for applies, reason in (
            (bool(compatibility.get("relational-additive")), "canonical_relational_change"),
            (physical is not None and physical[0] != physical[1], "trusted_physical_change"),
            (bool(request.retire), "explicit_native_retirement"),
            (bool(request.recreate), "explicit_native_recreation"),
            (bool(request.data_steps), "revision_data_steps"),
        )
        if applies
    )
    if native and not native_basis:
        native_basis = ("explicit_native_authoring",)
    checks = ["canonical_validation", "revision_log", "exact_file_bytes"]
    if native:
        checks.extend(("physical_compilation", "acquired_predecessor", "native_admission"))
    if admission:
        checks.extend(
            (
                "prepared_release_identity",
                "prepared_release_artifacts",
                "release_admission",
                "acquired_target",
            )
        )
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
            _diff(path, original.get(path), content)
            for path, content in source.items()
            if content is not None and content != original.get(path)
        ),
        request=request,
        target=target,
        target_profile=target_profile if target else None,
        authoring_target=authoring_target,
        target_identity=target_identity,
        authoring_identity=authoring_identity,
        native_base=native_base,
        deployment_base=deployment_base,
        effects=ChangeEffects(
            compatibility={
                kind: tuple(sorted(set(elements))) for kind, elements in compatibility.items()
            },
            routes={kind: change.route(kind) for kind in compatibility},
            generated=tuple(file.path for file in files if file.path in generated),
            physical=physical,
            native=native,
            native_basis=native_basis,
            admission=admission,
            admission_applicable=bool(local_release),
            release=release_effect,
            checks=tuple(checks),
        ),
        comparison=comparison,
        local_release=local_release,
        release_manifest_sha256=release_manifest_sha256,
        release_artifacts_sha256=release_artifacts_sha256,
        source_migrations=migrations,
        data_steps=prepare_data_steps(request.data_steps),
        source_comparison=source_comparison,
        query_analysis=query_analysis,
        discovery=locate_consumers(
            root,
            head,
            identifiers,
            comparison=comparison,
            proposed=proposed,
            sources=discovery_sources,
        )
        if identifiers or comparison or migrations
        else None,
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
    if preview.data_steps != prepare_data_steps(preview.request.data_steps):
        raise model.ModelError(["revision data-step custody changed after preview"])
    for migration in preview.source_migrations:
        try:
            check_source_migration(root, migration)
        except ValueError as error:
            raise model.ModelError([str(error)]) from error
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
    native_fence: AbstractContextManager[StorageTarget] | None = None,
    report: Callable[[str], None] | None = None,
) -> list[str]:
    """Apply only the approved files. Exact after-bytes make interrupted work retryable."""
    root = root.resolve()
    settled: list[str] = []
    with preparation.writer_lock(root):
        check_preview(root, preview)
        if preview.request.native_requested and native_fence is None:
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
