"""Shared test configuration for the corpus-structure package (D9 §4; coordinator decision 10).

- Hypothesis profiles `ci` and `dev`, chosen by `HYPOTHESIS_PROFILE` (default `dev`).
- Markers `db`, `gpu` and `corpus`. `corpus` tests skip when `docs/statistics_corpus/` is absent;
  nothing else skips. Tests using the database fixtures are marked `db` automatically.
- `cli`: Typer's runner with stdout and stderr apart and a fixed width.
- Database fixtures (store note §1; foundations §3.9) against the server `Settings()` names: the
  dedicated cluster 18/corpus (`just db-provision`, D3 §13) by default, or the one
  `CORPUS_DATABASE__URL` names. The admin URL is the settings URL with database `postgres`, so the
  fixtures and the application read one coordinate source (DA-020).
  - `cs_template`'s extensions must be at the versions of `ops/postgresql/extensions.txt`; a
    missing or different version fails the test with the instruction, as does a server that is
    down or lacks `cs_template`. Nothing skips (DA-018).
  - The migrated template `cs_tpl_<hash>` is cloned from `cs_template` once per state of the
    Alembic versions directory and of `cs_template`'s installed extension versions; the session
    database `ci_test_<pid>` is cloned from it. `db` is an outer transaction rolled back after each
    test, `committing_db` an engine on a clone of its own.
  - A session holds a lease, a shared session advisory lock on its template and its `ci_test_<pid>`
    name, on a connection kept open for the session. The sweep takes each other name's lock
    exclusively with `pg_try_advisory_lock` and skips what it cannot take, so a live session's
    databases survive it, on any host or checkout. An unheld `ci_test_*` is dropped; an unheld
    template is dropped once unused for `TEMPLATE_RETENTION` (DA-019).
"""

from __future__ import annotations

import hashlib
import itertools
import os
import re
from collections.abc import Callable, Generator, Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from hypothesis import settings as hypothesis_settings
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool
from typer.testing import CliRunner, Result

from corpus_structure.cli.app import app
from corpus_structure.cli.output import CliState
from corpus_structure.core.db import extensions
from corpus_structure.settings import Settings

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
ALEMBIC_DIR = PACKAGE / "alembic"
VERSIONS_DIR = ALEMBIC_DIR / "versions"
CORPUS_DIR = REPO / "docs" / "statistics_corpus"
EXTENSION_RECORD = extensions.EXTENSION_RECORD
PROVISION = (
    "run `just db-provision` (the dedicated cluster 18/corpus with cs_template, D3 §13), "
    "or point CORPUS_DATABASE__URL at a server that has it"
)
TEST_DB = re.compile(r"(ci_test_\d+)(?:_\d+)?")
TEMPLATE_PREFIX = "cs_tpl_"
TEMPLATE_RETENTION = timedelta(days=1)
LEASE_SPACE = 0x63735450  # first key of the two-key advisory locks the fixtures take ("csTP")
STAMP = re.compile(r"corpus-structure test template, last used (\S+)")
CLI_WIDTH = 100

hypothesis_settings.register_profile(
    "ci", deadline=None, derandomize=True, database=None, print_blob=True, max_examples=300
)
hypothesis_settings.register_profile("dev")
hypothesis_settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))

DB_FIXTURES = frozenset({"db", "committing_db", "db_engine", "db_server"})


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    # Scratch stays in the checkout, as the root tests/conftest.py arranges for whole-tree runs;
    # repeated here so a run of this package alone does the same.
    if config.option.basetemp is None and "PYTEST_DEBUG_TEMPROOT" not in os.environ:
        root = config.rootpath / "build" / "tmp" / "pytest"
        root.mkdir(parents=True, exist_ok=True)
        environment = pytest.MonkeyPatch()
        config.add_cleanup(environment.undo)
        environment.setenv("PYTEST_DEBUG_TEMPROOT", str(root))
    config.addinivalue_line("markers", "db: uses the PostgreSQL test database")
    config.addinivalue_line("markers", "gpu: needs a GPU")
    config.addinivalue_line("markers", "corpus: needs docs/statistics_corpus (skipped without it)")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    no_corpus = pytest.mark.skip(reason=f"{CORPUS_DIR.relative_to(REPO)} is absent")
    for item in items:
        if DB_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.db)
        if item.get_closest_marker("corpus") and not CORPUS_DIR.is_dir():
            item.add_marker(no_corpus)


# --- CLI -------------------------------------------------------------------------------------


