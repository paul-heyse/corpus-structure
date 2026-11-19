"""Binding deadlines preserve the caller and recover after an actual native timeout."""

from typing import cast

import pytest
from psycopg.errors import QueryCanceled
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import data_operation_bindings as bindings
from corpus_structure.settings import DatabaseSettings


def test_binding_deadline_is_scoped_and_keeps_stricter_caller(native_read, monkeypatch):
    connection = native_read
    monkeypatch.setattr(
        connection.engine,
        "_corpus_database_settings",
        DatabaseSettings(binding_statement_timeout_seconds=0.1),
        raising=False,
    )
    connection.execute(select(func.set_config("statement_timeout", "50ms", True)))
    connection.execute(select(func.set_config("lock_timeout", "20ms", True)))
    observed = []
    expected = object()

    def read(conn, compiled):
        observed.append(
            conn.execute(
                select(
                    func.current_setting("statement_timeout"), func.current_setting("lock_timeout")
                )
            ).one()
        )
        return expected

    monkeypatch.setattr(bindings, "_execute_binding", read)
    compiled = cast(bindings.CompiledBinding, object())
    assert bindings.execute_binding(connection, compiled) is expected
    assert tuple(observed[0]) == ("50ms", "20ms")
    assert tuple(
        connection.execute(
            select(func.current_setting("statement_timeout"), func.current_setting("lock_timeout"))
        ).one()
    ) == ("50ms", "20ms")


def test_binding_timeout_rolls_back_only_the_owned_savepoint(native_read, monkeypatch):
    connection = native_read
    monkeypatch.setattr(
        connection.engine,
        "_corpus_database_settings",
        DatabaseSettings(binding_statement_timeout_seconds=0.03),
        raising=False,
    )
    connection.execute(select(func.set_config("statement_timeout", "2s", True)))
    connection.execute(select(func.set_config("lock_timeout", "500ms", True)))

    def slow_read(conn, compiled):
        return conn.scalar(select(func.pg_sleep(0.2)))

    monkeypatch.setattr(bindings, "_execute_binding", slow_read)
    with pytest.raises(DBAPIError) as refusal:
        bindings.execute_binding(connection, cast(bindings.CompiledBinding, object()))
    assert isinstance(refusal.value.orig, QueryCanceled)
    assert refusal.value.orig.sqlstate == "57014"
    assert tuple(
        connection.execute(
            select(func.current_setting("statement_timeout"), func.current_setting("lock_timeout"))
        ).one()
    ) == ("2s", "500ms")
    assert connection.scalar(select(1)) == 1
