"""An exact installed candidate resumes without selecting a project result."""

import json
import os
import py_compile
from hashlib import sha256
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import insert, select, update
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError
from typer.testing import CliRunner

from corpus_structure.schema.model import ModelError
from corpus_structure.schema.model_change import generator_fingerprint
from corpus_structure.schema.model_deployment import (
    Candidate,
    deploy_candidate,
    deployment_settings,
    migration_wrapper,
    target_fingerprint,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.execution_admission import (
    ExecutionAdmissionError,
    _verify_deployment_functions,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.migrations import alembic_config, current_revision, head_revision
from corpus_structure.semantic.releases import activation_token
from corpus_structure.semantic.runtime import connection_settings, open_runtime_engine
from corpus_structure.semantic.storage_target import StorageTargetError, acquired_target
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies
from corpus_structure.settings import DeploymentDatabaseSettings
from semantic.archive_faults import administrative_archive_edit


@pytest.mark.parametrize("pending_base", [False, True])
def test_exact_native_deployment_resumes_before_separate_activation(
    semantic_database_at, native_settings, tmp_path, monkeypatch, pending_base
):
    from corpus_structure.cli import model as commands
    from corpus_structure.cli import recipes
    from corpus_structure.cli.app import app
    from corpus_structure.cli.managed import Invocation, ResultStore
    from corpus_structure.cli.output import CliState
    from corpus_structure.core.db.store import Store
    from corpus_structure.semantic import migrations

    revision = head_revision()
    assert revision is not None
    scripts = ScriptDirectory.from_config(alembic_config())
    script = scripts.get_revision(revision)
    assert script is not None and isinstance(script.down_revision, str)
    predecessor = script.down_revision
    prior_script = scripts.get_revision(predecessor)
    assert prior_script is not None and isinstance(prior_script.down_revision, str)
    starting_revision = prior_script.down_revision if pending_base else predecessor
    ancestors = {Path(item.path).name for item in scripts.iterate_revisions(predecessor, "base")}
    products = {
        product: Path(script.path)
        .with_name(getattr(script.module, f"NATIVE_{kind}_FILE"))
        .read_bytes()
        for kind, product in (
            ("UPGRADE", "native_candidate.py"),
            ("STATE", "native_operations.json"),
            ("ADMISSION", "native_admission.sql"),
        )
    }
    bundle = SourceBundle(
        "deployment-control",
        (
            SourceArtifact(
                "deployment-control",
                b"id: https://example.test/deployment-control\n"
                b"name: control\nprefixes: {ex: 'https://example.test/'}\n"
                b"default_prefix: ex\nclasses: {Thing: {}}\n",
            ),
        ),
    )
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    prepared_input = bundle, dependencies, profile, prepared
    project = table("data.project")

    def authentication(purpose):
        original = make_url(connection_settings(native_settings, purpose).database.url)
        return URL.create(
            "postgresql", username=original.username, password=original.password
        ).render_as_string(hide_password=False)

    with semantic_database_at(starting_revision) as engine:
        settings = native_settings.model_copy(
            update={
                "deployment": DeploymentDatabaseSettings.model_validate(
                    native_settings.database.model_dump()
                    | {
                        "url": make_url(native_settings.database.url)
                        .set(database=engine.url.database)
                        .render_as_string(hide_password=False),
                        "maintenance_url": authentication("maintenance"),
                        "admission_url": authentication("admit"),
                        "reader_url": authentication("read"),
                    }
                ),
            }
        )
        profile, destination = deployment_settings(settings)
        assert profile == "deployment"
        assert target_fingerprint(settings) != target_fingerprint(destination)
        versions = tmp_path / "migrations" / "versions"
        versions.mkdir(parents=True)
        (versions.parent / "env.py").write_bytes((migrations.ALEMBIC_DIR / "env.py").read_bytes())
        replaced = {
            Path(script.path).name,
            *(
                getattr(script.module, f"NATIVE_{kind}_FILE")
                for kind in ("UPGRADE", "STATE", "ADMISSION")
            ),
        }
        for source in (migrations.ALEMBIC_DIR / "versions").iterdir():
            if (
                source.is_file()
                and source.name not in replaced
                and (source.suffix != ".py" or source.name in ancestors)
            ):
                (versions / source.name).symlink_to(source)
        monkeypatch.setattr(migrations, "ALEMBIC_DIR", versions.parent)
        with engine.begin() as conn:
            assert current_revision(conn) == starting_revision
            identity = acquired_target(conn, purpose="maintenance")
            conn.execute(insert(project).values(project_id="model-deployment-control"))
        from corpus_structure.semantic.migration_chain import registered_base

        native_base = (
            registered_base(versions.parent, starting_revision, predecessor)
            if pending_base
            else None
        )
        binding = Candidate(
            workspace=str(tmp_path),
            model_revision="fixture",
            generator=generator_fingerprint(tmp_path),
            revision=revision,
            predecessor=predecessor,
            deployment_base=native_base,
            target=target_fingerprint(destination),
            target_profile=profile,
            authoring_target=target_fingerprint(settings),
            target_identity=identity,
            release=prepared.release_id,
            release_manifest_sha256=sha256(prepared.manifest).hexdigest(),
            release_artifacts_sha256=prepared.artifacts_sha256,
            packs=(),
            files={},
            hashes={name: sha256(content).hexdigest() for name, content in products.items()},
        )
        binding = binding.model_copy(
            update={"wrapper_sha256": sha256(migration_wrapper(binding)).hexdigest()}
        )
        store = ResultStore(tmp_path / "results")

        def create_candidate():
            with store.operation("model.candidate") as candidate:
                products_dir = candidate.directory / "native-candidate"
                products_dir.mkdir()
                for name, content in products.items():
                    (products_dir / name).write_bytes(content)
                deployment = candidate.directory / "deployment.json"
                deployment.write_text(binding.model_dump_json(), encoding="utf-8")
                wrapper = candidate.directory / "migration.py"
                wrapper.write_bytes(migration_wrapper(binding))
                candidate.publish("candidate", products_dir)
                candidate.publish("deployment", deployment)
                candidate.publish("wrapper", wrapper)
                candidate.settle(sha256=sha256(deployment.read_bytes()).hexdigest())
            return candidate

        authored = create_candidate()
        configured = settings.model_copy(update={"ci_results": store.root})
        monkeypatch.setattr(recipes, "checkout", lambda _: tmp_path)
        monkeypatch.setattr(commands, "_prepare_release", lambda *_, **__: prepared_input)
        runner = CliRunner()

        def command(*args):
            return runner.invoke(
                app,
                [*args, "--json"],
                obj=CliState(settings_factory=lambda: configured),
            )

        def run(action, candidate=authored):
            return command("model", "change", action, candidate.id)

        registered = run("register")
        assert registered.exit_code == 0, registered.output
        assert f"migrations/versions/{revision}.py" in json.loads(registered.stdout)["changed"]
        # Register an unapplied successor whose descriptor genuinely differs.
        # Neither older reads nor the exact non-head deployment should use it.
        future_revision = "semantic_ptd_test_successor"
        admission = products["native_admission.sql"]
        different_admission = admission.replace(
            b'"physical_id":"physical:', b'"physical_id":"future:'
        )
        assert different_admission != admission
        successor = binding.model_copy(
            update={
                "revision": future_revision,
                "predecessor": revision,
                "hashes": binding.hashes
                | {
                    "native_admission.sql": sha256(different_admission).hexdigest(),
                },
            }
        )
        (versions / f"{future_revision}.py").write_bytes(migration_wrapper(successor))
        (versions / f"{future_revision}_admission.sql").write_bytes(different_admission)
        (versions / f"{future_revision}_native.json").write_bytes(
            products["native_operations.json"]
        )
        (versions / f"{future_revision}_upgrade.txt").write_bytes(products["native_candidate.py"])
        assert head_revision() == future_revision
        with (
            open_runtime_engine(destination, "dma-test-older-read", purpose="read") as reader,
            reader.connect() as conn,
        ):
            assert _verify_deployment_functions(conn).startswith("physical:")

        with engine.connect() as conn:
            conn.exec_driver_sql(
                "GRANT EXECUTE ON FUNCTION data.execution_contract_descriptor() TO PUBLIC"
            )
            with pytest.raises(
                ExecutionAdmissionError, match="native execution deployment differs"
            ):
                _verify_deployment_functions(conn, revision=predecessor)

        def write_installed_revision(label):
            with engine.begin() as conn:
                conn.exec_driver_sql("UPDATE semantic_alembic_version SET version_num=%s", (label,))

        write_installed_revision("semantic_wce_lineage_20261107")
        try:
            with pytest.raises(ModelError, match="differs from the approved predecessor"):
                deploy_candidate(
                    tmp_path,
                    settings,
                    binding,
                    prepared_input,
                    report=lambda _: pytest.fail("unexpected effect"),
                )
        finally:
            write_installed_revision(starting_revision)

        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER VIEW data.selected_fact RENAME TO selected_fact_drift")
        try:
            with pytest.raises(ExecutionAdmissionError, match="selected-fact view differs"):
                deploy_candidate(
                    tmp_path,
                    settings,
                    binding,
                    prepared_input,
                    report=lambda _: pytest.fail("unexpected effect"),
                )
        finally:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER VIEW data.selected_fact_drift RENAME TO selected_fact")
        installed_wrapper = versions / f"{revision}.py"
        marker = tmp_path / "unapproved-wrapper-executed"
        original = installed_wrapper.read_bytes()
        mtime = installed_wrapper.stat().st_mtime_ns
        unapproved = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n".encode()
        installed_wrapper.write_bytes(unapproved.ljust(len(original), b" "))
        os.utime(installed_wrapper, ns=(mtime, mtime))
        cache_name = py_compile.compile(
            str(installed_wrapper),
            doraise=True,
            invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP,
        )
        assert cache_name is not None
        cache = Path(cache_name)
        installed_wrapper.write_bytes(original)
        os.utime(installed_wrapper, ns=(mtime, mtime))
        wrong_cluster = binding.model_copy(
            update={"target_identity": identity.model_copy(update={"system_identifier": "0"})}
        )
        with pytest.raises(StorageTargetError, match="differs from the approved target"):
            deploy_candidate(
                tmp_path,
                settings,
                wrong_cluster,
                prepared_input,
                report=lambda _: pytest.fail("unexpected effect"),
            )
        wrong_purpose = settings.model_copy(
            update={
                "deployment": settings.deployment.model_copy(
                    update={"admission_url": authentication("read")}
                ),
            }
        )
        with pytest.raises(DBAPIError, match="mismatched runtime principal for admit") as denied:
            deploy_candidate(
                tmp_path,
                wrong_purpose,
                binding,
                prepared_input,
                report=lambda _: pytest.fail("unexpected effect"),
            )
        assert getattr(denied.value.orig, "sqlstate", None) == "42501"
        with engine.begin() as conn:
            assert current_revision(conn) == starting_revision

        with engine.begin() as conn:
            conn.exec_driver_sql(
                "GRANT TEMP ON DATABASE "
                + conn.dialect.identifier_preparer.quote(identity.database)
                + " TO corpus_sem_writer"
            )
        try:
            refused = run("deploy")
            assert refused.exit_code == 1, refused.output
            denied = json.loads(refused.stdout)
            assert "privileged runtime principal" in denied["error"]["message"]
            assert denied["operation_account"]["known_effects"] == []
            failed_attempts = [denied["invocation_id"]]
            with engine.begin() as conn:
                assert current_revision(conn) == starting_revision
                assert conn.scalar(select(table("sem.release").c.release_id)) is None
                assert conn.scalar(select(table("sem.deployment_admission").c.release_id)) is None
                assert activation_token(conn, "model-deployment-control").generation == 0
        finally:
            with engine.begin() as conn:
                conn.exec_driver_sql(
                    "REVOKE TEMP ON DATABASE "
                    + conn.dialect.identifier_preparer.quote(identity.database)
                    + " FROM corpus_sem_writer"
                )

        upgrade = migrations.upgrade

        def drift_after_upgrade(conn, *args, **kwargs):
            result = upgrade(conn, *args, **kwargs)
            conn.exec_driver_sql("ALTER TABLE eval.document_split ADD CHECK (length(split) > 0)")
            return result

        with monkeypatch.context() as faults:
            faults.setattr(migrations, "upgrade", drift_after_upgrade)
            refused = run("deploy")
        assert refused.exit_code == 1, refused.output
        denied = json.loads(refused.stdout)
        assert "unexpected physical CHECK" in denied["error"]["message"]
        assert denied["operation_account"]["known_effects"] == []
        failed_attempts.append(denied["invocation_id"])
        with engine.connect() as conn:
            assert current_revision(conn) == starting_revision
            assert conn.scalar(select(table("sem.release").c.release_id)) is None
            assert activation_token(conn, "model-deployment-control").generation == 0

        write = Invocation._write
        close = Store.close

        def fail_checkpoint(invocation):
            if (
                invocation.manifest.action == "model.deploy"
                and invocation.manifest.stage == "migration"
                and invocation.manifest.settled is None
            ):
                raise OSError("injected post-commit receipt write failure")
            write(invocation)

        def fail_cleanup(store):
            close(store)
            if store.application_name == "ci-model-verify":
                raise OSError("injected database cleanup failure")

        def lose_commit_acknowledgement(conn, *args, **kwargs):
            result = upgrade(conn, *args, **kwargs)
            commit = conn.dialect.do_commit

            def commit_and_lose(driver):
                faults.setattr(conn.dialect, "do_commit", commit)
                commit(driver)
                raise OSError("injected lost migration commit acknowledgement")

            faults.setattr(conn.dialect, "do_commit", commit_and_lose)
            return result

        with monkeypatch.context() as faults:
            faults.setattr(migrations, "upgrade", lose_commit_acknowledgement)
            failed = run("deploy")
        assert failed.exit_code == 1, failed.output
        failure = json.loads(failed.stdout)
        failed_attempts.append(failure["invocation_id"])
        assert failure["operation_account"]["known_effects"] == ["migration"]
        assert failure["operation_account"]["failure"]["database_effects"] == "commit_confirmed"
        assert failure["operation_account"]["failure"]["operation_id"] == "model.deploy:migration"
        with engine.connect() as conn:
            assert current_revision(conn) == revision
            assert conn.scalar(select(table("sem.release").c.release_id)) is None

        for cleanup in (False, True):
            candidate = create_candidate() if cleanup else authored
            with monkeypatch.context() as faults:
                faults.setattr(Invocation, "_write", fail_checkpoint)
                if cleanup:
                    faults.setattr(Store, "close", fail_cleanup)
                failed = run("deploy", candidate)
            assert failed.exit_code == 1, failed.output
            failure = json.loads(failed.stdout)
            account = failure["operation_account"]
            assert account["reached_revision"] == revision
            assert account["known_effects"] == ["migration"]
            assert account["cleanup"] == ("unresolved" if cleanup else "established")
            receipt = command("results", "show", failure["invocation_id"])
            assert receipt.exit_code == 0, receipt.output
            assert json.loads(receipt.stdout)["operation_account"] == account
            if cleanup:
                refused = command("evidence", "retain", failure["invocation_id"], "--for", "DMA-08")
                assert refused.exit_code == 1, refused.output
                assert "evidence promotion requires established custody" in refused.stdout
                assert failure["invocation_id"] in store.show(candidate.id).holds
            else:
                failed_attempts.append(failure["invocation_id"])

        with engine.connect() as conn:
            assert current_revision(conn) == revision
            assert conn.scalar(select(table("sem.release").c.release_id)) is None
            assert conn.scalar(select(table("sem.deployment_admission").c.release_id)) is None
            observed_physical = conn.exec_driver_sql(
                "SELECT data.execution_contract_descriptor()->>'physical_id'"
            ).scalar_one()
            # The unapplied successor's independently altered descriptor says
            # future:, while this connection still observes the exact candidate.
            assert observed_physical.startswith("physical:")
            assert _verify_deployment_functions(conn) == observed_physical
            assert activation_token(conn, "model-deployment-control").release_id is None

        deployed = run("deploy")
        assert deployed.exit_code == 0, deployed.output
        assert not marker.exists()
        cache.unlink()
        result = json.loads(deployed.stdout)
        assert result["acquired_target"]["database_oid"] == identity.database_oid
        assert result["selection"]["standing"] == "configured_unobserved"
        assert result["selection"]["profile"] == "deployment"
        assert result["selection"]["observed_binding"] is None
        assert result["selection"]["settings_section"] == "deployment"
        account = result["operation_account"]
        assert account["acquired_target"] == identity.model_dump(mode="json")
        assert account["predecessor"] == starting_revision
        assert account["reached_revision"] == revision
        assert account["release"] == prepared.release_id
        assert account["known_effects"] == ["migration", "archive", "admission", "verified"]

        admitted = table("sem.deployment_admission")
        exact = (admitted.c.release_id == prepared.release_id) & (admitted.c.kind == "native")
        with engine.begin() as conn:
            digest = conn.execute(select(admitted.c.content_digest).where(exact)).scalar_one()
            with administrative_archive_edit(conn, admitted):
                conn.execute(update(admitted).where(exact).values(content_digest="0" * 64))
        try:
            with pytest.raises(ModelError, match="admitted release does not match"):
                deploy_candidate(tmp_path, settings, binding, prepared_input, report=lambda _: None)
        finally:
            with engine.begin() as conn, administrative_archive_edit(conn, admitted):
                conn.execute(update(admitted).where(exact).values(content_digest=digest))

        store.hold(result["result_id"], result["result_id"])
        expiry = max(store.show(id_).expiry() for id_ in (authored.id, *failed_attempts))
        assert authored.id in store.collect(apply=True, now=expiry + 1).removed
        retained = command("results", "show", result["result_id"])
        assert retained.exit_code == 0, retained.output
        assert json.loads(retained.stdout)["operation_account"] == account
        assert store.show(result["result_id"]).details["settled_effects"] == [
            "migration",
            "archive",
            "admission",
            "verified",
        ]
        with engine.connect() as conn:
            assert activation_token(conn, "model-deployment-control").release_id is None
            assert conn.scalar(select(project.c.selected_result_run_id)) is None
        status = command("db", "status", "--target", "deployment", "--maintenance")
        assert status.exit_code == 0, status.output
        assert json.loads(status.stdout)["revision"] == revision
        assert json.loads(status.stdout)["acquired"]["database_oid"] == identity.database_oid
        checked = command(
            "release", "check", "--target", "deployment", "--release", prepared.release_id
        )
        assert checked.exit_code == 0, checked.output
        checked_report = json.loads(checked.stdout)
        assert checked_report["acquired"]["database_oid"] == identity.database_oid
        assert checked_report["selection"]["standing"] == "configured_unobserved"
        assert checked_report["selection"]["target_parameter_source"] == "commandline"
        assert checked_report["selection"]["observed_binding"] is None
        activation = (
            "release",
            "activate",
            prepared.release_id,
            "--project",
            "model-deployment-control",
        )
        refused = command(*activation)
        assert refused.exit_code == 1
        assert "select --target" in refused.stdout
        activated = command(*activation, "--target", "deployment")
        assert activated.exit_code == 0, activated.output
        selected = json.loads(activated.stdout)
        assert selected["release_id"] == prepared.release_id
        assert selected["generation"] == 1
        assert selected["acquired"]["database_oid"] == identity.database_oid
        with engine.connect() as conn:
            assert conn.scalar(select(project.c.selected_result_run_id)) is None
