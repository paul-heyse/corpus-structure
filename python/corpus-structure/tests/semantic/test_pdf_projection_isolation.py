"""Projection admission rejects a stale snapshot before waiting for the build fence."""

import json

import pytest
from pdf_acceptance_support import stage_complete_native
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_publication import (
    freeze_pdf_build,
    prepare_pdf_build,
    validate_pdf_build,
)
from semantic.pdf_staging_support import private_build as private_build


@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "READ COMMITTED"])
def test_projection_write_requires_fresh_validation_snapshot(
    private_build, commit_writer_engine, commit_db_engine, tmp_path, isolation
):
    build = private_build
    stage_complete_native(commit_writer_engine, build, tmp_path)
    with commit_writer_engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    params = dict(
        build=build.build_id,
        task=build.task_id,
        attempt=build.attempt,
        holder=build.holder,
        frozen=frozen.frozen_digest,
    )
    lookup = text(
        "SELECT count(*) FROM ops.lookup_pdf_validation(:build,:task,:attempt,:holder,:frozen)"
    )
    adopt = text(
        "SELECT ops.adopt_pdf_access(:build,:task,:attempt,:holder,:frozen,'access',"
        "CAST(:body AS jsonb))"
    )
    with (
        commit_writer_engine.connect().execution_options(isolation_level=isolation) as conn,
        conn.begin(),
    ):
        # Establish the reader snapshot before the independent validator commits.
        assert conn.execute(lookup, params).scalar_one() == 0
        validate_pdf_build(commit_writer_engine, frozen)
        with commit_db_engine.begin() as owner:
            owner.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
            body = owner.execute(
                text(
                    "SELECT to_jsonb(r)-'product_id'-'revision_id' "
                    "FROM kb.pdf_record_access r WHERE product_id=:build "
                    "AND revision_id=:build AND pointer='#/texts/0'"
                ),
                params,
            ).scalar_one()
        if isolation == "REPEATABLE READ":
            # The original race precondition is real: a finalized witness is
            # committed, while this transaction continues to miss that row.
            assert conn.execute(lookup, params).scalar_one() == 0
            with commit_db_engine.begin() as blocker:
                blocker.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
                blocker.execute(
                    text(
                        "SELECT build_id FROM ops.pdf_stage_build "
                        "WHERE build_id=:build FOR NO KEY UPDATE"
                    ),
                    params,
                ).one()
                conn.exec_driver_sql("SET LOCAL lock_timeout='100ms'")
                with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                    conn.execute(adopt, params | {"body": json.dumps(body)})
                # An isolation refusal must happen before acquiring the fence;
                # a late guard would block here and report lock timeout 55P03.
                assert getattr(refused.value.orig, "sqlstate", None) == "25000"
            return
        # READ COMMITTED observes the newly finalized witness and preserves
        # both exact replay and refusal of new post-validation membership.
        assert conn.execute(lookup, params).scalar_one() == 1
        conn.execute(adopt, params | {"body": json.dumps(body)})
        with (
            pytest.raises(DBAPIError, match="projection membership is immutable"),
            conn.begin_nested(),
        ):
            conn.execute(adopt, params | {"body": json.dumps(body | {"pointer": "#/late"})})
