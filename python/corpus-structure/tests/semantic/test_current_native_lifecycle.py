"""Current native-only root uses the ordinary managed model lifecycle on an empty target."""

import json
import shutil
import subprocess

import pytest
import yaml
from conftest import settings_for_native_clone
from model_change_support import model_checkout as model_checkout
from sqlalchemy import text


def test_native_only_current_root_preview_register_deploy_and_refusals(
    cli, semantic_bare_engine, native_settings, model_checkout, monkeypatch
):
    from typer.testing import CliRunner

    from corpus_structure.cli import recipes
    from corpus_structure.cli.app import app
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.cli.output import CliState
    from corpus_structure.schema import generate, preparation
    from corpus_structure.schema.model_deployment import Candidate
    from corpus_structure.semantic import migrations, runtime
    from corpus_structure.semantic.execution_admission import verify_deployment_catalog

    root, _ = model_checkout
    # Review exactly the production owners, without a second implementation or
    # historical migration checkout. The loaded code and captured files agree.
    for name in ("semantic", "schema", "model"):
        shutil.copytree(
            generate.PACKAGE / name,
            root / preparation.PACKAGE_PATH / name,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "-qm",
            "current native source basis",
        ],
        check=True,
    )
    location = root / preparation.PACKAGE_PATH.parents[1] / "target_alembic"
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
    monkeypatch.setattr(recipes, "checkout", lambda _: root)
    settings = settings_for_native_clone(native_settings, semantic_bare_engine.url.database)
    settings = settings.model_copy(update={"ci_results": root / "results", "deployment": None})
    assert migrations.head_revision() is None

    runner = CliRunner()

    def run(*args, **kwargs):
        return runner.invoke(
            app,
            ["model", "change", *args, "--json"],
            obj=CliState(settings_factory=lambda: settings),
            **kwargs,
        )

    def success(result):
        assert result.exit_code == 0, result.output
        return json.loads(result.stdout)

    staged = success(
        run("preview", "-", input=yaml.safe_dump({"native_revision": "current_root_control"}))
    )
    preview_id = staged["result_id"]
    success(run("apply", preview_id))
    candidate = success(run("candidate", preview_id))
    candidate_id = candidate["result_id"]
    store = ResultStore(root / "results")
    binding = Candidate.model_validate_json(store.read_artifact(candidate_id, "deployment"))
    assert binding.revision == "current_root_control" and binding.predecessor is None
    assert binding.release is None
    assert (
        binding.release_manifest_sha256
        is binding.release_artifacts_sha256
        is binding.inspection_sha256
        is None
    )
    assert "inspection" not in store.show(candidate_id).artifacts
    assert b"down_revision = None" in store.read_artifact(candidate_id, "wrapper")
    for view in ("operations", "sql"):
        success(run("inspect-candidate", candidate_id, "--view", view))
    no_capsule = run("inspect-candidate", candidate_id, "--view", "contract")
    assert no_capsule.exit_code == 1
    assert "native-only candidate" in no_capsule.stdout
    with semantic_bare_engine.connect() as connection:
        assert migrations.current_revision(connection) is None
        assert connection.scalar(text("SELECT to_regnamespace('sem')")) is None

    # Env bytes are reviewed inputs even for a fresh root with no base chain.
    environment = location / "env.py"
    original = environment.read_bytes()
    environment.write_bytes(original + b"\n# unreviewed environment\n")
    refused = run("register", candidate_id)
    assert refused.exit_code == 1
    environment.write_bytes(original)
    success(run("register", candidate_id))
    assert migrations.head_revision() == "current_root_control"

    from alembic.script import ScriptDirectory

    revision = ScriptDirectory.from_config(migrations.alembic_config()).get_revision(
        binding.revision
    )
    state = location / "versions" / revision.module.NATIVE_STATE_FILE
    original_state = state.read_bytes()
    state.write_bytes(original_state + b" ")
    refused = run("deploy", candidate_id)
    assert refused.exit_code == 1
    with semantic_bare_engine.connect() as connection:
        assert migrations.current_revision(connection) is None
    state.write_bytes(original_state)

    # Native-only installation must not acquire application/archive principals.
    opened = []
    original_open = runtime.open_runtime_engine

    def observed(settings, application_name: str, *, purpose: runtime.Purpose = "write", **kwargs):
        opened.append(purpose)
        return original_open(settings, application_name, purpose=purpose, **kwargs)

    monkeypatch.setattr(runtime, "open_runtime_engine", observed)
    deployed = success(run("deploy", candidate_id))
    assert deployed["release"] is None
    assert opened and set(opened) == {"maintenance"}
    with semantic_bare_engine.connect() as connection:
        assert migrations.current_revision(connection) == "current_root_control"
        verify_deployment_catalog(connection)
        assert connection.scalar(text("SELECT count(*) FROM sem.release")) == 0
        assert connection.scalar(text("SELECT count(*) FROM sem.deployment_admission")) == 0
        assert connection.scalar(text("SELECT to_regclass('ops.run')")) is None
        from corpus_structure.semantic.execution_admission import ExecutionAdmissionError
        from corpus_structure.semantic.native_objects import native_owner

        with connection.begin_nested() as damaged:
            with native_owner(connection, "corpus_sem_publisher"):
                connection.exec_driver_sql(
                    "ALTER FUNCTION data.execution_contract_descriptor() COST 900"
                )
            with pytest.raises(ExecutionAdmissionError):
                verify_deployment_catalog(connection)
            damaged.rollback()
        verify_deployment_catalog(connection)
    # Explicit root means empty, not an unconstrained predecessor selection.
    refused = run("preview", "-", input=yaml.safe_dump({"native_revision": "another_root"}))
    assert refused.exit_code == 1
    assert "fresh native authoring requires an empty target" in refused.stdout


