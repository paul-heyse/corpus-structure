"""Explicit administrator fault injection for archive-verifier tests only."""

from contextlib import contextmanager

from sqlalchemy import text


@contextmanager
def administrative_archive_edit(conn, relation):
    """Restore archive guards after a deliberately corrupting owned-database edit."""
    if relation.schema != "sem":
        raise ValueError("archive fault injection only supports semantic archive relations")
    quote = conn.dialect.identifier_preparer.quote
    target = quote(relation.schema) + "." + quote(relation.name)
    previous = conn.scalar(text("SELECT current_user"))
    owner = conn.scalar(
        text("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=to_regclass(:name)"),
        {"name": relation.fullname},
    )
    triggers = (
        conn.execute(
            text(
                "SELECT tgname FROM pg_trigger WHERE tgrelid=to_regclass(:name) AND tgname "
                "IN ('semantic_immutable','release_finalized') AND tgenabled='O'"
            ),
            {"name": relation.fullname},
        )
        .scalars()
        .all()
    )
    conn.exec_driver_sql("SET LOCAL ROLE " + quote(owner))
    for name in triggers:
        conn.exec_driver_sql("ALTER TABLE " + target + " DISABLE TRIGGER " + quote(name))
    try:
        yield
    finally:
        for name in triggers:
            conn.exec_driver_sql("ALTER TABLE " + target + " ENABLE TRIGGER " + quote(name))
        conn.exec_driver_sql("SET LOCAL ROLE " + quote(previous))
