"""Current native execution authority from exact registered frozen contracts.

Compilation supplies model meaning; the deployed descriptor and release guard
must match their frozen state before current admission or archive effects.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from .refusals import SemanticRefusal
from .types import PreparedRelease

if TYPE_CHECKING:
    from sqlalchemy import Connection


class ExecutionAdmissionError(SemanticRefusal):
    """The archived binding lacks a compatible trusted enforcing implementation."""


def admit_execution_release(
    prepared: PreparedRelease, *, connection: Connection | None = None
) -> str:
    """Check current code compatibility and refuse unavailable required semantics.

    Pure compiled products may be reused by the compiler. Database state and permissions
    are checked by their existing owners on every activation and are never cached here.
    """
    from .data_operation_admission import admit_data_operation_release, bound_data_operation_model

    bound_data_operation_model(prepared)
    if connection is None:
        raise ExecutionAdmissionError("target admission requires verified native deployment")
    return admit_data_operation_release(connection, prepared)


_DESCRIPTOR = "data.execution_contract_descriptor"
_REQUIRED = "data.require_execution_release"
_PROOF = "data.prove_execution_release"
_CATALOG = "data.prove_execution_catalog"


@dataclass(frozen=True)
class NativeExpectation:
    functions: tuple[str, str]
    physical_id: str
    state: tuple[Path, str]
    admission_body: str
    named_catalog_proof: bool = False


def _revision_expectation(versions: Path, revision: str) -> NativeExpectation:
    selected = _expectation_metadata(_revision_index(versions), revision)
    if selected is None:
        raise ExecutionAdmissionError(f"native deployment lacks frozen expectations for {revision}")
    return _selected_expectation(selected)


def require_frozen_native_revision(versions: Path, revision: str) -> str:
    """Resolve and validate the approved successor before attempting its migration."""
    from .native_objects import NativeAuthoringError

    expected = _revision_expectation(versions, revision)
    try:
        _frozen_functions(*expected.state)
        if not expected.named_catalog_proof:
            _catalog_checks(expected.admission_body)
    except (NativeAuthoringError, OSError, ValueError) as exc:
        raise ExecutionAdmissionError(f"frozen native state is unavailable: {exc}") from exc
    return expected.physical_id


def _catalog_checks(body: str) -> str:
    from .native_admission import catalog_checks

    return catalog_checks(body)


def verify_deployment_catalog(
    connection: Connection, *, revision: str | None = None, versions: Path | None = None
) -> str:
    """Verify the full known revision before an effect on the maintenance connection."""
    from sqlalchemy import func, select
    from sqlalchemy.exc import DBAPIError

    from .migrations import ALEMBIC_DIR
    from .native_admission import frozen_catalog_verification
    from .native_objects import execute_native_sql

    versions = ALEMBIC_DIR / "versions" if versions is None else versions
    expected = _deployment_expectation(connection, revision=revision, versions=versions)
    physical_id = expected.physical_id
    try:
        savepoint = connection.begin_nested()
        try:
            if expected.named_catalog_proof:
                connection.execute(select(func.data.prove_execution_catalog()))
            else:
                verification = frozen_catalog_verification(expected.admission_body)
                connection.exec_driver_sql("SET LOCAL search_path = pg_catalog, pg_temp")
                execute_native_sql(connection, verification)
        finally:
            savepoint.rollback()
    except (DBAPIError, ValueError) as exc:
        original = exc.orig if isinstance(exc, DBAPIError) else exc
        if isinstance(exc, DBAPIError) and getattr(original, "sqlstate", None) not in {
            "23514",
            "42501",
        }:
            raise
        raise ExecutionAdmissionError(
            f"native deployment catalog differs: {str(original).splitlines()[0]}"
        ) from exc
    return physical_id


def _deployment_expectation(
    connection: Connection, *, revision: str | None = None, versions: Path | None = None
) -> NativeExpectation:
    """Compare the acquired catalog with its frozen expectations."""
    from .migrations import ALEMBIC_DIR
    from .native_catalog import function_body_fingerprints
    from .native_objects import NativeAuthoringError, admit_native

    if versions is None:
        versions = ALEMBIC_DIR / "versions"
    if revision is not None:
        candidates = (_revision_expectation(versions, revision),)
    else:
        # Reader and admission principals deliberately cannot read Alembic's private
        # revision table. A body fingerprint locates a contract, never an Alembic label.
        bodies = connection.scalars(
            function_body_fingerprints((_DESCRIPTOR + "()", _REQUIRED + "(text)"))
        ).all()
        candidates = tuple(
            item for item in _expectations(versions).values() if item.functions == tuple(bodies)
        )
    if not candidates:
        raise ExecutionAdmissionError("native execution deployment differs from frozen contracts")

    try:
        # An unchanged contract may appear in several revisions. Compare the
        # scoped objects and descriptor semantics, not the containing state file.
        contracts = {
            (
                item.physical_id,
                tuple(
                    (
                        obj.identity,
                        obj.catalog_json,
                        obj.role_bindings,
                        obj.catalog_version,
                        obj.binding_version,
                    )
                    for obj in _frozen_functions(*item.state)
                ),
            )
            for item in candidates
        }
        if len(contracts) != 1:
            raise ExecutionAdmissionError(
                "native execution deployment has conflicting expectations"
            )
        contracts.pop()
        admit_native(connection, _frozen_functions(*candidates[0].state))
    except (NativeAuthoringError, OSError, ValueError) as exc:
        raise ExecutionAdmissionError(f"native execution deployment differs: {exc}") from exc

    return candidates[0]


def verify_deployment_functions(
    connection: Connection, *, revision: str | None = None, versions: Path | None = None
) -> str:
    """Authenticate the current descriptor and enforcing release guard."""
    return _deployment_expectation(connection, revision=revision, versions=versions).physical_id


def require_native_execution(connection: Connection, prepared: PreparedRelease) -> str:
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from .data_operation_admission import bound_data_operation_model

    bound_data_operation_model(prepared)

    physical_id = verify_deployment_functions(connection)
    try:
        connection.execute(
            text("SELECT data.require_execution_release(:release)"),
            {"release": prepared.release_id},
        )
    except DBAPIError as exc:
        if getattr(exc.orig, "sqlstate", None) not in {"23514", "P0001"}:
            raise
        reason = str(exc.orig).splitlines()[0]
        raise ExecutionAdmissionError(
            "native execution deployment or archived binding is incompatible: "
            + reason
            + "; inspect the owning contract and prepare a reviewed current revision with "
            "ci model change preview"
        ) from exc

    return physical_id


def require_archive_fence(connection: Connection) -> None:
    """Require current frozen native/physical/privilege custody before archive effects."""
    verify_deployment_catalog(connection)


def _descriptor_sha256() -> str:
    """Inspect the authoring head's frozen descriptor for provenance checks."""
    from .migrations import ALEMBIC_DIR, head_revision

    head = head_revision()
    if head is None:
        raise ExecutionAdmissionError("authoring head is unavailable")
    return _revision_expectation(ALEMBIC_DIR / "versions", head).functions[0]


