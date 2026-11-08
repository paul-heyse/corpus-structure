"""Bind an authored candidate to a reviewed model, installed revision and storage target."""

from __future__ import annotations

import ast
import json
import os
import re
from collections.abc import Callable, Generator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from pydantic import BaseModel, ConfigDict

from corpus_structure.schema.model import ModelError
from corpus_structure.schema.model_change import (
    ChangePreview,
    checked_path,
    generator_fingerprint,
    verify_release_products,
)
from corpus_structure.semantic.runtime import Purpose
from corpus_structure.semantic.storage_target import (
    StorageTarget,
    acquired_target,
    assert_explicit_route,
    verify_declared_route,
    verify_target,
)
from corpus_structure.semantic.types import PreparedRelease
from corpus_structure.settings import DeploymentProfile, Settings

_NATIVE_PRODUCTS = (
    ("UPGRADE", "native_candidate.py", "upgrade.txt"),
    ("STATE", "native_operations.json", "native.json"),
    ("ADMISSION", "native_admission.sql", "admission.sql"),
)


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace: str
    model_revision: str
    generator: str
    revision: str | None
    predecessor: str | None
    target: str
    target_profile: DeploymentProfile = "development"
    authoring_target: str | None = None
    target_identity: StorageTarget | None = None
    authoring_identity: StorageTarget | None = None
    release: str
    release_manifest_sha256: str | None = None
    release_artifacts_sha256: str | None = None
    packs: tuple[str, ...]
    files: dict[str, str | None]
    hashes: dict[str, str]
    wrapper_sha256: str | None = None

    @classmethod
    def from_preview(
        cls,
        preview: ChangePreview,
        revision: str | None,
        prepared: PreparedRelease,
        products: dict[str, bytes],
    ) -> Candidate:
        if (
            not preview.target
            or not preview.target_profile
            or bool(revision) != bool(preview.request.native_predecessor)
            or bool(revision) != bool(preview.authoring_target)
        ):
            raise ModelError(
                ["candidate requires a deployment target and matching native authoring binding"]
            )
        preview.verify_release(prepared)
        binding = cls(
            workspace=preview.workspace,
            model_revision=preview.revision,
            generator=preview.generator,
            revision=revision,
            predecessor=preview.request.native_predecessor,
            target=preview.target,
            target_profile=preview.target_profile,
            authoring_target=preview.authoring_target,
            target_identity=preview.target_identity,
            authoring_identity=preview.authoring_identity,
            release=prepared.release_id,
            release_manifest_sha256=preview.release_manifest_sha256,
            release_artifacts_sha256=preview.release_artifacts_sha256,
            packs=preview.request.packs,
            files={
                **preview.inputs,
                **{
                    effect.path: sha256(effect.after.encode()).hexdigest()
                    for effect in preview.files
                },
            },
            hashes={name: sha256(content).hexdigest() for name, content in products.items()},
        )
        if revision:
            binding = binding.model_copy(
                update={"wrapper_sha256": sha256(migration_wrapper(binding)).hexdigest()}
            )
        return binding


def deployment_settings(
    settings: Settings, profile: DeploymentProfile | None = None
) -> tuple[DeploymentProfile, Settings]:
    """Resolve the chosen profile once and keep its role credentials scoped to it."""
    selected = profile or ("deployment" if settings.deployment else "development")
    if selected == "development":
        return selected, settings
    if settings.deployment is None:
        raise ModelError(["the bound deployment profile is not configured"])
    return selected, settings.model_copy(update={"database": settings.deployment})


def target_fingerprint(settings: Settings) -> str:
    """Identify the configured endpoint without copying role credentials into a result."""
    from sqlalchemy.engine import make_url

    source = make_url(settings.database.url)
    if source.query.get("dbname") not in {None, source.database}:
        raise ModelError(["configured PostgreSQL database conflicts with its libpq route"])
    if source.database in {
        None,
        "",
        "postgres",
        "template0",
        "template1",
        settings.database.template,
    }:
        raise ModelError(["model effects require an explicit non-system, non-template database"])
    query = {
        key: value
        for key, value in source.query.items()
        if key not in {"user", "password", "passfile"}
    }
    data = [source.database, source.host, source.port, query]
    return sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def capture_target(settings: Settings, *, purpose: Purpose) -> StorageTarget:
    from corpus_structure.semantic.runtime import open_runtime_engine

    assert_explicit_route(settings)
    with (
        open_runtime_engine(settings, "ci-model-bind", purpose=purpose) as engine,
        engine.begin() as conn,
    ):
        verify_declared_route(conn, settings)
        return acquired_target(conn, purpose=purpose)