def test_creation_only_bootstrap_status_distinguishes_absent_from_unreadable_revision(
    cli, semantic_absent_database, native_server, native_settings, model_checkout, monkeypatch
):
    from corpus_structure.schema import preparation
    from corpus_structure.semantic import migrations

    root, _ = model_checkout
    location = root / preparation.PACKAGE_PATH.parents[1] / migrations.ALEMBIC_DIR.name
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
    settings = settings_for_native_clone(native_settings, semantic_absent_database.name)
    assert migrations.head_revision() is None
    bootstrap = ("db", "init", "--creation-token", semantic_absent_database.token, "--json")
    refused = cli(*bootstrap, settings=lambda: settings)
    assert refused.exit_code == 1 and "no current native root is registered" in refused.stdout
    assert not native_server.exists(semantic_absent_database.name)
    created = cli(*bootstrap, "--creation-only", settings=lambda: settings)
    assert created.exit_code == 0, created.output
    report = json.loads(created.stdout)
    assert report["created"] is True
    assert report["revision"] is report["model_revision"] is None and report["applied"] == []
    status = cli("db", "status", "--maintenance", "--json", settings=lambda: settings)
    assert status.exit_code == 0, status.output
    report = json.loads(status.stdout)
    assert report["revision_table_present"] is False and report["revision_readable"] is False
    assert report["revision"] is None and report["acquired"]["database"] == semantic_absent_database.name
    with native_server.connect(semantic_absent_database.name) as connection:
        connection.exec_driver_sql("CREATE TABLE public.semantic_alembic_version(version_num varchar(32) NOT NULL)")
        connection.exec_driver_sql("REVOKE ALL ON public.semantic_alembic_version FROM PUBLIC,corpus_sem_reader")
    denied_settings = settings.model_copy(update={
        "database": settings.database.model_copy(update={"maintenance_url": settings.database.reader_url})
    })
    denied = cli("db", "status", "--maintenance", "--json", settings=lambda: denied_settings)
    assert denied.exit_code == 1
    assert "configured maintenance principal cannot read the migration revision" in denied.stdout
