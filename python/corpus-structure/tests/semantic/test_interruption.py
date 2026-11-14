"""A lost native connection before outer COMMIT must discard both data and receipt."""

from __future__ import annotations

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import PublicationBatch, publish_on_connection
from corpus_structure.semantic.releases import activate_release, persist_release


def test_native_disconnect_before_outer_commit_discards_receipt(
    commit_db_engine, commit_writer_engine
):
    bundle = SourceBundle(
        "interrupt",
        (
            SourceArtifact(
                "interrupt",
                b"""id: https://example.org/interruption
name: interruption
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
classes: {Thing: {}}
""",
            ),
        ),
    )
    dependencies = composed_dependencies(ResolvedDependencies())
    profile = PreparationProfile(version="semantic-2")
    release = prepare_release(bundle, dependencies, profile)
    with commit_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, release)
        conn.execute(insert(table("data.project")).values(project_id="p"))
        activate_release(conn, "p", release.release_id, expected_parent=None, expected_generation=0)
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="r", project_id="p", release_id=release.release_id
            )
        )
    with (
        pytest.raises(DBAPIError),
        commit_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        receipt = publish_on_connection(
            conn, PublicationBatch(release.release_id, "r", "interrupted")
        )
        assert receipt.data_revision == 1  # a function result is still private to this transaction
        driver = conn.connection.driver_connection
        assert driver is not None
        driver.close()
    with commit_db_engine.connect() as conn:
        assert conn.execute(select(table("data.batch"))).all() == []
        assert conn.execute(select(table("data.realization").c.data_revision)).scalar_one() == 0