@contextmanager
def predecessor_fence(
    settings: Settings, target: str, predecessor: str, identity: StorageTarget | None = None
) -> Generator[StorageTarget]:
    from corpus_structure.semantic.migrations import current_revision, migration_fence
    from corpus_structure.semantic.runtime import open_runtime_engine

    if target_fingerprint(settings) != target:
        raise ModelError(["configured target differs from the model preview"])
    assert_explicit_route(settings)
    with (
        open_runtime_engine(settings, "ci-model-predecessor", purpose="maintenance") as engine,
        engine.begin() as conn,
    ):
        verify_declared_route(conn, settings)
        actual = (
            acquired_target(conn, purpose="maintenance")
            if identity is None
            else verify_target(conn, identity, purpose="maintenance")
        )
        migration_fence(conn)
        if current_revision(conn) != predecessor:
            raise ModelError(["installed native predecessor differs from the model preview"])
        yield actual


def verify_predecessor(settings: Settings, target: str, predecessor: str) -> StorageTarget:
    with predecessor_fence(settings, target, predecessor) as actual:
        return actual


def _migration_names(binding: Candidate) -> dict[str, str]:
    if not binding.revision or not re.fullmatch(r"[A-Za-z0-9_]{1,32}", binding.revision):
        raise ModelError(["revision ID must contain 1 to 32 letters, digits or underscores"])
    if not binding.predecessor or binding.predecessor == binding.revision:
        raise ModelError(["native registration requires a distinct predecessor"])
    return {kind: f"{binding.revision}_{suffix}" for kind, _, suffix in _NATIVE_PRODUCTS}


def migration_wrapper(binding: Candidate) -> bytes:
    names = _migration_names(binding)
    constants = "\n".join(
        f"NATIVE_{kind}_FILE = {json.dumps(names[kind])}\n"
        f"NATIVE_{kind}_SHA256 = {json.dumps(binding.hashes[product])}"
        for kind, product, _ in _NATIVE_PRODUCTS
    )
    return f'''\
"""Apply the frozen native candidate {binding.revision}."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = {json.dumps(binding.revision)}
down_revision = {json.dumps(binding.predecessor)}
branch_labels = None
depends_on = None
{constants}


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {{}}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
'''.encode()


def _versions() -> Path:
    from corpus_structure.semantic.migrations import ALEMBIC_DIR

    return ALEMBIC_DIR / "versions"


def _migration_declarations(
    versions: Path,
) -> Generator[tuple[Path, str, dict[str, ast.expr]]]:
    for path in versions.glob("*.py"):
        if path.name == "__init__.py":
            continue
        try:
            tree = ast.parse(path.read_bytes(), filename=path.name)
        except (OSError, SyntaxError) as error:
            raise ModelError([f"cannot inspect migration declaration: {path.name}"]) from error
        fields: dict[str, ast.expr] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            else:
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {
                    "revision",
                    "down_revision",
                    "depends_on",
                    "branch_labels",
                }:
                    if target.id in fields:
                        raise ModelError([f"duplicate {target.id} in {path.name}"])
                    fields[target.id] = value
        revision = fields.get("revision")
        if not isinstance(revision, ast.Constant) or not isinstance(revision.value, str):
            raise ModelError([f"migration requires one literal revision ID: {path.name}"])
        yield path, revision.value, fields


def _declared_revision_paths(versions: Path, revision: str) -> set[Path]:
    return {path for path, name, _ in _migration_declarations(versions) if name == revision}


def _declared_revision_head(
    declarations: list[tuple[Path, str, dict[str, ast.expr]]],
) -> str | None:
    """Ask Alembic to resolve the graph from literal metadata without importing migrations."""
    from alembic.script.revision import Revision, RevisionError, RevisionMap

    def declared_edges(fields: dict[str, ast.expr], name: str) -> str | tuple[str, ...] | None:
        if name not in fields:
            if name == "down_revision":
                raise ValueError("missing down_revision")
            return None
        value = ast.literal_eval(fields[name])
        if value is None or isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
            return tuple(value)
        raise ValueError(f"invalid {name}")

    revisions: dict[str, Revision] = {}
    for path, revision, fields in declarations:
        try:
            if revision in revisions:
                raise ValueError("duplicate revision ID")
            revisions[revision] = Revision(
                revision,
                declared_edges(fields, "down_revision"),
                dependencies=declared_edges(fields, "depends_on"),
                branch_labels=declared_edges(fields, "branch_labels"),
            )
        except (RevisionError, ValueError, TypeError) as error:
            raise ModelError(
                [f"invalid migration graph metadata in {path.name}: {error}"]
            ) from error
    try:
        return RevisionMap(lambda: revisions.values()).get_current_head()
    except (RevisionError, KeyError) as error:
        raise ModelError([f"cannot resolve the installed migration head: {error}"]) from error


