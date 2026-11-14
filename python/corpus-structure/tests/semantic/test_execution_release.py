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
from semantic.archive_faults import administrative_archive_edit
from semantic.execution_release_support import (
    bundle as _bundle,
)
from semantic.execution_release_support import (
    project as _project,
)
from semantic.execution_release_support import (
    stage_authored_sql as _stage_authored_sql,
)


def _stage(conn):
    bundle = _bundle()
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    releases.persist_release(conn, bundle, dependencies, profile, prepared)
    return bundle, dependencies, profile, prepared


def test_execution_inputs_and_products_reload_exactly_offline(
    commit_db_engine: Engine, monkeypatch
):
    from corpus_structure.semantic import contracts, metadata
    from corpus_structure.semantic.prepare import _prepare_release_cached

    with commit_db_engine.begin() as conn:
        bundle, dependencies, profile, prepared = _stage(conn)
        assert prepared.execution_model_id is not None
        archived = conn.execute(
            select(table("sem.release").c.prepared_bytes).where(
                table("sem.release").c.release_id == prepared.release_id
            )
        ).scalar_one()
        archive = json.loads(bytes(archived))
        assert archive["format"] == "semantic-release-archive-3"
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

        with (
            contracts.implementation_override(contracts.IMPLEMENTATION_UNAVAILABLE),
            monkeypatch.context() as different,
        ):
            different.setattr(metadata, "PHYSICAL_MODEL_ID", "physical:different-installed-profile")
            _prepare_release_cached.cache_clear()
            verified = releases.load_release(conn, prepared.release_id)
        assert verified == prepared
        assert verified.artifacts_sha256 == prepared.artifacts_sha256
        assert (
            releases.persist_release(conn, bundle, dependencies, profile, prepared)
            == prepared.release_id
        )


@pytest.mark.parametrize("relation", ["input", "artifact", "registry_row", "release"])
def test_corrupt_execution_archive_refuses_even_with_recomputed_digest(
    commit_db_engine: Engine, relation: str
):
    with commit_db_engine.begin() as conn:
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
        with administrative_archive_edit(conn, target):
            conn.execute(update(target).where(*predicate).values(**values))
        with pytest.raises(releases.ReleaseConflict):
            releases.load_release(conn, prepared.release_id)


def test_execution_manifest_identity_is_derived_from_inputs(commit_db_engine: Engine):
    with commit_db_engine.begin() as conn:
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
    commit_db_engine: Engine,
):
    with commit_db_engine.begin() as conn:
        bundle = _bundle()
        bundle = replace(
            bundle,
            sources=(
                replace(
                    bundle.sources[0], content=bundle.sources[0].content + b"\n# Existing release\n"
                ),
            ),
        )
        dependencies = composed_dependencies(ResolvedDependencies())
        profile = PreparationProfile(version="semantic-2")
        existing = prepare_release(bundle, dependencies, profile)
        releases.persist_release(conn, bundle, dependencies, profile, existing)
        project_id = _project(conn)
        releases.activate_release(
            conn, project_id, existing.release_id, expected_parent=None, expected_generation=0
        )
        *_, prepared = _stage(conn)
        before = releases.activation_token(conn, project_id)
        conn.execute(text("ALTER TABLE ops.task DISABLE TRIGGER zz_execution_task"))
        with pytest.raises(ExecutionAdmissionError, match="native execution deployment"):
            releases.activate_release(
                conn,
                project_id,
                prepared.release_id,
                expected_parent=existing.release_id,
                expected_generation=1,
            )
        assert releases.activation_token(conn, project_id) == before
        assert releases.load_release(conn, prepared.release_id) == prepared


def test_comment_only_trusted_input_change_preserves_archived_execution_binding(
    commit_db_engine: Engine,
):
    from corpus_structure.semantic import contracts

    with commit_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
        project_id = _project(conn)
        current = contracts.trusted_execution_inputs()
        changed = replace(
            current,
            catalog=replace(
                current.catalog, content=current.catalog.content + b"\n# new code model\n"
            ),
        )
        snapshot = replace(contracts.current_implementation(), execution_inputs=changed)
        with contracts.implementation_override(snapshot):
            releases.activate_release(
                conn, project_id, prepared.release_id, expected_parent=None, expected_generation=0
            )
            assert releases.activation_token(conn, project_id) == releases.ActivationToken(
                prepared.release_id, 1
            )
            assert (
                releases.open_release(conn, prepared.release_id).execution_model_id
                == prepared.execution_model_id
            )