class Cli:
    """Invokes `ci` in process with stdout and stderr apart and Rich's width fixed."""

    def __init__(self) -> None:
        self.runner = CliRunner(env={"COLUMNS": str(CLI_WIDTH), "NO_COLOR": "1"})

    def __call__(
        self, *args: str, settings: Callable[[], Settings] | None = None, env: dict | None = None
    ) -> Result:
        obj = CliState(settings) if settings is not None else None
        return self.runner.invoke(app, list(args), obj=obj, env=env)


@pytest.fixture
def cli() -> Cli:
    return Cli()


# --- Database --------------------------------------------------------------------------------


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


def versions_hash(extensions: Mapping[str, str]) -> str:
    """Hash of the Alembic versions directory and the template's installed extension versions."""
    sha = hashlib.sha256()
    for path in sorted(VERSIONS_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        sha.update(path.relative_to(VERSIONS_DIR).as_posix().encode() + b"\0")
        sha.update(path.read_bytes() + b"\0")
    for name, version in sorted(extensions.items()):
        sha.update(f"extension {name} {version}".encode() + b"\0")
    return sha.hexdigest()[:16]


def template_name(extensions: Mapping[str, str]) -> str:
    """The migrated template for this migration state and these extension versions."""
    return f"{TEMPLATE_PREFIX}{versions_hash(extensions)}"


def quote(name: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
        raise ValueError(f"unexpected database name {name!r}")
    return f'"{name}"'


def lock_sql(function: str) -> str:
    """One advisory-lock call on the key of the name bound to `:name`."""
    return f"SELECT {function}({LEASE_SPACE}, hashtext(:name))"


class PgAdmin:
    """Database-level operations on the test server, each on its own autocommit connection."""

    def __init__(self, url: str, template: str, expected: Mapping[str, str] | None = None) -> None:
        self.url = url
        self.template = template
        self.expected = dict(expected_extensions() if expected is None else expected)
        self.current = ""  # the migrated template's name, set by `check`

    def url_of(self, name: str) -> str:
        return make_url(self.url).set(database=name).render_as_string(hide_password=False)

    @contextmanager
    def connect(self, name: str = "postgres") -> Generator[Connection]:
        engine = create_engine(self.url_of(name), poolclass=NullPool, isolation_level="AUTOCOMMIT")
        try:
            with engine.connect() as conn:
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

    def create(self, name: str, template: str) -> None:
        with self.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {quote(name)} WITH (FORCE)"))
            conn.execute(text(f"CREATE DATABASE {quote(name)} TEMPLATE {quote(template)}"))

    def drop(self, name: str) -> None:
        with self.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {quote(name)} WITH (FORCE)"))

    def installed(self) -> dict[str, str]:
        """Every extension installed in `cs_template`, with its `extversion`."""
        with self.connect(self.template) as conn:
            rows = conn.execute(text("SELECT extname, extversion FROM pg_extension"))
            return {name: version for name, version in rows}

    def check(self) -> dict[str, str]:
        """Fail, never skip, when the server is down, `cs_template` is missing, or one of its
        extensions is absent or at another version than the record; then name the template."""
        try:
            if not self.exists(self.template):
                pytest.fail(f"database {self.template!r} is missing: {PROVISION}", pytrace=False)
            installed = self.installed()
        except OperationalError as exc:
            reason = str(exc.orig or exc).strip().splitlines()[0]
            pytest.fail(f"cannot reach PostgreSQL ({reason}): {PROVISION}", pytrace=False)
        wrong = [
            f"{name} {installed.get(name, 'absent')} (expected {version})"
            for name, version in sorted(self.expected.items())
            if installed.get(name) != version
        ]
        if wrong:
            pytest.fail(
                f"{self.template} extensions differ from {EXTENSION_RECORD.relative_to(REPO)}: "
                f"{', '.join(wrong)}: {PROVISION}",
                pytrace=False,
            )
        self.current = template_name(installed)
        return installed

    @contextmanager
    def lease(self, *names: str) -> Generator[Connection]:
        """Hold a shared session advisory lock on each name while the block runs (DA-019)."""
        with self.connect() as conn:
            for name in names:
                conn.execute(text(lock_sql("pg_advisory_lock_shared")), {"name": name})
            yield conn

    def stamp(self, name: str, at: datetime | None = None) -> None:
        """Record when a template was last used, in its database comment."""
        when = (at or datetime.now(UTC)).isoformat()
        comment = f"corpus-structure test template, last used {when}"
        with self.connect() as conn:
            conn.execute(text(f"COMMENT ON DATABASE {quote(name)} IS '{comment}'"))

    def sweep(self, now: datetime | None = None) -> list[str]:
        """Drop each `ci_test_*` no session holds, and each other `cs_tpl_*` no session holds that
        has gone unused for `TEMPLATE_RETENTION` (or carries no stamp).

        Each candidate's lock is taken exclusively with `pg_try_advisory_lock` around its drop, and
        a name whose lock is held is skipped. Only these two prefixes are touched; the server may
        hold other projects' databases.
        """
        cutoff = (now or datetime.now(UTC)) - TEMPLATE_RETENTION
        dropped = []
        with self.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT datname, shobj_description(oid, 'pg_database') FROM pg_database"
                    " WHERE starts_with(datname, 'ci_test_') OR starts_with(datname, :tpl)"
                    " ORDER BY datname"
                ),
                {"tpl": TEMPLATE_PREFIX},
            ).all()
            for name, comment in rows:
                if name.startswith(TEMPLATE_PREFIX):
                    if name == self.current:
                        continue
                    key = name
                    stamp = STAMP.fullmatch(comment or "")
                    if stamp and datetime.fromisoformat(stamp.group(1)) > cutoff:
                        continue
                else:
                    match = TEST_DB.fullmatch(name)
                    if match is None:
                        continue
                    key = match.group(1)
                if not conn.execute(text(lock_sql("pg_try_advisory_lock")), {"name": key}).scalar():
                    continue
                try:
                    conn.execute(text(f"DROP DATABASE IF EXISTS {quote(name)} WITH (FORCE)"))
                    dropped.append(name)
                finally:
                    conn.execute(text(lock_sql("pg_advisory_unlock")), {"name": key})
        return dropped

    def ensure_template(self, lease: Connection) -> None:
        """Build the migrated template unless it exists, one builder at a time on the server."""
        scratch = f"{self.current}_build"
        lease.execute(text(lock_sql("pg_advisory_lock")), {"name": scratch})
        try:
            if not self.exists(self.current):
                self.build_template(scratch)
        finally:
            lease.execute(text(lock_sql("pg_advisory_unlock")), {"name": scratch})
        self.stamp(self.current)

    def build_template(self, scratch: str) -> None:
        """Clone `cs_template` to a scratch name, migrate it to head, then rename it."""
        self.create(scratch, self.template)
        engine = create_engine(self.url_of(scratch), poolclass=NullPool)
        try:
            with engine.begin() as conn:
                config = Config()
                config.set_main_option("script_location", str(ALEMBIC_DIR))
                config.attributes["connection"] = conn
                command.upgrade(config, "head")
        finally:
            engine.dispose()  # a template must have no connection while it is cloned
        with self.connect() as conn:
            conn.execute(text(f"ALTER DATABASE {quote(scratch)} RENAME TO {quote(self.current)}"))

    @contextmanager
    def clone(self, name: str) -> Generator[Engine]:
        """A database cloned from the migrated template, dropped `WITH (FORCE)` afterwards."""
        self.create(name, self.current)
        engine = create_engine(self.url_of(name))
        try:
            yield engine
        finally:
            engine.dispose()
            self.drop(name)