def _approved_wrapper(binding: Candidate) -> bytes:
    if missing := {product for _, product, _ in _NATIVE_PRODUCTS} - binding.hashes.keys():
        raise ModelError(
            ["native candidate lacks required products: " + ", ".join(sorted(missing))]
        )
    content = migration_wrapper(binding)
    if sha256(content).hexdigest() != binding.wrapper_sha256:
        raise ModelError(
            ["registered migration wrapper differs from the approved executable bytes"]
        )
    return content


def candidate_registration_files(
    root: Path, binding: Candidate, products: Path | int
) -> dict[Path, bytes]:
    """Validate the exact registration and return its files without changing the checkout."""
    check_candidate_files(root, binding)
    names = _migration_names(binding)
    versions = _versions().relative_to(root)
    wrapper = checked_path(root, (versions / f"{binding.revision}.py").as_posix())
    declarations = list(_migration_declarations(root / versions))
    if any(name == binding.revision and path != wrapper for path, name, _ in declarations):
        raise ModelError(["candidate revision is declared by a different migration wrapper"])
    staged = {}
    for kind, product, _ in _NATIVE_PRODUCTS:
        if isinstance(products, int):
            fd = os.open(product, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=products)
            with os.fdopen(fd, "rb") as artifact:
                content = artifact.read()
        else:
            content = (products / product).read_bytes()
        if sha256(content).hexdigest() != binding.hashes.get(product):
            raise ModelError([f"candidate artifact differs: {product}"])
        staged[checked_path(root, (versions / names[kind]).as_posix())] = content
    staged[wrapper] = _approved_wrapper(binding)
    for path, content in staged.items():
        if path.exists() and path.read_bytes() != content:
            raise ModelError([f"migration file already has different content: {path.name}"])
    if not wrapper.is_file() and _declared_revision_head(declarations) != binding.predecessor:
        raise ModelError(["installed migration head differs from the candidate predecessor"])
    return staged


def register_candidate(
    root: Path,
    binding: Candidate,
    products: Path | int,
    *,
    report: Callable[[str], None] | None = None,
) -> tuple[str, ...]:
    """Install exact migration products under the caller's checkout writer lock."""
    staged = candidate_registration_files(root, binding, products)
    for path, content in staged.items():
        if not path.exists():
            with NamedTemporaryFile(dir=path.parent) as pending:
                pending.write(content)
                pending.flush()
                os.fchmod(pending.fileno(), 0o644)
                os.link(pending.name, path)
        if report is not None:
            report(path.relative_to(root).as_posix())
    return tuple(path.relative_to(root).as_posix() for path in staged)


class MigrationNotRegistered(ModelError):
    """The reviewed revision needs one or more missing registration files."""


def _verify_installed_revision(root: Path, binding: Candidate) -> dict[str, bytes]:
    """Only the repository migration owner may execute an admitted frozen revision."""
    if binding.revision is None:
        return {}
    names = _migration_names(binding)
    versions = _versions().relative_to(root)
    wrapper = checked_path(root, (versions / f"{binding.revision}.py").as_posix())
    wrapper_bytes = _approved_wrapper(binding)
    if not wrapper.exists():
        raise MigrationNotRegistered(["the approved migration wrapper is missing"])
    if wrapper.read_bytes() != wrapper_bytes:
        raise ModelError(["installed migration wrapper differs from the approved wrapper"])
    if _declared_revision_paths(root / versions, binding.revision) != {wrapper}:
        raise ModelError(["candidate revision is declared by a different migration wrapper"])
    frozen = {wrapper.name: wrapper_bytes}
    for kind, product, _ in _NATIVE_PRODUCTS:
        name = names[kind]
        path = checked_path(root, (versions / name).as_posix())
        if not path.is_file():
            raise MigrationNotRegistered([f"installed migration artifact is missing: {name}"])
        content = path.read_bytes()
        if sha256(content).hexdigest() != binding.hashes[product]:
            raise ModelError([f"installed migration artifact differs: {name}"])
        frozen[name] = content
    return frozen


@contextmanager
def _verified_script_location(root: Path, binding: Candidate) -> Generator[Path | None]:
    frozen = _verify_installed_revision(root, binding)
    if not frozen:
        yield None
        return
    source = _versions()
    # Load the exact frozen bytes from a private fresh path. Python cannot reuse a
    # checkout __pycache__ entry, and later edits cannot change this candidate.
    with TemporaryDirectory(prefix="ci-model-migration-") as directory:
        location = Path(directory)
        versions = location / "versions"
        versions.mkdir()
        (location / "env.py").symlink_to(source.parent / "env.py")
        for file in source.iterdir():
            if file.name not in frozen and file.is_file():
                (versions / file.name).symlink_to(file)
        for name, content in frozen.items():
            (versions / name).write_bytes(content)
        yield location


