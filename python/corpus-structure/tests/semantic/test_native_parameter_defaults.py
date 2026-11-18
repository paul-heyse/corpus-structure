"""Execute typed native argument defaults through PostgreSQL's own call binding."""

from sqlalchemy import Boolean, Text, func, select, text

from corpus_structure.semantic.native_program import (
    Parameter,
    core_variable,
    literal,
    pg_type,
    sql_function,
)


def test_native_parameter_defaults_preserve_omission_and_explicit_values(semantic_bare_engine):
    statement = sql_function(
        "public", "native_default_control",
        parameters=(Parameter("flag", pg_type("bool"), literal(False)), Parameter("value", pg_type("text"), literal(None))),
        returns=pg_type("jsonb"),
        body=select(func.jsonb_build_array(core_variable("flag", Boolean()), core_variable("value", Text()))),
        search_path=("pg_catalog", "pg_temp"),
    )
    with semantic_bare_engine.begin() as connection:
        connection.exec_driver_sql(statement)
        assert connection.scalar(text("SELECT public.native_default_control()")) == [False, None]
        assert connection.scalar(text("SELECT public.native_default_control(true)")) == [True, None]
        assert connection.scalar(text("SELECT public.native_default_control(false,'explicit')")) == [False, "explicit"]
