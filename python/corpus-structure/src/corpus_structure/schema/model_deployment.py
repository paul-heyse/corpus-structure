"""Bind an authored candidate to a reviewed model, installed revision and storage target."""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections.abc import Callable, Generator
from contextlib import ExitStack, contextmanager
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, model_validator

from corpus_structure.schema.model import ModelError
from corpus_structure.schema.model_change import (
    ChangePreview,
    ChangeRequest,
    RuntimeCustody,
    checked_path,
    compilation_fingerprint,
    generator_fingerprint,
    verify_release_products,
)
from corpus_structure.semantic.migration_chain import (
    NativeMigrationBase,
    registered_base,
    verify_registered_base,
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

if TYPE_CHECKING:
    from sqlalchemy import Connection, Engine

    from corpus_structure.semantic.data_operation_runtime import RuntimeBinding

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
    native_base: NativeMigrationBase | None = None
    deployment_base: NativeMigrationBase | None = None
    release: str | None
    release_manifest_sha256: str | None = None
    release_artifacts_sha256: str | None = None
    packs: tuple[str, ...]
    data_operations: str | None = None
    runtime: RuntimeCustody | None = None
    files: dict[str, str | None]
    hashes: dict[str, str]
    wrapper_sha256: str | None = None
    inspection_sha256: str | None = None
    preparation_request: ChangeRequest | None = None
    preparation_fingerprint: str | None = None

    @model_validator(mode="after")
    def native_only_has_no_release_claims(self):
        if self.release is None:
            if (
                self.release_manifest_sha256 is not None
                or self.release_artifacts_sha256 is not None
                or self.inspection_sha256 is not None
                or self.runtime is not None
            ):
                raise ValueError(
                    "a native-only candidate cannot carry release hashes or an application inspection capsule"
                )
            if self.packs or self.data_operations is not None or self.revision is None:
                raise ValueError(
                    "a native-only candidate requires a native revision and no application release inputs"
                )
        return self

    @classmethod
    def from_preview(
        cls,
        preview: ChangePreview,
        revision: str | None,
        prepared: PreparedRelease | None,
        products: dict[str, bytes],
        *,
        runtime: RuntimeBinding | None = None,
    ) -> Candidate:
        if (
            not preview.target
            or not preview.target_profile
            or bool(revision) != preview.request.native_requested
            or bool(revision) != bool(preview.authoring_target)
        ):
            raise ModelError(
                ["candidate requires a deployment target and matching native authoring binding"]
            )
        if prepared is None:
            if (
                runtime is not None
                or preview.runtime is not None
                or not preview.effects.native
                or preview.effects.admission
                or preview.local_release is not None
                or preview.release_manifest_sha256 is not None
                or preview.release_artifacts_sha256 is not None
            ):
                raise ModelError(
                    ["native-only candidate differs from the reviewed release-free preview"]
                )
        else:
            preview.verify_release(prepared)
            preview.verify_runtime(runtime, prepared)
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
            native_base=preview.native_base,
            deployment_base=preview.deployment_base,
            release=prepared.release_id if prepared is not None else None,
            release_manifest_sha256=preview.release_manifest_sha256,
            release_artifacts_sha256=preview.release_artifacts_sha256,
            packs=preview.request.packs,
            data_operations=preview.request.data_operations,
            runtime=preview.runtime,
            preparation_request=preview.request,
            preparation_fingerprint=preview.preparation_fingerprint,
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
    settings: Settings,
    target: str,
    predecessor: str | None,
    identity: StorageTarget | None = None,
    *,
    native_base: NativeMigrationBase | None = None,
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
        if native_base is not None:
            if native_base.predecessor != predecessor:
                raise ModelError(["native authoring base has a different predecessor"])
            verify_registered_base(_versions().parent, native_base)
        expected = predecessor if native_base is None else native_base.acquired_revision
        if current_revision(conn) != expected:
            raise ModelError(["installed native predecessor differs from the model preview"])
        if expected is None:
            from corpus_structure.semantic.target_installation import require_empty_target

            require_empty_target(conn)
        yield actual


def verify_predecessor(settings: Settings, target: str, predecessor: str | None) -> StorageTarget:
    with predecessor_fence(settings, target, predecessor) as actual:
        return actual


def capture_authoring_base(
    settings: Settings, target: str, predecessor: str | None
) -> tuple[StorageTarget, NativeMigrationBase | None]:
    """Bind the acquired database and a registered, still undeployed forward base."""
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
        identity = acquired_target(conn, purpose="maintenance")
        migration_fence(conn)
        actual = current_revision(conn)
        if actual is None:
            from corpus_structure.semantic.target_installation import require_empty_target

            require_empty_target(conn)
        if predecessor is None:
            if actual is not None:
                raise ModelError(["fresh native authoring requires an empty target"])
            return identity, None
        base = (
            None
            if actual == predecessor
            else registered_base(_versions().parent, actual, predecessor)
        )
        return identity, base


def _migration_names(binding: Candidate) -> dict[str, str]:
    if not binding.revision or not re.fullmatch(r"[A-Za-z0-9_]{1,32}", binding.revision):
        raise ModelError(["revision ID must contain 1 to 32 letters, digits or underscores"])
    if binding.predecessor == binding.revision:
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
down_revision = {binding.predecessor!r}
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
    if state["version"] != 2 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {{}}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))
    if state["version"] == 2:
        from corpus_structure.semantic.alembic_privileges import admit_privileges
        admit_privileges(op.get_bind(), state["privileges"])


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
    base = binding.deployment_base
    if base is None and binding.predecessor is not None:
        base = registered_base(_versions().parent, binding.predecessor, binding.predecessor)
    if base is not None:
        if base.predecessor != binding.predecessor:
            raise ModelError(["deployment base has a different candidate predecessor"])
        verify_registered_base(_versions().parent, base)
        for relative, digest in base.files:
            if relative == "env.py":
                continue
            path = checked_path(root, (_versions().parent / relative).relative_to(root).as_posix())
            content = path.read_bytes()
            if sha256(content).hexdigest() != digest:
                raise ModelError(["registered native chain changed during acquisition"])
            frozen[Path(relative).name] = content
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
        environment = (source.parent / "env.py").read_bytes()
        relative_environment = (source.parent / "env.py").relative_to(root).as_posix()
        if sha256(environment).hexdigest() != binding.files.get(relative_environment):
            raise ModelError(["current migration environment differs from the reviewed candidate"])
        if base is not None and sha256(environment).hexdigest() != dict(base.files)["env.py"]:
            raise ModelError(["registered migration environment changed during acquisition"])
        (location / "env.py").write_bytes(environment)
        for name, content in frozen.items():
            (versions / name).write_bytes(content)
        yield location