def check_candidate_files(root: Path, binding: Candidate) -> None:
    """Verify that the candidate still matches the local inputs and generator."""
    if str(root) != binding.workspace or generator_fingerprint(root) != binding.generator:
        raise ModelError(["candidate belongs to another workspace or generator"])
    for relative, expected in binding.files.items():
        file = checked_path(root, relative)
        actual = sha256(file.read_bytes()).hexdigest() if file.exists() else None
        if actual != expected:
            raise ModelError([f"candidate input has changed: {relative}"])


def deploy_candidate(
    root: Path,
    settings: Settings,
    binding: Candidate,
    deployment: tuple,
    *,
    report: Callable[[str], None],
    report_target: Callable[[StorageTarget, str | None, str | None], None] | None = None,
) -> None:
    from corpus_structure.semantic.authored_sql import (
        admit_archived_sql,
        analyze_archived_sql,
        has_authored_sql,
    )
    from corpus_structure.semantic.execution_admission import (
        _verify_deployment_functions,
        require_frozen_native_revision,
    )
    from corpus_structure.semantic.migrations import current_revision, migration_fence, upgrade
    from corpus_structure.semantic.publication import admit_release
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.releases import open_release, persist_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    check_candidate_files(root, binding)
    _, destination = deployment_settings(settings, binding.target_profile)
    if target_fingerprint(destination) != binding.target:
        raise ModelError(["configured deployment target differs from the candidate"])
    bundle, deps, profile, prepared = deployment
    verify_release_products(
        prepared,
        release=binding.release,
        manifest_sha256=binding.release_manifest_sha256,
        artifacts_sha256=binding.release_artifacts_sha256,
        binding="the candidate",
    )
    if binding.target_identity is None:
        raise ModelError(["candidate lacks the approved acquired PostgreSQL target"])
    assert_explicit_route(destination)

    def verify(conn, purpose: Purpose) -> StorageTarget:
        verify_declared_route(conn, destination)
        return verify_target(conn, binding.target_identity, purpose=purpose)

    with (
        _verified_script_location(root, binding) as script_location,
        open_runtime_engine(destination, "ci-model-migrate", purpose="maintenance") as maintenance,
        maintenance.connect() as conn,
        open_runtime_engine(destination, "ci-model-admit", purpose="admit") as admission,
        admission.connect() as writer,
        open_runtime_engine(destination, "ci-model-verify", purpose="read") as reader,
    ):
        versions = None if script_location is None else script_location / "versions"
        # Verify all acquired purpose routes before the first durable effect. Recheck any
        # later borrower before use, including the fresh post-admission reader snapshot.
        with writer.begin(), reader.begin() as check:
            verify(writer, "admit")
            verify(check, "read")
        if binding.revision is not None:
            assert versions is not None
            require_frozen_native_revision(versions, binding.revision)
            with conn.begin():
                target = verify(conn, "maintenance")
                migration_fence(conn)
                actual = current_revision(conn)
                if actual is None or actual not in {binding.predecessor, binding.revision}:
                    raise ModelError(["acquired revision differs from the approved predecessor"])
                _verify_deployment_functions(conn, revision=actual, versions=versions)
                if report_target is not None:
                    report_target(target, binding.predecessor, actual)
                upgrade(
                    conn,
                    binding.revision,
                    expected_predecessor=binding.predecessor,
                    script_location=script_location,
                )
                if current_revision(conn) != binding.revision:
                    raise ModelError(["migration did not reach the approved revision"])
                _verify_deployment_functions(conn, revision=binding.revision, versions=versions)
            if report_target is not None:
                report_target(target, binding.predecessor, binding.revision)
            report("migration")
        with conn.begin():
            target = verify(conn, "maintenance")
            migration_fence(conn)
            actual = current_revision(conn)
            if actual is None or (binding.revision is not None and actual != binding.revision):
                raise ModelError(["native revision changed before archive/admission"])
            _verify_deployment_functions(conn, revision=actual, versions=versions)
            if report_target is not None:
                report_target(target, binding.predecessor, actual)
            with writer.begin():
                verify(writer, "admit")
                persist_release(writer, bundle, deps, profile, prepared)
            report("archive")
            analyzed = None
            if has_authored_sql(prepared):
                with reader.connect() as sql_connection:
                    verify(sql_connection, "read")
                    analyzed = analyze_archived_sql(sql_connection, binding.release)
            with writer.begin():
                verify(writer, "admit")
                if analyzed is not None:
                    admit_archived_sql(writer, binding.release, analyzed=analyzed)
                admit_release(prepared, connection=writer)
            report("admission")
            with read_snapshot(reader) as snapshot:
                verify(snapshot, "read")
                if open_release(snapshot, binding.release).release_id != binding.release:
                    raise ModelError(["admitted release does not match the candidate"])
            report("verified")
