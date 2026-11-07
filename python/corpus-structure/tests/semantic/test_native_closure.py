"""Independent native closure and actual restricted-principal obligations."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import ReleaseConflict, persist_release
from corpus_structure.semantic.types import PreparedArtifact

from .test_releases import source_bundle


def archive(engine):
    bundle = source_bundle()
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    with engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
    return bundle, dependencies, profile, prepared


def realization(engine, release):
    key = str(uuid4())
    with engine.begin() as conn:
        conn.execute(insert(table("data.project")).values(project_id=key))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id=key, project_id=key, release_id=release
            )
        )
    return key


def test_restricted_complete_archive_replay_and_immutable_closure(semantic_db_engine, admitter):
    bundle, deps, profile, prepared = archive(admitter)
    with admitter.begin() as conn:
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
        "SELECT * FROM eval.reference_set",
    ):
        with admitter.begin() as conn, pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(text(sql))
    # Even the protected publisher's payload authority cannot extend finalized meaning.
    with semantic_db_engine.begin() as conn:
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


def test_protected_workspace_and_no_writer_temp(
    semantic_db_engine, semantic_writer_engine, admitter
):
    *_, prepared = archive(admitter)
    z = realization(semantic_db_engine, prepared.release_id)
    params = {"r": prepared.release_id, "z": z, "revision": 0, "snapshot": "independent-snapshot"}
    with (
        semantic_writer_engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as conn,
        conn.begin(),
    ):
        conn.execute(text("SELECT data.require_runtime_principal('write')"))
        with pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(text("CREATE TEMP TABLE counterfeit(x text)"))
        conn.execute(
            text("SELECT data.begin_inference_workspace(:r,:z,:revision,:snapshot)"), params
        )
        owner = conn.execute(
            text(
                "SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid='pg_temp.semantic"
                "_inference_work'::regclass"
            )
        ).scalar_one()
        assert owner == "corpus_sem_publisher"
        conn.execute(
            text(
                "INSERT INTO pg_temp.semantic_inference_work VALUES('a','p','b',NULL,NULL,'"
                "context')"
            )
        )
        conn.execute(text("UPDATE pg_temp.semantic_inference_work SET qualification='q'"))
        with pytest.raises(DBAPIError), conn.begin_nested():
            conn.execute(text("UPDATE pg_temp.semantic_inference_work SET predicate='forged'"))
        with pytest.raises(DBAPIError, match="preexisting"), conn.begin_nested():
            conn.execute(
                text("SELECT data.begin_inference_workspace(:r,:z,:revision,:snapshot)"), params
            )
        with pytest.raises(DBAPIError, match="binding differs"), conn.begin_nested():
            conn.execute(
                text("SELECT data.end_inference_workspace(:r,:z,:revision,'other')"), params
            )
        conn.execute(text("SELECT data.end_inference_workspace(:r,:z,:revision,:snapshot)"), params)
        assert (
            conn.execute(text("SELECT to_regclass('pg_temp.semantic_inference_work')")).scalar_one()
            is None
        )


def test_restricted_activation_cas_and_deployment_record(semantic_db_engine, admitter, monkeypatch):
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.releases import ActivationConflict, activate_release

    from .test_execution_release import _bundle

    bundle, deps, profile = (
        _bundle(),
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )
    prepared = prepare_release(bundle, deps, profile)
    project = str(uuid4())
    with semantic_db_engine.begin() as conn:
        conn.execute(insert(table("data.project")).values(project_id=project))
    with admitter.begin() as conn:
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

    from corpus_structure.cli.app import app

    monkeypatch.setenv(
        "CORPUS_DATABASE__URL",
        semantic_db_engine.url.set(
            drivername="postgresql", username="corpus_sem_writer"
        ).render_as_string(hide_password=False),
    )
    report = CliRunner().invoke(app, ["db", "check", "--release", prepared.release_id, "--json"])
    assert report.exit_code == 0, (report.output, report.exception)
    with semantic_db_engine.connect() as conn:
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
    quote = semantic_db_engine.dialect.identifier_preparer.quote
    with semantic_db_engine.begin() as conn:
        owner = conn.execute(
            text("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid='ops.task'::regclass")
        ).scalar_one()
        conn.exec_driver_sql("SET LOCAL ROLE " + quote(owner))
        conn.exec_driver_sql("ALTER TABLE ops.task DROP CONSTRAINT " + quote(check.name))
        conn.exec_driver_sql(
            "ALTER TABLE ops.task ADD CONSTRAINT " + quote(check.name) + " CHECK(true)"
        )
    with (
        admitter.begin() as conn,
        pytest.raises(ExecutionAdmissionError, match="physical CHECK expression differs"),
    ):
        admit_execution_release(prepared, connection=conn)


def test_bulk_exact_native_codec_vectors(semantic_db_engine, admitter):
    from decimal import Decimal

    from corpus_structure.semantic.value_codec import value_meaning as meaning

    *_, prepared = archive(admitter)
    z = realization(semantic_db_engine, prepared.release_id)
    samples = [
        ("decimal", "1.2300", Decimal("1.23")),
        ("decimal", "-0.000", Decimal("0")),
        ("decimal", "1e100", Decimal("1e100")),
        ("decimal", "1e-100", Decimal("1e-100")),
        ("string", "Straße/東京", "Straße/東京"),
        ("float", (0.0).hex(), 0.0),
        ("float", (-0.0).hex(), -0.0),
        ("float", (0.1).hex(), 0.1),
        (
            "float",
            float.fromhex("0x0.0000000000001p-1022").hex(),
            float.fromhex("0x0.0000000000001p-1022"),
        ),
    ]
    with semantic_db_engine.begin() as conn:
        rows = [
            {
                "realization_id": z,
                "release_id": prepared.release_id,
                "value_id": str(i),
                "kind": kind,
                "text_value": lexical if kind != "decimal" else None,
                "decimal_lexical": lexical if kind == "decimal" else None,
            }
            for i, (kind, lexical, _) in enumerate(samples)
        ]
        conn.execute(insert(table("data.typed_value")), rows)
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        actual = conn.execute(
            text(
                "SELECT value_id,data.value_meaning(release_id,realization_id,value_id) FRO"
                "M data.typed_value ORDER BY value_id::integer"
            )
        ).all()
        assert [value for _, value in actual] == [meaning(value) for _, _, value in samples]
        assert actual[0][1] == ["decimal", "1.23"]
        assert actual[5][1] == ["float", "0x0.0p+0"]
        assert actual[6][1] == ["float", "-0x0.0p+0"]
        for lexical in (
            "NaN",
            "Infinity",
            "0x1.0000000000000p+1024",
            "0x1.0p+0",
            "-0x0.0000000000000p-1022",
        ):
            with pytest.raises(DBAPIError, match="invalid finite float"), conn.begin_nested():
                conn.execute(
                    insert(table("data.typed_value")).values(
                        realization_id=z,
                        release_id=prepared.release_id,
                        value_id="bad",
                        kind="float",
                        text_value=lexical,
                    )
                )


def test_selected_view_drift_refuses_admission(semantic_db_engine, admitter):
    from corpus_structure.semantic.execution_admission import (
        ExecutionAdmissionError,
        _verify_deployment_functions,
    )

    with semantic_db_engine.begin() as conn:
        _verify_deployment_functions(conn)
        conn.execute(
            text("CREATE OR REPLACE VIEW data.selected_fact AS SELECT f.* FROM data.fact f")
        )
        with pytest.raises(ExecutionAdmissionError, match="selected-fact view"):
            _verify_deployment_functions(conn)


def test_model_products_match_frozen_current_native_state(semantic_db_engine, monkeypatch):
    from sqlalchemy.dialects.postgresql import dialect
    from sqlalchemy.schema import CreateTable

    from corpus_structure.semantic import source_view_native
    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.native_candidate import (
        current_native_state,
        prepare_series_candidate,
    )

    before = {
        name: str(CreateTable(relation).compile(dialect=dialect()))
        for name, relation in metadata.tables.items()
    }

    def refuse_recorded_provenance(_admission):
        raise AssertionError("current candidate must declare current authoring provenance")

    monkeypatch.setattr(
        source_view_native, "recorded_authoring_provenance", refuse_recorded_provenance
    )
    with semantic_db_engine.connect() as conn:
        frozen = current_native_state(conn)
        assert frozen is not None
        script, authoring = prepare_series_candidate(conn, owned_authoring=True)
        assert script.upgrade_ops is not None and script.upgrade_ops.is_empty()
        assert {item.identity: item.payload() for item in authoring.desired} == {
            item.identity: item.payload() for item in frozen
        }
    assert before == {
        name: str(CreateTable(relation).compile(dialect=dialect()))
        for name, relation in metadata.tables.items()
    }


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


def test_current_frozen_head_witness_records_current_authoring_provenance():
    from hashlib import sha256
    from pathlib import Path

    from alembic.script import ScriptDirectory

    from corpus_structure.semantic.contracts import EXECUTION_COMPILER_VERSION
    from corpus_structure.semantic.execution_admission import _descriptor_sha256
    from corpus_structure.semantic.migrations import alembic_config, head_revision
    from corpus_structure.semantic.native_products import (
        NativeProduct,
        current_authoring_provenance,
        function_bodies,
    )

    current_head = head_revision()
    assert current_head is not None
    head_script = ScriptDirectory.from_config(alembic_config()).get_revision(current_head)
    assert head_script is not None
    revision = head_script.module
    head = NativeProduct(
        revision.NATIVE_ADMISSION_FILE,
        Path(head_script.path).with_name(revision.NATIVE_ADMISSION_FILE).read_bytes(),
    )
    assert head.digest == revision.NATIVE_ADMISSION_SHA256
    recorded = _forward_descriptor(head)
    assert (
        sha256(
            function_bodies(head.content.decode())["data.execution_contract_descriptor"].encode()
        ).hexdigest()
        == _descriptor_sha256()
    )

    current = current_authoring_provenance()
    assert recorded["execution_abi"] == EXECUTION_COMPILER_VERSION == "27"
    assert recorded["model_id"] == current.model_id
    assert recorded["inputs"] == [
        {"name": name, "sha256": digest} for name, digest in current.inputs
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


def test_current_admission_refuses_unsupported_effect(monkeypatch):
    from corpus_structure.semantic.effect_support import SUPPORTED_EFFECTS
    from corpus_structure.semantic.native_products import current_admission_fields
    from corpus_structure.semantic.types import PreparationError

    monkeypatch.setitem(
        SUPPORTED_EFFECTS["read_pdf_product"], "effects", ("atomic_native_publication",)
    )
    with pytest.raises(PreparationError, match="effect"):
        current_admission_fields()


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


def test_alembic_current_physical_comparison(semantic_db_engine):
    from alembic import command

    from corpus_structure.semantic.migrations import alembic_config
    from corpus_structure.semantic.native_objects import NativeAuthoring

    with semantic_db_engine.connect() as conn:
        config = alembic_config(conn)
        config.attributes["native_authoring"] = NativeAuthoring(())
        command.check(config)


def test_live_cross_purpose_privilege_drift_refuses(
    semantic_db_engine, semantic_reader_engine, admitter
):
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.settings import Settings

    owner_url = semantic_db_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    with (
        open_runtime_engine(Settings(database={"url": owner_url}), purpose="read") as restricted,
        restricted.connect() as read,
    ):
        assert read.execute(text("SELECT session_user")).scalar_one() == "corpus_sem_reader"
    bundle, deps, profile, prepared = archive(admitter)
    with semantic_reader_engine.connect() as reader:
        reader.execute(text("SELECT data.require_runtime_principal('read')"))
    with admitter.connect() as admission:
        admission.execute(text("SELECT data.require_runtime_principal('admit')"))
        admission.commit()
        with semantic_db_engine.begin() as admin:
            admin.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
            admin.execute(text("GRANT EXECUTE ON FUNCTION data.begin_stage() TO corpus_sem_reader"))
            admin.execute(text("GRANT SELECT ON eval.reference_set TO corpus_sem_admitter"))
        with (
            semantic_reader_engine.begin() as reader,
            pytest.raises(DBAPIError, match="purpose contract"),
        ):
            reader.execute(text("SELECT data.require_runtime_principal('read')"))
        with pytest.raises(DBAPIError, match="unrestricted admission caller"), admission.begin():
            persist_release(admission, bundle, deps, profile, prepared)


@pytest.fixture
def codec_binding(semantic_db_engine, admitter):
    *_, prepared = archive(admitter)
    return prepared.release_id, realization(semantic_db_engine, prepared.release_id)


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
def test_generated_codec_batch(semantic_db_engine, codec_binding, values):
    """One native DB, rolled-back examples, and one typed batch per example."""
    from corpus_structure.semantic.value_codec import value_meaning

    r, z = codec_binding
    rows = []
    for i, value in enumerate(values):
        kind = (
            "float"
            if isinstance(value, float)
            else "decimal"
            if isinstance(value, Decimal)
            else "string"
        )
        lexical = value.hex() if isinstance(value, float) else str(value)
        rows.append(
            {
                "release_id": r,
                "realization_id": z,
                "value_id": str(i),
                "kind": kind,
                "text_value": None if kind == "decimal" else lexical,
                "decimal_lexical": lexical if kind == "decimal" else None,
            }
        )
    with semantic_db_engine.connect() as conn:
        try:
            conn.execute(insert(table("data.typed_value")), rows)
            conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
            actual = (
                conn.execute(
                    text(
                        "SELECT data.value_meaning(release_id,realization_id,value_id) FROM"
                        " data.typed_value ORDER BY value_id::integer"
                    )
                )
                .scalars()
                .all()
            )
            assert actual == [value_meaning(value) for value in values]
        finally:
            conn.rollback()