@pytest.fixture(scope="session")
def db_support() -> SimpleNamespace:
    """The helpers above, for tests (importlib import mode leaves this module unimportable)."""
    return SimpleNamespace(
        PgAdmin=PgAdmin,
        server_url=server_url,
        expected_extensions=expected_extensions,
        template_name=template_name,
        TEMPLATE_RETENTION=TEMPLATE_RETENTION,
    )


@pytest.fixture(scope="session")
def db_server() -> Iterator[PgAdmin]:
    """The test server, checked and swept, with the migrated template for this state, leased for
    the session: clones and the build happen under the lease, which the sweep honours."""
    settings = Settings()
    server = PgAdmin(server_url(settings), settings.database.template)
    server.check()
    session_db = f"ci_test_{os.getpid()}"
    with server.lease(server.current, session_db) as lease:
        server.drop(session_db)
        server.sweep()
        server.ensure_template(lease)
        yield server


_clones = itertools.count(1)


@pytest.fixture(scope="session")
def db_engine(db_server: PgAdmin) -> Iterator[Engine]:
    """An engine on the session database `ci_test_<pid>`."""
    with db_server.clone(f"ci_test_{os.getpid()}") as engine:
        yield engine


@pytest.fixture
def db(db_engine: Engine) -> Iterator[Connection]:
    """A connection inside an outer transaction that is rolled back after the test."""
    with db_engine.connect() as conn:
        outer = conn.begin()
        try:
            yield conn
        finally:
            outer.rollback()


@pytest.fixture
def committing_db(db_server: PgAdmin) -> Iterator[Engine]:
    """An engine on a clone of its own, for tests that need commits (queue, NOTIFY, COPY)."""
    with db_server.clone(f"ci_test_{os.getpid()}_{next(_clones)}") as engine:
        yield engine