@pytest.mark.parametrize("route", ["owner_insert", "writer_initialize"])
def test_native_writer_cannot_bypass_execution_admission(
    commit_db_engine: Engine, commit_writer_engine: Engine, route: str
):
    with commit_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
        project_id = _project(conn)
        conn.execute(
            text("ALTER FUNCTION ops.execution_edge(text,text,text) OWNER TO corpus_sem_publisher")
        )
    realization_id = str(uuid4())
    engine = commit_db_engine if route == "owner_insert" else commit_writer_engine
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
    with commit_db_engine.begin() as conn:
        assert not conn.execute(
            select(table("data.realization").c.realization_id).where(
                table("data.realization").c.realization_id == realization_id
            )
        ).first()
        assert releases.activation_token(conn, project_id) == releases.ActivationToken(None, 0)


def test_composed_archive_requires_enabled_native_fence(commit_db_engine):
    from sqlalchemy import text

    bundle = _bundle()
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with commit_db_engine.begin() as conn:
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


def test_composed_activation_requires_actual_verified_deployment(commit_db_engine):
    from corpus_structure.semantic.publication import admit_release

    with commit_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
        project = _project(conn)
        with pytest.raises(ExecutionAdmissionError, match="requires verified native deployment"):
            admit_release(prepared)
        admitted = releases.activate_release(
            conn, project, prepared.release_id, expected_parent=None, expected_generation=0
        )
        assert admitted == releases.ActivationToken(prepared.release_id, 1)
        conn.execute(
            insert(table("data.realization")).values(
                realization_id=str(uuid4()), release_id=prepared.release_id, project_id=project
            )
        )


def test_composed_legacy_analysis_abi_refuses_without_intent(
    commit_db_engine, commit_writer_engine
):
    with commit_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
    with (
        commit_writer_engine.begin() as conn,
        pytest.raises(DBAPIError, match="explicit derived intent"),
    ):
        conn.execute(
            text("SELECT data.publish_analysis_batch(:r,'z','b',:content,0)"),
            {"r": prepared.release_id, "content": b"[]"},
        )


@pytest.mark.parametrize("tamper", ["body", "attachment", "column_grant"])
def test_composed_activation_refuses_actual_kernel_and_privilege_drift(commit_db_engine, tamper):
    with commit_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
        project = _project(conn)
        if tamper == "body":
            conn.execute(
                text(
                    "CREATE OR REPLACE FUNCTION ops.execution_edge(lifecycle text,prior "
                    "text,result text) RETURNS boolean LANGUAGE sql IMMUTABLE SET "
                    "search_path=pg_catalog,pg_temp AS 'SELECT true'"
                )
            )
        elif tamper == "attachment":
            conn.execute(text("DROP TRIGGER zz_execution_task ON ops.task"))
            conn.execute(
                text(
                    "CREATE TRIGGER zz_execution_task BEFORE INSERT OR UPDATE ON ops.run FOR "
                    "EACH ROW EXECUTE FUNCTION ops.guard_execution_task()"
                )
            )
        else:
            conn.execute(text("GRANT INSERT(entity_id) ON data.entity TO corpus_sem_writer"))
        with pytest.raises(ExecutionAdmissionError, match="native execution deployment"):
            releases.activate_release(
                conn, project, prepared.release_id, expected_parent=None, expected_generation=0
            )
        assert releases.activation_token(conn, project) == releases.ActivationToken(None, 0)


@pytest.mark.parametrize("scope", ["occurrence", "context"])
def test_native_constructor_refuses_unimplemented_required_scope(
    commit_db_engine, commit_writer_engine, scope
):
    with commit_db_engine.begin() as conn:
        bundle = _bundle()
        dependencies = composed_dependencies(ResolvedDependencies())
        profile = PreparationProfile(version="semantic-2", constraint_scope=scope)
        prepared = prepare_release(bundle, dependencies, profile)
        releases.persist_release(conn, bundle, dependencies, profile, prepared)
        project = _project(conn)
    with (
        commit_writer_engine.begin() as conn,
        pytest.raises(DBAPIError, match="unsupported required native constraint"),
    ):
        conn.execute(
            text("SELECT data.initialize_source_project(:p,:r,:z)"),
            {"p": project, "r": prepared.release_id, "z": str(uuid4())},
        )


def test_native_project_generation_cannot_reset_or_skip(commit_db_engine):
    with commit_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
        project = _project(conn)
        releases.activate_release(
            conn, project, prepared.release_id, expected_parent=None, expected_generation=0
        )
        for generation in (0, 3):
            with pytest.raises(DBAPIError, match="generation must advance"), conn.begin_nested():
                conn.execute(
                    text("UPDATE data.project SET generation=:g WHERE project_id=:p"),
                    {"g": generation, "p": project},
                )
        conn.execute(
            text("UPDATE data.project SET generation=generation WHERE project_id=:p"),
            {"p": project},
        )
        assert releases.activation_token(conn, project) == releases.ActivationToken(
            prepared.release_id, 1
        )
        with pytest.raises(DBAPIError, match="generation must start"), conn.begin_nested():
            conn.execute(
                insert(table("data.project")).values(
                    project_id=str(uuid4()), active_release_id=prepared.release_id, generation=5
                )
            )


