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
- Driver utility tests use extension-ready infrastructure clones. Shared semantic cases receive
  read-only or rollback-only connections; commit cases own fresh clones.
- All consumers clone one sealed session head template and replay normalized database ACLs
  and settings. Cold bootstrap, historical-revision and reserved absent-name routes remain real.
- PgAdmin owns acquisition, advisory leases and authenticated cleanup for both fixture families.
  The sweeper checks namespace, owner and comment; untagged residue is never adopted. Restricted
  backends exit normally under a bounded retry; no backend termination privilege is introduced.

"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from hypothesis import settings as hypothesis_settings
from native_fixture_support import (
    commit_admitter_engine as commit_admitter_engine,
)
from native_fixture_support import (
    commit_db_engine as commit_db_engine,
)
from native_fixture_support import (
    commit_evaluator_engine as commit_evaluator_engine,
)
from native_fixture_support import (
    commit_reader_engine as commit_reader_engine,
)
from native_fixture_support import (
    commit_writer_engine as commit_writer_engine,
)
from native_fixture_support import (
    semantic_bare_engine as semantic_bare_engine,
)
from native_fixture_support import (
    semantic_database_at as semantic_database_at,
)
from sqlalchemy import Connection, Engine
from sqlalchemy.engine import URL, make_url
from statistics_pack_support import (
    statistics_pack_inputs as statistics_pack_inputs,
)
from statistics_pack_support import (
    statistics_pack_prepared as statistics_pack_prepared,
)
from statistics_pack_support import (
    statistics_rules_policy as statistics_rules_policy,
)
from typer.testing import CliRunner, Result

from corpus_structure.core.db.ownership import DatabaseReservation
from corpus_structure.semantic.runtime import Purpose, connection_settings
from corpus_structure.settings import Settings
from native_test_support import (
    DatabaseGrant,
    DatabasePolicy,
    DatabaseSetting,
    PgAdmin,
    RollbackCase,
    SemanticDeployment,
    database_name,
    expected_extensions,
    record_server_context,
    rollback_case,
    rollback_connection,
    semantic_principals,
    server_url,
)
from test_prerequisites import mark_prerequisites

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
        "domain_default_case",
        "domain_formula_source",
        "resubmission_case",
        "resubmission_historical_source",
        "resubmission_application_settings",
        "exclusion_case",
        "exclusion_read_case",
        "exclusion_literal_case",
        "exclusion_refusal_family",
        "occurrence_case",
        "occurrence_refusal_family",
        "imported_declaration_case",
        "imported_membership_case",
        "declared_membership_case",
        "record_source_settings",
        "ddo_original_source",
        "db_server",
        "native_server",
        "commit_db_engine",
        "semantic_head_template",
        "semantic_bare_engine",
        "semantic_database_at",
        "semantic_absent_database",
        "commit_writer_engine",
        "commit_reader_engine",
        "commit_evaluator_engine",
        "commit_admitter_engine",
        "commit_application_settings",
        "native_read",
        "native_rollback",
        "commit_clone",
        "infrastructure_engine",
        "infrastructure_rollback",
        "infrastructure_commit_engine",
        "scenario_seeds",
        "ddo_kernel",
        "record_source_admin",
        "record_source_writer",
        "record_source_reader",
        "record_source_evaluator",
        "record_source_admitter",
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


def _missing_retained_files(paths: tuple[Path, ...]) -> str | None:
    missing = []
    for path in paths:
        if not path.is_file():
            missing.append(f"retained asset requires {path}")
        else:
            with path.open("rb") as stream:
                if stream.readline(128).strip() == b"version https://git-lfs.github.com/spec/v1":
                    missing.append(f"retained asset requires Git LFS hydration of {path}")
    return "; ".join(missing) if missing else None


def _missing_pm2_native_assets() -> str | None:
    selected = os.environ.get("CORPUS_PM2_NATIVE_TEST_ASSETS")
    if not selected or not Path(selected).is_dir():
        return (
            "CORPUS_PM2_NATIVE_TEST_ASSETS must name an available native provider assets directory"
        )
    return None


