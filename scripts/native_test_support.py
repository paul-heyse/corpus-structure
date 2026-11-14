"""Shared native PostgreSQL fixture lifecycle and typed database-policy replay.

Importing this module acquires no settings, database, process or provider resource.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Generator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from sqlalchemy import Connection, Engine, create_engine, event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.pool import NullPool

from corpus_structure.core.db import extensions
from corpus_structure.core.db.ownership import (
    DatabaseCreation,
    DatabaseReservation,
    OwnedDatabase,
    acknowledged_database,
    is_owned_stamp,
    stamp_owned,
)
from corpus_structure.settings import Settings
from test_prerequisites import PrerequisiteUnavailable

if TYPE_CHECKING:
    from corpus_structure.semantic.runtime import Purpose


REPO = Path(__file__).resolve().parents[1]
EXTENSION_RECORD = extensions.EXTENSION_RECORD
PROVISION = (
    "run `just db-provision` (the dedicated cluster 18/corpus with cs_template, D3 §13), "
    "or point CORPUS_DATABASE__URL at a server that has it"
)
LEASE_SPACE = 0x63735450
_DEPLOYMENTS: dict[tuple[str, str, str, int], dict[str, object]] = {}


@dataclass(frozen=True)
class DatabaseName:
    name: str
    lease_key: str
    sweep_rule: Literal["unleased", "retained"]


@dataclass(frozen=True)
class _NameRule:
    prefix: str
    fields: tuple[str, ...]
    sweep_rule: Literal["unleased", "retained"] = "unleased"

    def recognize(self, name: str) -> DatabaseName | None:
        suffix = "_".join(_NAME_FIELDS[field] for field in self.fields)
        if re.fullmatch(re.escape(self.prefix) + suffix, name):
            return DatabaseName(name, name, self.sweep_rule)
        return None


_NAME_FIELDS = {
    "pid": r"[1-9][0-9]*",
    "token": r"[0-9a-f]{12}",
    "key": r"[0-9a-f]{16}",
    "run": r"[0-9a-f]{8}",
}
_NAME_RULES = {
    "session": _NameRule("ci_test_", ("pid",)),
    **{
        kind: _NameRule(f"cs_sem_{kind}_", ("pid", "token"))
        for kind in (
            "infra",
            "infra_case",
            "test",
            "bare",
            "revision",
            "init",
            "build",
            "stale",
            "seed",
        )
    },
    "reusable_head": _NameRule("cs_sem_head_", ("key",), "retained"),
    "run_private_head": _NameRule("cs_sem_head_", ("key", "run")),
}


def database_name(
    kind: str,
    *,
    pid: int | None = None,
    token: str | None = None,
    key: str | None = None,
    run: str | None = None,
) -> DatabaseName:
    """Produce a test database identity and its lifecycle rule from one declaration."""
    rule = _NAME_RULES[kind]
    values = {
        "pid": str(os.getpid() if pid is None else pid),
        "token": uuid4().hex[:12] if token is None else token,
        "key": key[:16] if key is not None else "",
        "run": run[:8] if run is not None else "",
    }
    name = rule.prefix + "_".join(values[field] for field in rule.fields)
    identity = rule.recognize(name)
    if identity is None or len(name) > 63:
        raise ValueError(f"invalid parameters for database kind {kind!r}")
    return identity


def recognize_database_name(name: str) -> DatabaseName | None:
    for rule in _NAME_RULES.values():
        if identity := rule.recognize(name):
            return identity
    return None


@dataclass(frozen=True)
class SweepResult:
    dropped: tuple[str, ...]
    skipped: tuple[str, ...]


@contextmanager
def rollback_connection(
    engine: Engine,
    *,
    readonly: bool = False,
    isolation_level: str | None = None,
    enforce: bool = True,
) -> Generator[Connection]:
    """Lend one connection whose outer transaction rolls back on every exit."""
    with engine.connect() as conn:
        if isolation_level is not None:
            conn = conn.execution_options(isolation_level=isolation_level)
        if readonly:
            conn = conn.execution_options(postgresql_readonly=True)
        outer = conn.begin()
        primary: BaseException | None = None
        try:
            yield conn
        except BaseException as error:
            primary = error
            raise
        finally:
            inactive = not outer.is_active
            if not inactive:
                outer.rollback()
            if inactive and enforce:
                violation = RuntimeError(
                    "borrowed outer transaction was committed or rolled back by its consumer"
                )
                if primary is not None:
                    raise BaseExceptionGroup(
                        "rollback case transaction contract failed", [primary, violation]
                    ) from None
                raise violation


class RollbackCase:
    """Connections belong to one rollback-only case; the reader sees committed state only."""

    def __init__(
        self,
        connection: Connection,
        reader: Engine,
        settings: Settings,
        database: str,
        *,
        scenario_seed: Mapping[str, str] | None = None,
        stage: object = None,
    ):
        self.connection = connection
        self.reader = reader
        self._settings = settings
        self._database = database
        self.origin = scenario_seed
        self.stage = stage

    @contextmanager
    def principal(
        self, purpose: Purpose, isolation_level: str | None = None
    ) -> Generator[Connection]:
        engine = principal_engine(
            self._settings, purpose, self._database, scenario_seed=self.origin
        )
        try:
            with rollback_connection(engine, isolation_level=isolation_level) as connection:
                yield connection
        finally:
            engine.dispose()


@contextmanager
def rollback_case(
    server: PgAdmin,
    settings: Settings,
    database: str,
    *,
    scenario_seed: Mapping[str, str] | None = None,
    stage: object = None,
    reader_purpose: Purpose = "read",
) -> Generator[RollbackCase]:
    """One case implementation over either the semantic session or a seeded family clone."""
    engine = create_engine(server.url_of(database), poolclass=NullPool)
    observe_engine(engine, purpose="maintenance", scenario_seed=scenario_seed)
    reader = principal_engine(
        settings, reader_purpose, database, readonly=True, scenario_seed=scenario_seed
    )
    try:
        with rollback_connection(engine) as connection:
            yield RollbackCase(
                connection, reader, settings, database, scenario_seed=scenario_seed, stage=stage
            )
    finally:
        reader.dispose()
        engine.dispose()


def server_url(settings: Settings | None = None) -> str:
    """The admin URL (database `postgres`) of the server `Settings()` names, as SQLAlchemy's."""
    settings = Settings() if settings is None else settings
    from corpus_structure.semantic.runtime import connection_settings

    url = make_url(connection_settings(settings, "maintenance").database.sqlalchemy_url).set(
        database="postgres"
    )
    return url.render_as_string(hide_password=False)


