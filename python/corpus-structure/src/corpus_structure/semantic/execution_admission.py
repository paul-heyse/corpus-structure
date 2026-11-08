"""Trusted execution compatibility at the immutable release activation boundary.

Contract compilation establishes the model's meaning and implementation requirements.
It does not establish that those requirements have native enforcement. In particular,
the execution lifecycle contracts cannot activate until their SP-C03 guards exist.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from .refusals import SemanticRefusal
from .types import PreparedRelease

if TYPE_CHECKING:
    from sqlalchemy import Connection

# Code support is distinct from deployment: composed admission additionally checks
# the exact native implementation on the caller's connection. This set is code-owned.
_NATIVE_CAPABILITIES = frozenset(
    {
        "semantic_registry",
        "scoped_publication",
        "typed_values",
        "execution.lifecycle.v1",
        "execution.identity_exclusions.v1",
        "execution.reference_evaluation.v1",
        "execution.selected_result.v1",
        "conditional_rules_native",
    }
)


class ExecutionAdmissionError(SemanticRefusal):
    """The archived binding lacks a compatible trusted enforcing implementation."""


def admit_execution_release(
    prepared: PreparedRelease, *, connection: Connection | None = None
) -> str:
    """Check current code compatibility and refuse unavailable required semantics.

    Pure compiled products may be reused by the compiler. Database state and permissions
    are checked by their existing owners on every activation and are never cached here.
    """
    if prepared.execution_model_id is not None:
        from .contracts import bound_execution_model

        current = bound_execution_model(prepared)
        for operation in current.operations:
            if operation.implementation is not None:
                current.require_operation(operation.id)
        missing_requirements = set(current.required_capabilities) - set(
            prepared.required_capabilities
        )
        if missing_requirements:
            raise ExecutionAdmissionError(
                "release omits required execution capabilities: "
                + ", ".join(sorted(missing_requirements))
            )
    if prepared.execution_model_id is None:
        raise ExecutionAdmissionError("native execution requires a composed model")
    unavailable = set(prepared.required_capabilities) - _NATIVE_CAPABILITIES
    if unavailable:
        raise ExecutionAdmissionError(
            "required native enforcement is unavailable: " + ", ".join(sorted(unavailable))
        )

    if connection is None:
        raise ExecutionAdmissionError("composed admission requires verified native deployment")
    from .unicode_identity import require_unicode_identity_release, requires_unicode_identity

    if requires_unicode_identity(prepared):
        require_unicode_identity_release(connection, prepared)
    return require_native_execution(connection, prepared)


_DESCRIPTOR = "data.execution_contract_descriptor"
_REQUIRED = "data.require_execution_release"


@dataclass(frozen=True)
class NativeExpectation:
    functions: tuple[str, str]
    physical_id: str
    guard_digest: str
    selected_fact_sql: str
    state: tuple[Path, str]
    admission_body: str


def _revision_expectation(versions: Path, revision: str) -> NativeExpectation:
    try:
        return _expectations(versions)[revision]
    except KeyError:
        raise ExecutionAdmissionError(
            f"native deployment lacks frozen expectations for {revision}"
        ) from None


def require_frozen_native_revision(versions: Path, revision: str) -> str:
    """Resolve and validate the approved successor before attempting its migration."""
    from .native_objects import NativeAuthoringError

    expected = _revision_expectation(versions, revision)
    try:
        _frozen_functions(*expected.state)
        _catalog_checks(expected.admission_body)
    except (NativeAuthoringError, OSError, ValueError) as exc:
        raise ExecutionAdmissionError(f"frozen native state is unavailable: {exc}") from exc
    return expected.physical_id


def _catalog_checks(body: str) -> str:
    """Reuse the immutable guard's catalog checks without its release reads or writes."""
    boundaries = (
        (
            " IF NOT EXISTS(SELECT FROM sem.physical_contract ",
            " IF EXISTS(SELECT FROM sem.release archived CROSS JOIN LATERAL",
        ),
        (
            " SELECT item.value INTO spec FROM jsonb_array_elements(expected->'functions')",
            " IF NOT EXISTS(SELECT FROM sem.deployment_admission ",
        ),
    )
    checks = []
    for first, following in boundaries:
        if body.count(first) != 1 or body.count(following) != 1:
            raise ValueError("frozen native guard does not identify its catalog checks")
        start, end = body.index(first), body.index(following)
        if end <= start:
            raise ValueError("frozen native guard has invalid catalog check boundaries")
        checks.append(body[start:end])
    return "\n".join(checks)