def check_candidate_files(root: Path, binding: Candidate) -> None:
    """Verify that the candidate still matches the local inputs and generator."""
    if str(root) != binding.workspace or generator_fingerprint(root) != binding.generator:
        raise ModelError(["candidate belongs to another workspace or generator"])
    if binding.release is not None:
        if binding.preparation_request is None or binding.preparation_fingerprint is None:
            raise ModelError(
                ["candidate lacks complete preparation custody; prepare a fresh preview"]
            )
        if (
            compilation_fingerprint(
                root,
                binding.preparation_request,
                native_base=binding.native_base,
                deployment_base=binding.deployment_base,
            )
            != binding.preparation_fingerprint
        ):
            raise ModelError(["candidate compilation inputs changed; prepare a fresh preview"])
    for relative, expected in binding.files.items():
        file = checked_path(root, relative)
        actual = sha256(file.read_bytes()).hexdigest() if file.exists() else None
        if actual != expected:
            raise ModelError([f"candidate input has changed: {relative}"])


@contextmanager
def _deployment_connection(engine: Engine) -> Generator[Connection]:
    from corpus_structure.core.db.store import record_cleanup_failure

    connection = engine.connect()
    try:
        yield connection
    finally:
        primary = sys.exception()
        try:
            connection.close()
        except BaseException as cleanup:
            record_cleanup_failure(primary or cleanup, cleanup)
            if primary is None:
                raise


