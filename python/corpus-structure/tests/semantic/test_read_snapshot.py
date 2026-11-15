"""Actual PostgreSQL transaction and cancellation ownership for catalog reads."""

from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.semantic.read_snapshot import read_snapshot


@pytest.mark.parametrize("through_store", [False, True])
def test_catalog_snapshot_is_repeatable_read_readonly_and_returns_connection_cleanly(infrastructure_engine, through_store):
    selected = SimpleNamespace(engine=infrastructure_engine) if through_store else infrastructure_engine
    cancellation = BorrowerCancellation()
    with read_snapshot(selected, cancellation=cancellation) as connection:
        assert connection.get_isolation_level() == "REPEATABLE READ"
        assert connection.scalar(text("SHOW transaction_read_only")) == "on"
        with pytest.raises(DBAPIError) as refused:
            connection.execute(text("CREATE SCHEMA read_snapshot_must_refuse"))
        cause = refused.value.orig
        assert isinstance(cause, psycopg.Error)
        assert cause.sqlstate == "25006"
    with infrastructure_engine.connect() as next_connection:
        assert next_connection.get_isolation_level() == "READ COMMITTED"
        assert next_connection.scalar(text("SHOW transaction_read_only")) == "off"
