"""The record scenario seed boundary holds no consumer claim."""

from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from typing import Any, cast

import pytest
from sqlalchemy import insert, select

from corpus_structure.core.evidence import document_key
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import read_original
from semantic.native_record_fixtures import (
    RecordSourceRecipe,
    build_record_recipe,
    claim_record_source,
)
from semantic.native_record_fixtures import private_source as private_source


@pytest.mark.parametrize("private_source", [RecordSourceRecipe()], indirect=True)
def test_seed_claim_rebinds_writer_to_authenticated_clone(private_source):
    source = private_source
    assert source.clone.stage.writer is None
    assert source.writer is source.clone.writer
    with source.writer.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database())"
        ).one() == (source.clone.admin.url.database, source.clone.database_oid)


def test_record_seed_is_unclaimed_until_consumer_acquires_invocation(
    commit_db_engine, commit_writer_engine, tmp_path
):
    source = build_record_recipe(
        RecordSourceRecipe(), commit_db_engine, commit_writer_engine, tmp_path
    )
    tasks = table("ops.task")
    with commit_db_engine.connect() as conn:
        actual = conn.execute(
            select(
                tasks.c.status, tasks.c.attempt, tasks.c.claimed_by, tasks.c.invocation_key
            ).where(tasks.c.id == source.task)
        ).one()
        assert actual == ("pending", 0, None, source.invocation_key)
        assert (
            conn.scalar(select(tasks.c.status).where(tasks.c.id == source.source_task)) == "empty"
        )
    assert not hasattr(source, "held")
    assert source.writer is None
    assert source.seed_files == ()
    (tmp_path / "source.pdf").unlink()
    source.validate_clone(commit_db_engine)

    # Deliberately bypass registration's artifact retention to create a corrupt
    # file-only descriptor. Production fallback can read it; a seed must refuse it.
    unretained = b"%PDF-1.7\nunretained seed-original control"
    unretained_path = tmp_path / "unretained.pdf"
    unretained_path.write_bytes(unretained)
    content_hash = sha256(unretained).hexdigest()
    documents = table("kb.document")
    with commit_db_engine.begin() as conn:
        document = conn.execute(
            insert(documents)
            .values(
                project_id=source.project_id,
                key=document_key(source.project_id, "unretained.pdf", content_hash),
                source_uri="unretained.pdf",
                content_hash=content_hash,
                original_path=str(unretained_path),
                mime="application/pdf",
                meta={},
            )
            .returning(documents.c.id)
        ).scalar_one()
    with commit_db_engine.connect() as conn:
        assert read_original(conn, document, prepared=source.prepared) == unretained
    with pytest.raises(ValueError, match="record seed original artifact is missing"):
        replace(source, document=document).validate_clone(commit_db_engine)
    with pytest.raises(FrozenInstanceError):
        setattr(source, "task", -1)  # noqa: B010 - frozen stage runtime contract
    claimed = claim_record_source(source, commit_writer_engine)
    assert claimed.writer is commit_writer_engine
    assert claimed.held.task_id == source.task
    assert claimed.held.invocation_key == source.invocation_key
    assert claimed.task_row["status"] == "running"
    with pytest.raises(TypeError):
        cast(MutableMapping[str, Any], claimed.task_row)["status"] = "done"

    with pytest.raises(ValueError, match="record seed task is claimed or differs"):
        source.validate_clone(commit_db_engine)
