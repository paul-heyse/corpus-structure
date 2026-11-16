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
        deploy_candidate(root, wrong_purpose, binding, prepared, report=effects.append)
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

    deployed = success(run("deploy", authored))
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
            deploy_candidate(root, settings, binding, prepared, report=lambda _: None)
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
