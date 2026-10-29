"""Native exact archives and fail-closed activation for composed execution bindings."""

from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import Engine, insert, select, text, update
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
    releases,
)
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.execution_admission import ExecutionAdmissionError
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table


def _bundle() -> SourceBundle:
    return SourceBundle(
        "domain",
        (
            SourceArtifact(
                "domain",
                b"""# Domain extraction remains a separate namespace.
id: https://example.org/execution-archive
name: domain
prefixes:
  ex: https://example.org/
default_prefix: ex
types:
  string:
    base: str
    uri: xsd:string
classes:
  Item:
    attributes:
      id:
        identifier: true
        range: string
""",
            ),
        ),
    )


def _stage(conn):
    bundle = _bundle()
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    releases.persist_release(conn, bundle, dependencies, profile, prepared)
    return bundle, dependencies, profile, prepared


def _project(conn, release_id: str | None = None) -> str:
    project_id = str(uuid4())
    conn.execute(
        insert(table("data.project")).values(
            project_id=project_id, active_release_id=release_id, generation=0
        )
    )
    return project_id


def test_execution_inputs_and_products_reload_exactly_offline(
    semantic_db_engine: Engine, monkeypatch
):
    from corpus_structure.semantic import contracts

    with semantic_db_engine.begin() as conn:
        bundle, dependencies, profile, prepared = _stage(conn)
        assert prepared.execution_model_id is not None
        archived = conn.execute(
            select(table("sem.release").c.prepared_bytes).where(
                table("sem.release").c.release_id == prepared.release_id
            )
        ).scalar_one()
        archive = json.loads(bytes(archived))
        assert archive["format"] == "semantic-release-archive-2"
        assert archive["products"]["execution_model_id"] == prepared.execution_model_id
        assert json.loads(prepared.manifest)["execution_model_id"] == prepared.execution_model_id
        inputs = table("sem.input")
        actual = {
            row.input_name: bytes(row.content)
            for row in conn.execute(
                select(inputs.c.input_name, inputs.c.content).where(
                    inputs.c.release_id == prepared.release_id,
                    inputs.c.input_kind == "dependency",
                )
            )
        }
        assert actual == {item.name: item.content for item in dependencies.artifacts}
        execution_artifact = next(
            artifact
            for artifact in prepared.artifacts
            if artifact.kind == "execution/contracts.json"
        )
        assert prepared.execution_model_id.encode() in execution_artifact.content
        assert any(row.kind == "execution_model" for row in prepared.registry_rows)
        assert {definition.name for definition in prepared.definitions} == {"Item"}

        def unavailable():
            pytest.fail("archive reconstruction must not acquire installed execution inputs")

        monkeypatch.setattr(contracts, "trusted_execution_inputs", unavailable)
        assert releases.load_release(conn, prepared.release_id) == prepared
        assert (
            releases.persist_release(conn, bundle, dependencies, profile, prepared)
            == prepared.release_id
        )


@pytest.mark.parametrize("relation", ["input", "artifact", "registry_row", "release"])
def test_corrupt_execution_archive_refuses_even_with_recomputed_digest(
    semantic_db_engine: Engine, relation: str
):
    with semantic_db_engine.begin() as conn:
        _, dependencies, _, prepared = _stage(conn)
        target = table("sem." + relation)
        predicate = [target.c.release_id == prepared.release_id]
        if relation == "input":
            item = next(
                item for item in dependencies.artifacts if item.name == "execution/catalog.yaml"
            )
            content = item.content + b"\n# archived bytes changed\n"
            predicate.extend(
                [target.c.input_kind == "dependency", target.c.input_name == item.name]
            )
            values = {"content": content, "content_digest": sha256(content).hexdigest()}
        elif relation == "artifact":
            predicate.append(target.c.artifact_name == "execution/contracts.json")
            content = b'{"model_id":"execution:forged"}'
            values = {"content": content, "content_digest": sha256(content).hexdigest()}
        elif relation == "registry_row":
            predicate.append(target.c.kind == "execution_model")
            values = {"body": b'{"model_id":"execution:forged"}'}
        else:
            archived = bytes(
                conn.execute(select(target.c.prepared_bytes).where(*predicate)).scalar_one()
            )
            archive = json.loads(archived)
            archive["products"]["execution_model_id"] = "execution:forged"
            content = canonical_bytes(archive)
            values = {"prepared_bytes": content, "content_digest": sha256(content).hexdigest()}
        conn.execute(update(target).where(*predicate).values(**values))
        with pytest.raises(releases.ReleaseConflict):
            releases.load_release(conn, prepared.release_id)


