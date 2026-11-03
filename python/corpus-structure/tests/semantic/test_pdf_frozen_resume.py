"""A reclaimed frozen build changes invocation ownership without reopening its snapshot."""

from dataclasses import replace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.operations import claim_tasks
from corpus_structure.semantic.pdf_publication import (
    freeze_pdf_build,
    inspect_pdf_build,
    prepare_pdf_build,
    seal_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.pdf_staging import (
    abandon_pdf_build,
    adopt_pdf_batch,
    resume_pdf_build,
)

from .pdf_staging_support import private_build as private_build
from .test_pdf_publication import stage_complete_native


def snapshot(engine, build):
    with engine.connect() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        bindings = dict(
            conn.execute(
                text("""
          SELECT b.build_id,b.task_id,b.release_id,b.source_digest,b.recipe_digest,b.schema_digest,
                 b.state,f.frozen_digest,f.kind
          FROM ops.pdf_stage_build b JOIN ops.pdf_frozen_build f USING(build_id)
          WHERE b.build_id=:build
        """),
                {"build": build.build_id},
            )
            .mappings()
            .one()
        )
        native = (
            conn.execute(
                text("""
          SELECT to_jsonb(n) FROM ops.pdf_stage_native n WHERE product_id=:build
          ORDER BY record_id
        """),
                {"build": build.build_id},
            )
            .scalars()
            .all()
        )
        receipts = conn.execute(
            text("""
          SELECT replay_key,content_digest,row_count FROM ops.pdf_stage_receipt
          WHERE build_id=:build ORDER BY replay_key
        """),
            {"build": build.build_id},
        ).all()
        return bindings, native, receipts


def test_frozen_reclaim_changes_owner_only_and_can_finish_same_snapshot(
    private_build, semantic_db_engine, semantic_writer_engine, tmp_path
):
    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    with semantic_writer_engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
    before = snapshot(semantic_db_engine, build)
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        task = conn.execute(
            text("SELECT run_id,method_config_id FROM ops.task WHERE id=:task"),
            {"task": build.task_id},
        ).one()
        conn.execute(
            text("""
          UPDATE ops.task SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:task
        """),
            {"task": build.task_id},
        )
    with semantic_writer_engine.begin() as conn:
        claim = claim_tasks(
            conn, run_id=task.run_id, config_id=task.method_config_id, holder="frozen-successor"
        )[0]
        assert claim.attempt == build.attempt + 1
        resumed = resume_pdf_build(conn, build, attempt=claim.attempt, holder=claim.holder)
        actual = inspect_pdf_build(
            conn,
            task_id=build.task_id,
            attempt=claim.attempt,
            holder=claim.holder,
            replay_key="build-1",
        )
        assert actual is not None and actual.state == "frozen"
        assert actual.frozen == replace(frozen, build=resumed)
    assert snapshot(semantic_db_engine, build) == before
    # Rebinding grants no append capability and cannot reactivate the stale owner.
    with pytest.raises(DBAPIError, match="not owned/open"), semantic_writer_engine.begin() as conn:
        adopt_pdf_batch(conn, resumed, "after-freeze", {})
    with pytest.raises(DBAPIError, match="stale private"), semantic_writer_engine.begin() as conn:
        resume_pdf_build(conn, build, attempt=build.attempt, holder=build.holder)
    resumed_frozen = replace(frozen, build=resumed)
    with semantic_writer_engine.begin() as conn:
        prepare_pdf_build(conn, resumed_frozen)
    outcome = validate_pdf_build(semantic_writer_engine, resumed_frozen)
    with semantic_writer_engine.begin() as conn:
        published = seal_pdf_build(conn, resumed_frozen, "native")
    assert published.build_id == build.build_id
    assert published.frozen_digest == frozen.frozen_digest
    assert published.logical_digest == outcome.logical_digest
    with (
        pytest.raises(DBAPIError, match="resume binding differs"),
        semantic_writer_engine.begin() as conn,
    ):
        resume_pdf_build(conn, resumed, attempt=claim.attempt, holder=claim.holder)


def test_resume_cannot_rebind_an_abandoned_build(private_build, semantic_writer_engine):
    build = private_build
    with semantic_writer_engine.begin() as conn:
        abandon_pdf_build(conn, build)
    with (
        pytest.raises(DBAPIError, match="resume binding differs"),
        semantic_writer_engine.begin() as conn,
    ):
        resume_pdf_build(conn, build, attempt=build.attempt, holder=build.holder)