def expected_extensions(path: Path = EXTENSION_RECORD) -> dict[str, str]:
    """The record of expected extension versions (DA-018), read by the product's reader."""
    return extensions.expected_extensions(path)


def quote(name: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
        raise ValueError(f"unexpected database name {name!r}")
    return f'"{name}"'


def lock_sql(function: str) -> str:
    """One advisory-lock call on the key of the name bound to `:name`."""
    return f"SELECT {function}({LEASE_SPACE}, hashtext(:name))"


@dataclass(frozen=True, order=True)
class DatabaseGrant:
    grantor: str
    grantee: str
    privilege: str
    grantable: bool


@dataclass(frozen=True, order=True)
class DatabaseSetting:
    role: str  # empty means the all-role ALTER DATABASE setting (setrole=0)
    key: str
    value: str


@dataclass(frozen=True)
class DatabasePolicy:
    owner: str
    connection_limit: int
    grants: tuple[DatabaseGrant, ...]
    settings: tuple[DatabaseSetting, ...]


class SemanticDeployment:
    """Hold a sealed head and expose only clones that crossed its verification boundary."""

    def __init__(
        self, server: PgAdmin, key: str, run_id: str, run_scope: str, private: bool
    ) -> None:
        self.server = server
        self.key = key
        self.run_id = run_id
        self.run_scope = run_scope
        self._usage = ExitStack()
        self._lock = threading.RLock()
        self._recorded = False
        self._closed = False
        self.gap: dict[str, object] | None = None
        self._acquire(private)

    def _acquire(self, private: bool) -> None:
        identity = database_name(
            "run_private_head" if private else "reusable_head", key=self.key, run=self.run_id
        )
        usage = ExitStack()
        try:
            usage.enter_context(self.server.lease(identity.lease_key))
            with self.server.lease(identity.lease_key + ":build", exclusive=True):
                policy, built = self.server._publish_deployment(identity.name)
            self.name, self.policy, self.built = identity.name, policy, built
            self.verification = "fresh" if built or private else "pending"
            if not private:
                self.server._retain_deployments()
            self._usage = usage.pop_all()
        finally:
            usage.close()

    def _record(self) -> None:
        if self._recorded or not native_context_active():
            return
        from qualification_plugin import record_native_context

        record_native_context(
            {
                "native_test_deployment": {
                    "head": self.name,
                    "key": self.key,
                    "run_scope": self.run_scope,
                    "acquisition": "built" if self.built else "reused",
                    "verification": self.verification,
                    "deployment_key_gap": self.gap,
                }
            },
            scope="session",
        )
        self._recorded = True

    def _replace(self, error: Exception) -> None:
        stale = self.name
        with self.server.lease(stale + ":build", exclusive=True):
            self._usage.close()
            retirement = self.server._retire_deployment(stale)
            self.gap = {
                "stale_head": stale,
                "reason": str(error).splitlines()[0],
                "retirement": retirement,
            }
            print(
                f"Native deployment key gap: {stale}; replacing with a fresh run-private head",
                file=sys.stderr,
            )
            self._acquire(True)

    @contextmanager
    def clone(self, name: str) -> Generator[Engine]:
        from corpus_structure.semantic.execution_admission import (
            ExecutionAdmissionError,
            verify_deployment_catalog,
        )
        from corpus_structure.semantic.migrations import current_revision, head_revision

        with ExitStack() as owned_clone:
            with self._lock:
                if self._closed:
                    raise RuntimeError("native deployment acquisition is closed")
                engine = owned_clone.enter_context(
                    self.server.database(name, self.name, policy=self.policy)
                )
                if self.verification == "pending":
                    self.verification = "in_progress"
                    try:
                        with rollback_connection(engine) as connection:
                            expected = head_revision()
                            if expected is None or current_revision(connection) != expected:
                                raise ExecutionAdmissionError(
                                    "native deployment revision differs from the current head"
                                )
                            verify_deployment_catalog(connection, revision=expected)
                    except ExecutionAdmissionError as error:
                        self.verification = "failed"
                        owned_clone.close()
                        self._replace(error)
                        engine = owned_clone.enter_context(
                            self.server.database(name, self.name, policy=self.policy)
                        )
                    else:
                        self.verification = "verified"
                self._record()
            # Consumer exceptions cannot enter stale-head replacement.
            yield engine

    def close(self) -> None:
        try:
            self._record()
        finally:
            self._closed = True
            self._usage.close()


def semantic_principals() -> dict[str, str]:
    """The provisioning script owns canonical role names, without probing the host."""
    result = subprocess.run(
        ["bash", str(REPO / "scripts/pg_semantic_roles.sh"), "--principals"],
        text=True,
        capture_output=True,
        check=True,
    )
    return dict(line.split() for line in result.stdout.splitlines())


class PgAdmin:
    """Database-level operations on the test server, each on its own autocommit connection."""

    def __init__(
        self,
        url: str,
        template: str,
        expected: Mapping[str, str] | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.url = url
        self.template = template
        self.expected = dict(expected_extensions() if expected is None else expected)
        self._deployment_key: str | None = None
        self._semantic_ready = False
        # Resolve only the existing purpose credentials, once against the original endpoint.
        # Role-self replay later changes the database to postgres, never the authentication.
        self._purpose_settings = settings
        self._purpose_urls: tuple[URL, ...] | None = None

    def url_of(self, name: str) -> str:
        return make_url(self.url).set(database=name).render_as_string(hide_password=False)

    def alternate_reader(self, database: str):
        from native_auth import alternate_reader

        return alternate_reader(self, database)

    @contextmanager
    def connect(
        self, name: str = "postgres", *, transactional: bool = False
    ) -> Generator[Connection]:
        engine = create_engine(
            self.url_of(name),
            poolclass=NullPool,
            isolation_level="READ COMMITTED" if transactional else "AUTOCOMMIT",
        )
        observe_engine(engine, purpose="maintenance")
        try:
            with engine.begin() if transactional else engine.connect() as conn:
                yield conn
        finally:
            engine.dispose()

    def names(self, prefix: str) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                text("SELECT datname FROM pg_database WHERE starts_with(datname, :p)"),
                {"p": prefix},
            )
            return sorted(row[0] for row in rows)

    def exists(self, name: str) -> bool:
        return name in self.names(name)

    def create(
        self, name: str, template: str, *, creation: DatabaseCreation | None = None
    ) -> OwnedDatabase:
        # CREATE deliberately refuses a collision; a name is never disposal authority.
        creation = creation or DatabaseCreation(DatabaseReservation.new(name))
        if creation.reservation.name != name:
            raise ValueError("creation reservation names another database")
        with self.connect() as conn:
            conn.execute(text(f"CREATE DATABASE {quote(name)} TEMPLATE {quote(template)}"))
            owned = creation.acknowledge(conn)
            self.tag(conn, name, owned)
            return owned

    def tag(self, conn: Connection, name: str, owned: OwnedDatabase) -> None:
        if owned.reservation.name != name:
            raise ValueError("ownership acknowledgement names another database")
        stamp_owned(conn, owned)

    def drop(self, name: str) -> None:
        self._drop(name)

    @staticmethod
    def _wait_for_backend_exit(name: str, operation: Callable[[], bool]) -> None:
        # libpq close can precede the backend's final exit. One bounded owner serves
        # publication and cleanup; it never terminates a backend or grants disposal authority.
        deadline = time.monotonic() + 2.0
        while True:
            pending: DBAPIError | None = None
            try:
                if operation():
                    return
            except DBAPIError as error:
                if getattr(error.orig, "sqlstate", None) != "55006":
                    raise
                pending = error
            if time.monotonic() >= deadline:
                if pending is not None:
                    raise pending
                raise RuntimeError(f"database {name!r} still has connected backends")
            time.sleep(0.05)

    def _drop(self, name: str, *, owned: OwnedDatabase | None = None) -> None:
        def attempt() -> bool:
            with self.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT oid,pg_get_userbyid(datdba),"
                        " shobj_description(oid,'pg_database'), "
                        "current_user FROM pg_database WHERE datname=:name"
                    ),
                    {"name": name},
                ).one_or_none()
                if row is None:
                    return True
                oid, owner, comment, user = row
                authenticated = (
                    oid == owned.oid and owner == owned.owner
                    if owned is not None
                    else self.owned_comment(comment, oid)
                )
                if owner != user or not authenticated:
                    raise RuntimeError(f"refusing to drop unauthenticated database {name!r}")
                conn.execute(text(f"DROP DATABASE {quote(name)}"))
            return True

        self._wait_for_backend_exit(name, attempt)

    @staticmethod
    def owned_comment(comment: str | None, oid: int) -> bool:
        return is_owned_stamp(comment, oid)

    def check_roles(self, principals: Mapping[str, str]) -> None:
        with self.connect() as conn:
            available = set(conn.execute(text("SELECT rolname FROM pg_roles")).scalars())
        missing = sorted(set(principals.values()) - available)
        if missing:
            raise PrerequisiteUnavailable(
                "postgres-roles",
                "semantic principals missing: "
                + ", ".join(missing)
                + "; run `just db-semantic-roles`",
            )

    def policy(self, name: str) -> DatabasePolicy:
        """Read source policy from postgres; never open a connection to a clone source."""
        with self.connect() as conn:
            owner, limit = conn.execute(
                text(
                    "SELECT pg_get_userbyid(datdba),datconnlimit "
                    "FROM pg_database WHERE datname=:name"
                ),
                {"name": name},
            ).one()
            grants = tuple(
                sorted(
                    DatabaseGrant(*row)
                    for row in conn.execute(
                        text(
                            "SELECT pg_get_userbyid(a.grantor), "
                            "CASE WHEN a.grantee=0 THEN 'PUBLIC' "
                            "ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,a.is_grantable "
                            "FROM pg_database d CROSS JOIN LATERAL "
                            "aclexplode(COALESCE(d.datacl,acldefault('d',d.datdba))) a "
                            "WHERE d.datname=:name"
                        ),
                        {"name": name},
                    )
                )
            )
            settings = tuple(
                sorted(
                    DatabaseSetting(role, *setting.split("=", 1))
                    for role, setting in conn.execute(
                        text(
                            "SELECT CASE WHEN s.setrole=0 THEN '' "
                            "ELSE pg_get_userbyid(s.setrole) END, "
                            "unnest(s.setconfig) FROM pg_db_role_setting s JOIN pg_database d "
                            "ON d.oid=s.setdatabase WHERE d.datname=:name"
                        ),
                        {"name": name},
                    )
                )
            )
        return DatabasePolicy(owner, limit, grants, settings)

    def replay_policy(self, name: str, policy: DatabasePolicy) -> None:
        """Replay the present owner-granted ACL through its authorized identity, fail closed.

        A non-owner grant graph requires a separately designed authority path; silently changing
        grantors or obtaining superuser authority would not preserve policy.
        """
        if any(grant.grantor != policy.owner for grant in policy.grants):
            raise RuntimeError("database ACL replay requires owner-granted source privileges")
        with self.connect() as conn:
            q = conn.dialect.identifier_preparer.quote

            conn.exec_driver_sql(f"ALTER DATABASE {q(name)} OWNER TO {q(policy.owner)}")
            conn.exec_driver_sql(
                f"ALTER DATABASE {q(name)} CONNECTION LIMIT {policy.connection_limit}"
            )
            before = self.policy(name)
            conn.exec_driver_sql(f"SET ROLE {q(policy.owner)}")
            try:
                for grantee in sorted({g.grantee for g in before.grants}):
                    target = "PUBLIC" if grantee == "PUBLIC" else q(grantee)
                    conn.exec_driver_sql(f"REVOKE ALL ON DATABASE {q(name)} FROM {target}")
                # Grant options first so normalized replay retains the exact ACL atoms.
                for grant in sorted(policy.grants, key=lambda item: not item.grantable):
                    if grant.privilege not in {"CREATE", "CONNECT", "TEMPORARY"}:
                        raise RuntimeError(f"unsupported database privilege {grant.privilege!r}")
                    target = "PUBLIC" if grant.grantee == "PUBLIC" else q(grant.grantee)
                    option = " WITH GRANT OPTION" if grant.grantable else ""
                    conn.exec_driver_sql(
                        f"GRANT {grant.privilege} ON DATABASE {q(name)} TO {target}{option}"
                    )
            finally:
                conn.exec_driver_sql("RESET ROLE")
        # These are real transactions on postgres. SET LOCAL must remain in effect through
        # FROM CURRENT, and target defaults must never shape the replay connection itself.
        with self.connect(transactional=True) as conn:
            q = conn.dialect.identifier_preparer.quote
            conn.exec_driver_sql(f"SET LOCAL ROLE {q(policy.owner)}")
            conn.exec_driver_sql(f"ALTER DATABASE {q(name)} RESET ALL")
            for setting in policy.settings:
                if not setting.role:
                    conn.execute(
                        text("SELECT pg_catalog.set_config(:key,:value,true)"),
                        {"key": setting.key, "value": setting.value},
                    )
                    conn.exec_driver_sql(
                        f"ALTER DATABASE {q(name)} SET {q(setting.key)} FROM CURRENT"
                    )
        roles = {setting.role for setting in (*before.settings, *policy.settings) if setting.role}
        for role in sorted(roles):
            with self.connect(transactional=True) as conn:
                authorized = conn.execute(
                    text("SELECT pg_catalog.pg_has_role(current_user,:role,'SET')"),
                    {"role": role},
                ).scalar_one()
                if authorized:
                    q = conn.dialect.identifier_preparer.quote
                    conn.exec_driver_sql(f"SET LOCAL ROLE {q(role)}")
                    self._replay_role_settings(conn, name, role, policy.settings)
            if not authorized:
                # Use only the exact declared purpose login, authenticated on postgres.
                self._replay_role_self(name, role, policy.settings)
        actual = self.policy(name)
        if actual != policy:
            raise AssertionError(
                f"clone database policy differs: expected {policy!r}; actual {actual!r}"
            )

    @staticmethod
    def _replay_role_settings(
        conn: Connection, name: str, role: str, settings: tuple[DatabaseSetting, ...]
    ) -> None:
        q = conn.dialect.identifier_preparer.quote
        conn.exec_driver_sql(f"ALTER ROLE {q(role)} IN DATABASE {q(name)} RESET ALL")
        for setting in settings:
            if setting.role == role:
                conn.execute(
                    text("SELECT pg_catalog.set_config(:key,:value,true)"),
                    {"key": setting.key, "value": setting.value},
                )
                conn.exec_driver_sql(
                    f"ALTER ROLE {q(role)} IN DATABASE {q(name)} SET {q(setting.key)} FROM CURRENT"
                )

    def _replay_role_self(
        self, name: str, role: str, settings: tuple[DatabaseSetting, ...]
    ) -> None:
        if self._purpose_urls is None:
            from corpus_structure.semantic.runtime import connection_settings

            purposes: tuple[Purpose, ...] = ("write", "read", "evaluate", "admit")
            self._purpose_urls = (
                tuple(
                    make_url(
                        connection_settings(self._purpose_settings, purpose).database.sqlalchemy_url
                    )
                    for purpose in purposes
                )
                if self._purpose_settings is not None
                else ()
            )
        candidates = [url for url in self._purpose_urls if url.username == role]
        if not candidates:
            raise RuntimeError(
                f"cannot replay database settings for role {role!r}: maintenance cannot SET ROLE "
                "and no matching purpose credentials authorize role-self replay"
            )
        engine = create_engine(
            candidates[0].set(database="postgres"),
            poolclass=NullPool,
            isolation_level="READ COMMITTED",
        )
        try:
            with engine.begin() as conn:
                if conn.exec_driver_sql("SELECT current_user,session_user").one() != (role, role):
                    raise RuntimeError(
                        f"database settings replay for {role!r} did not authenticate as role-self"
                    )
                self._replay_role_settings(conn, name, role, settings)
        except DBAPIError as exc:
            raise RuntimeError(
                f"database settings replay for {role!r} failed using its purpose credentials"
            ) from exc
        finally:
            engine.dispose()

    @contextmanager
    def reserved(self, name: str) -> Generator[DatabaseReservation]:
        """Lease an absent bootstrap name; only a creation acknowledgement permits cleanup."""
        with self.lease(name):
            if self.exists(name):
                raise RuntimeError(f"reserved database name already exists: {name!r}")
            primary: BaseException | None = None
            reservation = DatabaseReservation.new(name)
            try:
                yield reservation
            except BaseException as exc:
                primary = exc
                raise
            finally:
                try:
                    with self.connect() as conn:
                        owned = acknowledged_database(conn, reservation)
                    if owned is not None:
                        self._drop(name, owned=owned)
                except BaseException as cleanup:
                    if primary is not None:
                        raise BaseExceptionGroup(
                            "reserved database cleanup failures", [primary, cleanup]
                        ) from None
                    raise

    @contextmanager
    def database(
        self,
        name: str,
        source: str,
        *,
        policy: DatabasePolicy | None = None,
        scenario_seed: Mapping[str, str] | None = None,
    ) -> Generator[Engine]:
        """Lease an absent name before CREATE and protect every acquisition/cleanup step."""
        with self.lease(name):
            if self.exists(name):
                raise RuntimeError(f"reserved database name already exists: {name!r}")
            engine: Engine | None = None
            failure: BaseException | None = None
            creation = DatabaseCreation(DatabaseReservation.new(name))
            try:
                self.create(name, source, creation=creation)
                engine = create_engine(self.url_of(name), poolclass=NullPool)
                if policy is not None:
                    self.replay_policy(name, policy)
                    if self.policy(name) != policy:
                        raise RuntimeError("cloned database policy differs after replay")
                observe_engine(
                    engine, purpose="maintenance", policy=policy, scenario_seed=scenario_seed
                )
                # A real consumer needs deployment observations before restricted acquisitions.
                # Ordinary fixture use has no reason to perform this otherwise-unused checkout.
                if native_context_active():
                    with engine.connect():
                        pass
                yield engine
            except BaseException as exc:
                failure = exc
                if creation.owned is None:
                    exc.add_note(
                        f"CREATE for {name!r} was not acknowledged; any database at that name "
                        "is preserved without disposal authority"
                    )
                raise
            finally:
                failures: list[BaseException] = []
                cleanups: list[Callable[[], None]] = []
                if engine is not None:
                    cleanups.append(engine.dispose)
                if creation.owned is not None:
                    cleanups.append(lambda: self._drop(name, owned=creation.owned))
                for cleanup in cleanups:
                    try:
                        cleanup()
                    except BaseException as exc:
                        failures.append(exc)
                if failures:
                    if failure is not None:
                        failures.insert(0, failure)
                    raise BaseExceptionGroup("native database cleanup failures", failures)

    def installed(self) -> dict[str, str]:
        """Every extension installed in `cs_template`, with its `extversion`."""
        with self.connect(self.template) as conn:
            rows = conn.execute(text("SELECT extname, extversion FROM pg_extension"))
            return {name: version for name, version in rows}

    def check(self) -> dict[str, str]:
        """Fail, never skip, when the server is down, `cs_template` is missing, or one of its
        extensions is absent or at another version than the record."""
        try:
            if not self.exists(self.template):
                raise PrerequisiteUnavailable(
                    "postgres-template", f"database {self.template!r} is missing: {PROVISION}"
                )
            installed = self.installed()
        except OperationalError as exc:
            reason = str(exc.orig or exc).strip().splitlines()[0]
            # Authentication and configuration defects remain ordinary setup failures.
            if getattr(exc.orig, "sqlstate", None) is not None or not any(
                phrase in reason.lower()
                for phrase in (
                    "connection refused",
                    "no such file or directory",
                    "timeout expired",
                )
            ):
                raise
            raise PrerequisiteUnavailable(
                "postgres-server", f"cannot reach PostgreSQL ({reason}): {PROVISION}"
            ) from exc
        wrong = [
            f"{name} {installed.get(name, 'absent')} (expected {version})"
            for name, version in sorted(self.expected.items())
            if installed.get(name) != version
        ]
        if wrong:
            raise PrerequisiteUnavailable(
                "postgres-extensions",
                f"{self.template} extensions differ from {EXTENSION_RECORD.relative_to(REPO)}: "
                f"{', '.join(wrong)}: {PROVISION}",
            )
        return installed

    @contextmanager
    def lease(self, *names: str, exclusive: bool = False) -> Generator[Connection]:
        """Hold session locks; cluster authentication edits require exclusive ownership."""
        with self.connect() as conn:
            for name in names:
                function = "pg_advisory_lock" if exclusive else "pg_advisory_lock_shared"
                identity = recognize_database_name(name)
                conn.execute(
                    text(lock_sql(function)), {"name": identity.lease_key if identity else name}
                )
            yield conn

    def sweep(self) -> SweepResult:
        """Drop authenticated unleased names; report leased or still-connected residue."""
        dropped = []
        skipped = []
        with self.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT datname, shobj_description(oid, 'pg_database'),oid, "
                    "datdba=current_user::regrole FROM pg_database"
                    " WHERE starts_with(datname, 'ci_test_')"
                    " OR starts_with(datname, 'cs_sem_')"
                    " ORDER BY datname"
                ),
            ).all()
            failures: list[BaseException] = []
            for name, comment, oid, owned in rows:
                if not owned or not self.owned_comment(comment, oid):
                    continue
                identity = recognize_database_name(name)
                if identity is None or identity.sweep_rule == "retained":
                    continue
                key = identity.lease_key
                if not conn.execute(text(lock_sql("pg_try_advisory_lock")), {"name": key}).scalar():
                    skipped.append(name)
                    continue
                try:
                    self.drop(name)
                    dropped.append(name)
                except DBAPIError as exc:
                    if getattr(exc.orig, "sqlstate", None) == "55006":
                        skipped.append(name)
                    else:
                        failures.append(exc)
                except BaseException as exc:
                    failures.append(exc)
                finally:
                    try:
                        conn.execute(text(lock_sql("pg_advisory_unlock")), {"name": key})
                    except BaseException as exc:
                        failures.append(exc)
        if failures:
            raise BaseExceptionGroup("database sweep failures", failures)
        return SweepResult(tuple(dropped), tuple(skipped))

    def deployment_key(self, repository: Path = REPO) -> str:
        """Acquire the server identity and compute the declared key once per server owner."""
        if self._deployment_key is None:
            from native_deployment_key import deployment_key

            principals = tuple(semantic_principals().values())
            with self.connect() as conn:
                version, cluster = conn.exec_driver_sql(
                    "SELECT current_setting('server_version_num'),system_identifier::text FROM pg_control_system()"
                ).one()
                template_oid = conn.execute(
                    text("SELECT oid FROM pg_database WHERE datname=:name"), {"name": self.template}
                ).scalar_one()
                roles = conn.execute(
                    text(
                        "SELECT rolname,oid FROM pg_roles WHERE rolname=ANY(:names) ORDER BY rolname"
                    ),
                    {"names": list(principals)},
                ).all()
            key, _ = deployment_key(
                repository=repository,
                chain=repository / "python/corpus-structure/semantic_alembic",
                package=repository / "python/corpus-structure/src/corpus_structure",
                construction=repository / "scripts/native_deployment_build.py",
                lockfile=repository / "uv.lock",
                server={
                    "server_version": version,
                    "cluster": cluster,
                    "template_oid": template_oid,
                    "extensions": self.installed(),
                    "principals": [tuple(row) for row in roles],
                },
            )
            self._deployment_key = key
        return self._deployment_key

    def semantic_ready(self) -> None:
        if not self._semantic_ready:
            self.check_roles(semantic_principals())
            self._semantic_ready = True

    @contextmanager
    def deployment(
        self,
        *,
        key: str | None = None,
        run_id: str | None = None,
        run_private: bool | None = None,
    ) -> Generator[SemanticDeployment]:
        scope = os.environ.get("CORPUS_CI_RUN_SCOPE", "narrowed")
        if scope not in {"narrowed", "qualification"}:
            raise ValueError("unexpected native test run scope")
        self.semantic_ready()
        receipt = os.environ.get("CORPUS_CI_RECEIPT_DIR")
        run_id = (
            run_id
            or (Path(receipt).parent.name if receipt else os.environ.get("PYTEST_XDIST_TESTRUNUID"))
            or uuid4().hex
        )
        handle = SemanticDeployment(
            self,
            key or self.deployment_key(),
            run_id,
            scope,
            scope == "qualification" if run_private is None else run_private,
        )
        try:
            yield handle
        finally:
            handle.close()

    def _deployment_record(self, name: str):
        with self.connect() as conn:
            return conn.execute(
                text(
                    "SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database'),"
                    "datdba=current_user::regrole,datallowconn,datistemplate "
                    "FROM pg_database WHERE datname=:name"
                ),
                {"name": name},
            ).one_or_none()

    def seal_database(self, name: str) -> None:
        record = self._deployment_record(name)
        if record is None or not record[3] or not self.owned_comment(record[2], record[0]):
            raise RuntimeError("cannot seal an unauthenticated database")
        with self.connect() as connection:
            connection.exec_driver_sql(
                f"ALTER DATABASE {quote(name)} ALLOW_CONNECTIONS false IS_TEMPLATE false"
            )

            def drained() -> bool:
                return not connection.execute(
                    text("SELECT count(*) FROM pg_stat_activity WHERE datname=:name"),
                    {"name": name},
                ).scalar_one()

            self._wait_for_backend_exit(name, drained)

    def _publish_deployment(self, name: str) -> tuple[DatabasePolicy, bool]:
        existing = self._deployment_record(name)
        if existing is not None:
            oid, _, comment, owner, allowed, template = existing
            if not owner or not self.owned_comment(comment, oid) or allowed or template:
                raise RuntimeError(f"refusing unowned or unsealed deployment {name!r}")
            return self.policy(name), False
        from native_deployment_build import construct_deployment

        build = database_name("build").name
        creation = DatabaseCreation(DatabaseReservation.new(build))
        engine = None
        with self.lease(build):
            try:
                self.create(build, self.template, creation=creation)
                engine = create_engine(self.url_of(build), poolclass=NullPool)
                observe_engine(engine, purpose="maintenance")
                with engine.begin() as connection:
                    construct_deployment(connection)
                engine.dispose()
                engine = None
                policy = self.policy(build)
                self.seal_database(build)
                with self.connect() as conn:
                    conn.exec_driver_sql(f"ALTER DATABASE {quote(build)} RENAME TO {quote(name)}")
                published = self._deployment_record(name)
                owned = creation.owned
                if (
                    owned is None
                    or published is None
                    or (
                        published[0] != owned.oid
                        or published[1] != owned.owner
                        or published[2] != owned.comment
                        or published[4]
                        or published[5]
                    )
                ):
                    raise RuntimeError(
                        "native deployment publication lost its acknowledged identity"
                    )
                return policy, True
            except BaseException as primary:
                failures = [primary]
                if engine is not None:
                    try:
                        engine.dispose()
                    except BaseException as error:
                        failures.append(error)
                if creation.owned is not None:
                    try:
                        self._dispose_deployment_creation(build, creation.owned)
                    except BaseException as error:
                        failures.append(error)
                else:
                    primary.add_note(
                        "Unacknowledged native build outcome preserved without disposal authority"
                    )
                if len(failures) > 1:
                    raise BaseExceptionGroup(
                        "native deployment construction cleanup failures", failures
                    ) from None
                raise

    def _dispose_deployment_creation(self, build: str, owned: OwnedDatabase) -> None:
        with self.connect() as conn:
            found = conn.execute(
                text(
                    "SELECT datname,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') "
                    "FROM pg_database WHERE oid=:oid"
                ),
                {"oid": owned.oid},
            ).one_or_none()
        if found is None:
            return
        actual, owner, comment = found
        if owner != owned.owner or (actual != build and comment != owned.comment):
            raise RuntimeError("native deployment cleanup lacks acknowledged ownership")
        self._drop(actual, owned=owned)

    def _retire_deployment(self, name: str) -> str:
        with self.connect() as conn:
            if not conn.execute(text(lock_sql("pg_try_advisory_lock")), {"name": name}).scalar():
                return "still_leased"
            row = self._deployment_record(name)
            if row is None:
                return "already_absent"
            if not row[3] or not self.owned_comment(row[2], row[0]):
                raise RuntimeError("stale deployment retirement lost ownership")
            retired = database_name("stale").name
            conn.exec_driver_sql(f"ALTER DATABASE {quote(name)} RENAME TO {quote(retired)}")
            return retired

    def _retain_deployments(self) -> None:
        with self.connect() as conn:
            rows = conn.exec_driver_sql(
                "SELECT datname,oid,shobj_description(oid,'pg_database') FROM pg_database "
                "WHERE datdba=current_user::regrole ORDER BY oid DESC"
            ).all()
            heads = [
                name
                for name, oid, comment in rows
                if (identity := recognize_database_name(name)) is not None
                and identity.sweep_rule == "retained"
                and self.owned_comment(comment, oid)
            ]
            for name in heads[3:]:
                if not conn.execute(
                    text(lock_sql("pg_try_advisory_lock")), {"name": name}
                ).scalar():
                    continue
                try:
                    self.drop(name)
                except DBAPIError as error:
                    if getattr(error.orig, "sqlstate", None) != "55006":
                        raise
                    print(
                        f"Native deployment retention skipped connected database: {name}",
                        file=sys.stderr,
                    )
                finally:
                    conn.execute(text(lock_sql("pg_advisory_unlock")), {"name": name})