def test_execution_manifest_identity_is_derived_from_inputs(semantic_db_engine: Engine):
    with semantic_db_engine.begin() as conn:
        bundle, dependencies, profile, prepared = _stage(conn)
        manifest = json.loads(prepared.manifest)
        manifest["execution_model_id"] = "execution:forged"
        content = canonical_bytes(manifest)
        forged = replace(
            prepared,
            execution_model_id="execution:forged",
            manifest=content,
            release_id="release:" + sha256(content).hexdigest(),
        )
        with pytest.raises(
            releases.ReleaseConflict, match="execution model differs from exact inputs"
        ):
            releases.persist_release(conn, bundle, dependencies, profile, forged)
        assert releases.load_release(conn, prepared.release_id) == prepared
        assert not conn.execute(
            select(table("sem.release").c.release_id).where(
                table("sem.release").c.release_id == forged.release_id
            )
        ).first()


def test_execution_activation_refuses_missing_native_enforcement_and_preserves_pointer(
    semantic_db_engine: Engine,
):
    with semantic_db_engine.begin() as conn:
        bundle = _bundle()
        dependencies = ResolvedDependencies()
        profile = PreparationProfile()
        existing = prepare_release(bundle, dependencies, profile)
        releases.persist_release(conn, bundle, dependencies, profile, existing)
        project_id = _project(conn)
        releases.activate_release(
            conn, project_id, existing.release_id, expected_parent=None, expected_generation=0
        )
        *_, prepared = _stage(conn)
        before = releases.activation_token(conn, project_id)
        with pytest.raises(ExecutionAdmissionError, match=r"execution\.lifecycle\.v1"):
            releases.activate_release(
                conn,
                project_id,
                prepared.release_id,
                expected_parent=existing.release_id,
                expected_generation=1,
            )
        assert releases.activation_token(conn, project_id) == before
        assert releases.load_release(conn, prepared.release_id) == prepared


def test_changed_trusted_model_refuses_before_activation(semantic_db_engine: Engine, monkeypatch):
    from corpus_structure.semantic import contracts

    with semantic_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
        project_id = _project(conn)
        current = contracts.trusted_execution_inputs()
        changed = replace(
            current,
            catalog=replace(
                current.catalog, content=current.catalog.content + b"\n# new code model\n"
            ),
        )
        monkeypatch.setattr(contracts, "trusted_execution_inputs", lambda: changed)
        with pytest.raises(ExecutionAdmissionError, match="incompatible with trusted code"):
            releases.activate_release(
                conn, project_id, prepared.release_id, expected_parent=None, expected_generation=0
            )
        assert releases.activation_token(conn, project_id) == releases.ActivationToken(None, 0)


@pytest.mark.parametrize("route", ["owner_insert", "writer_initialize"])
def test_native_writer_cannot_bypass_execution_admission(
    semantic_db_engine: Engine, semantic_writer_engine: Engine, route: str
):
    with semantic_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
        project_id = _project(conn)
    realization_id = str(uuid4())
    engine = semantic_db_engine if route == "owner_insert" else semantic_writer_engine
    with (
        pytest.raises(DBAPIError, match=r"semantic-2|execution") as error,
        engine.begin() as conn,
    ):
        if route == "owner_insert":
            conn.execute(
                insert(table("data.realization")).values(
                    realization_id=realization_id,
                    release_id=prepared.release_id,
                    project_id=project_id,
                )
            )
        else:
            conn.execute(
                text("SELECT data.initialize_source_project(:project, :release, :realization)"),
                {
                    "project": project_id,
                    "release": prepared.release_id,
                    "realization": realization_id,
                },
            )
    assert getattr(error.value.orig, "sqlstate", None) == "23514"
    with semantic_db_engine.begin() as conn:
        assert not conn.execute(
            select(table("data.realization").c.realization_id).where(
                table("data.realization").c.realization_id == realization_id
            )
        ).first()
        assert releases.activation_token(conn, project_id) == releases.ActivationToken(None, 0)


def test_composed_archive_requires_enabled_native_fence(semantic_db_engine):
    from sqlalchemy import text

    bundle = _bundle()
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with semantic_db_engine.begin() as conn:
        conn.execute(text("ALTER TABLE data.realization DISABLE TRIGGER guard_execution_admission"))
        with pytest.raises(ExecutionAdmissionError, match="fence is not deployed"):
            releases.persist_release(conn, bundle, dependencies, profile, prepared)
        assert (
            conn.execute(
                select(table("sem.release")).where(
                    table("sem.release").c.release_id == prepared.release_id
                )
            ).first()
            is None
        )
        conn.execute(text("ALTER TABLE data.realization ENABLE TRIGGER guard_execution_admission"))
