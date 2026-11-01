"""Unfinished validation witnesses from a stale policy cannot become publications."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_publication import freeze_pdf_build, prepare_pdf_build

from .test_pdf_publication import stage_complete_native
from .test_pdf_staging import private_build as private_build


@pytest.mark.parametrize(
    "operation", ["lookup_pdf_validation", "validate_pdf_build", "seal_pdf_build"]
)
def test_stale_final_validation_requires_fresh_derivation(
    private_build, semantic_writer_engine, semantic_db_engine, tmp_path, operation
):
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
        stale="0" * 64,
        logical="1" * 64,
        projection="2" * 64,
    )
    # Install an independently invalid receipt using trusted fixture authority.
    # Application roles cannot manufacture or update these protected witnesses.
    with semantic_db_engine.begin() as owner:
        owner.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        assert (
            owner.execute(
                text("SELECT ops.pdf_validation_contract(:release)"), {"release": build.release_id}
            ).scalar_one()
            != params["stale"]
        )
        owner.execute(
            text(
                "INSERT INTO ops.pdf_native_validation"
                "(build_id,frozen_digest,contract_digest,passed) "
                "VALUES(:build,:frozen,:stale,true)"
            ),
            params,
        )
        owner.execute(
            text(
                "INSERT INTO ops.pdf_build_validation"
                "(build_id,frozen_digest,logical_digest,contract_digest,"
                "native_callbacks,native_contract_digest) "
                "VALUES(:build,:frozen,:logical,:projection,true,:stale)"
            ),
            params,
        )
    suffix = ", 'native'" if operation == "seal_pdf_build" else ""
    with (
        pytest.raises(DBAPIError, match=r"fresh.*rebuild|rebuild.*fresh"),
        semantic_writer_engine.begin() as conn,
    ):
        conn.execute(
            text(f"SELECT * FROM ops.{operation}(:build,:task,:attempt,:holder,:frozen{suffix})"),
            params,
        ).all()
    with semantic_db_engine.begin() as owner:
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
