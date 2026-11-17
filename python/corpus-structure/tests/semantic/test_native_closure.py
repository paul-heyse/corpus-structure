"""Independent native closure and actual restricted-principal obligations."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from native_refusals import native_refusal
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import ReleaseConflict, persist_release
from corpus_structure.semantic.types import PreparedArtifact
from semantic.native_closure_support import archive as archive


def test_restricted_complete_archive_replay_and_immutable_closure(
    commit_db_engine, commit_admitter_engine
):
    bundle, deps, profile, prepared = archive(commit_admitter_engine)
    with commit_admitter_engine.begin() as conn:
        conn.execute(text("SELECT data.require_runtime_principal('admit')"))
        assert persist_release(conn, bundle, deps, profile, prepared) == prepared.release_id
        with (
            pytest.raises(
                ReleaseConflict, match="prepared products differ from exact-source verification"
            ),
            conn.begin_nested(),
        ):
            persist_release(
                conn,
                bundle,
                deps,
                profile,
                replace(
                    prepared, artifacts=(*prepared.artifacts, PreparedArtifact("extra", b"new"))
                ),
            )
    # Actual application credentials cannot directly mutate or extend the archive.
    for sql in (
        "UPDATE sem.release SET profile=profile",
        "DELETE FROM sem.artifact",
        "TRUNCATE sem.input",
        "INSERT INTO sem.input SELECT * FROM sem.input LIMIT 1",
        "SELECT * FROM ops.data_request",
    ):
        with commit_admitter_engine.begin() as conn, native_refusal("42501"), conn.begin_nested():
            conn.execute(text(sql))
    # Even the protected publisher's payload authority cannot extend finalized meaning.
    with commit_db_engine.begin() as conn:
        for sql in (
            "UPDATE sem.release SET profile=profile",
            "DELETE FROM sem.artifact",
            "TRUNCATE sem.input CASCADE",
        ):
            with pytest.raises(DBAPIError, match="immutable semantic content"), conn.begin_nested():
                conn.execute(text(sql))
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        with pytest.raises(DBAPIError, match="finalized release"), conn.begin_nested():
            conn.execute(
                text("INSERT INTO sem.input VALUES(:r,'extra','extra','x'::bytea,'wrong')"),
                {"r": prepared.release_id},
            )


def test_restricted_activation_cas_and_deployment_record(
    commit_db_engine, commit_admitter_engine, commit_application_settings
):
    from corpus_structure.semantic.releases import ActivationConflict, activate_release
    from semantic.data_operation_kernel_support import STORAGE, prepare_kernel

    captured = prepare_kernel(STORAGE)
    bundle, deps, profile, prepared = (
        captured.bundle,
        captured.dependencies,
        captured.profile,
        captured.prepared,
    )
    project = str(uuid4())
    with commit_db_engine.begin() as conn:
        conn.execute(insert(table("data.project")).values(project_id=project))
    with commit_admitter_engine.begin() as conn:
        persist_release(conn, bundle, deps, profile, prepared)
        assert (
            activate_release(
                conn, project, prepared.release_id, expected_parent=None, expected_generation=0
            ).generation
            == 1
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM sem.deployment_admission WHERE release_id=:r AND "
                    "kind='native'"
                ),
                {"r": prepared.release_id},
            ).scalar_one()
            == 1
        )
        with pytest.raises((DBAPIError, ActivationConflict)), conn.begin_nested():
            activate_release(
                conn, project, prepared.release_id, expected_parent=None, expected_generation=0
            )

    from typer.testing import CliRunner

    from corpus_structure.cli.app import build_full_app
    app = build_full_app()
    from corpus_structure.cli.output import CliState

    report = CliRunner().invoke(
        app,
        ["db", "check", "--release", prepared.release_id, "--json"],
        obj=CliState(settings_factory=lambda: commit_application_settings),
    )
    assert report.exit_code == 0, (report.output, report.exception)
    with commit_db_engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT generation FROM data.project WHERE project_id=:p"), {"p": project}
            ).scalar_one()
            == 1
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM sem.deployment_admission WHERE release_id=:r"),
                {"r": prepared.release_id},
            ).scalar_one()
            == 1
        )

    # Preserve the name while weakening a non-split constraint: names cannot attest meaning.
    from corpus_structure.semantic.execution_admission import (
        ExecutionAdmissionError,
        admit_execution_release,
    )

    task = table("ops.task")
    check = next(
        item
        for item in task.constraints
        if hasattr(item, "sqltext") and "invocation_key" in str(item.sqltext)
    )
    quote = commit_db_engine.dialect.identifier_preparer.quote
    with commit_db_engine.begin() as conn:
        owner = conn.execute(
            text("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid='ops.task'::regclass")
        ).scalar_one()
        conn.exec_driver_sql("SET LOCAL ROLE " + quote(owner))
        conn.exec_driver_sql("ALTER TABLE ops.task DROP CONSTRAINT " + quote(check.name))
        conn.exec_driver_sql(
            "ALTER TABLE ops.task ADD CONSTRAINT " + quote(check.name) + " CHECK(true)"
        )
    with (
        commit_admitter_engine.begin() as conn,
        pytest.raises(ExecutionAdmissionError, match="physical CHECK expression differs"),
    ):
        admit_execution_release(prepared, connection=conn)


def test_bulk_exact_native_codec_vectors(commit_db_engine):
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.value_codec import value_meaning

    # The actual current semantic value boundary consumes tagged values, not
    # mutable typed-value rows in the retired realization model.
    samples = [
        ("decimal", "1.2300", Decimal("1.23")),
        ("decimal", "-0.000", Decimal("0")),
        ("decimal", "1e100", Decimal("1e100")),
        ("decimal", "1e-100", Decimal("1e-100")),
        ("string", "Straße/東京", "Straße/東京"),
        ("float", (0.0).hex(), 0.0),
        ("float", (-0.0).hex(), -0.0),
        ("float", (0.1).hex(), 0.1),
        ("float", "0x0.0000000000001p-1022", float.fromhex("0x0.0000000000001p-1022")),
    ]
    with commit_db_engine.begin() as conn:
        actual = (
            conn.execute(
                text(
                    "SELECT data.ddo_normalize(value) FROM jsonb_array_elements(CAST(:values AS jsonb)) WITH ORDINALITY AS item(value,ordinal) ORDER BY ordinal"
                ),
                {
                    "values": canonical_bytes(
                        [[kind, lexical] for kind, lexical, _ in samples]
                    ).decode()
                },
            )
            .scalars()
            .all()
        )
        assert actual == [value_meaning(value) for _, _, value in samples]
        assert actual[0] == ["decimal", "1.23"]
        assert actual[5] == ["float", "0x0.0p+0"]
        assert actual[6] == ["float", "-0x0.0p+0"]
        for lexical in (
            "NaN",
            "Infinity",
            "0x1.0000000000000p+1024",
            "0x1.0p+0",
            "-0x0.0000000000000p-1022",
        ):
            with pytest.raises(DBAPIError, match="invalid finite float"), conn.begin_nested():
                conn.execute(
                    text("SELECT data.ddo_normalize(CAST(:value AS jsonb))"),
                    {"value": canonical_bytes(["float", lexical]).decode()},
                )


def _forward_descriptor(product):
    import json

    from pglast import ast, parse_sql

    from corpus_structure.semantic.native_products import function_bodies

    body = function_bodies(product.content.decode())["data.execution_contract_descriptor"]
    statement = parse_sql(body)[0].stmt
    assert isinstance(statement, ast.SelectStmt) and statement.targetList
    cast = statement.targetList[0].val
    assert isinstance(cast, ast.TypeCast) and isinstance(cast.arg, ast.A_Const)
    assert isinstance(cast.arg.val, ast.String) and cast.arg.val.sval is not None
    return json.loads(cast.arg.val.sval)


def test_frozen_head_witness_preserves_its_explicit_authoring_provenance():
    from pathlib import Path

    from alembic.script import ScriptDirectory

    from corpus_structure.semantic.execution_admission import require_frozen_native_revision
    from corpus_structure.semantic.migrations import alembic_config, head_revision
    from corpus_structure.semantic.types import SourceArtifact

    current_head = head_revision()
    assert current_head is not None
    head_script = ScriptDirectory.from_config(alembic_config()).get_revision(current_head)
    assert head_script is not None
    revision = head_script.module
    head = SourceArtifact(
        revision.NATIVE_ADMISSION_FILE,
        Path(head_script.path).with_name(revision.NATIVE_ADMISSION_FILE).read_bytes(),
    )
    assert head.digest == revision.NATIVE_ADMISSION_SHA256
    recorded = _forward_descriptor(head)
    assert (
        require_frozen_native_revision(Path(head_script.path).parent, current_head)
        == recorded["physical_id"]
    )

    from corpus_structure.semantic.native_admission import recorded_authoring_provenance

    provenance = recorded_authoring_provenance(head.content.decode())
    assert provenance.model_id == recorded["model_id"]
    assert [{"name": name, "sha256": digest} for name, digest in provenance.inputs] == recorded[
        "inputs"
    ]


def test_current_context_source_and_identity_helper_changes_are_visible(monkeypatch):
    from pathlib import Path

    from corpus_structure.semantic.native_products import function_bodies
    from corpus_structure.semantic.pdf_publication_native import publication_sql

    original = Path.read_text
    before = function_bodies(publication_sql())

    def changed(path, *args, **kwargs):
        content = original(path, *args, **kwargs)
        if path.name == "pdf_record_context.sql":
            return content.replace(
                "'descriptor',jsonb_build_object", "'changed_descriptor',jsonb_build_object"
            )
        return content

    monkeypatch.setattr(Path, "read_text", changed)
    after = function_bodies(publication_sql())
    assert "'changed_descriptor'" in after["ops.record_integrated_source_context"]
    assert (
        before["ops.record_integrated_source_context"]
        != after["ops.record_integrated_source_context"]
    )


@pytest.mark.parametrize(
    "relation_name,expression",
    [
        ("kb.pdf_record_access", "ordinal >= 2"),
        ("ops.pdf_product_body", "octet_length(payload) >= 2"),
    ],
)
def test_current_physical_constraint_changes_admission_identity(relation_name, expression):
    from sqlalchemy import CheckConstraint

    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.native_products import current_admission_fields

    before = current_admission_fields()
    relation = metadata.tables[relation_name]
    constraint = CheckConstraint(expression, name="counterfactual_reproduction")
    relation.append_constraint(constraint)
    try:
        after = current_admission_fields()
    finally:
        relation.constraints.remove(constraint)
    assert before["physical_checks_source_digest"] != after["physical_checks_source_digest"]


def test_alembic_current_physical_comparison(commit_db_engine):
    from alembic import command

    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.migrations import alembic_config
    from corpus_structure.semantic.native_objects import NativeAuthoring

    with commit_db_engine.connect() as conn:
        config = alembic_config(conn)
        config.attributes["target_metadata"] = metadata
        config.attributes["native_authoring"] = NativeAuthoring(())
        command.check(config)


def test_live_cross_purpose_privilege_drift_refuses(
    commit_db_engine, commit_reader_engine, commit_admitter_engine, commit_application_settings
):
    from corpus_structure.semantic.runtime import open_runtime_engine

    with (
        open_runtime_engine(commit_application_settings, purpose="read") as restricted,
        restricted.connect() as read,
    ):
        assert read.execute(text("SELECT session_user")).scalar_one() == "corpus_sem_reader"
    bundle, deps, profile, prepared = archive(commit_admitter_engine)
    with commit_reader_engine.connect() as reader:
        reader.execute(text("SELECT data.require_runtime_principal('read')"))
    with commit_admitter_engine.connect() as admission:
        admission.execute(text("SELECT data.require_runtime_principal('admit')"))
        admission.commit()
        with commit_db_engine.begin() as admin:
            admin.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
            admin.execute(
                text(
                    "GRANT EXECUTE ON FUNCTION ops.initialize_source_project(jsonb) TO corpus_sem_reader"
                )
            )
        with (
            commit_reader_engine.begin() as reader,
            pytest.raises(DBAPIError, match="purpose contract"),
        ):
            reader.execute(text("SELECT data.require_runtime_principal('read')"))
        with commit_db_engine.begin() as admin:
            admin.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
            admin.execute(
                text(
                    "REVOKE EXECUTE ON FUNCTION ops.initialize_source_project(jsonb) FROM corpus_sem_reader"
                )
            )
            admin.execute(
                text(
                    "GRANT EXECUTE ON FUNCTION ops.read_selected_feature_fit_frame(jsonb) TO corpus_sem_admitter"
                )
            )
        with admission.begin(), pytest.raises(DBAPIError, match="purpose contract"):
            admission.execute(text("SELECT data.require_runtime_principal('admit')"))
        from corpus_structure.semantic.execution_admission import ExecutionAdmissionError

        with (
            pytest.raises(ExecutionAdmissionError, match="native deployment catalog differs"),
            admission.begin(),
        ):
            persist_release(admission, bundle, deps, profile, prepared)


@settings(
    max_examples=16, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    st.lists(
        st.one_of(
            st.floats(allow_nan=False, allow_infinity=False),
            st.decimals(
                min_value=-(10**60),
                max_value=10**60,
                places=18,
                allow_nan=False,
                allow_infinity=False,
            ),
            st.text(max_size=30).filter(lambda value: "\x00" not in value),
        ),
        min_size=1,
        max_size=16,
    )
)
def test_generated_codec_batch(commit_db_engine, values):
    """One native DB, rolled-back examples, and one typed batch per example."""
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.value_codec import value_meaning

    tagged = []
    for value in values:
        kind = (
            "float"
            if isinstance(value, float)
            else "decimal"
            if isinstance(value, Decimal)
            else "string"
        )
        lexical = value.hex() if isinstance(value, float) else str(value)
        tagged.append([kind, lexical])
    with commit_db_engine.connect() as conn:
        try:
            actual = (
                conn.execute(
                    text(
                        "SELECT data.ddo_normalize(value) FROM jsonb_array_elements(CAST(:values AS jsonb)) WITH ORDINALITY AS item(value,ordinal) ORDER BY ordinal"
                    ),
                    {"values": canonical_bytes(tagged).decode()},
                )
                .scalars()
                .all()
            )
            assert actual == [value_meaning(value) for value in values]
        finally:
            conn.rollback()
