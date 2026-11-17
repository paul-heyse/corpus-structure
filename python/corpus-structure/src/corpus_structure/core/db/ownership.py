"""Operation-scoped identity for disposable database acquisition.

These values describe deployment resources, not application semantic state. A reservation is
only a request; only a successful CREATE may acknowledge an owned database.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import uuid4

from pglast import ast, enums
from pglast.stream import RawStream
from sqlalchemy import Connection, Text, column, func, select, table
from sqlalchemy.dialects.postgresql import OID

_STAMP = re.compile(r"corpus-structure owned database ([0-9a-f]{32}) oid ([1-9][0-9]*)")
database_catalog = table(
    "pg_database",
    column("oid", OID()),
    column("datname", Text()),
    column("datdba", OID()),
    schema="pg_catalog",
)


@dataclass(frozen=True)
class DatabaseReservation:
    name: str
    token: str

    @classmethod
    def new(cls, name: str) -> DatabaseReservation:
        return cls(name, uuid4().hex)

    def __post_init__(self) -> None:
        if re.fullmatch(r"[0-9a-f]{32}", self.token) is None:
            raise ValueError("database creation token must be 32 lowercase hexadecimal digits")


@dataclass(frozen=True)
class OwnedDatabase:
    reservation: DatabaseReservation
    oid: int
    owner: str

    @property
    def comment(self) -> str:
        return f"corpus-structure owned database {self.reservation.token} oid {self.oid}"


@dataclass
class DatabaseCreation:
    """Mutable acknowledgement slot retained across later acquisition failures."""

    reservation: DatabaseReservation
    owned: OwnedDatabase | None = None

    def acknowledge(self, connection: Connection) -> OwnedDatabase:
        # Call only after CREATE returned successfully, never following existence or cancellation.
        oid, owner = connection.execute(
            select(database_catalog.c.oid, func.pg_catalog.pg_get_userbyid(database_catalog.c.datdba))
            .where(database_catalog.c.datname == self.reservation.name)
        ).one()
        self.owned = OwnedDatabase(self.reservation, oid, owner)
        return self.owned


def stamp_owned(connection: Connection, owned: OwnedDatabase) -> None:
    connection.exec_driver_sql(
        RawStream()(
            ast.CommentStmt(
                objtype=enums.ObjectType.OBJECT_DATABASE,
                object=ast.String(sval=owned.reservation.name),
                comment=owned.comment,
            )
        ),
        execution_options={"no_parameters": True},
    )


def acknowledged_database(
    connection: Connection, reservation: DatabaseReservation
) -> OwnedDatabase | None:
    row = connection.execute(
        select(
            database_catalog.c.oid,
            func.pg_catalog.pg_get_userbyid(database_catalog.c.datdba),
            func.pg_catalog.shobj_description(database_catalog.c.oid, "pg_database"),
        ).where(database_catalog.c.datname == reservation.name)
    ).one_or_none()
    if row is None:
        return None
    oid, owner, comment = row
    owned = OwnedDatabase(reservation, oid, owner)
    if comment != owned.comment:
        raise RuntimeError(f"refusing unauthenticated database {reservation.name!r}")
    return owned


def is_owned_stamp(comment: str | None, oid: int) -> bool:
    match = _STAMP.fullmatch(comment or "")
    return match is not None and int(match.group(2)) == oid