@contextmanager
def _commit_deployment_effect(
    conn: Connection,
    effect: str,
    *,
    release: str | None,
    reconcile: Callable[[], bool | None],
    settled: Callable[[str], None],
) -> Generator[None]:
    from corpus_structure.core.db.store import (
        DatabaseOperationFailure,
        DatabasePhase,
        EffectKnowledge,
        classify_error,
        record_operation_failure,
    )

    committing = False
    try:
        with conn.begin():
            yield
            committing = True
    except BaseException as error:
        if committing:
            try:
                observed = reconcile()
            except Exception as observation_error:
                error.add_note("deployment reconciliation failed: " + repr(observation_error))
                observed = None
            knowledge = {
                True: EffectKnowledge.COMMITTED,
                False: EffectKnowledge.ROLLED_BACK,
                None: EffectKnowledge.UNCERTAIN,
            }[observed]
            record_operation_failure(
                error,
                DatabaseOperationFailure(
                    classify_error(error, phase=DatabasePhase.COMMITTING, effects=knowledge),
                    operation_id=f"model.deploy:{effect}",
                    remediation="inspect_exact_deployment_target",
                    release_id=release,
                ),
            )
            if observed is True:
                try:
                    settled(effect)
                except OSError as receipt_error:
                    error.add_note("could not checkpoint confirmed effect: " + repr(receipt_error))
        raise
    else:
        settled(effect)


