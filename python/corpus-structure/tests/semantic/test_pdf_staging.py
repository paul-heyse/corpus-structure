"""Actual private PDF upload, independent fence/replay/privacy expectations."""

from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import psycopg
import pyarrow as pa
import pytest
from pydantic import create_model
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    create_run,
    create_task,
    record_method,
    register_document,
)
from corpus_structure.semantic.pdf_contracts import store_pdf_original
from corpus_structure.semantic.pdf_records import native_schema_bytes
from corpus_structure.semantic.pdf_staging import (
    abandon_pdf_build,
    adopt_pdf_batch,
    begin_pdf_build,
    inspect_pdf_progress,
    resume_pdf_build,
    stage_schema,
)

from .test_operations import setup


@pytest.fixture
def private_build(semantic_db_engine, semantic_writer_engine, tmp_path):
    prepared = setup(semantic_db_engine, composed=True)
    original = b"%PDF-1.7 private staging fixture"
    recipe = b'{"recipe":"stage-test"}'
    path = tmp_path / "source.pdf"
    path.write_bytes(original)
    with semantic_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="stage-test",
        )
        method = SimpleNamespace(
            name="pdf.stage.fixture",
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("PdfStageFixture"),
        )
        config = record_method(conn, method, "default", {}, "pdf-stage")
        document = register_document(
            conn,
            project_id="p",
            source_uri="file:pdf-stage",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=document,
            unit_key="pdf-stage",
            input_hash=sha256(original).hexdigest(),
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="stage-owner")[0]
        store_pdf_original(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="stage-owner",
            original=original,
            recipe_bytes=recipe,
        )
        build = begin_pdf_build(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="stage-owner",
            source_digest=sha256(original).hexdigest(),
            recipe_digest=sha256(recipe).hexdigest(),
            schema_digest=sha256(native_schema_bytes()).hexdigest(),
            replay_key="build-1",
        )
    return build


def native_batch(build, text_value="first"):
    return pa.RecordBatch.from_pylist(
        [
            dict(
                product_id=build.product_id,
                revision_id=build.revision_id,
                record_id="node-1",
                native_type="TextItem",
                family="node",
                native_address="#/texts/0",
                native_address_stream_id=None,
                scalars_json='{"text":"' + text_value + '"}',
                structure_json="{}",
            )
        ],
        schema=stage_schema("native"),
    )


def test_private_typed_copy_exact_replay_and_changed_duplicate(
    private_build, semantic_writer_engine
):
    build = private_build
    with semantic_writer_engine.begin() as conn:
        first = adopt_pdf_batch(conn, build, "batch-1", {"native": [native_batch(build)]})
        assert first.row_count == 1
    with semantic_writer_engine.begin() as conn:
        assert adopt_pdf_batch(conn, build, "batch-1", {"native": [native_batch(build)]}) == first
        assert inspect_pdf_progress(conn, build) == (first,)
    for key in ("batch-1", "different-batch"):
        with (
            semantic_writer_engine.begin() as conn,
            pytest.raises(DBAPIError, match=r"replay differs|changed private record"),
        ):
            adopt_pdf_batch(conn, build, key, {"native": [native_batch(build, "changed")]})


def test_private_forward_references_are_rows_before_their_targets(
    private_build, semantic_writer_engine
):
    build = private_build
    row = dict(
        product_id=build.product_id,
        revision_id=build.revision_id,
        reference_id="r",
        source_id="not-yet-present",
        field_name="cref",
        native_pointer="#/texts/99",
        native_pointer_stream_id=None,
        target_id=None,
    )
    with semantic_writer_engine.begin() as conn:
        receipt = adopt_pdf_batch(
            conn,
            build,
            "reference-first",
            {"reference": [pa.RecordBatch.from_pylist([row], schema=stage_schema("reference"))]},
        )
        assert receipt.row_count == 1
    with semantic_writer_engine.begin() as conn:
        assert len(inspect_pdf_progress(conn, build)) == 1


def test_private_stage_denies_read_and_stale_holder(
    private_build, semantic_writer_engine, semantic_reader_engine
):
    with semantic_reader_engine.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("SELECT * FROM ops.pdf_stage_native"))
    with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError, match="stale private"):
        adopt_pdf_batch(conn, replace(private_build, holder="wrong-holder"), "stale", {})
    with semantic_writer_engine.begin() as conn:
        abandon_pdf_build(conn, private_build)
    with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError, match="not owned/open"):
        adopt_pdf_batch(conn, private_build, "after-abandon", {})


