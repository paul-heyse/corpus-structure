"""Connection lifetime and driver controls for invocation-owned SQLite stores."""

from os import PathLike

from sqlalchemy import URL, Connection, create_engine
from sqlalchemy.pool import NullPool


def open_scratch(path: str | PathLike[str]) -> Connection:
    """Open a private session whose DBAPI connection ends when the owner closes it."""
    return create_engine(URL.create("sqlite", database=str(path)), poolclass=NullPool).connect()


def seal_reads(connection: Connection) -> None:
    """Make the current scratch session read-only, including direct driver writes."""
    connection.exec_driver_sql("PRAGMA query_only=ON")
