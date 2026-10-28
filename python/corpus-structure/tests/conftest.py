"""Shared test configuration for the corpus-structure package (D9 §4; coordinator decision 10).

- Hypothesis profiles `ci` and `dev`, chosen by `HYPOTHESIS_PROFILE` (default `dev`).
- Markers `db`, `gpu` and `corpus`. `corpus` tests skip when `docs/statistics_corpus/` is absent;
  nothing else skips. Tests using the database fixtures are marked `db` automatically.
- `cli`: Typer's runner with stdout and stderr apart and a fixed width.
- Database fixtures (store note §1) against the project-local cluster (`just db-up`, D3 §3) unless
  `CORPUS_DATABASE__URL` names another server: a migrated template `cs_tpl_<hash>` cloned from
  `cs_template` once per state of the Alembic versions directory, the session database
  `ci_test_<pid>` cloned from it, `db` (an outer transaction rolled back after each test) and
  `committing_db` (an engine on its own clone). A server that is down or lacks `cs_template` fails
  the test with the instruction; it never skips.
"""

from __future__ import annotations

import fcntl
import hashlib
import itertools
import os
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

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
from corpus_structure.settings import Settings

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
ALEMBIC_DIR = PACKAGE / "alembic"
VERSIONS_DIR = ALEMBIC_DIR / "versions"
CORPUS_DIR = REPO / "docs" / "statistics_corpus"
LOCK_FILE = REPO / "build" / "pg" / "test-templates.lock"
LOCAL_CLUSTER_URL = f"postgresql:///postgres?host={REPO}/build/pg/run&port=5440"
PROVISION = (
    "run `just db-up` (the project-local cluster with cs_template, D3 §3), "
    "or point CORPUS_DATABASE__URL at a server that has it"
)
TEST_DB = re.compile(r"ci_test_(\d+)(?:_\d+)?")
CLI_WIDTH = 100
EXTENSIONS = ("pg_textsearch", "vector")

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


def server_url() -> str:
    """The admin URL (database `postgres`) of the server the tests use, in SQLAlchemy's form."""
    libpq = os.environ.get("CORPUS_DATABASE__URL") or LOCAL_CLUSTER_URL
    url = make_url(Settings(database={"url": libpq}).database.sqlalchemy_url)
    return url.set(database="postgres").render_as_string(hide_password=False)


def versions_hash() -> str:
    """Hash of the Alembic versions directory: one migrated template per migration state."""
    sha = hashlib.sha256()
    for path in sorted(VERSIONS_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        sha.update(path.relative_to(VERSIONS_DIR).as_posix().encode() + b"\0")
        sha.update(path.read_bytes() + b"\0")
    return sha.hexdigest()[:16]


def quote(name: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
        raise ValueError(f"unexpected database name {name!r}")
    return f'"{name}"'


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextmanager
def template_lock() -> Iterator[None]:
    """Serialize template building and sweeping across processes (xdist workers, other sessions)."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


class PgAdmin:
    """Database-level operations on the test server, each on its own autocommit connection."""

    def __init__(self, url: str, template: str) -> None:
        self.url = url
        self.template = template
        self.current = f"cs_tpl_{versions_hash()}"

    def url_of(self, name: str) -> str:
        return make_url(self.url).set(database=name).render_as_string(hide_password=False)

    @contextmanager
    def connect(self, name: str = "postgres") -> Iterator[Connection]:
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

    def check(self) -> None:
        """Fail, never skip, when the server is down or `cs_template` lacks an extension."""
        try:
            if not self.exists(self.template):
                pytest.fail(f"database {self.template!r} is missing: {PROVISION}", pytrace=False)
            with self.connect(self.template) as conn:
                rows = conn.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = ANY(:e)"),
                    {"e": list(EXTENSIONS)},
                )
                missing = sorted(set(EXTENSIONS) - {row[0] for row in rows})
        except OperationalError as exc:
            reason = str(exc.orig or exc).strip().splitlines()[0]
            pytest.fail(f"cannot reach PostgreSQL ({reason}): {PROVISION}", pytrace=False)
        if missing:
            pytest.fail(f"{self.template} lacks {', '.join(missing)}: {PROVISION}", pytrace=False)

    def sweep(self) -> list[str]:
        """Drop `ci_test_*` databases whose process is gone and `cs_tpl_*` of other hashes.

        Only these two prefixes are touched; the server may hold other projects' databases.
        """
        dropped = []
        for name in self.names("ci_test_"):
            match = TEST_DB.fullmatch(name)
            if match and not alive(int(match.group(1))):
                dropped.append(name)
        dropped += [name for name in self.names("cs_tpl_") if name != self.current]
        for name in dropped:
            self.drop(name)
        return dropped

    def build_template(self) -> None:
        """Clone `cs_template` to a scratch name, migrate it to head, then rename it."""
        scratch = f"{self.current}_build"
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
    def clone(self, name: str) -> Iterator[Engine]:
        """A database cloned from the migrated template, dropped `WITH (FORCE)` afterwards."""
        self.create(name, self.current)
        engine = create_engine(self.url_of(name))
        try:
            yield engine
        finally:
            engine.dispose()
            self.drop(name)


@pytest.fixture(scope="session")
def db_server() -> PgAdmin:
    """The test server, checked and swept, with the migrated template for this migration state."""
    server = PgAdmin(server_url(), Settings().database.template)
    server.check()
    with template_lock():
        server.drop(f"ci_test_{os.getpid()}")
        server.sweep()
        if not server.exists(server.current):
            server.build_template()
    return server


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
