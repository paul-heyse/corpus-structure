"""Actual restricted publication rejects changed, duplicate and foreign staged rows."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.archive_transport import archive_tables, scratch_name
from semantic.native_closure_support import archive


def stage_exact_archive(connection, release):
    connection.execute(text("SELECT sem.prepare_release_archive(:r)"), {"r": release})
    quote = connection.dialect.identifier_preparer.quote
    for relation in archive_tables():
        connection.execute(
            text(
                f"INSERT INTO pg_temp.{quote(scratch_name(relation))} "
                f"SELECT * FROM sem.{quote(relation.name)} WHERE release_id=:r"
            ),
            {"r": release},
        )


def test_archive_scratch_is_publisher_owned_and_exact_binary_replay_is_atomic(
    commit_admitter_engine,
):
    *_, prepared = archive(commit_admitter_engine)
    with commit_admitter_engine.begin() as connection:
        stage_exact_archive(connection, prepared.release_id)
        assert (
            connection.scalar(
                text(
                    "SELECT bool_and(relowner='corpus_sem_publisher'::regrole) FROM pg_class "
                    "WHERE relnamespace=pg_my_temp_schema() AND left(relname,11)='cs_archive_'"
                )
            )
            is True
        )
        assert (
            connection.scalar(
                text("SELECT sem.publish_release_archive(:r)"), {"r": prepared.release_id}
            )
            == prepared.release_id
        )
        for sql in (
            "CREATE TEMP TABLE cs_archive_extra(a text)",
            "ALTER TABLE pg_temp.cs_archive_input ADD COLUMN injected text",
            "UPDATE pg_temp.cs_archive_input SET content='wrong'::bytea",
        ):
            with pytest.raises(DBAPIError), connection.begin_nested():
                connection.execute(text(sql))
        # Reuse within the transaction empties every stream, and requires full closure again.
        connection.execute(
            text("SELECT sem.prepare_release_archive(:r)"), {"r": prepared.release_id}
        )
        with pytest.raises(DBAPIError, match="one complete release"), connection.begin_nested():
            connection.execute(
                text("SELECT sem.publish_release_archive(:r)"), {"r": prepared.release_id}
            )


@pytest.mark.parametrize("damage", ["duplicate", "foreign", "binary"])
def test_archive_staged_damage_refuses_without_changing_finalized_archive(
    commit_admitter_engine, damage
):
    *_, prepared = archive(commit_admitter_engine)
    with commit_admitter_engine.begin() as connection:
        stage_exact_archive(connection, prepared.release_id)
        if damage == "duplicate":
            connection.execute(
                text(
                    "INSERT INTO pg_temp.cs_archive_input "
                    "SELECT * FROM pg_temp.cs_archive_input LIMIT 1"
                )
            )
        elif damage == "foreign":
            connection.execute(
                text(
                    "INSERT INTO pg_temp.cs_archive_input "
                    "VALUES('release:foreign','source','x','x'::bytea,'wrong')"
                )
            )
        else:
            # INSERT authority cannot replace existing rows. Prepare again and stream one
            # altered relation while retaining the complete other original typed rows.
            connection.execute(
                text("SELECT sem.prepare_release_archive(:r)"), {"r": prepared.release_id}
            )
            quote = connection.dialect.identifier_preparer.quote
            for relation in archive_tables():
                columns = ",".join(
                    "content||decode('00','hex')"
                    if relation.name == "input" and c.name == "content"
                    else quote(c.name)
                    for c in relation.columns
                )
                connection.execute(
                    text(
                        f"INSERT INTO pg_temp.{quote(scratch_name(relation))} SELECT {columns} "
                        f"FROM sem.{quote(relation.name)} WHERE release_id=:r"
                    ),
                    {"r": prepared.release_id},
                )
        with (
            pytest.raises(DBAPIError, match=r"scope/key differs|archive replay differs"),
            connection.begin_nested(),
        ):
            connection.execute(
                text("SELECT sem.publish_release_archive(:r)"), {"r": prepared.release_id}
            )
        assert (
            connection.scalar(
                text("SELECT count(*) FROM sem.release_finalization WHERE release_id=:r"),
                {"r": prepared.release_id},
            )
            == 1
        )


def test_generated_archive_program_executes_with_actual_admitter_custody(native_rollback):
    from sqlalchemy import select

    from corpus_structure.semantic.archive_native import archive_native_definitions
    from corpus_structure.semantic.metadata import metadata, table
    from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
    from corpus_structure.semantic.releases import persist_release
    from semantic.data_operation_kernel_support import STORAGE, prepare_kernel

    connection = native_rollback.connection
    captured = prepare_kernel(STORAGE)
    persist_release(
        connection, captured.bundle, captured.dependencies, captured.profile, captured.prepared
    )
    expected_digest = connection.scalar(
        select(table("sem.release").c.content_digest).where(
            table("sem.release").c.release_id == captured.prepared.release_id
        )
    )
    definitions = archive_native_definitions(connection, target_metadata=metadata)
    assert {item.identity.name: item.grants for item in definitions} == {
        "require_archive_scratch": (),
        "prepare_release_archive": (("corpus_sem_admitter", "EXECUTE", False),),
        "publish_release_archive": (("corpus_sem_admitter", "EXECUTE", False),),
    }
    with native_owner(connection, "corpus_sem_publisher"):
        for definition in definitions:
            for statement in definition.install_sql:
                execute_native_sql(connection, statement)
    release = captured.prepared.release_id
    with native_owner(connection, "corpus_sem_admitter"):
        stage_exact_archive(connection, release)
        assert (
            connection.scalar(text("SELECT sem.publish_release_archive(:r)"), {"r": release})
            == release
        )
        # A second prepare truncates existing protected scratch; its exact
        # typed replay still succeeds after all source rows are streamed again.
        stage_exact_archive(connection, release)
        assert (
            connection.scalar(text("SELECT sem.publish_release_archive(:r)"), {"r": release})
            == release
        )
        with (
            pytest.raises(DBAPIError, match="scope/key differs"),
            connection.begin_nested(),
        ):
            connection.execute(
                text(
                    "INSERT INTO pg_temp.cs_archive_input SELECT * FROM pg_temp.cs_archive_input LIMIT 1"
                )
            )
            connection.execute(text("SELECT sem.publish_release_archive(:r)"), {"r": release})
    finalized = table("sem.release_finalization")
    assert (
        connection.scalar(
            select(finalized.c.content_digest).where(finalized.c.release_id == release)
        )
        == expected_digest
    )
    with (
        pytest.raises(DBAPIError),
        connection.begin_nested(),
        native_owner(connection, "corpus_sem_writer"),
    ):
        connection.execute(text("SELECT sem.prepare_release_archive(:r)"), {"r": release})
