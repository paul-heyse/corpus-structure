"""An exact candidate resumes after a committed native step without selecting a result."""

from hashlib import sha256
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import insert, select
from sqlalchemy.engine import URL, make_url

from corpus_structure.schema.model_change import generator_fingerprint
from corpus_structure.schema.model_deployment import Candidate, deploy_candidate, target_fingerprint
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.migrations import alembic_config, current_revision
from corpus_structure.semantic.releases import activate_release, activation_token
from corpus_structure.semantic.runtime import connection_settings, open_runtime_engine
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies


def test_exact_native_deployment_resumes_before_separate_activation(
    semantic_database_at, native_settings, tmp_path
):
    predecessor = "semantic_wce_gaps_20261106"
    revision = "semantic_wce_lineage_20261107"
    script = ScriptDirectory.from_config(alembic_config()).get_revision(revision)
    assert script is not None
    hashes = {
        product: sha256(
            Path(script.path).with_name(getattr(script.module, f"NATIVE_{kind}_FILE")).read_bytes()
        ).hexdigest()
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
                "database": native_settings.database.model_copy(
                    update={
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
        binding = Candidate(
            workspace=str(tmp_path),
            model_revision="fixture",
            generator=generator_fingerprint(tmp_path),
            revision=revision,
            predecessor=predecessor,
            target=target_fingerprint(settings),
            release=prepared.release_id,
            packs=(),
            files={},
            hashes=hashes,
        )
        with engine.begin() as conn:
            assert current_revision(conn) == predecessor
            conn.execute(insert(project).values(project_id="model-deployment-control"))

        def interrupt_after_migration(stage):
            assert stage == "migration"
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            deploy_candidate(
                tmp_path, settings, binding, prepared_input, report=interrupt_after_migration
            )
        with engine.connect() as conn:
            assert current_revision(conn) == revision
            assert activation_token(conn, "model-deployment-control").release_id is None

        stages = []
        deploy_candidate(tmp_path, settings, binding, prepared_input, report=stages.append)
        assert stages == ["migration", "archive", "admission", "verified"]
        with engine.connect() as conn:
            assert activation_token(conn, "model-deployment-control").release_id is None
            assert conn.scalar(select(project.c.selected_result_run_id)) is None
        with (
            open_runtime_engine(settings, "model-activation-control", purpose="admit") as admit,
            admit.begin() as conn,
        ):
            selected = activate_release(
                conn,
                "model-deployment-control",
                prepared.release_id,
                expected_parent=None,
                expected_generation=0,
            )
            assert selected.release_id == prepared.release_id
            assert selected.generation == 1
        with engine.connect() as conn:
            assert conn.scalar(select(project.c.selected_result_run_id)) is None
