"""Explicit fixture-only restoration of independent finished-result metadata."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Connection, Table, text


@contextmanager
def restore_finished_metadata(conn: Connection, relation: Table) -> Generator[None]:
    """Restore retained terminal metadata without granting a production write capability.

    Keep foreign keys/checks active. Only the named table's enabled user triggers pause;
    ownership, trigger state and role are restored before any acceptance operation runs.
    """
    if relation.schema is None or relation.fullname not in {
        "ops.run",
        "ops.input_cut",
        "ops.completed_result",
    }:
        raise ValueError("only finished-result fixture metadata can be restored")
    quote = conn.dialect.identifier_preparer.quote
    previous = conn.scalar(text("SELECT current_user"))
    owner = conn.scalar(
        text("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=to_regclass(:name)"),
        {"name": relation.fullname},
    )
    triggers = (
        conn.execute(
            text(
                "SELECT tgname FROM pg_trigger WHERE tgrelid=to_regclass(:name) "
                "AND NOT tgisinternal AND tgenabled='O'"
            ),
            {"name": relation.fullname},
        )
        .scalars()
        .all()
    )
    target = quote(relation.schema) + "." + quote(relation.name)
    conn.exec_driver_sql("SET LOCAL ROLE " + quote(owner))
    for name in triggers:
        conn.exec_driver_sql("ALTER TABLE " + target + " DISABLE TRIGGER " + quote(name))
    try:
        yield
    finally:
        for name in triggers:
            conn.exec_driver_sql("ALTER TABLE " + target + " ENABLE TRIGGER " + quote(name))
        conn.exec_driver_sql("SET LOCAL ROLE " + quote(previous))