def _missing_page85_native_capture() -> str | None:
    evidence = REPO / "docs/design_review/evidence/2026-10-31_pdf-serialization-retention/raw"
    original = Path(
        os.environ.get(
            "CORPUS_PDF_QUALIFICATION_SOURCE",
            str(CORPUS_DIR / "corpus/siegrist_random/Full_PDF/Full.pdf"),
        )
    )
    return _missing_retained_files(
        (original, evidence / "convert.payload.json", evidence / "convert.recipe.json")
    )


def _missing_task86_witness() -> str | None:
    witness = Path(
        os.environ.get(
            "CORPUS_PDF_REPLAY_PAYLOAD",
            str(
                REPO
                / "docs/design_review/evidence/2026-10-31_pdf-integrated-adoption"
                / "integration/raw/book-task86-prepared.json.gz"
            ),
        )
    )
    return _missing_retained_files((witness,))


def _missing_nemotron_runtime() -> str | None:
    candidates = (
        REPO / "services/nemotron-parse/.venv/bin/python",
        Path.home() / ".cache/corpus-structure/nemotron-runtime-py312/bin/python",
    )
    if not any(path.is_file() for path in candidates):
        return "isolated public Nemotron parser environment unavailable"
    return None


_PREREQUISITES = {
    "corpus": lambda: _missing_local_corpus(CORPUS_DIR),
    "pm2_native_assets": _missing_pm2_native_assets,
    "page85_native_capture": _missing_page85_native_capture,
    "task86_witness": _missing_task86_witness,
    "nemotron_runtime": _missing_nemotron_runtime,
}
_prerequisite_cache = pytest.StashKey[dict[str, str | None]]()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if DB_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.db)


def pytest_collection_finish(session: pytest.Session) -> None:
    # Provider/lane/keyword deselection has finished; no scenario fixture has started.
    cache = session.config.stash.setdefault(_prerequisite_cache, {})
    mark_prerequisites(session.items, _PREREQUISITES, cache)


# --- CLI -------------------------------------------------------------------------------------


class Cli:
    """Invokes `ci` in process with stdout and stderr apart and Rich's width fixed."""

    def __init__(self) -> None:
        self.runner = CliRunner(env={"COLUMNS": str(CLI_WIDTH), "NO_COLOR": "1"})

    def __call__(
        self, *args: str, settings: Callable[[], Settings] | None = None, env: dict | None = None
    ) -> Result:
        from corpus_structure.cli.app import app
        from corpus_structure.cli.output import CliState

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
def commit_application_settings(native_settings: Settings, commit_db_engine: Engine) -> Settings:
    """Application settings bound to this test's owned semantic clone."""
    assert commit_db_engine.url.database is not None
    return settings_for_native_clone(native_settings, commit_db_engine.url.database)


@pytest.fixture(scope="session")
def native_server(native_settings: Settings) -> PgAdmin:
    server = PgAdmin(
        server_url(native_settings), native_settings.database.template, settings=native_settings
    )
    server.check()
    swept = server.sweep()
    if swept.skipped:
        print("Native database sweep skipped: " + ", ".join(swept.skipped), file=sys.stderr)
    record_server_context(native_settings, server, sweep=swept)
    return server


@pytest.fixture(scope="session")
def semantic_head_template(native_server: PgAdmin) -> Iterator[SemanticDeployment]:
    """One package-wide fixture definition, shared by semantic and sibling consumers."""
    with native_server.deployment() as template:
        yield template


@pytest.fixture
def semantic_absent_database(native_server: PgAdmin) -> Iterator[DatabaseReservation]:
    native_server.semantic_ready()
    name = database_name("init").name
    with native_server.reserved(name) as reserved:
        yield reserved


@pytest.fixture(scope="session")
def db_server(native_server: PgAdmin) -> PgAdmin:
    """The same authenticated server lifecycle used by semantic role controls."""
    return native_server


@pytest.fixture(scope="session")
def _semantic_session_engine(semantic_head_template: SemanticDeployment) -> Iterator[Engine]:
    """Private writable base; public shared semantic fixtures lend constrained connections."""
    with semantic_head_template.clone(database_name("session").name) as engine:
        yield engine


@pytest.fixture
def native_read(_semantic_session_engine: Engine) -> Iterator[Connection]:
    with rollback_connection(_semantic_session_engine, readonly=True, enforce=False) as conn:
        yield conn


