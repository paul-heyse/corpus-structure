"""Actual native custody, frozen capture and typed logical identity boundaries."""

import json
from hashlib import sha256

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_publication import (
    adopt_pdf_companion_batch,
    freeze_pdf_build,
    prepare_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.pdf_record_identity import structured_payload_scalar

from .test_pdf_publication import stage_complete_native
from .test_pdf_staging import private_build as private_build


def test_payload_forward_state_retains_previous_managed_objects():
    from corpus_structure.semantic.migrations import ALEMBIC_DIR

    before = json.loads(
        ALEMBIC_DIR.joinpath("versions/semantic_pg_20261101_native.json").read_bytes()
    )
    after = json.loads(
        ALEMBIC_DIR.joinpath("versions/semantic_pdf_20261101_native.json").read_bytes()
    )

    def identities(state):
        return {
            (
                item["identity"]["schema"],
                item["identity"]["name"],
                tuple(item["identity"]["arguments"]),
            )
            for item in state["desired"]
        }

    assert len(before["desired"]) == 10
    assert identities(before) <= identities(after)
    assert after["predecessor"] == "semantic_pg_20261101"
    assert all(item["after"] is not None for item in after["operations"])


def test_frozen_capture_includes_actual_ipc_and_logical_scalar(
    private_build, semantic_writer_engine, semantic_db_engine, tmp_path
):
    from corpus_structure.semantic.pdf_payloads import PROFILE, prepare_payload_family

    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    value = {
        "page_no": 1,
        "has_words": True,
        "has_chars": False,
        "candidates": [
            {
                "page_no": 1,
                "text": "a\x00β",
                "left": -0.0,
                "top": 1,
                "right": 2,
                "bottom": 3,
                "origin": "top_left",
                "basis": "native-font",
            }
        ],
    }
    logical = prepare_payload_family().logical_digest(value)
    with semantic_writer_engine.begin() as conn:
        adopt_pdf_companion_batch(
            conn,
            build,
            "native_metadata",
            [{"kind": "inline_candidate_pages", "ordinal": 0, "value": value}],
            "opaque-native",
        )
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
        params = dict(
            build=build.build_id,
            task=build.task_id,
            attempt=build.attempt,
            holder=build.holder,
            frozen=frozen.frozen_digest,
        )
        captured = {}
        for family in ("companion", "companion_field", "artifact_stream", "artifact_part"):
            captured[family] = (
                conn.execute(
                    text(
                        "SELECT * FROM ops.read_pdf_frozen_rows("
                        ":build,:task,:attempt,:holder,:frozen,:family,NULL,256)"
                    ),
                    params | {"family": family},
                )
                .scalars()
                .all()
            )
        stream = next(
            row for row in captured["artifact_stream"] if row["encoding_profile"] == PROFILE
        )
        assert any(row["stream_id"] == stream["stream_id"] for row in captured["artifact_part"])
        assert any(row["stream_id"] == stream["stream_id"] for row in captured["companion_field"])
        body = next(
            row["body"] for row in captured["companion"] if row["family"] == "native_metadata"
        )
        assert body["payload_logical_digest"] == logical
        assert body["page_no"] == 1
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        actual = conn.execute(
            text(
                "SELECT ops.pdf_identity_companion_scalar(:build,:build,'native_metadata',"
                "'inline_candidate_pages:0','value',CAST(:body AS jsonb))"
            ),
            {"build": build.build_id, "body": json.dumps(body)},
        ).scalar_one()
    assert actual == structured_payload_scalar(logical).encode()


def test_final_validation_freezes_projection_membership(
    private_build, semantic_writer_engine, semantic_db_engine, tmp_path
):
    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    with semantic_writer_engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(semantic_writer_engine, frozen)
    params = dict(
        build=build.build_id,
        task=build.task_id,
        attempt=build.attempt,
        holder=build.holder,
        frozen=frozen.frozen_digest,
    )
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        projection = conn.execute(
            text(
                "SELECT to_jsonb(a)-'product_id'-'revision_id' FROM kb.pdf_record_access a "
                "WHERE product_id=:build LIMIT 1"
            ),
            params,
        ).scalar_one()
        contract, recorded = conn.execute(
            text(
                "SELECT ops.pdf_validation_contract(:release),v.native_contract_digest "
                "FROM ops.pdf_build_validation v WHERE build_id=:build"
            ),
            params | {"release": build.release_id},
        ).one()
        assert contract == recorded
        old_single_source = conn.execute(
            text(
                "SELECT content FROM sem.input WHERE release_id=:release "
                "AND input_kind='dependency' "
                "AND input_name='execution/implementation/pdf/publication.py'"
            ),
            {"release": build.release_id},
        ).scalar_one()
        assert recorded != sha256(old_single_source).hexdigest()
    with semantic_writer_engine.begin() as conn:
        conn.execute(
            text(
                "SELECT ops.adopt_pdf_access(:build,:task,:attempt,:holder,:frozen,'access',"
                "CAST(:body AS jsonb))"
            ),
            params | {"body": json.dumps(projection)},
        )
    with (
        pytest.raises(DBAPIError, match="projection membership is immutable"),
        semantic_writer_engine.begin() as conn,
    ):
        conn.execute(
            text(
                "SELECT ops.adopt_pdf_access(:build,:task,:attempt,:holder,:frozen,'access',"
                "CAST(:body AS jsonb))"
            ),
            params | {"body": json.dumps(projection | {"pointer": "#/unexpected"})},
        )


def test_projection_finalization_serializes_on_build_without_blocking_heartbeat(
    private_build, semantic_writer_engine, semantic_db_engine, tmp_path
):
    from corpus_structure.semantic.operations import renew_claim

    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    with semantic_writer_engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    params = dict(
        build=build.build_id,
        task=build.task_id,
        attempt=build.attempt,
        holder=build.holder,
        frozen=frozen.frozen_digest,
    )
    with semantic_db_engine.begin() as owner:
        owner.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        owner.execute(
            text("SELECT 1 FROM ops.pdf_stage_build WHERE build_id=:build FOR NO KEY UPDATE"),
            params,
        )
        # All three mutations contend on the same build row before observing validation
        # membership/state; validation cannot finalize between an append's check and write.
        for statement in (
            "SELECT ops.adopt_pdf_access(:build,:task,:attempt,:holder,:frozen,'access',"
            "'{}'::jsonb)",
            "SELECT ops.validate_pdf_build(:build,:task,:attempt,:holder,:frozen)",
            "SELECT ops.seal_pdf_build(:build,:task,:attempt,:holder,:frozen,'native')",
        ):
            with (
                pytest.raises(DBAPIError, match="lock timeout"),
                semantic_writer_engine.begin() as conn,
            ):
                conn.exec_driver_sql("SET LOCAL lock_timeout='100ms'")
                conn.execute(text(statement), params)
        with semantic_writer_engine.begin() as heartbeat:
            heartbeat.exec_driver_sql("SET LOCAL lock_timeout='100ms'")
            renew_claim(
                heartbeat, task_id=build.task_id, attempt=build.attempt, holder=build.holder
            )
