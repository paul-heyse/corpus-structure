"""Physical registration deduplicates dialect callbacks without suppressing setup."""

from unittest.mock import Mock

import psycopg
from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg

from corpus_structure.core.db.store import PooledConnection


def test_repeated_dialect_initialization_preserves_isolation_and_registers_notice_once(monkeypatch):
    # Exercise the public Psycopg methods over a detached callback inventory.
    callbacks = []
    monkeypatch.setattr(psycopg.Connection, "add_notice_handler", lambda self, cb: callbacks.append(cb))
    monkeypatch.setattr(psycopg.Connection, "remove_notice_handler", lambda self, cb: callbacks.remove(cb))
    physical = object.__new__(PooledConnection)
    dialect = PGDialect_psycopg()
    dialect.isolation_level = "SERIALIZABLE"
    isolation = Mock()
    monkeypatch.setattr(dialect, "set_isolation_level", isolation)
    initialize = dialect.on_connect()
    initialize(physical)
    initialize(physical)
    assert len(callbacks) == 1
    assert isolation.call_count == 2

    reconnected = object.__new__(PooledConnection)
    callbacks.clear()
    initialize(reconnected)
    assert len(callbacks) == 1
    assert isolation.call_count == 3
