"""Shared native PostgreSQL fixture lifecycle and typed database-policy replay.

Importing this module acquires no settings, database, process or provider resource.
"""

from __future__ import annotations

import re
import subprocess
import time
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

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
TEST_DB = re.compile(r"(ci_test_\d+)(?:_\d+)?")
TEMPLATE_PREFIX = "cs_tpl_"
TEMPLATE_RETENTION = timedelta(days=1)
LEASE_SPACE = 0x63735450
STAMP = re.compile(r"corpus-structure test template, last used (\S+)")
_DEPLOYMENTS: dict[tuple[str, str, str, int], dict[str, object]] = {}


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


@dataclass(frozen=True)
class SemanticTemplate:
    name: str
    policy: DatabasePolicy


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
        # Resolve only the existing purpose credentials, once against the original endpoint.
        # Role-self replay later changes the database to postgres, never the authentication.
        self._purpose_urls: tuple[URL, ...] = ()
        if settings is not None:
            from corpus_structure.semantic.runtime import connection_settings

            purposes: tuple[Purpose, ...] = ("write", "read", "evaluate", "admit")
            self._purpose_urls = tuple(
                make_url(connection_settings(settings, purpose).database.sqlalchemy_url)
                for purpose in purposes
            )

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

    def _drop(self, name: str, *, owned: OwnedDatabase | None = None) -> None:
        # libpq close can precede the backend's final exit. Never terminate other logins.
        deadline = time.monotonic() + 2.0
        while True:
            try:
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
                        return
                    oid, owner, comment, user = row
                    authenticated = (
                        oid == owned.oid and owner == owned.owner
                        if owned is not None
                        else self.owned_comment(comment, oid)
                    )
                    if owner != user or not authenticated:
                        raise RuntimeError(f"refusing to drop unauthenticated database {name!r}")
                    conn.execute(text(f"DROP DATABASE {quote(name)}"))
                return
            except DBAPIError as exc:
                if getattr(exc.orig, "sqlstate", None) != "55006" or time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)

    @staticmethod
    def owned_comment(comment: str | None, oid: int) -> bool:
        return (
            comment == "corpus-structure owned test database"
            or bool(STAMP.fullmatch(comment or ""))
            or is_owned_stamp(comment, oid)
        )

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
                observe_engine(engine, purpose="maintenance", policy=policy)
                # Observe deployment once through its maintenance connection before lending it.
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
                conn.execute(text(lock_sql(function)), {"name": name})
            yield conn

    def stamp(self, name: str, at: datetime | None = None) -> None:
        """Record when a template was last used, in its database comment."""
        when = (at or datetime.now(UTC)).isoformat()
        comment = f"corpus-structure test template, last used {when}"
        with self.connect() as conn:
            conn.execute(text(f"COMMENT ON DATABASE {quote(name)} IS '{comment}'"))

    def sweep(self, now: datetime | None = None) -> list[str]:
        """Drop each `ci_test_*` no session holds, and each other `cs_tpl_*` no session holds that
        has gone unused for `TEMPLATE_RETENTION`. Names, owner and fixture comment must match;
        untagged historical residue is never adopted.

        Each candidate's lock is taken exclusively with `pg_try_advisory_lock` around its drop, and
        a name whose lock is held is skipped. Authenticated session-only semantic names share
        this owner; the server may hold other projects' databases.
        """
        cutoff = (now or datetime.now(UTC)) - TEMPLATE_RETENTION
        dropped = []
        with self.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT datname, shobj_description(oid, 'pg_database'),oid, "
                    "datdba=current_user::regrole FROM pg_database"
                    " WHERE starts_with(datname, 'ci_test_') OR starts_with(datname, :tpl)"
                    " OR starts_with(datname, 'cs_sem_')"
                    " ORDER BY datname"
                ),
                {"tpl": TEMPLATE_PREFIX},
            ).all()
            failures: list[BaseException] = []
            for name, comment, oid, owned in rows:
                if not owned or not self.owned_comment(comment, oid):
                    continue
                if name.startswith(TEMPLATE_PREFIX):
                    if not re.fullmatch(r"cs_tpl_[0-9a-f]{16}(?:_build)?", name):
                        continue
                    key = name
                    stamp = STAMP.fullmatch(comment or "")
                    if stamp and datetime.fromisoformat(stamp.group(1)) > cutoff:
                        continue
                elif re.fullmatch(
                    r"cs_sem_(?:head|test|bare|revision|init)_\d+_[0-9a-f]{12}", name
                ):
                    key = name
                else:
                    match = TEST_DB.fullmatch(name)
                    if match is None:
                        continue
                    key = match.group(1)
                if not conn.execute(text(lock_sql("pg_try_advisory_lock")), {"name": key}).scalar():
                    continue
                try:
                    self.drop(name)
                    dropped.append(name)
                except BaseException as exc:
                    failures.append(exc)
                finally:
                    try:
                        conn.execute(text(lock_sql("pg_advisory_unlock")), {"name": key})
                    except BaseException as exc:
                        failures.append(exc)
        if failures:
            raise BaseExceptionGroup("database sweep failures", failures)
        return dropped

    @contextmanager
    def semantic_template(self, name: str) -> Generator[SemanticTemplate]:
        """Bootstrap and seal a current frozen deployment for owned consumer clones."""
        from corpus_structure.semantic.migrations import upgrade

        with self.database(name, self.template) as engine:
            with engine.begin() as conn:
                extensions.check(conn.execute(text(extensions.FOUND)).all())
                assert not conn.execute(
                    text("SELECT 1 FROM pg_namespace WHERE nspname IN ('sem','data','kb','meta')")
                ).first()
                upgrade(conn)
            engine.dispose()
            policy = self.policy(name)
            with self.connect() as conn:
                conn.exec_driver_sql(
                    f"ALTER DATABASE {quote(name)} ALLOW_CONNECTIONS false IS_TEMPLATE false"
                )
            yield SemanticTemplate(name, policy)