def principal_engine(
    settings: Settings,
    purpose: Purpose,
    database: str | None,
    *,
    scenario_seed: Mapping[str, str] | None = None,
    readonly: bool = False,
) -> Engine:
    # Resolve credentials against the original endpoint before substituting the owned clone.
    # In particular no restricted login inherits a maintenance password.
    from corpus_structure.semantic.runtime import connection_settings

    assert database is not None, "an owned clone must have a database name"
    resolved = connection_settings(settings, purpose)
    url = make_url(resolved.database.sqlalchemy_url).set(database=database)
    options = str(url.query.get("options", "")) + " -c default_transaction_read_only=on"
    engine = create_engine(
        url, poolclass=NullPool, **({"connect_args": {"options": options}} if readonly else {})
    )
    observe_engine(engine, purpose=purpose, scenario_seed=scenario_seed)
    return engine


def observe_engine(
    engine: Engine,
    *,
    purpose: str,
    policy: DatabasePolicy | None = None,
    scenario_seed: Mapping[str, str] | None = None,
) -> None:
    """Observe each physical acquisition without opening a SQLAlchemy transaction."""

    @event.listens_for(engine, "connect")
    def acquired(connection, _record):
        observe_connection(
            connection, engine.url, purpose=purpose, policy=policy, scenario_seed=scenario_seed
        )


