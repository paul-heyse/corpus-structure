"""Shared test configuration for the corpus-structure package (D9 §4; coordinator decision 10).

- Hypothesis profiles `ci` and `dev`, chosen by `HYPOTHESIS_PROFILE` (default `dev`).
- Markers `db`, `gpu` and `corpus`. `corpus` tests require the prepared local acquisition,
  including its indexes and hydrated source files. Tests using database fixtures are marked `db`.
- `cli`: Typer's runner with stdout and stderr apart and a fixed width.
- Native coordinates come from the original session Settings. Maintenance and restricted
  credentials resolve by purpose before changing only the owned clone's database name.
- External server/template/extension/principal absence or incompatible extensions are reported
  as blocked prerequisites while preserving pytest's setup failure. Authentication, configuration,
  migration, posture and cleanup defects remain failures.
- Generic database utility tests use maintenance connections on current semantic clones; `db`
  uses an outer rollback and `committing_db` uses an independently committed clone.
- All consumers clone one sealed session head template and replay normalized database ACLs
  and settings. Cold bootstrap, historical-revision and reserved absent-name routes remain real.
- PgAdmin owns acquisition, advisory leases and authenticated cleanup for both fixture families.
  The sweeper checks namespace, owner and comment; untagged residue is never adopted. Restricted
  backends exit normally under a bounded retry; no backend termination privilege is introduced.

"""

from __future__ import annotations

import itertools
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from hypothesis import settings as hypothesis_settings
from sqlalchemy import Connection, Engine
from sqlalchemy.engine import URL, make_url
from typer.testing import CliRunner, Result

from corpus_structure.cli.app import app
from corpus_structure.cli.output import CliState
from corpus_structure.core.db.ownership import DatabaseReservation
from corpus_structure.semantic.runtime import Purpose, connection_settings
from corpus_structure.settings import Settings
from native_test_support import (
    TEMPLATE_RETENTION,
    DatabaseGrant,
    DatabasePolicy,
    DatabaseSetting,
    PgAdmin,
    SemanticTemplate,
    expected_extensions,
    record_server_context,
    rollback_connection,
    semantic_principals,
    server_url,
)

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
CORPUS_DIR = REPO / "docs" / "statistics_corpus"
CLI_WIDTH = 100
REFUSED_APPLICATION_URL = (
    "postgresql://corpus_test_unbound@/unbound"
    "?host=/__corpus_structure_refused_application_target__&port=5434"
)

hypothesis_settings.register_profile(
    "ci", deadline=None, derandomize=True, database=None, print_blob=True, max_examples=300
)
hypothesis_settings.register_profile("dev")
hypothesis_settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))

DB_FIXTURES = frozenset(
    {
        "db",
        "committing_db",
        "db_engine",
        "db_server",
        "native_server",
        "semantic_db_engine",
        "semantic_head_template",
        "semantic_bare_engine",
        "semantic_database_at",
        "semantic_absent_database",
        "semantic_writer_engine",
        "semantic_reader_engine",
        "semantic_evaluator_engine",
        "semantic_admitter_engine",
    }
)


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
    config.addinivalue_line("markers", "corpus: needs the prepared local statistics corpus")


def _missing_local_corpus(root: Path) -> str | None:
    # The public archive is a source subset. The full local acquisition supplies its own indexes.
    for name in (
        "MANIFEST.sha256",
        "index/siegrist_sections.tsv",
        "corpus/siegrist_random/random/special/Pareto.html",
    ):
        path = root / name
        if not path.is_file():
            return f"prepared local corpus requires {path}"
        with path.open("rb") as stream:
            if stream.readline(128).strip() == b"version https://git-lfs.github.com/spec/v1":
                return f"prepared local corpus requires Git LFS hydration of {path}"
    return None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    missing_corpus = (
        _missing_local_corpus(CORPUS_DIR)
        if any(item.get_closest_marker("corpus") for item in items)
        else None
    )
    for item in items:
        if DB_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.db)
        if missing_corpus and item.get_closest_marker("corpus"):
            item.user_properties.extend(
                [
                    ("qualification_prerequisite", "corpus"),
                    ("qualification_reason", missing_corpus),
                ]
            )
            item.add_marker(pytest.mark.skip(reason=missing_corpus))


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


@dataclass(frozen=True)
class DatabaseSupport:
    PgAdmin = PgAdmin
    server_url = staticmethod(server_url)
    expected_extensions = staticmethod(expected_extensions)
    TEMPLATE_RETENTION = TEMPLATE_RETENTION
    semantic_principals = staticmethod(semantic_principals)
    DatabaseGrant = DatabaseGrant
    DatabaseSetting = DatabaseSetting
    DatabasePolicy = DatabasePolicy


@pytest.fixture(scope="session")
def db_support() -> DatabaseSupport:
    """The helpers above, for tests (importlib import mode leaves this module unimportable)."""
    return DatabaseSupport()