@pytest.fixture
def native_rollback(
    native_server: PgAdmin, native_settings: Settings, _semantic_session_engine: Engine
) -> Iterator[RollbackCase]:
    assert _semantic_session_engine.url.database is not None
    with rollback_case(
        native_server, native_settings, _semantic_session_engine.url.database
    ) as case:
        yield case


@pytest.fixture
def commit_clone(semantic_head_template: SemanticDeployment):
    def clone():
        return semantic_head_template.clone(database_name("test").name)

    return clone


@pytest.fixture(scope="session")
def infrastructure_engine(native_server: PgAdmin) -> Iterator[Engine]:
    policy = native_server.policy(native_server.template)
    with native_server.database(
        database_name("infra").name, native_server.template, policy=policy
    ) as engine:
        yield engine


@pytest.fixture
def infrastructure_rollback(infrastructure_engine: Engine) -> Iterator[Connection]:
    with rollback_connection(infrastructure_engine) as connection:
        yield connection


@pytest.fixture
def infrastructure_commit_engine(native_server: PgAdmin) -> Iterator[Engine]:
    policy = native_server.policy(native_server.template)
    with native_server.database(
        database_name("infra_case").name, native_server.template, policy=policy
    ) as engine:
        yield engine


@pytest.fixture(scope="session")
def scenario_seeds(native_server, semantic_head_template, native_settings, tmp_path_factory):
    from native_scenario_seeds import ScenarioSeeds

    registry = ScenarioSeeds(
        native_server, semantic_head_template, native_settings, tmp_path_factory.mktemp
    )
    try:
        yield registry
    finally:
        registry.close()