def native_context_active() -> bool:
    """Ask the plugin at observation time, including for already-created engines."""
    try:
        from qualification_plugin import native_context_active as active
    except ImportError:
        return False
    return active()


def observe_connection(
    connection,
    url: URL,
    *,
    purpose: str | None,
    policy: DatabasePolicy | None = None,
    scenario_seed: Mapping[str, str] | None = None,
    nodeid: str | None = None,
) -> None:
    """Observe an actual acquisition; callers retain the native resource lifetime."""
    if not native_context_active():
        return
    import hashlib
    import json
    from dataclasses import asdict

    from qualification_plugin import record_native_context

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_database(), (SELECT oid FROM pg_database "
            "WHERE datname=current_database()), current_user, session_user, "
            "current_setting('server_version'), current_setting('port'), "
            "pg_postmaster_start_time()"
        )
        database, oid, principal, login, version, port, started = cursor.fetchone()
        cursor.execute("SELECT to_regclass('public.semantic_alembic_version')")
        revision = None
        if cursor.fetchone()[0] is not None:
            cursor.execute(
                "SELECT has_table_privilege(current_user, "
                "'public.semantic_alembic_version', 'SELECT')"
            )
            if cursor.fetchone()[0]:
                cursor.execute("SELECT version_num FROM public.semantic_alembic_version")
                row = cursor.fetchone()
                revision = row[0] if row else None
    if not connection.autocommit:
        connection.rollback()
    key = (connection.info.host, port, started.isoformat(), oid)
    policy_ref = (
        hashlib.sha256(json.dumps(asdict(policy), sort_keys=True).encode()).hexdigest()
        if policy
        else None
    )
    if policy is not None:
        _DEPLOYMENTS[key] = {"revision": revision, "policy_ref": policy_ref}
    deployment = _DEPLOYMENTS.get(key, {})
    record_native_context(
        {
            "schema": "native-context/v1",
            "requested": {
                "database": url.database,
                "host": url.query.get("host", url.host),
                "port": url.query.get("port", url.port),
                "principal": url.username,
                "purpose": purpose,
            },
            "acquired": {
                "database": database,
                "database_oid": oid,
                "current_user": principal,
                "session_user": login,
                "server_version": version,
                "server_started": started.isoformat(),
                "port": port,
                "host": connection.info.host,
                "revision": revision or deployment.get("revision"),
                "policy_ref": policy_ref or deployment.get("policy_ref"),
                "scenario_seed": dict(scenario_seed) if scenario_seed is not None else None,
                # This reports revision availability, not complete policy reproducibility.
                "deployment_status": "observed"
                if revision or deployment.get("revision")
                else "unavailable",
            },
            "provenance": {"complete": True, "missing": []},
        },
        nodeid=nodeid,
    )


def record_server_context(
    settings: Settings, server: PgAdmin, *, sweep: SweepResult | None = None
) -> None:
    """Report an already-acquired server for either native fixture family."""
    if not native_context_active():
        return
    import os

    import psycopg

    from corpus_structure.settings import settings_report

    with server.connect() as conn:
        server_version, principal = conn.exec_driver_sql(
            "SELECT current_setting('server_version'),current_user"
        ).one()
    from qualification_plugin import record_native_context

    sweep_context = (
        {"database_sweep": {"dropped": list(sweep.dropped), "skipped": list(sweep.skipped)}}
        if sweep is not None
        else {}
    )
    record_native_context(
        {
            "settings": settings_report(settings, os.environ).model_dump(mode="json"),
            "server_version": server_version,
            "current_user": principal,
            "driver": "psycopg " + psycopg.__version__,
            **sweep_context,
        },
        scope="session",
    )