def test_malformed_wire_rolls_back_then_retry(private_build, semantic_writer_engine):
    build = private_build
    row: dict[str, Any] = dict(
        product_id=build.product_id,
        revision_id=build.revision_id,
        stream_id="s",
        ordinal=0,
        byte_offset=0,
        byte_length=3,
        body=b"abc",
        sha256_digest="0" * 64,
    )
    with semantic_writer_engine.begin() as conn, pytest.raises(psycopg.errors.CheckViolation):
        adopt_pdf_batch(
            conn,
            build,
            "parts",
            {
                "artifact_part": [
                    pa.RecordBatch.from_pylist([row], schema=stage_schema("artifact_part"))
                ]
            },
        )
    row["sha256_digest"] = sha256(b"abc").hexdigest()
    with semantic_writer_engine.begin() as conn:
        receipt = adopt_pdf_batch(
            conn,
            build,
            "parts",
            {
                "artifact_part": [
                    pa.RecordBatch.from_pylist([row], schema=stage_schema("artifact_part"))
                ]
            },
        )
        assert receipt.row_count == 1


def test_native_batch_limit_cannot_be_bypassed_by_raw_scratch(
    private_build, semantic_writer_engine
):
    build = private_build
    params = dict(
        build=build.build_id, task=build.task_id, attempt=build.attempt, holder=build.holder
    )
    with (
        semantic_writer_engine.begin() as conn,
        pytest.raises(DBAPIError, match="upload profile exceeded"),
    ):
        conn.execute(text("SELECT ops.prepare_pdf_stage(:build,:task,:attempt,:holder)"), params)
        conn.execute(
            text("""INSERT INTO pg_temp.ps_pdf_stage_native
          (product_id,revision_id,record_id,native_type,family,native_address,native_address_stream_id,scalars_json,structure_json)
          SELECT :build,:build,'large-'||i::text,'TextItem','node','#/texts/'||i::text,NULL,
          jsonb_build_object('text',repeat('x',65000)),'{}'::jsonb FROM generate_series(1,140) i
                """),
            params,
        )
        conn.execute(
            text("SELECT * FROM ops.adopt_pdf_batch(:build,:task,:attempt,:holder,'oversized')"),
            params,
        )
    with semantic_writer_engine.begin() as conn:
        assert inspect_pdf_progress(conn, build) == ()


def test_wrong_schema_and_immutable_begin_replay(private_build, semantic_writer_engine):
    build = private_build
    args = dict(
        task_id=build.task_id,
        attempt=build.attempt,
        holder=build.holder,
        release_id=build.release_id,
        source_digest=build.source_digest,
        recipe_digest=build.recipe_digest,
        schema_digest=build.schema_digest,
        replay_key="build-1",
    )
    with semantic_writer_engine.begin() as conn:
        assert begin_pdf_build(conn, **args) == build
    args["schema_digest"] = "0" * 64
    with (
        semantic_writer_engine.begin() as conn,
        pytest.raises(DBAPIError, match="source custody differs"),
    ):
        begin_pdf_build(conn, **args)


def test_reclaimed_attempt_requires_explicit_resume_and_preserves_progress(
    private_build, semantic_db_engine, semantic_writer_engine
):
    build = private_build
    with semantic_writer_engine.begin() as conn:
        receipt = adopt_pdf_batch(conn, build, "before-expiry", {"native": [native_batch(build)]})
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        task = conn.execute(
            text("SELECT run_id,method_config_id FROM ops.task WHERE id=:task"),
            {"task": build.task_id},
        ).one()
        conn.execute(
            text(
                "UPDATE ops.task SET lease_until=clock_timestamp()-interval '1 second' "
                "WHERE id=:task"
            ),
            {"task": build.task_id},
        )
    with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError, match="stale private"):
        inspect_pdf_progress(conn, build)
    with semantic_writer_engine.begin() as conn:
        claim = claim_tasks(
            conn, run_id=task.run_id, config_id=task.method_config_id, holder="next-owner"
        )[0]
        assert claim.attempt == build.attempt + 1
    with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError, match="explicit resume"):
        begin_pdf_build(
            conn,
            task_id=build.task_id,
            attempt=claim.attempt,
            holder="next-owner",
            source_digest=build.source_digest,
            recipe_digest=build.recipe_digest,
            schema_digest=build.schema_digest,
            replay_key="build-1",
        )
    with semantic_writer_engine.begin() as conn:
        resumed = resume_pdf_build(conn, build, attempt=claim.attempt, holder="next-owner")
        assert inspect_pdf_progress(conn, resumed) == (receipt,)
        assert (
            adopt_pdf_batch(conn, resumed, "before-expiry", {"native": [native_batch(resumed)]})
            == receipt
        )
    with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError, match="stale private"):
        adopt_pdf_batch(conn, build, "late-old-owner", {})