@dataclass(frozen=True)
class _RevisionMetadata:
    revision: str
    predecessor: str | None
    admission: tuple[Path, str] | None
    state: tuple[Path, str] | None


def _file_identity(path: Path) -> tuple[Path, int, int, int]:
    stamp = path.stat()
    return path, stamp.st_mtime_ns, stamp.st_ctime_ns, stamp.st_size


def _revision_index(versions: Path) -> dict[str, _RevisionMetadata]:
    try:
        identities = tuple(
            _file_identity(path)
            for path in sorted(versions.glob("*.py"))
            if path.name != "__init__.py"
        )
        return _cached_revision_index(identities)
    except (OSError, SyntaxError, ValueError, KeyError, AttributeError, TypeError) as exc:
        raise ExecutionAdmissionError(
            f"frozen native revision metadata is unavailable: {exc}"
        ) from exc


def _artifact_metadata(path: Path, declared: dict[str, object], kind: str) -> tuple[Path, str]:
    filename = declared[f"NATIVE_{kind}_FILE"]
    digest = declared[f"NATIVE_{kind}_SHA256"]
    if (
        not isinstance(filename, str)
        or not filename
        or Path(filename).name != filename
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        raise ValueError(f"{path.name}: unsafe frozen native artifact metadata")
    target = path.with_name(filename)
    if target.resolve().parent != path.parent.resolve():
        raise ValueError(f"{path.name}: unsafe frozen native artifact path")
    return target, digest


@lru_cache(maxsize=4)
def _cached_revision_index(identities) -> dict[str, _RevisionMetadata]:
    fields = {
        "revision",
        "down_revision",
        "NATIVE_ADMISSION_FILE",
        "NATIVE_ADMISSION_SHA256",
        "NATIVE_STATE_FILE",
        "NATIVE_STATE_SHA256",
    }
    revisions = {}
    for path, *_ in identities:
        declared = {}
        for node in ast.parse(path.read_bytes(), filename=path.name).body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            for target in node.targets if isinstance(node, ast.Assign) else (node.target,):
                if isinstance(target, ast.Name) and target.id in fields:
                    if target.id in declared or node.value is None:
                        raise ValueError(f"{path.name}: duplicate or missing revision metadata")
                    declared[target.id] = ast.literal_eval(node.value)
        revision = declared["revision"]
        predecessor = declared["down_revision"]
        if not isinstance(revision, str) or not revision or revision in revisions:
            raise ValueError(f"{path.name}: ambiguous revision")
        if predecessor is not None and (not isinstance(predecessor, str) or not predecessor):
            raise ValueError(f"{path.name}: invalid revision predecessor")
        artifact_fields = fields - {"revision", "down_revision"}
        present = artifact_fields & declared.keys()
        if present and present != artifact_fields:
            raise ValueError(f"{path.name}: incomplete frozen native metadata")

        revisions[revision] = _RevisionMetadata(
            revision,
            predecessor,
            _artifact_metadata(path, declared, "ADMISSION") if present else None,
            _artifact_metadata(path, declared, "STATE") if present else None,
        )
    return revisions


def _expectation_metadata(
    revisions: dict[str, _RevisionMetadata], revision: str
) -> _RevisionMetadata | None:
    seen = set()
    current = revision
    while True:
        if current in seen:
            raise ExecutionAdmissionError(
                f"frozen native revision inheritance has a cycle: {current}"
            )
        seen.add(current)
        metadata = revisions.get(current)
        if metadata is None:
            raise ExecutionAdmissionError(
                f"frozen native revision predecessor is unavailable: {current}"
            )
        if metadata.admission is not None:
            return metadata
        if metadata.predecessor is None:
            return None
        current = metadata.predecessor


def _expectations(versions: Path) -> dict[str, NativeExpectation]:
    """Discover current registered contracts by their exact native body fingerprints."""
    revisions = _revision_index(versions)
    try:
        identities = tuple(
            (metadata, _file_identity(metadata.admission[0]), _file_identity(metadata.state[0]))
            for metadata in revisions.values()
            if metadata.admission is not None and metadata.state is not None
        )
        return _cached_all_expectations(tuple(revisions.items()), identities)
    except OSError as exc:
        raise ExecutionAdmissionError(f"frozen native expectations are unavailable: {exc}") from exc


@lru_cache(maxsize=4)
def _cached_all_expectations(metadata_items, _artifact_identities) -> dict[str, NativeExpectation]:
    revisions = dict(metadata_items)
    return {
        revision: _selected_expectation(metadata)
        for revision in revisions
        if (metadata := _expectation_metadata(revisions, revision)) is not None
    }


def _selected_expectation(metadata: _RevisionMetadata) -> NativeExpectation:
    from pglast.error import Error as PostgreSQLParseError

    assert metadata.admission is not None and metadata.state is not None
    try:
        return _cached_selected_expectation(
            metadata, _file_identity(metadata.admission[0]), _file_identity(metadata.state[0])
        )
    except (
        OSError,
        SyntaxError,
        ValueError,
        KeyError,
        AttributeError,
        TypeError,
        PostgreSQLParseError,
    ) as exc:
        raise ExecutionAdmissionError(f"frozen native expectations are unavailable: {exc}") from exc


@lru_cache(maxsize=32)
def _cached_selected_expectation(
    metadata: _RevisionMetadata, _admission_identity, _state_identity
) -> NativeExpectation:
    from .native_products import function_bodies, literal_json_descriptor

    assert metadata.admission is not None and metadata.state is not None
    path, digest = metadata.admission
    sql = path.read_bytes()
    if sha256(sql).hexdigest() != digest:
        raise ValueError(f"{path.name}: frozen native admission digest differs")
    bodies = function_bodies(sql.decode())
    body = bodies[_DESCRIPTOR]
    descriptor = literal_json_descriptor(sql.decode(), _DESCRIPTOR)
    return NativeExpectation(
        (sha256(body.encode()).hexdigest(), sha256(bodies[_REQUIRED].encode()).hexdigest()),
        descriptor["physical_id"],
        metadata.state,
        bodies.get(_CATALOG, bodies.get(_PROOF, bodies[_REQUIRED])),
        _CATALOG in bodies,
    )


def _frozen_functions(path: Path, digest: str):
    stamp = path.stat()
    return _cached_frozen_functions(path, digest, stamp.st_mtime_ns, stamp.st_ctime_ns)


@lru_cache(maxsize=32)
def _cached_frozen_functions(path: Path, digest: str, _mtime: int, _ctime: int):
    from .native_authoring import load_native_state

    selected = {
        f"{item.identity.schema}.{item.identity.name}": item
        for item in load_native_state(path, digest=digest)
        if item.identity.kind == "function"
        and f"{item.identity.schema}.{item.identity.name}"
        in {_DESCRIPTOR, _REQUIRED, _PROOF, _CATALOG}
    }
    if not {_DESCRIPTOR, _REQUIRED} <= selected.keys():
        raise ValueError(f"{path.name}: required native enforcement functions are unavailable")
    return tuple(selected[name] for name in sorted(selected))
