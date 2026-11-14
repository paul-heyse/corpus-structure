"""Infrastructure connections retain each declared purpose's authenticated identity."""

import os

import pytest

from native_test_support import principal_engine, semantic_principals


@pytest.mark.parametrize("purpose", ("write", "read", "evaluate", "fit", "admit"))
def test_infrastructure_purpose_uses_its_actual_restricted_login(
    native_settings, native_server, infrastructure_engine, purpose
):
    native_server.check_roles(semantic_principals())
    database = infrastructure_engine.url.database
    assert database is not None
    engine = principal_engine(native_settings, purpose, database)
    try:
        with engine.connect() as connection:
            principal, login, superuser, createdb, createrole, replication, bypass, port = (
                connection.exec_driver_sql(
                    "SELECT current_user,session_user,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,"
                    "current_setting('port')::int FROM pg_roles WHERE rolname=current_user"
                ).one()
            )
        assert (principal, login) == (semantic_principals()[purpose],) * 2
        assert (superuser, createdb, createrole, replication, bypass) == (False,) * 5
        if os.environ.get("CORPUS_CI_NATIVE_HOST", "shared") == "private":
            assert port not in {5432, 5434}
    finally:
        engine.dispose()