@pytest.fixture
def observed_store_checkouts(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Attach the existing recorder to actual Store sessions, including startup refusal."""
    from psycopg_pool import ConnectionPool

    from native_test_support import observe_connection

    engine = request.getfixturevalue("infrastructure_engine")
    nodeid = request.node.nodeid
    check = ConnectionPool.check_connection

    def observed(connection):
        check(connection)
        observe_connection(connection, engine.url, purpose=None, nodeid=nodeid)

    monkeypatch.setattr(ConnectionPool, "check_connection", staticmethod(observed))


@pytest.fixture
def ddo_kernel(request, scenario_seeds):
    """Select a declared kernel recipe without importing its owner for unrelated tests."""
    from semantic.data_operation_kernel_support import kernel_clone

    yield from kernel_clone(request, scenario_seeds)


@pytest.fixture
def original_target(tmp_path, request):
    """Build the selected original-target input only for its explicit consumers."""
    from semantic.data_operation_kernel_support import original_target as build_original_target

    return build_original_target(tmp_path, request)


@pytest.fixture
def record_source_admin(private_source):
    """Maintenance access to this source's owned committed clone."""
    assert private_source.clone is not None
    return private_source.clone.admin


@pytest.fixture
def record_source_writer(private_source):
    assert private_source.clone is not None
    return private_source.clone.writer


@pytest.fixture
def record_source_reader(private_source):
    assert private_source.clone is not None
    return private_source.clone.reader


@pytest.fixture
def record_source_evaluator(private_source):
    assert private_source.clone is not None
    return private_source.clone.evaluator


@pytest.fixture
def record_source_admitter(private_source):
    assert private_source.clone is not None
    return private_source.clone.admitter


@pytest.fixture
def record_source_settings(native_settings, record_source_admin):
    database = record_source_admin.url.database
    assert database is not None
    return settings_for_native_clone(native_settings, database)


@pytest.fixture
def domain_default_case(scenario_seeds):
    from semantic.domain_scenarios import DomainCaseRecipe

    with scenario_seeds.commit_clone(DomainCaseRecipe()) as clone:
        yield clone


@pytest.fixture
def domain_formula_source(scenario_seeds, request):
    from semantic.domain_scenarios import DomainPreparationRecipe, DomainSourceRecipe

    recipe = getattr(
        request, "param", DomainSourceRecipe(DomainPreparationRecipe(formula_values=True))
    )
    if not isinstance(recipe, DomainSourceRecipe) or not recipe.preparation.formula_values:
        raise TypeError("formula source requires a frozen formula-capable prefix recipe")
    with scenario_seeds.commit_clone(recipe) as clone:
        yield clone


@pytest.fixture
def resubmission_case(scenario_seeds, request):
    from semantic.agent_scenarios import ResubmissionRecipe

    recipe = getattr(request, "param", ResubmissionRecipe())
    if not isinstance(recipe, ResubmissionRecipe):
        raise TypeError("resubmission case requires a frozen recipe")
    with scenario_seeds.commit_clone(recipe) as clone:
        yield clone


@pytest.fixture
def resubmission_application_settings(native_settings, resubmission_case):
    database = resubmission_case.admin.url.database
    assert database is not None
    return settings_for_native_clone(native_settings, database)


@pytest.fixture
def exclusion_case(scenario_seeds, request):
    from semantic.agent_scenarios import ExclusionRecipe

    recipe = getattr(request, "param", ExclusionRecipe(finalize=True))
    if not isinstance(recipe, ExclusionRecipe):
        raise TypeError("exclusion case requires a frozen recipe")
    with scenario_seeds.commit_clone(recipe) as clone:
        yield clone


@pytest.fixture
def exclusion_read_case(scenario_seeds, attribute_assertions):
    from semantic.agent_scenarios import ExclusionRecipe

    recipe = ExclusionRecipe(finalize=True, attribute_assertions=attribute_assertions)
    with scenario_seeds.rollback_family(recipe) as case:
        yield case


@pytest.fixture
def exclusion_literal_case(scenario_seeds, local_ids):
    from semantic.agent_scenarios import ExclusionRecipe

    recipe = ExclusionRecipe(finalize=True, attribute_assertions=True, local_ids=local_ids)
    with scenario_seeds.commit_clone(recipe) as clone:
        yield clone


@pytest.fixture
def exclusion_refusal_family(scenario_seeds, attack):
    from semantic.agent_scenarios import ExclusionRecipe

    recipe = ExclusionRecipe(
        citations=2, local_ids=("p_", "q"), attribute_assertions=attack.startswith("attribute_")
    )
    with scenario_seeds.rollback_family(recipe) as case:
        yield case


@pytest.fixture
def occurrence_case(scenario_seeds, request):
    from semantic.domain_scenarios import DomainCaseRecipe

    recipe = getattr(request, "param", DomainCaseRecipe(duplicate=True, occurrence_context=True))
    with scenario_seeds.commit_clone(recipe) as clone:
        yield clone


@pytest.fixture
def occurrence_refusal_family(scenario_seeds):
    from semantic.domain_scenarios import DomainCaseRecipe

    with scenario_seeds.rollback_family(
        DomainCaseRecipe(duplicate=True, occurrence_context=True)
    ) as case:
        yield case


@pytest.fixture
def imported_declaration_case(scenario_seeds):
    from semantic.membership_scenarios import ImportedDeclarationRecipe

    with scenario_seeds.commit_clone(ImportedDeclarationRecipe()) as clone:
        yield clone


@pytest.fixture
def imported_membership_case(scenario_seeds, forgery):
    from semantic.membership_scenarios import ImportedDeclarationRecipe

    recipe = ImportedDeclarationRecipe()
    lifetime = (
        scenario_seeds.commit_clone(recipe)
        if forgery == "valid"
        else scenario_seeds.rollback_family(recipe)
    )
    with lifetime as case:
        yield case


@pytest.fixture
def declared_membership_case(scenario_seeds, forgery):
    from semantic.domain_scenarios import domain_case_recipe

    recipe = domain_case_recipe(
        graph=True, membership_subtype=True, unselected_report=forgery == "source_cut"
    )
    lifetime = (
        scenario_seeds.commit_clone(recipe)
        if forgery == "valid"
        else scenario_seeds.rollback_family(recipe)
    )
    with lifetime as case:
        yield case


@pytest.fixture
def resubmission_historical_source(scenario_seeds, request):
    from semantic.agent_scenarios import ResubmissionRecipe, ResubmissionSourceRecipe

    recipe = getattr(request, "param", ResubmissionRecipe())
    if not isinstance(recipe, ResubmissionRecipe):
        raise TypeError("historical source requires a frozen resubmission recipe")
    with scenario_seeds.commit_clone(ResubmissionSourceRecipe(recipe)) as clone:
        yield clone


@pytest.fixture
def ddo_original_source(request, scenario_seeds):
    from semantic.data_operation_original_support import original_source_clone

    yield from original_source_clone(request, scenario_seeds)
