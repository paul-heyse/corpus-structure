"""A current captured DDO release resumes exact native deployment before separate activation."""

import json
from hashlib import sha256

import pytest
import yaml
from conftest import settings_for_native_clone
from model_change_support import current_native_model_checkout as current_native_model_checkout
from model_change_support import model_checkout as model_checkout
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import DBAPIError
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.cli.managed import Invocation, ResultStore
from corpus_structure.cli.output import CliState
from corpus_structure.schema.model import ModelError
from corpus_structure.schema.model_deployment import Candidate, deploy_candidate
from corpus_structure.semantic import migrations
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import activation_token
from semantic.archive_faults import administrative_archive_edit
from semantic.data_operation_kernel_support import STORAGE


@pytest.mark.prerequisite("pm2_native_assets")
def test_maintained_statistics_application_cli_retains_large_runtime_and_atomic_admission(
    commit_db_engine, native_settings, current_native_model_checkout, monkeypatch
):
    """Actual local application metadata and native transport, without model inference."""
    import shutil
    import subprocess
    from pathlib import Path

    from corpus_structure.cli import model as commands
    from corpus_structure.cli import recipes
    from corpus_structure.schema import preparation
    from corpus_structure.semantic import runtime_binding_store
    from corpus_structure.semantic.runtime import open_runtime_engine

    root, _ = current_native_model_checkout
    maintained = Path(__file__).resolve().parents[4] / "domains/statistics"
    shutil.copytree(maintained, root / "domains/statistics")
    location = root / preparation.PACKAGE_PATH.parents[1] / migrations.ALEMBIC_DIR.name
    # This application-only journey starts at the registered current head. Its
    # checkout therefore retains that real frozen chain, unlike the fresh-root
    # authoring fixture's intentionally empty versions directory.
    shutil.copytree(migrations.ALEMBIC_DIR / "versions", location / "versions", dirs_exist_ok=True)
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
            "actual statistics application inputs",
        ],
        check=True,
    )
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
    monkeypatch.setattr(recipes, "checkout", lambda _: root)
    settings = settings_for_native_clone(native_settings, commit_db_engine.url.database)
    settings = settings.model_copy(update={"ci_results": root / "results", "deployment": None})
    runner = CliRunner()

    def command(action, identifier, **kwargs):
        result = runner.invoke(
            app,
            ["model", "change", action, identifier, "--json"],
            obj=CliState(settings_factory=lambda: settings),
            **kwargs,
        )
        return result

    def success(result):
        assert result.exit_code == 0, result.output
        return json.loads(result.stdout)

    staged = success(
        command(
            "preview",
            "-",
            input=yaml.safe_dump(
                {
                    "deployment": True,
                    "data_operations": "domains/statistics/operations.yaml",
                    "execution_profile": "source-native",
                }
            ),
        )
    )
    success(command("apply", staged["result_id"]))
    authored = success(command("candidate", staged["result_id"]))
    store = ResultStore(root / "results")
    binding = Candidate.model_validate_json(
        store.read_artifact(authored["result_id"], "deployment")
    )
    assert binding.revision is None
    assert binding.target_identity is not None and binding.runtime is not None
    prepared = commands._prepare_release(
        root, (), data_operations="domains/statistics/operations.yaml"
    )
    runtime = commands._read_runtime(store, authored["result_id"], binding.runtime, prepared[3])
    assert runtime is not None
    assert len(runtime.archive) > 64 * 1024**2
    assert json.loads(runtime.manifest)["execution_profile"] == "source-native"
    assert json.loads(runtime.manifest)["observed"] == {}
    assert sha256(runtime.archive).hexdigest() == binding.runtime.archive_sha256
    assert store.read_artifact(staged["result_id"], "runtime_archive") == runtime.archive
    assert store.read_artifact(staged["result_id"], "runtime_manifest") == runtime.manifest

    for purpose, principal in (("admit", "corpus_sem_admitter"), ("read", "corpus_sem_reader")):
        with (
            open_runtime_engine(settings, "statistics-actual-purpose", purpose=purpose) as engine,
            engine.connect() as connection,
        ):
            assert connection.scalar(text("SELECT current_user")) == principal

    persist_runtime = runtime_binding_store.persist_runtime_binding

    def refuse_after_real_runtime(connection, release, actual):
        assert actual == runtime
        assert connection.scalar(text("SELECT current_user")) == "corpus_sem_admitter"
        persist_runtime(connection, release, actual)
        raise ModelError(["controlled refusal after actual statistics runtime registration"])

    with monkeypatch.context() as faults:
        faults.setattr(runtime_binding_store, "persist_runtime_binding", refuse_after_real_runtime)
        failed = command("deploy", authored["result_id"])
    assert failed.exit_code == 1, failed.output
    failure = json.loads(failed.stdout)
    assert "controlled refusal after actual statistics runtime" in failure["error"]["message"]
    assert failure["operation_account"]["known_effects"] == ["archive"]
    with (
        open_runtime_engine(settings, "statistics-rollback-read", purpose="read") as engine,
        engine.connect() as connection,
    ):
        for relation in ("sem.runtime_binding", "sem.deployment_admission"):
            assert (
                connection.scalar(
                    text(f"SELECT count(*) FROM {relation} WHERE release_id=:release"),
                    {"release": binding.release},
                )
                == 0
            )

    deployed = success(command("deploy", authored["result_id"]))
    assert deployed["runtime"] == binding.runtime.model_dump(mode="json")
    assert deployed["operation_account"]["known_effects"] == ["archive", "admission", "verified"]
    assert deployed["operation_account"]["acquired_target"] == binding.target_identity.model_dump(
        mode="json"
    )
    with (
        open_runtime_engine(settings, "statistics-verified-read", purpose="read") as engine,
        engine.connect() as connection,
        connection.begin(),
    ):
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        assert connection.scalar(text("SHOW transaction_read_only")) == "on"
        assert connection.scalar(text("SELECT current_user")) == "corpus_sem_reader"
        assert (
            runtime_binding_store.runtime_binding_for_release(
                connection, prepared[3], runtime.runtime_id
            )
            == runtime
        )
    replay = success(command("deploy", authored["result_id"]))
    assert replay["runtime"] == deployed["runtime"]


