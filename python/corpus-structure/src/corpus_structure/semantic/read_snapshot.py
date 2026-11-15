"""Borrow one repeatable read-only PostgreSQL snapshot for catalog and pure reads."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager, nullcontext
from typing import Protocol

from sqlalchemy import Connection, Engine

from corpus_structure.core.db.lifetime import BorrowerCancellation


class _Store(Protocol):
    engine: Engine


@contextmanager
def read_snapshot(
    store: Engine | _Store, *, cancellation: BorrowerCancellation | None = None
) -> Generator[Connection]:
    """One read-only snapshot opener, including SQLAlchemy/psycopg reset ownership."""
    engine = store if isinstance(store, Engine) else store.engine
    with (
        engine.connect().execution_options(
            isolation_level="REPEATABLE READ", postgresql_readonly=True
        ) as conn,
        cancellation.borrow(conn) if cancellation is not None else nullcontext(),
        conn.begin(),
    ):
        yield conn
        if cancellation is not None:
            cancellation.check_active()

