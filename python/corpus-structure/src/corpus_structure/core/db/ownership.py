"""Operation-scoped identity for disposable database acquisition.

These values describe deployment resources, not application semantic state. A reservation is
only a request; only a successful CREATE may acknowledge an owned database.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import Connection, text

_STAMP = re.compile(r"corpus-structure owned database ([0-9a-f]{32}) oid ([1-9][0-9]*)")


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
            text("SELECT oid,pg_get_userbyid(datdba) FROM pg_database WHERE datname=:name"),
            {"name": self.reservation.name},
        ).one()
        self.owned = OwnedDatabase(self.reservation, oid, owner)
        return self.owned


def stamp_owned(connection: Connection, owned: OwnedDatabase) -> None:
    quote = connection.dialect.identifier_preparer.quote
    # COMMENT does not accept a bound value. The comment contains only a fixed prefix, hex and int.
    connection.exec_driver_sql(
        f"COMMENT ON DATABASE {quote(owned.reservation.name)} IS '{owned.comment}'"
    )


def acknowledged_database(
    connection: Connection, reservation: DatabaseReservation
) -> OwnedDatabase | None:
    row = connection.execute(
        text(
            "SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') "
            "FROM pg_database WHERE datname=:name"
        ),
        {"name": reservation.name},
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
