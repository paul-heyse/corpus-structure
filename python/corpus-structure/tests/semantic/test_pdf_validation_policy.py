"""Unfinished validation witnesses from a stale policy cannot become publications."""

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


@pytest.mark.parametrize(
    "operation", ["lookup_pdf_validation", "validate_pdf_build", "seal_pdf_build"]
)
def test_stale_final_validation_requires_fresh_derivation(
    private_build, commit_writer_engine, commit_db_engine, tmp_path, operation
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
        stale="0" * 64,
        logical="1" * 64,
        projection="2" * 64,
    )
    # First establish a real producer/oracle/final witness, then independently
    # corrupt only its policy binding under trusted fixture authority.
    # Application roles cannot manufacture or update these protected witnesses.
    validated = validate_pdf_build(commit_writer_engine, frozen)
    params.update(logical=validated.logical_digest, projection=validated.contract_digest)
    with commit_db_engine.begin() as owner:
        owner.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        assert (
            owner.execute(
                text("SELECT ops.pdf_validation_contract(:release)"), {"release": build.release_id}
            ).scalar_one()
            != params["stale"]
        )
        owner.execute(
            text(
                "UPDATE ops.pdf_build_validation SET native_contract_digest=:stale WHERE build_id=:build"
            ),
            params,
        )
    suffix = ", 'native'" if operation == "seal_pdf_build" else ""
    with (
        pytest.raises(DBAPIError, match=r"fresh.*rebuild|rebuild.*fresh"),
        commit_writer_engine.begin() as conn,
    ):
        conn.execute(
            text(f"SELECT * FROM ops.{operation}(:build,:task,:attempt,:holder,:frozen{suffix})"),
            params,
        ).all()
    with commit_db_engine.begin() as owner:
        owner.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        witness = owner.execute(
            text(
                "SELECT frozen_digest,logical_digest,contract_digest,native_contract_digest "
                "FROM ops.pdf_build_validation WHERE build_id=:build"
            ),
            params,
        ).one()
        assert tuple(witness) == (
            frozen.frozen_digest,
            params["logical"],
            params["projection"],
            params["stale"],
        )
        assert (
            owner.execute(
                text("SELECT count(*) FROM ops.pdf_published_revision WHERE build_id=:build"),
                params,
            ).scalar_one()
            == 0
        )
