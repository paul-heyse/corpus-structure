"""Shared test configuration for the corpus-structure package (D9 §4; coordinator decision 10).

- Hypothesis profiles `ci` and `dev`, chosen by `HYPOTHESIS_PROFILE` (default `dev`).
- Markers `db`, `gpu` and `corpus`. `corpus` tests skip when `docs/statistics_corpus/` is absent;
  nothing else skips. Tests using the database fixtures are marked `db` automatically.
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
from typer.testing import CliRunner, Result

from corpus_structure.cli.app import app
from corpus_structure.cli.output import CliState
from corpus_structure.core.db.ownership import DatabaseReservation
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
    semantic_principals,
    server_url,
)

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
CORPUS_DIR = REPO / "docs" / "statistics_corpus"
CLI_WIDTH = 100

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
    config.addinivalue_line("markers", "corpus: needs docs/statistics_corpus (skipped without it)")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    no_corpus = pytest.mark.skip(reason=f"{CORPUS_DIR.relative_to(REPO)} is absent")
    for item in items:
        if DB_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.db)
        if item.get_closest_marker("corpus") and not CORPUS_DIR.is_dir():
            item.user_properties.extend(
                [
                    ("qualification_prerequisite", "corpus"),
                    ("qualification_reason", f"{CORPUS_DIR.relative_to(REPO)} is absent"),
                ]
            )
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
    return Settings()


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
    with db_engine.connect() as conn:
        outer = conn.begin()
        try:
            yield conn
        finally:
            outer.rollback()


@pytest.fixture
def committing_db(db_server: PgAdmin, semantic_head_template: SemanticTemplate) -> Iterator[Engine]:
    """An engine on a clone of its own, for tests that need commits (queue, NOTIFY, COPY)."""
    with db_server.database(
        f"ci_test_{os.getpid()}_{next(_clones)}",
        semantic_head_template.name,
        policy=semantic_head_template.policy,
    ) as engine:
        yield engine