@pytest.fixture(scope="session")
def native_settings() -> Settings:
    """Capture original environment coordinates before application-target fencing."""
    return Settings()


@pytest.fixture(autouse=True)
def refuse_unbound_application_target(
    monkeypatch: pytest.MonkeyPatch, native_settings: Settings
) -> None:
    """Keep default application acquisition away from the native admin endpoint.

    The dependency forces the original session settings to be captured before the sentinel is
    installed. Native server and purpose fixtures keep using that immutable captured value.
    Tests that exercise an application connection must pass clone settings or an explicit
    ``CORPUS_DATABASE__URL`` themselves.
    """
    monkeypatch.setenv("CORPUS_DATABASE__URL", REFUSED_APPLICATION_URL)


def settings_for_native_clone(
    original: Settings, database_name: str, purpose: Purpose = "write"
) -> Settings:
    """Resolve purpose credentials on the original endpoint, then bind them to one clone.

    Every declared purpose URL in the returned settings is authentication-only. A later
    ``connection_settings`` call therefore inherits the clone endpoint instead of conflicting
    with the original endpoint retained by a fully qualified purpose URL.
    """
    resolved = connection_settings(original, purpose)
    target = make_url(resolved.database.url).set(database=database_name)
    database = resolved.database.model_copy(
        update={
            "url": target.render_as_string(hide_password=False),
            "maintenance_url": _authentication_url(original, "maintenance"),
            "reader_url": _authentication_url(original, "read"),
            "evaluator_url": _authentication_url(original, "evaluate"),
            "admission_url": _authentication_url(original, "admit"),
        }
    )
    return resolved.model_copy(update={"database": database})


def _authentication_url(original: Settings, purpose: Purpose) -> str:
    selected = make_url(connection_settings(original, purpose).database.url)
    return URL.create(
        "postgresql", username=selected.username, password=selected.password
    ).render_as_string(hide_password=False)


@pytest.fixture
def semantic_application_settings(
    native_settings: Settings, semantic_db_engine: Engine
) -> Settings:
    """Application settings bound to this test's owned semantic clone."""
    assert semantic_db_engine.url.database is not None
    return settings_for_native_clone(native_settings, semantic_db_engine.url.database)


@pytest.fixture(scope="session")
def native_server(native_settings: Settings) -> PgAdmin:
    server = PgAdmin(
        server_url(native_settings), native_settings.database.template, settings=native_settings
    )
    server.check()
    principals = semantic_principals()
    server.check_roles(principals)
    server.sweep()
    record_server_context(native_settings, server)
    return server


@pytest.fixture(scope="session")
def semantic_head_template(native_server: PgAdmin) -> Iterator[SemanticTemplate]:
    """One package-wide fixture definition, shared by semantic and sibling consumers."""
    name = f"cs_sem_head_{os.getpid()}_{uuid4().hex[:12]}"
    with native_server.semantic_template(name) as template:
        yield template


@pytest.fixture
def semantic_absent_database(native_server: PgAdmin) -> Iterator[DatabaseReservation]:
    name = f"cs_sem_init_{os.getpid()}_{uuid4().hex[:12]}"
    with native_server.reserved(name) as reserved:
        yield reserved


@pytest.fixture(scope="session")
def db_server(native_server: PgAdmin) -> PgAdmin:
    """The same authenticated server lifecycle used by semantic role controls."""
    return native_server


_clones = itertools.count(1)


@pytest.fixture(scope="session")
def db_engine(db_server: PgAdmin, semantic_head_template: SemanticTemplate) -> Iterator[Engine]:
    """Maintenance engine on a current frozen semantic clone for utility probe DDL."""
    with db_server.database(
        f"ci_test_{os.getpid()}", semantic_head_template.name, policy=semantic_head_template.policy
    ) as engine:
        yield engine


@pytest.fixture
def db(db_engine: Engine) -> Iterator[Connection]:
    """A connection inside an outer transaction that is rolled back after the test."""
    with rollback_connection(db_engine) as conn:
        yield conn


@pytest.fixture
def committing_db(db_server: PgAdmin, semantic_head_template: SemanticTemplate) -> Iterator[Engine]:
    """An engine on a clone of its own, for tests that need commits (queue, NOTIFY, COPY)."""
    with db_server.database(
        f"ci_test_{os.getpid()}_{next(_clones)}",
        semantic_head_template.name,
        policy=semantic_head_template.policy,
    ) as engine:
        yield engine


@pytest.fixture
def observed_store_checkouts(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Attach the existing recorder to actual Store sessions, including startup refusal."""
    from psycopg_pool import ConnectionPool

    from native_test_support import observe_connection

    engine = request.getfixturevalue("db_engine")
    nodeid = request.node.nodeid
    check = ConnectionPool.check_connection

    def observed(connection):
        check(connection)
        observe_connection(connection, engine.url, purpose=None, nodeid=nodeid)

    monkeypatch.setattr(ConnectionPool, "check_connection", staticmethod(observed))