@pytest.mark.parametrize("flag", ["transitive", "symmetric"])
def test_native_constructor_refuses_scalar_inference_relation(
    commit_db_engine, commit_writer_engine, flag
):
    import yaml

    from corpus_structure.semantic.publication import _admit_inference

    domain = yaml.safe_load(_bundle().sources[0].content)
    domain["slots"] = {"scalar_relation": {"range": "string", flag: True}}
    domain["classes"]["Item"]["slots"] = ["scalar_relation"]
    bundle = SourceBundle("domain", (SourceArtifact("domain", yaml.safe_dump(domain).encode()),))
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with pytest.raises(ValueError, match="binary entity relations"):
        _admit_inference(prepared)
    with commit_db_engine.begin() as conn:
        releases.persist_release(conn, bundle, dependencies, profile, prepared)
        project = _project(conn)
    with (
        commit_writer_engine.begin() as conn,
        pytest.raises(DBAPIError, match="native binary inference profile") as failure,
    ):
        conn.execute(
            text("SELECT data.initialize_source_project(:p,:r,:z)"),
            {"p": project, "r": prepared.release_id, "z": str(uuid4())},
        )
    assert getattr(failure.value.orig, "sqlstate", None) == "23514"


@pytest.mark.parametrize("capability", ["execute", "select"])
def test_native_readiness_requires_positive_application_capabilities(commit_db_engine, capability):
    with commit_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
        project = _project(conn)
        owner = conn.dialect.identifier_preparer.quote(conn.scalar(text("SELECT current_user")))
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        if capability == "execute":
            conn.execute(
                text(
                    "REVOKE EXECUTE ON FUNCTION "
                    "ops.create_run(text,text,text,bigint,bytea,text,bigint,jsonb,text,text) "
                    "FROM corpus_sem_writer"
                )
            )
        else:
            conn.execute(text("REVOKE SELECT ON data.occurrence_context FROM corpus_sem_writer"))
        with pytest.raises(ExecutionAdmissionError, match="native execution deployment"):
            releases.activate_release(
                conn, project, prepared.release_id, expected_parent=None, expected_generation=0
            )
        conn.execute(text("SET LOCAL ROLE " + owner))
        assert releases.activation_token(conn, project) == releases.ActivationToken(None, 0)


def test_native_empty_realization_cannot_rebind_interpretation(commit_db_engine):
    with commit_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
        project = _project(conn)
        realization = str(uuid4())
        conn.execute(
            insert(table("data.realization")).values(
                realization_id=realization, project_id=project, release_id=prepared.release_id
            )
        )
        other_project = _project(conn)
        with pytest.raises(DBAPIError, match="binding is immutable"), conn.begin_nested():
            conn.execute(
                update(table("data.realization"))
                .where(table("data.realization").c.realization_id == realization)
                .values(project_id=other_project)
            )


def test_native_constructor_admits_binary_rules_with_subtyped_range(
    commit_db_engine, commit_writer_engine
):
    import yaml

    from corpus_structure.semantic.publication import _admit_inference

    domain = yaml.safe_load(_bundle().sources[0].content)
    domain["slots"] = {
        "edge": {"range": "Item", "inverse": "reverse", "transitive": True},
        "reverse": {"range": "Item", "symmetric": True},
        "broad": {"range": "Item"},
        "narrow": {"range": "Child", "is_a": "broad"},
    }
    domain["classes"]["Item"]["slots"] = ["edge", "reverse", "broad", "narrow"]
    domain["classes"]["Child"] = {"is_a": "Item"}
    bundle = SourceBundle("domain", (SourceArtifact("domain", yaml.safe_dump(domain).encode()),))
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    _admit_inference(prepared)
    with commit_db_engine.begin() as conn:
        releases.persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(text("SELECT data.require_execution_release(:r)"), {"r": prepared.release_id})
        project = _project(conn)
    realization = str(uuid4())
    with commit_writer_engine.begin() as conn:
        assert (
            conn.scalar(
                text("SELECT data.initialize_source_project(:p,:r,:z)"),
                {"p": project, "r": prepared.release_id, "z": realization},
            )
            == realization
        )


def test_native_constructor_requires_existing_authored_sql_admission(
    commit_db_engine, commit_writer_engine
):
    with commit_db_engine.begin() as conn:
        prepared = _stage_authored_sql(conn)
        project = _project(conn)
    with commit_writer_engine.begin() as conn:
        with pytest.raises(DBAPIError, match="required authored SQL"), conn.begin_nested():
            conn.execute(
                text("SELECT data.initialize_source_project(:p,:r,:z)"),
                {"p": project, "r": prepared.release_id, "z": str(uuid4())},
            )
        assert releases.activation_token(conn, project) == releases.ActivationToken(None, 0)
        assert (
            conn.scalar(
                select(table("data.realization").c.realization_id).where(
                    table("data.realization").c.project_id == project
                )
            )
            is None
        )


