"""Generated publication controls preserve native lookup and projection custody."""

import json

import pytest
from pdf_acceptance_support import stage_complete_native
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
from corpus_structure.semantic.pdf_publication_native import (
    pdf_freeze_native_sql,
    pdf_publication_controls_sql,
)
from semantic.pdf_staging_support import private_build as private_build


def test_generated_publication_controls_keep_writer_fences(native_rollback):
    connection = native_rollback.connection
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, pdf_freeze_native_sql(get_metadata()))
        execute_native_sql(connection, pdf_publication_controls_sql(get_metadata()))
    calls = (
        ("ops.stage_pdf_access_batch(NULL,NULL,NULL,NULL,'[]'::jsonb)", "P0004"),
        ("ops.lookup_pdf_build(NULL,NULL,NULL,NULL)", "P0004"),
        ("ops.lookup_pdf_frozen_digest(NULL,NULL,NULL,NULL)", "P0004"),
        ("ops.lookup_pdf_frozen_kind(NULL,NULL,NULL,NULL)", "P0004"),
        ("ops.lookup_pdf_validation(NULL,NULL,NULL,NULL,NULL)", "P0002"),
        ("ops.lookup_pdf_published_build(NULL,NULL,NULL,NULL)", "P0004"),
    )
    with native_owner(connection, "corpus_sem_writer"):
        for call, expected in calls:
            with pytest.raises(DBAPIError) as failure, connection.begin_nested():
                connection.execute(text("SELECT * FROM " + call)).all()
            assert getattr(failure.value.orig, "sqlstate", None) == expected, call


def test_generated_lookups_and_access_admission_keep_actual_private_pins(
    private_build, commit_db_engine, commit_writer_engine, tmp_path
):
    build = private_build
    with commit_db_engine.begin() as connection, native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, pdf_publication_controls_sql(get_metadata()))
    parameters = {
        "build": build.build_id,
        "task": build.task_id,
        "attempt": build.attempt,
        "holder": build.holder,
        "key": "product:native",
    }
    with commit_writer_engine.begin() as connection:
        retained = (
            connection.execute(
                text("SELECT * FROM ops.lookup_pdf_build(:task,:attempt,:holder,:key)"), parameters
            )
            .mappings()
            .one()
        )
        assert retained["build_id"] == build.build_id
        assert retained["release_id"] == build.release_id
        assert (
            connection.execute(
                text("SELECT * FROM ops.lookup_pdf_build(:task,:attempt,:holder,'missing')"),
                parameters,
            ).all()
            == []
        )
        assert (
            connection.scalar(
                text("SELECT ops.lookup_pdf_frozen_digest(:build,:task,:attempt,:holder)"),
                parameters,
            )
            is None
        )
        assert (
            connection.scalar(
                text("SELECT ops.lookup_pdf_frozen_kind(:build,:task,:attempt,:holder)"), parameters
            )
            is None
        )
        assert (
            connection.execute(
                text("SELECT * FROM ops.lookup_pdf_published_build(:build,:task,:attempt,:holder)"),
                parameters,
            ).all()
            == []
        )
    stage_complete_native(commit_writer_engine, build, tmp_path)
    with commit_db_engine.connect() as connection:
        original = connection.scalar(
            text(
                "SELECT to_jsonb(r)-'product_id'-'revision_id' FROM ops.pdf_stage_access r WHERE product_id=:build AND revision_id=:build ORDER BY pointer LIMIT 1"
            ),
            parameters,
        )
    packet = [{"family": "access", "body": original}]
    query = text(
        "SELECT ops.stage_pdf_access_batch(:build,:task,:attempt,:holder,CAST(:rows AS jsonb))"
    )
    with commit_writer_engine.begin() as connection:
        connection.execute(query, {**parameters, "rows": json.dumps(packet)}).one()
    packet[0]["body"] = {**original, "native_json": {"conflicting": True}}
    with (
        commit_writer_engine.begin() as connection,
        pytest.raises(DBAPIError, match="changed access projection") as failure,
    ):
        connection.execute(query, {**parameters, "rows": json.dumps(packet)}).one()
    assert getattr(failure.value.orig, "sqlstate", None) == "23514"