def test_current_native_release_deployment_resumes_before_separate_activation(
    semantic_bare_engine, native_settings, current_native_model_checkout, monkeypatch
):
    from corpus_structure.cli import model as commands
    from corpus_structure.cli import recipes
    from corpus_structure.core.db.store import Store
    from corpus_structure.schema import preparation
    from corpus_structure.semantic.storage_target import StorageTargetError

    root, _ = current_native_model_checkout
    (root / "schema.yaml").write_text(STORAGE.schema_text)
    assert STORAGE.declaration_content is not None
    (root / "operations.yaml").write_bytes(STORAGE.declaration_content)
    (root / "target.yaml").write_text(STORAGE.manifest_text)
    location = root / preparation.PACKAGE_PATH.parents[1] / migrations.ALEMBIC_DIR.name
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", location)
    monkeypatch.setattr(recipes, "checkout", lambda _: root)
    settings = settings_for_native_clone(native_settings, semantic_bare_engine.url.database)
    settings = settings.model_copy(update={"ci_results": root / "results", "deployment": None})
    runner = CliRunner()

    def command(*args, **kwargs):
        return runner.invoke(
            app, [*args, "--json"], obj=CliState(settings_factory=lambda: settings), **kwargs
        )

    def run(action, candidate):
        return command("model", "change", action, candidate)

    def success(result):
        assert result.exit_code == 0, result.output
        return json.loads(result.stdout)

    staged = success(
        command(
            "model",
            "change",
            "preview",
            "-",
            input=yaml.safe_dump(
                {
                    "native_revision": "current_release_root",
                    "data_operations": "target.yaml",
                    "execution_profile": "execution:deployment-control",
                }
            ),
        )
    )
    success(run("apply", staged["result_id"]))
    authored = success(run("candidate", staged["result_id"]))["result_id"]
    store = ResultStore(root / "results")
    binding = Candidate.model_validate_json(store.read_artifact(authored, "deployment"))
    assert binding.release is not None and binding.inspection_sha256 is not None
    assert binding.target_identity is not None
    assert binding.release_artifacts_sha256 is not None
    success(run("register", authored))
    prepared = commands._prepare_release(root, (), data_operations="target.yaml")
    runtime = commands._read_runtime(store, authored, binding.runtime, prepared[3])
    assert runtime is not None and binding.runtime is not None
    assert staged["runtime"]["runtime_id"] == runtime.runtime_id
    assert binding.runtime.execution_profile == "execution:deployment-control"
    assert json.loads(runtime.manifest)["observed"] == {}
    wrong_cluster = binding.model_copy(
        update={
            "target_identity": binding.target_identity.model_copy(update={"system_identifier": "0"})
        }
    )
    with pytest.raises(StorageTargetError, match="differs from the approved target"):
        deploy_candidate(
            root,
            settings,
            wrong_cluster,
            prepared,
            report=lambda _: pytest.fail("unexpected effect"),
            runtime=runtime,
        )

    upgrade = migrations.upgrade

    def drift_after_upgrade(connection, *args, **kwargs):
        result = upgrade(connection, *args, **kwargs)
        connection.exec_driver_sql(
            "ALTER TABLE data.project ADD CONSTRAINT controlled_deployment_drift CHECK(length(project_id)>0)"
        )
        return result

    with monkeypatch.context() as faults:
        faults.setattr(migrations, "upgrade", drift_after_upgrade)
        failed = run("deploy", authored)
    assert failed.exit_code == 1, failed.output
    failure = json.loads(failed.stdout)
    assert "unexpected physical CHECK" in failure["error"]["message"]
    assert failure["operation_account"]["known_effects"] == []
    with semantic_bare_engine.connect() as connection:
        assert migrations.current_revision(connection) is None
        assert connection.scalar(text("SELECT to_regnamespace('sem')")) is None

    def lose_commit_acknowledgement(connection, *args, **kwargs):
        result = upgrade(connection, *args, **kwargs)
        commit = connection.dialect.do_commit

        def commit_and_lose(driver):
            faults.setattr(connection.dialect, "do_commit", commit)
            commit(driver)
            raise OSError("controlled lost migration commit acknowledgement")

        faults.setattr(connection.dialect, "do_commit", commit_and_lose)
        return result

    with monkeypatch.context() as faults:
        faults.setattr(migrations, "upgrade", lose_commit_acknowledgement)
        failed = run("deploy", authored)
    assert failed.exit_code == 1, failed.output
    failure = json.loads(failed.stdout)
    assert failure["operation_account"]["known_effects"] == ["migration"]
    assert failure["operation_account"]["failure"]["database_effects"] == "commit_confirmed"
    assert failure["operation_account"]["failure"]["operation_id"] == "model.deploy:migration"
    with semantic_bare_engine.connect() as connection:
        assert migrations.current_revision(connection) == binding.revision
        assert connection.scalar(text("SELECT count(*) FROM sem.release")) == 0

    wrong_purpose = settings.model_copy(
        update={
            "database": settings.database.model_copy(
                update={"admission_url": settings.database.reader_url}
            )
        }
    )
    effects = []
    with pytest.raises(DBAPIError) as denied:
        deploy_candidate(
            root, wrong_purpose, binding, prepared, report=effects.append, runtime=runtime
        )
    assert getattr(denied.value.orig, "sqlstate", None) == "42501"
    assert effects == ["migration"]
    with semantic_bare_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM sem.release")) == 0

    write, close = Invocation._write, Store.close

    def fail_checkpoint(invocation):
        if (
            invocation.manifest.action == "model.deploy"
            and invocation.manifest.stage == "migration"
            and invocation.manifest.settled is None
        ):
            raise OSError("controlled post-commit receipt failure")
        write(invocation)

    def fail_cleanup(store):
        close(store)
        if store.application_name == "ci-model-migrate":
            raise OSError("controlled maintenance cleanup failure")

    for cleanup in (False, True):
        with monkeypatch.context() as faults:
            faults.setattr(Invocation, "_write", fail_checkpoint)
            if cleanup:
                faults.setattr(Store, "close", fail_cleanup)
            failed = run("deploy", authored)
        assert failed.exit_code == 1, failed.output
        failure = json.loads(failed.stdout)
        account = failure["operation_account"]
        assert account["reached_revision"] == binding.revision
        assert account["known_effects"] == ["migration"]
        assert account["cleanup"] == ("unresolved" if cleanup else "established")
        retained = success(command("results", "show", failure["invocation_id"]))
        assert retained["operation_account"] == account
        if cleanup:
            refused = command("evidence", "retain", failure["invocation_id"], "--for", "I09")
            assert (
                refused.exit_code == 1
                and "evidence promotion requires established custody" in refused.stdout
            )

    # Existing current roots preflight all purpose/privilege boundaries before
    # publishing any application release or claiming admission.
    with semantic_bare_engine.begin() as connection:
        connection.exec_driver_sql(
            "GRANT TEMP ON DATABASE "
            + connection.dialect.identifier_preparer.quote(binding.target_identity.database)
            + " TO corpus_sem_writer"
        )
    try:
        failed = run("deploy", authored)
        assert failed.exit_code == 1, failed.output
        failure = json.loads(failed.stdout)
        assert "privileged runtime principal" in failure["error"]["message"]
        assert failure["operation_account"]["known_effects"] == []
    finally:
        with semantic_bare_engine.begin() as connection:
            connection.exec_driver_sql(
                "REVOKE TEMP ON DATABASE "
                + connection.dialect.identifier_preparer.quote(binding.target_identity.database)
                + " FROM corpus_sem_writer"
            )

    # Both native admissions share the transaction. A real runtime insert followed
    # by refusal must leave neither runtime nor operation admission standing.
    from corpus_structure.semantic import runtime_binding_store

    persist_runtime = runtime_binding_store.persist_runtime_binding

    def refuse_after_runtime(connection, release, actual):
        persist_runtime(connection, release, actual)
        raise ModelError(["controlled refusal after real runtime registration"])

    with monkeypatch.context() as faults:
        faults.setattr(runtime_binding_store, "persist_runtime_binding", refuse_after_runtime)
        failed = run("deploy", authored)
    assert failed.exit_code == 1, failed.output
    failure = json.loads(failed.stdout)
    assert failure["operation_account"]["known_effects"] == ["migration", "archive"]
    with semantic_bare_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM sem.runtime_binding")) == 0
        assert connection.scalar(text("SELECT count(*) FROM sem.deployment_admission")) == 0

    def lose_admission_ack(connection, release, actual):
        identity = persist_runtime(connection, release, actual)
        commit = connection.dialect.do_commit

        def commit_and_lose(driver):
            faults.setattr(connection.dialect, "do_commit", commit)
            commit(driver)
            raise OSError("controlled lost admission/runtime commit acknowledgement")

        faults.setattr(connection.dialect, "do_commit", commit_and_lose)
        return identity

    with monkeypatch.context() as faults:
        faults.setattr(runtime_binding_store, "persist_runtime_binding", lose_admission_ack)
        failed = run("deploy", authored)
    assert failed.exit_code == 1, failed.output
    failure = json.loads(failed.stdout)
    assert failure["operation_account"]["known_effects"] == ["migration", "archive", "admission"]
    assert failure["operation_account"]["failure"]["database_effects"] == "commit_confirmed"
    assert failure["operation_account"]["failure"]["operation_id"] == "model.deploy:admission"
    from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_release

    with semantic_bare_engine.connect() as connection:
        assert runtime_binding_for_release(connection, prepared[3], runtime.runtime_id) == runtime

    deployed = success(run("deploy", authored))
    assert deployed["runtime"] == binding.runtime.model_dump(mode="json")
    account = deployed["operation_account"]
    assert account["release"] == binding.release
    assert account["known_effects"] == ["migration", "archive", "admission", "verified"]
    assert account["acquired_target"] == binding.target_identity.model_dump(mode="json")
    admitted = table("sem.deployment_admission")
    exact = (admitted.c.release_id == binding.release) & (admitted.c.kind == "native")
    with semantic_bare_engine.begin() as connection:
        digest = connection.execute(select(admitted.c.content_digest).where(exact)).scalar_one()
        with administrative_archive_edit(connection, admitted):
            connection.execute(update(admitted).where(exact).values(content_digest="0" * 64))
    try:
        with pytest.raises(ModelError, match="admitted release does not match"):
            deploy_candidate(
                root, settings, binding, prepared, report=lambda _: None, runtime=runtime
            )
    finally:
        with (
            semantic_bare_engine.begin() as connection,
            administrative_archive_edit(connection, admitted),
        ):
            connection.execute(update(admitted).where(exact).values(content_digest=digest))

    project = "current-deployment-control"
    with semantic_bare_engine.begin() as connection:
        connection.execute(insert(table("data.project")).values(project_id=project))
        assert activation_token(connection, project).release_id is None
    checked = success(
        command("release", "check", "--target", "development", "--release", binding.release)
    )
    assert checked["acquired"]["database_oid"] == binding.target_identity.database_oid
    activated = success(
        command(
            "release", "activate", binding.release, "--project", project, "--target", "development"
        )
    )
    assert activated["release_id"] == binding.release and activated["generation"] == 1
    with semantic_bare_engine.connect() as connection:
        assert activation_token(connection, project).release_id == binding.release
        assert "selected_result_run_id" not in table("data.project").c
    # Archive bytes stay the actual reviewed release, without a second schema-only
    # or legacy-run publication route.
    assert sha256(prepared[3].manifest).hexdigest() == binding.release_manifest_sha256

    # The normal application-only route reuses the installed native root and
    # admits the same exact reviewed runtime without authoring another migration.
    application = success(
        command(
            "model",
            "change",
            "preview",
            "-",
            input=yaml.safe_dump(
                {
                    "deployment": True,
                    "data_operations": "target.yaml",
                    "execution_profile": "execution:deployment-control",
                }
            ),
        )
    )
    success(run("apply", application["result_id"]))
    application_candidate = success(run("candidate", application["result_id"]))
    assert application_candidate["runtime"]["runtime_id"] == runtime.runtime_id
    application_deployed = success(run("deploy", application_candidate["result_id"]))
    assert application_deployed["operation_account"]["known_effects"] == [
        "archive",
        "admission",
        "verified",
    ]

    # Actual ordinary demand creation can select the newly admitted runtime.
    # This controlled native integer producer establishes transport/custody,
    # without claiming PDF or provider execution.
    from typing import cast

    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand
    from corpus_structure.semantic.data_operation_service import (
        CreateDataDemand,
        create_data_demand,
    )
    from corpus_structure.semantic.runtime import open_runtime_engine

    intent = freeze_demand(
        bound_data_operation_model(prepared[3]),
        roots=(RootSubject("deployment:subject", "deployment:source", b'{"page":1}'),),
        targets=("urn:ddo-test:source",),
        inference="deployment:initial-native-request",
        execution_profile="execution:deployment-control",
    )
    with (
        open_runtime_engine(settings, "deployment-first-demand", purpose="write") as engine,
        engine.begin() as connection,
    ):
        created = create_data_demand(
            connection,
            CreateDataDemand(
                project_id=project,
                release_id=binding.release,
                runtime_id=runtime.runtime_id,
                intent=cast(dict, intent.record),
            ),
        )
    assert created["runtime_id"] == runtime.runtime_id
    assert created["release_id"] == binding.release
    assert created["obligations"][0]["subject"] == "deployment:subject"