def deploy_candidate(
    root: Path,
    settings: Settings,
    binding: Candidate,
    deployment: tuple | None,
    *,
    report: Callable[[str], None],
    runtime: RuntimeBinding | None = None,
    checkpoint: Callable[[StorageTarget, str | None, str, str | None], None] | None = None,
) -> None:
    from sqlalchemy import text
    from sqlalchemy.exc import NoResultFound

    from corpus_structure.semantic.authored_sql import (
        SQLAdmissionError,
        admit_archived_sql,
        analyze_release_sql,
        prepare_release_sql,
    )
    from corpus_structure.semantic.data_operation_admission import admit_data_operation_release
    from corpus_structure.semantic.data_operation_runtime import RuntimeBindingError
    from corpus_structure.semantic.execution_admission import (
        require_frozen_native_revision,
        verify_deployment_catalog,
    )
    from corpus_structure.semantic.migrations import current_revision, migration_fence, upgrade
    from corpus_structure.semantic.releases import open_release, persist_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.runtime_binding_store import (
        persist_runtime_binding,
        runtime_binding_for_release,
    )

    check_candidate_files(root, binding)
    _, destination = deployment_settings(settings, binding.target_profile)
    if target_fingerprint(destination) != binding.target:
        raise ModelError(["configured deployment target differs from the candidate"])
    prepared = None
    sql_inputs = None
    if binding.release is None:
        if runtime is not None:
            raise ModelError(["native-only candidate cannot admit a runtime"])
        if deployment is not None:
            raise ModelError(["native-only candidate cannot deploy application release inputs"])
    else:
        if deployment is None:
            raise ModelError(["release candidate requires its exact application inputs"])
        bundle, deps, profile, prepared = deployment
        verify_release_products(
            prepared,
            release=binding.release,
            manifest_sha256=binding.release_manifest_sha256,
            artifacts_sha256=binding.release_artifacts_sha256,
            binding="the candidate",
        )
        sql_inputs = prepare_release_sql(prepared, deps)
        if binding.data_operations:
            if binding.runtime is None or runtime is None:
                raise ModelError(["application candidate lacks exact reviewed runtime custody"])
            binding.runtime.verify(runtime, prepared)
        elif runtime is not None or binding.runtime is not None:
            raise ModelError(["runtime admission requires declared data-operation inputs"])
    if binding.target_identity is None:
        raise ModelError(["candidate lacks the approved acquired PostgreSQL target"])
    assert_explicit_route(destination)
    starting_revision = (
        binding.predecessor
        if binding.deployment_base is None
        else binding.deployment_base.acquired_revision
    )

    def verify(conn: Connection, purpose: Purpose) -> StorageTarget:
        verify_declared_route(conn, destination)
        return verify_target(conn, binding.target_identity, purpose=purpose)

    def release_fence(connection: Connection) -> None:
        # Use the archive owner's release lock to wait out a possibly live
        # committing backend before interpreting an absent durable row.
        connection.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:release,0))"),
            {"release": binding.release},
        )

    with (
        _verified_script_location(root, binding) as script_location,
        open_runtime_engine(destination, "ci-model-migrate", purpose="maintenance") as maintenance,
        _deployment_connection(maintenance) as conn,
        ExitStack() as purpose_routes,
    ):
        versions = None if script_location is None else script_location / "versions"

        def reconcile_migration() -> bool | None:
            with _deployment_connection(maintenance) as recovery, recovery.begin():
                recovery.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                recovery.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
                verify(recovery, "maintenance")
                migration_fence(recovery)
                observed = current_revision(recovery)
                if observed is None:
                    if starting_revision is None:
                        from corpus_structure.semantic.target_installation import (
                            require_empty_target,
                        )

                        require_empty_target(recovery)
                        return False
                    return None
                if observed not in {starting_revision, binding.revision}:
                    return None
                verify_deployment_catalog(recovery, revision=observed, versions=versions)
                return observed == binding.revision

        def open_purpose_routes():
            admission = purpose_routes.enter_context(
                open_runtime_engine(destination, "ci-model-admit", purpose="admit")
            )
            writer = purpose_routes.enter_context(_deployment_connection(admission))
            reader = purpose_routes.enter_context(
                open_runtime_engine(destination, "ci-model-verify", purpose="read")
            )
            with writer.begin(), _deployment_connection(reader) as check, check.begin():
                verify(writer, "admit")
                verify(check, "read")
            return writer, reader

        writer = reader = None
        # Existing releases can preflight their ordinary routes before migration.
        # A fresh root installs those kernels before ordinary purpose admission.
        if prepared is not None and (starting_revision is not None or binding.revision is None):
            writer, reader = open_purpose_routes()

        target = binding.target_identity
        reached = binding.revision

        def settled(effect: str) -> None:
            assert reached is not None
            if checkpoint is not None:
                checkpoint(target, starting_revision, reached, effect)
            report(effect)

        if binding.revision is not None:
            assert versions is not None
            successor_physical = require_frozen_native_revision(versions, binding.revision)
            if sql_inputs is not None and sql_inputs.physical_id != successor_physical:
                raise SQLAdmissionError(
                    "authored SQL physical model differs from the approved revision"
                )
            with _commit_deployment_effect(
                conn,
                "migration",
                release=binding.release,
                reconcile=reconcile_migration,
                settled=settled,
            ):
                conn.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                target = verify(conn, "maintenance")
                migration_fence(conn)
                actual = current_revision(conn)
                if actual not in {starting_revision, binding.revision}:
                    raise ModelError(["acquired revision differs from the approved predecessor"])
                if actual is None:
                    from corpus_structure.semantic.target_installation import require_empty_target

                    require_empty_target(conn)
                else:
                    verify_deployment_catalog(conn, revision=actual, versions=versions)
                if checkpoint is not None and actual is not None and actual != binding.revision:
                    checkpoint(target, starting_revision, actual, None)
                upgrade(
                    conn,
                    binding.revision,
                    expected_predecessor=starting_revision,
                    script_location=script_location,
                )
                if current_revision(conn) != binding.revision:
                    raise ModelError(["migration did not reach the approved revision"])
                if actual != binding.revision:
                    verify_deployment_catalog(conn, revision=binding.revision, versions=versions)

        if prepared is None:
            assert binding.revision is not None
            with conn.begin():
                verify(conn, "maintenance")
                migration_fence(conn)
                if current_revision(conn) != binding.revision:
                    raise ModelError(["native revision changed before final catalog verification"])
                verify_deployment_catalog(conn, revision=binding.revision, versions=versions)
            settled("verified")
            return
        assert binding.release is not None and deployment is not None
        bundle, deps, profile, prepared = deployment
        if writer is None or reader is None:
            writer, reader = open_purpose_routes()

        with conn.begin():
            conn.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            target = verify(conn, "maintenance")
            migration_fence(conn)
            actual = current_revision(conn)
            if actual is None or (binding.revision is not None and actual != binding.revision):
                raise ModelError(["native revision changed before archive/admission"])
            physical_id = verify_deployment_catalog(conn, revision=actual, versions=versions)
            reached = actual
            if checkpoint is not None and binding.revision is None:
                checkpoint(target, starting_revision, reached, None)

            def verify_reader(snapshot: Connection) -> None:
                verify(snapshot, "read")

            analyzed = None
            if sql_inputs is not None:
                with _deployment_connection(reader) as sql_connection:
                    analyzed = analyze_release_sql(
                        sql_connection,
                        sql_inputs,
                        physical_id=physical_id,
                        verify_target=verify_reader,
                    )

            def exact_archive(snapshot: Connection) -> bool | None:
                exists = snapshot.scalar(
                    text("SELECT EXISTS(SELECT FROM sem.release WHERE release_id=:release)"),
                    {"release": binding.release},
                )
                if not exists:
                    return False
                archived = open_release(snapshot, binding.release)
                exact = (
                    archived.manifest == prepared.manifest
                    and archived.artifacts_sha256 == prepared.artifacts_sha256
                )
                return True if exact else None

            def reconcile_archive() -> bool | None:
                with _deployment_connection(reader) as recovery, recovery.begin():
                    recovery.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                    verify_reader(recovery)
                    recovery.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
                    release_fence(recovery)
                    return exact_archive(recovery)

            def observe_admission(observing: Connection) -> bool | None:
                native = observing.scalar(
                    text("""
                        WITH descriptor AS (
                            SELECT convert_to(
                                data.execution_contract_descriptor()::text,'UTF8'
                            ) body
                        ), expected AS (
                            SELECT body, encode(sha256(body),'hex') digest FROM descriptor
                        )
                        SELECT CASE
                            WHEN EXISTS (
                                SELECT FROM sem.deployment_admission a CROSS JOIN expected
                                WHERE a.release_id=:release AND a.physical_id=:physical_id
                                  AND a.kind='native' AND a.deployment_id=expected.digest
                                  AND a.content=expected.body AND a.content_digest=expected.digest
                            ) THEN true
                            WHEN EXISTS (
                                SELECT FROM sem.deployment_admission a CROSS JOIN expected
                                WHERE a.release_id=:release AND a.physical_id=:physical_id
                                  AND a.kind='native'
                                  AND (a.deployment_id=expected.digest OR a.content=expected.body)
                            ) THEN NULL
                            ELSE false
                        END
                    """),
                    {"release": binding.release, "physical_id": physical_id},
                )
                if native is not True:
                    return native
                if runtime is not None:
                    try:
                        retained = runtime_binding_for_release(
                            observing, prepared, runtime.runtime_id
                        )
                    except NoResultFound:
                        return False
                    except RuntimeBindingError:
                        return None
                    if retained != runtime:
                        return None
                if analyzed is None:
                    return True
                rows = observing.execute(
                    text("""
                        SELECT input_name, content, content_digest FROM sem.sql_admission
                        WHERE release_id=:release AND physical_id=:physical_id
                          AND input_kind='dependency'
                    """),
                    {"release": binding.release, "physical_id": physical_id},
                )
                observed = {name: (bytes(content), digest) for name, content, digest in rows}
                exact = {
                    name: (artifact.content, artifact.digest) for name, artifact in analyzed.items()
                }
                return True if observed == exact else None

            def reconcile_admission() -> bool | None:
                conn.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
                release_fence(conn)
                return observe_admission(conn)

            with _commit_deployment_effect(
                writer,
                "archive",
                release=binding.release,
                reconcile=reconcile_archive,
                settled=settled,
            ):
                verify(writer, "admit")
                release_fence(writer)
                archived = exact_archive(writer)
                if archived is None:
                    raise ModelError(["archived release differs from the candidate"])
                if not archived:
                    persist_release(writer, bundle, deps, profile, prepared)
            with _commit_deployment_effect(
                writer,
                "admission",
                release=binding.release,
                reconcile=reconcile_admission,
                settled=settled,
            ):
                verify(writer, "admit")
                release_fence(writer)
                if analyzed is not None:
                    admit_archived_sql(
                        writer, binding.release, analyzed=analyzed, physical_id=physical_id
                    )
                admit_data_operation_release(writer, prepared)
                if runtime is not None:
                    persist_runtime_binding(writer, prepared, runtime)
            with _deployment_connection(reader) as snapshot, snapshot.begin():
                snapshot.exec_driver_sql(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                )
                verify_reader(snapshot)
                # Native catalog correspondence uses the acquired maintenance
                # route: the execution descriptor is deliberately not a reader API.
                if not exact_archive(snapshot) or observe_admission(conn) is not True:
                    raise ModelError(
                        ["admitted release does not match the candidate release/runtime custody"]
                    )
                if (
                    runtime is not None
                    and runtime_binding_for_release(snapshot, prepared, runtime.runtime_id)
                    != runtime
                ):
                    raise ModelError(["reader runtime differs from reviewed custody"])
            settled("verified")
