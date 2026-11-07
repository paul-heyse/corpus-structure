"""An exact installed candidate resumes without selecting a project result."""

import json
import os
import py_compile
from hashlib import sha256
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import insert, select
from sqlalchemy.engine import URL, make_url
from typer.testing import CliRunner

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
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.migrations import alembic_config, current_revision
from corpus_structure.semantic.releases import activation_token
from corpus_structure.semantic.runtime import connection_settings
from corpus_structure.semantic.storage_target import StorageTargetError, acquired_target
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies
from corpus_structure.settings import DeploymentDatabaseSettings


def test_exact_native_deployment_resumes_before_separate_activation(
    semantic_database_at, native_settings, tmp_path, monkeypatch
):
    from corpus_structure.cli import model as commands
    from corpus_structure.cli import recipes
    from corpus_structure.cli.app import app
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.cli.output import CliState
    from corpus_structure.semantic import migrations

    predecessor = "semantic_wce_gaps_20261106"
    revision = "semantic_wce_lineage_20261107"
    script = ScriptDirectory.from_config(alembic_config()).get_revision(revision)
    assert script is not None
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

    with semantic_database_at(predecessor) as engine:
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
                and (source.suffix != ".py" or source.name < Path(script.path).name)
            ):
                (versions / source.name).symlink_to(source)
        monkeypatch.setattr(migrations, "ALEMBIC_DIR", versions.parent)
        with engine.begin() as conn:
            assert current_revision(conn) == predecessor
            assert (
                conn.exec_driver_sql(
                    "SELECT to_regprocedure('ops.dossier_contribution_members(jsonb,jsonb)')"
                ).scalar_one()
                is not None
            )
            identity = acquired_target(conn, purpose="maintenance")
            conn.execute(insert(project).values(project_id="model-deployment-control"))
        binding = Candidate(
            workspace=str(tmp_path),
            model_revision="fixture",
            generator=generator_fingerprint(tmp_path),
            revision=revision,
            predecessor=predecessor,
            target=target_fingerprint(destination),
            target_profile=profile,
            authoring_target=target_fingerprint(settings),
            target_identity=identity,
            release=prepared.release_id,
            packs=(),
            files={},
            hashes={name: sha256(content).hexdigest() for name, content in products.items()},
        )
        binding = binding.model_copy(
            update={"wrapper_sha256": sha256(migration_wrapper(binding)).hexdigest()}
        )
        store = ResultStore(tmp_path / "results")
        with store.operation("model.candidate") as authored:
            products_dir = authored.directory / "native-candidate"
            products_dir.mkdir()
            for name, content in products.items():
                (products_dir / name).write_bytes(content)
            deployment = authored.directory / "deployment.json"
            deployment.write_text(binding.model_dump_json(), encoding="utf-8")
            wrapper = authored.directory / "migration.py"
            wrapper.write_bytes(migration_wrapper(binding))
            authored.publish("candidate", products_dir)
            authored.publish("deployment", deployment)
            authored.publish("wrapper", wrapper)
            authored.settle(sha256=sha256(deployment.read_bytes()).hexdigest())
        configured = settings.model_copy(update={"ci_results": store.root})
        monkeypatch.setattr(recipes, "checkout", lambda _: tmp_path)
        monkeypatch.setattr(commands, "_prepare_release", lambda *_: prepared_input)
        runner = CliRunner()

        def command(*args):
            return runner.invoke(
                app,
                [*args, "--json"],
                obj=CliState(settings_factory=lambda: configured),
            )

        def run(action):
            return command("model", "change", action, authored.id)

        registered = run("register")
        assert registered.exit_code == 0, registered.output
        assert f"migrations/versions/{revision}.py" in json.loads(registered.stdout)["changed"]
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
        with engine.begin() as conn:
            assert current_revision(conn) == predecessor

        def interrupt_after_migration(stage):
            assert stage == "migration"
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            deploy_candidate(
                tmp_path, settings, binding, prepared_input, report=interrupt_after_migration
            )
        with engine.connect() as conn:
            assert current_revision(conn) == revision
            assert (
                conn.exec_driver_sql(
                    "SELECT to_regprocedure('ops.dossier_contribution_members(jsonb,jsonb)')"
                ).scalar_one()
                is None
            )
            assert activation_token(conn, "model-deployment-control").release_id is None

        deployed = run("deploy")
        assert deployed.exit_code == 0, deployed.output
        assert not marker.exists()
        cache.unlink()
        result = json.loads(deployed.stdout)
        assert result["acquired_target"]["database_oid"] == identity.database_oid
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
        assert json.loads(checked.stdout)["acquired"]["database_oid"] == identity.database_oid
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