@pytest.mark.parametrize("entry", ["prepare", "adopt"])
def test_caller_scratch_cannot_execute_as_publisher_or_bypass_prepare(
    private_build, writer_with_temp_capability, entry
):
    semantic_writer_engine = writer_with_temp_capability
    build = private_build
    parameters = dict(
        build=build.build_id, task=build.task_id, attempt=build.attempt, holder=build.holder
    )
    with (
        semantic_writer_engine.begin() as conn,
        pytest.raises(DBAPIError, match="untrusted private PDF scratch"),
    ):
        conn.execute(text("CREATE TEMP TABLE ps_pdf_stage_artifact_part (forged text)"))
        conn.execute(
            text("""CREATE FUNCTION pg_temp.pdf_stage_attack() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'caller scratch trigger executed as %',current_user;
            END $$""")
        )
        conn.execute(
            text("""CREATE TRIGGER caller_attack BEFORE TRUNCATE
            ON pg_temp.ps_pdf_stage_artifact_part FOR EACH STATEMENT
            EXECUTE FUNCTION pg_temp.pdf_stage_attack()""")
        )
        if entry == "prepare":
            conn.execute(
                text("SELECT ops.prepare_pdf_stage(:build,:task,:attempt,:holder)"), parameters
            )
        else:
            conn.execute(
                text("SELECT * FROM ops.adopt_pdf_batch(:build,:task,:attempt,:holder,'forged')"),
                parameters,
            )
    with semantic_writer_engine.begin() as conn:
        assert inspect_pdf_progress(conn, build) == ()


@pytest.fixture
def writer_with_temp_capability(semantic_db_engine, semantic_writer_engine):
    # Normal workers lack TEMP. Exercise custody even if that separate privilege
    # is granted later; keep the adversary an actual restricted database role.
    with semantic_db_engine.begin() as conn:
        conn.execute(
            text("""DO $$ BEGIN EXECUTE format(
            'GRANT TEMPORARY ON DATABASE %I TO corpus_sem_writer',current_database()); END $$""")
        )
    try:
        yield semantic_writer_engine
    finally:
        with semantic_db_engine.begin() as conn:
            conn.execute(
                text("""DO $$ BEGIN EXECUTE format(
                'REVOKE TEMPORARY ON DATABASE %I FROM corpus_sem_writer',current_database());
                END $$""")
            )


@pytest.mark.parametrize("entry", ["prepare", "adopt"])
@pytest.mark.parametrize("missing", ["attempt", "holder"])
def test_direct_sql_null_identity_cannot_bypass_private_fence(
    private_build, semantic_writer_engine, entry, missing
):
    build = private_build
    parameters: dict[str, Any] = dict(
        build=build.build_id, task=build.task_id, attempt=build.attempt, holder=build.holder
    )
    with semantic_writer_engine.begin() as conn, pytest.raises(DBAPIError, match="stale private"):
        if entry == "prepare":
            parameters[missing] = None
            conn.execute(
                text("SELECT ops.prepare_pdf_stage(:build,:task,:attempt,:holder)"), parameters
            )
        else:
            conn.execute(
                text("SELECT ops.prepare_pdf_stage(:build,:task,:attempt,:holder)"), parameters
            )
            parameters[missing] = None
            conn.execute(
                text(
                    "SELECT * FROM ops.adopt_pdf_batch(:build,:task,:attempt,:holder,'null-owner')"
                ),
                parameters,
            )
    with semantic_writer_engine.begin() as conn:
        assert inspect_pdf_progress(conn, build) == ()


def test_private_encoder_failure_discards_state_and_fresh_replay_is_atomic(
    private_build, semantic_db_engine, semantic_writer_engine, monkeypatch
):
    from corpus_structure.semantic.arrow_transfer import ArrowWriteProfile

    build = private_build
    factory = ArrowWriteProfile.new_encoder
    finished = []

    class FailedEncoder:
        def __init__(self, encoder):
            self.encoder = encoder

        def write_header(self):
            return self.encoder.write_header()

        def write_batch(self, rows):
            self.encoder.write_batch(rows)
            raise ValueError("forced private encoder failure")

        def finish(self):
            finished.append(True)
            raise AssertionError("failed encoder must never be finished")

    with monkeypatch.context() as patch:
        patch.setattr(
            ArrowWriteProfile, "new_encoder", lambda profile: FailedEncoder(factory(profile))
        )
        with (
            pytest.raises(ValueError, match="forced private encoder failure"),
            semantic_writer_engine.begin() as conn,
        ):
            adopt_pdf_batch(conn, build, "encoder-replay", {"native": [native_batch(build)]})
    assert finished == []
    with semantic_writer_engine.begin() as conn:
        assert inspect_pdf_progress(conn, build) == ()
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.pdf_stage_native WHERE product_id=:p"),
                {"p": build.build_id},
            )
            == 0
        )
    with semantic_writer_engine.begin() as conn:
        receipt = adopt_pdf_batch(conn, build, "encoder-replay", {"native": [native_batch(build)]})
        assert receipt.row_count == 1