def test_composed_activation_establishes_exact_restricted_sql_admission(
    commit_db_engine, commit_reader_engine, commit_writer_engine
):
    from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID

    with commit_db_engine.begin() as conn:
        prepared = _stage_authored_sql(conn)
        project = _project(conn)
        with commit_reader_engine.connect() as reader:
            token = releases.activate_release(
                conn,
                project,
                prepared.release_id,
                expected_parent=None,
                expected_generation=0,
                sql_reader=reader,
            )
        assert token == releases.ActivationToken(prepared.release_id, 1)
        artifact = (
            conn.execute(
                select(table("sem.sql_admission")).where(
                    table("sem.sql_admission").c.release_id == prepared.release_id
                )
            )
            .mappings()
            .one()
        )
        assert sha256(bytes(artifact["content"])).hexdigest() == artifact["content_digest"]
        assert artifact["physical_id"] == PHYSICAL_MODEL_ID
        assert json.loads(bytes(artifact["content"]))["sql"] == "SELECT entity_id FROM data.entity"
    with commit_writer_engine.begin() as conn:
        realization = str(uuid4())
        assert (
            conn.scalar(
                text("SELECT data.initialize_source_project(:p,:r,:z)"),
                {"p": project, "r": prepared.release_id, "z": realization},
            )
            == realization
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("sql", "SELECT 'different'::text"),
        ("release_id", "release:another"),
        ("physical_id", "physical:another"),
        ("content_digest", "0" * 64),
    ],
)
def test_native_constructor_requires_exact_sql_artifact_binding(
    commit_db_engine, commit_reader_engine, commit_writer_engine, field, value
):
    from corpus_structure.semantic.authored_sql import admit_archived_sql

    with commit_db_engine.begin() as conn:
        prepared = _stage_authored_sql(conn)
        project = _project(conn)
        with commit_reader_engine.connect() as reader:
            (artifact,) = admit_archived_sql(conn, prepared.release_id, reader_conn=reader)
        body = json.loads(artifact.content)
        if field == "content_digest":
            values = {"content_digest": value}
        else:
            body[field] = value
            content = canonical_bytes(body)
            values = {"content": content, "content_digest": sha256(content).hexdigest()}
        admission = table("sem.sql_admission")
        with administrative_archive_edit(conn, admission):
            conn.execute(
                update(admission)
                .where(admission.c.release_id == prepared.release_id)
                .values(**values)
            )
    with (
        commit_writer_engine.begin() as conn,
        pytest.raises(DBAPIError, match="required authored SQL"),
    ):
        conn.execute(
            text("SELECT data.initialize_source_project(:p,:r,:z)"),
            {"p": project, "r": prepared.release_id, "z": str(uuid4())},
        )


@pytest.mark.parametrize(
    "outcome,code,message,refused",
    [
        ("unsupported", "unsupported", "unsupported required semantics", True),
        ("unresolved", "unresolved", "unresolved required semantics", True),
        ("unchecked", "unchecked_term", "different unchecked term", True),
        ("unchecked", "other_code", "not4curation:unchecked", True),
        ("unchecked", "unchecked_term", "not4curation:unchecked", False),
    ],
)
def test_native_constructor_obeys_archived_diagnostic_policy(
    commit_db_engine, commit_writer_engine, outcome, code, message, refused
):
    # Independent archive data exercises the native predicate, including its exact exception.
    with commit_db_engine.begin() as conn:
        *_, prepared = _stage(conn)
        project = _project(conn)
        archive = json.loads(
            conn.scalar(
                select(table("sem.release").c.prepared_bytes).where(
                    table("sem.release").c.release_id == prepared.release_id
                )
            )
        )
        archive["products"]["diagnostics"] = [
            {
                "outcome": outcome,
                "code": code,
                "message": message,
                "location": "test",
            }
        ]
        with administrative_archive_edit(conn, table("sem.release")):
            conn.execute(
                update(table("sem.release"))
                .where(table("sem.release").c.release_id == prepared.release_id)
                .values(prepared_bytes=canonical_bytes(archive))
            )
        if not refused:
            conn.execute(
                text("SELECT data.require_execution_release(:r)"), {"r": prepared.release_id}
            )
    with commit_writer_engine.begin() as conn:
        statement = text("SELECT data.initialize_source_project(:p,:r,:z)")
        parameters = {"p": project, "r": prepared.release_id, "z": str(uuid4())}
        if refused:
            with pytest.raises(DBAPIError, match="unresolved or unchecked"), conn.begin_nested():
                conn.execute(statement, parameters)
        else:
            assert conn.scalar(statement, parameters) == parameters["z"]
