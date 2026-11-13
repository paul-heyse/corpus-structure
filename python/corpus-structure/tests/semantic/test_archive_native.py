"""Actual restricted publication rejects changed, duplicate and foreign staged rows."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.archive_transport import archive_tables, scratch_name

from .test_native_closure import archive


def stage_exact_archive(connection, release):
    connection.execute(text("SELECT sem.prepare_release_archive(:r)"), {"r": release})
    quote = connection.dialect.identifier_preparer.quote
    for relation in archive_tables():
        connection.execute(text(
            f"INSERT INTO pg_temp.{quote(scratch_name(relation))} "
            f"SELECT * FROM sem.{quote(relation.name)} WHERE release_id=:r"
        ), {"r": release})


def test_archive_scratch_is_publisher_owned_and_exact_binary_replay_is_atomic(admitter):
    *_, prepared = archive(admitter)
    with admitter.begin() as connection:
        stage_exact_archive(connection, prepared.release_id)
        assert connection.scalar(text(
            "SELECT bool_and(relowner='corpus_sem_publisher'::regrole) FROM pg_class "
            "WHERE relnamespace=pg_my_temp_schema() AND left(relname,11)='cs_archive_'"
        )) is True
        assert connection.scalar(text("SELECT sem.publish_release_archive(:r)"),
                                 {"r": prepared.release_id}) == prepared.release_id
        for sql in ("CREATE TEMP TABLE cs_archive_extra(a text)",
                    "ALTER TABLE pg_temp.cs_archive_input ADD COLUMN injected text",
                    "UPDATE pg_temp.cs_archive_input SET content='wrong'::bytea"):
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
def test_archive_staged_damage_refuses_without_changing_finalized_archive(admitter, damage):
    *_, prepared = archive(admitter)
    with admitter.begin() as connection:
        stage_exact_archive(connection, prepared.release_id)
        if damage == "duplicate":
            connection.execute(text(
                "INSERT INTO pg_temp.cs_archive_input "
                "SELECT * FROM pg_temp.cs_archive_input LIMIT 1"
            ))
        elif damage == "foreign":
            connection.execute(text(
                "INSERT INTO pg_temp.cs_archive_input "
                "VALUES('release:foreign','source','x','x'::bytea,'wrong')"
            ))
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
                    else quote(c.name) for c in relation.columns
                )
                connection.execute(text(
                    f"INSERT INTO pg_temp.{quote(scratch_name(relation))} SELECT {columns} "
                    f"FROM sem.{quote(relation.name)} WHERE release_id=:r"
                ), {"r": prepared.release_id})
        with (
            pytest.raises(DBAPIError, match=r"scope/key differs|archive replay differs"),
            connection.begin_nested(),
        ):
            connection.execute(
                text("SELECT sem.publish_release_archive(:r)"), {"r": prepared.release_id}
            )
        assert connection.scalar(
            text("SELECT count(*) FROM sem.release_finalization WHERE release_id=:r"),
            {"r": prepared.release_id}
        ) == 1