def verify_deployment_catalog(
    connection: Connection, *, revision: str, versions: Path | None = None
) -> str:
    """Verify the full known revision before an effect on the maintenance connection."""
    from sqlalchemy.exc import DBAPIError

    from .migrations import ALEMBIC_DIR
    from .native_objects import execute_native_sql

    versions = ALEMBIC_DIR / "versions" if versions is None else versions
    expected = _revision_expectation(versions, revision)
    physical_id = _verify_deployment_functions(connection, revision=revision, versions=versions)
    try:
        checks = _catalog_checks(expected.admission_body)
        # Run the exact catalog clauses in the same search path as the authenticated
        # guard, without running that guard's release-specific admission effects.
        savepoint = connection.begin_nested()
        try:
            connection.exec_driver_sql("SET LOCAL search_path = pg_catalog, pg_temp")
            execute_native_sql(
                connection,
                "DO $deployment_catalog$ DECLARE expected jsonb; spec jsonb; owner_name text; "
                "BEGIN expected := data.execution_contract_descriptor(); "
                "SELECT pg_get_userbyid(nspowner) INTO owner_name FROM pg_namespace "
                "WHERE nspname='sem';\n" + checks + "\nEND $deployment_catalog$",
            )
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


def _verify_deployment_functions(
    connection: Connection, *, revision: str | None = None, versions: Path | None = None
) -> str:
    """Compare the acquired catalog with its frozen expectations."""
    from sqlalchemy import text

    from .migrations import ALEMBIC_DIR
    from .native_objects import NativeAuthoringError, admit_native

    guard_digest = _realization_fence_digest(connection)
    if guard_digest is None:
        raise ExecutionAdmissionError("native execution requires an enforcing realization fence")
    if versions is None:
        versions = ALEMBIC_DIR / "versions"
    if revision is not None:
        candidates = (_revision_expectation(versions, revision),)
    else:
        # Reader and admission principals deliberately cannot read Alembic's private
        # revision table. A body fingerprint locates a contract, never an Alembic label.
        bodies = (
            connection.execute(
                text("""
                SELECT encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')
                FROM unnest(ARRAY['data.execution_contract_descriptor()',
                                  'data.require_execution_release(text)'])
                     WITH ORDINALITY AS target(signature, position)
                LEFT JOIN pg_catalog.pg_proc p ON p.oid=to_regprocedure(target.signature)
                ORDER BY target.position
            """)
            )
            .scalars()
            .all()
        )
        candidates = tuple(
            item for item in _expectations(versions).values() if item.functions == tuple(bodies)
        )
    candidates = tuple(item for item in candidates if item.guard_digest == guard_digest)
    if not candidates:
        raise ExecutionAdmissionError("native execution deployment differs from frozen contracts")

    try:
        # An unchanged contract may appear in several revisions. Compare the
        # scoped objects and descriptor semantics, not the containing state file.
        contracts = {
            (
                item.physical_id,
                item.selected_fact_sql,
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
        physical_id, expected_view, _ = contracts.pop()
        admit_native(connection, _frozen_functions(*candidates[0].state))
    except (NativeAuthoringError, OSError, ValueError) as exc:
        raise ExecutionAdmissionError(f"native execution deployment differs: {exc}") from exc

    from pglast import parse_sql
    from pglast.stream import RawStream

    actual_view = connection.scalar(
        text("SELECT pg_get_viewdef(to_regclass('data.selected_fact'),true)")
    )
    if actual_view is None or RawStream()(parse_sql(actual_view)) != RawStream()(
        parse_sql(expected_view)
    ):
        raise ExecutionAdmissionError("native selected-fact view differs from its model projection")
    return physical_id


def require_native_execution(connection: Connection, prepared: PreparedRelease) -> str:
    from sqlalchemy.exc import DBAPIError

    from ._operation_calls import require_native_execution_release
    from ._operation_ids import ReleaseId

    physical_id = _verify_deployment_functions(connection)
    try:
        require_native_execution_release(
            connection,
            release_id=ReleaseId(prepared.release_id),
        )
    except DBAPIError as exc:
        if getattr(exc.orig, "sqlstate", None) not in {"23514", "P0001"}:
            raise
        reason = str(exc.orig).splitlines()[0]
        raise ExecutionAdmissionError(
            "native execution deployment or archived binding is incompatible: "
            + reason
            + "; inspect the owning contract and derive a new reviewed revision with "
            "ci schema derive --out <new-directory>"
        ) from exc

    return physical_id


def require_archive_fence(connection: Connection) -> None:
    """Archive under either the exact refusal fence or the enforcing deployment."""
    if _realization_fence_digest(connection) is not None:
        _verify_deployment_functions(connection)


def _realization_fence_digest(connection: Connection) -> str | None:
    """Read the enforcing trigger body, or recognize the exact archive-only fence."""
    from sqlalchemy import text

    row = (
        connection.execute(
            text("""
      SELECT encode(sha256(convert_to(p.prosrc,'UTF8')),'hex') AS digest,
             pg_get_userbyid(p.proowner) AS owner,
             p.prosecdef,p.proconfig,
             ARRAY(SELECT a.attname::text FROM unnest(t.tgattr::smallint[])
                   WITH ORDINALITY attrs(num,position)
                   JOIN pg_attribute a ON a.attrelid=t.tgrelid AND a.attnum=attrs.num
                   ORDER BY attrs.position) AS update_columns,
             (SELECT pg_get_userbyid(nspowner) FROM pg_namespace
              WHERE nspname='sem') AS schema_owner
      FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
      WHERE t.tgrelid='data.realization'::regclass AND t.tgname='guard_execution_admission'
        AND NOT t.tgisinternal AND t.tgenabled IN ('O','A') AND t.tgqual IS NULL AND t.tgnargs=0
        AND t.tgtype=23 AND p.oid=to_regprocedure('data.guard_execution_admission()')
    """)
        )
        .mappings()
        .one_or_none()
    )
    if row is None or row["proconfig"] != ["search_path=pg_catalog, pg_temp"]:
        raise ExecutionAdmissionError("native execution archive fence is not deployed")
    if (
        row["digest"] == _REFUSAL_SHA256
        and row["prosecdef"] is False
        and row["owner"] == row["schema_owner"]
        and row["update_columns"] == ["release_id"]
    ):
        return None
    if (
        row["owner"] == "corpus_sem_publisher"
        and row["prosecdef"] is True
        and row["update_columns"] == []
    ):
        return row["digest"]
    raise ExecutionAdmissionError("native execution archive fence differs from trusted enforcement")


def _descriptor_sha256() -> str:
    """Inspect the authoring head's frozen descriptor for provenance checks."""
    from .migrations import ALEMBIC_DIR, head_revision

    head = head_revision()
    if head is None:
        raise ExecutionAdmissionError("authoring head is unavailable")
    return _expectations(ALEMBIC_DIR / "versions")[head].functions[0]


def _expectations(versions: Path) -> dict[str, NativeExpectation]:
    # Stat identities invalidate only the immutable artifact cache, never a live
    # catalog observation. Registration adds new trusted inputs to this set.
    stamps = tuple(
        (path, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
        for path in sorted(versions.iterdir())
        if path.suffix == ".py" or path.name.endswith(("_admission.sql", "_native.json"))
        for stat in (path.stat(),)
    )
    return _frozen_expectations(stamps)


@lru_cache(maxsize=4)
def _frozen_expectations(stamps) -> dict[str, NativeExpectation]:
    from pglast import ast as pgast
    from pglast import parse_sql

    from .native_products import function_bodies

    fields = {
        "revision",
        "down_revision",
        "NATIVE_ADMISSION_FILE",
        "NATIVE_ADMISSION_SHA256",
        "NATIVE_STATE_FILE",
        "NATIVE_STATE_SHA256",
    }
    revisions = {}
    expectations = {}
    try:
        for path, *_ in stamps:
            if path.suffix != ".py" or path.name == "__init__.py":
                continue
            declared = {
                target.id: ast.literal_eval(node.value)
                for node in ast.parse(path.read_bytes(), filename=path.name).body
                if isinstance(node, (ast.Assign, ast.AnnAssign))
                for target in (node.targets if isinstance(node, ast.Assign) else (node.target,))
                if isinstance(target, ast.Name) and target.id in fields and node.value is not None
            }
            revision = declared["revision"]
            if not isinstance(revision, str) or revision in revisions:
                raise ValueError("ambiguous revision")
            revisions[revision] = declared.get("down_revision")
            if "NATIVE_ADMISSION_FILE" not in declared:
                continue
            filename = declared["NATIVE_ADMISSION_FILE"]
            state = declared["NATIVE_STATE_FILE"]
            if Path(filename).name != filename or Path(state).name != state:
                raise ValueError("unsafe frozen native artifact")
            sql = path.with_name(filename).read_bytes()
            if sha256(sql).hexdigest() != declared["NATIVE_ADMISSION_SHA256"]:
                raise ValueError(f"{filename}: frozen native admission digest differs")
            bodies = function_bodies(sql.decode())
            body = bodies[_DESCRIPTOR]
            # The frozen descriptor is a single literal JSON SELECT. Read the
            # literal from the trusted SQL rather than execute it on a target.
            (statement,) = parse_sql(body)
            query = statement.stmt
            if not isinstance(query, pgast.SelectStmt) or query.targetList is None:
                raise ValueError("frozen native descriptor is not a SELECT")
            (column,) = query.targetList
            value = column.val if isinstance(column, pgast.ResTarget) else None
            if (
                not isinstance(value, pgast.TypeCast)
                or not isinstance(value.arg, pgast.A_Const)
                or not isinstance(value.arg.val, pgast.String)
            ):
                raise ValueError("frozen native descriptor is not a literal")
            literal = value.arg.val.sval
            if literal is None:
                raise ValueError("frozen native descriptor lacks a literal value")
            descriptor = json.loads(literal)
            (view,) = (
                item["query"]
                for item in descriptor["views"]
                if item["relation"] == "data.selected_fact"
            )
            (guard,) = (
                item["body_sha256"]
                for item in descriptor["functions"]
                if item["signature"] == "data.guard_execution_admission()"
            )
            expectations[revision] = NativeExpectation(
                (sha256(body.encode()).hexdigest(), sha256(bodies[_REQUIRED].encode()).hexdigest()),
                descriptor["physical_id"],
                guard,
                view,
                (path.with_name(state), declared["NATIVE_STATE_SHA256"]),
                bodies[_REQUIRED],
            )

        def inherited(revision, visiting):
            if revision in expectations:
                return expectations[revision]
            predecessor = revisions.get(revision)
            if not isinstance(predecessor, str) or predecessor in visiting:
                return None
            return inherited(predecessor, visiting | {revision})

        return {
            revision: expectation
            for revision in revisions
            if (expectation := inherited(revision, set())) is not None
        }
    except (OSError, SyntaxError, ValueError, KeyError, AttributeError, TypeError) as exc:
        raise ExecutionAdmissionError(f"frozen native expectations are unavailable: {exc}") from exc


def _frozen_functions(path: Path, digest: str):
    stamp = path.stat()
    return _cached_frozen_functions(path, digest, stamp.st_mtime_ns, stamp.st_ctime_ns)


@lru_cache(maxsize=32)
def _cached_frozen_functions(path: Path, digest: str, _mtime: int, _ctime: int):
    from .native_candidate import load_native_state

    selected = tuple(
        item
        for item in load_native_state(path, digest=digest)
        if item.identity.kind == "function"
        and f"{item.identity.schema}.{item.identity.name}" in {_DESCRIPTOR, _REQUIRED}
    )
    if len(selected) != 2:
        raise ValueError(f"{path.name}: required native enforcement functions are unavailable")
    return tuple(sorted(selected, key=lambda item: item.identity.qualified))


# The realization trigger predates frozen native state. Preserve the independent
# exact refusal and enforcing trigger contracts.
_REFUSAL_SHA256 = "e5dc0f2a81371d4091c1d80a4fe4de6f5c94f519b9d916ffae486e9b75f4e462"
_GUARD_SHA256 = "225ab497a6a3c33dfa895ba3ca977de9a27f86d7777c84f92e0bc47edbba98a6"