def principal_engine(settings: Settings, purpose: Purpose, database: str | None) -> Engine:
    # Resolve credentials against the original endpoint before substituting the owned clone.
    # In particular no restricted login inherits a maintenance password.
    from corpus_structure.semantic.runtime import connection_settings

    assert database is not None, "an owned clone must have a database name"
    resolved = connection_settings(settings, purpose)
    url = make_url(resolved.database.sqlalchemy_url).set(database=database)
    engine = create_engine(url, poolclass=NullPool)
    observe_engine(engine, purpose=purpose)
    return engine


def observe_engine(engine: Engine, *, purpose: str, policy: DatabasePolicy | None = None) -> None:
    """Observe each physical acquisition without opening a SQLAlchemy transaction."""
    import hashlib
    import json
    from dataclasses import asdict

    @event.listens_for(engine, "connect")
    def acquired(connection, _record):
        try:
            from qualification_plugin import record_native_context
        except ImportError:
            return
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
                    "database": engine.url.database,
                    "host": engine.url.query.get("host", engine.url.host),
                    "port": engine.url.query.get("port", engine.url.port),
                    "principal": engine.url.username,
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
                    "deployment_status": "observed"
                    if revision or deployment.get("revision")
                    else "unavailable",
                },
                "provenance": {"complete": True, "missing": []},
            }
        )


def record_server_context(settings: Settings, server: PgAdmin) -> None:
    """Report an already-acquired server for either native fixture family."""
    import os

    import psycopg

    from corpus_structure.settings import settings_report

    with server.connect() as conn:
        server_version, principal = conn.exec_driver_sql(
            "SELECT current_setting('server_version'),current_user"
        ).one()
    try:
        from qualification_plugin import record_native_context
    except ImportError:
        return
    record_native_context(
        {
            "settings": settings_report(settings, os.environ).model_dump(mode="json"),
            "server_version": server_version,
            "current_user": principal,
            "driver": "psycopg " + psycopg.__version__,
        },
        scope="session",
    )
