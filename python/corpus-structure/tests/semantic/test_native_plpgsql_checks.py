"""Real PostgreSQL authoring checks, with no persistent checker installation."""

import pytest
from sqlalchemy import text

from corpus_structure.semantic.native_objects import (
    NativeAuthoringError,
    definition_from_sql,
    prepare_native_authoring,
)


def definition(connection, name, arguments, returns, body, *, language="plpgsql"):
    return definition_from_sql(
        connection,
        f"""CREATE OR REPLACE FUNCTION checker_test.{name}({arguments})
        RETURNS {returns} LANGUAGE {language} SET search_path=pg_catalog,pg_temp
        AS $body${body}$body$""",
        source=f"checker-control:{name}",
        owner=connection.scalar(text("SELECT current_user")),
    )


def checker(connection):
    return connection.execute(
        text("""SELECT e.extversion,n.nspname FROM pg_extension e
        JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='plpgsql_check'""")
    ).all()


@pytest.mark.parametrize(
    ("returns", "expression", "state"),
    [
        ("jsonb", "selected->'key' - 'version'", "42725"),
        ("boolean", "'{}'::jsonb <@ selected->'dependencies'", "42883"),
    ],
)
def test_precedence_errors_refused_before_registration(
    semantic_bare_engine, returns, expression, state
):
    with semantic_bare_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("CREATE SCHEMA checker_test")
        before = checker(connection)
        selected = definition(
            connection,
            "bad",
            "selected jsonb",
            returns,
            "BEGIN RETURN " + expression + "; END",
        )
        # PostgreSQL CREATE and catalog normalization alone accept these bodies.
        assert prepare_native_authoring(connection, (selected,), owned_authoring=True).desired
        with pytest.raises(
            NativeAuthoringError, match=r"checker_test.bad\(jsonb\).*SQLSTATE " + state
        ):
            prepare_native_authoring(
                connection,
                (selected,),
                owned_authoring=True,
                check_plpgsql=frozenset({selected.identity}),
            )
        assert checker(connection) == before
        assert connection.scalar(text("SELECT to_regprocedure('checker_test.bad(jsonb)')")) is None


def test_later_dependency_warnings_and_rollback(semantic_bare_engine):
    with semantic_bare_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("CREATE SCHEMA checker_test")
        before = checker(connection)
        selected = definition(
            connection,
            "first",
            "n integer",
            "integer",
            "DECLARE unused integer; BEGIN RETURN checker_test.later(n); END",
        )
        later = definition(
            connection,
            "later",
            "n integer",
            "integer",
            "SELECT n + 1",
            language="sql",
        )
        result = prepare_native_authoring(
            connection,
            (selected, later),
            owned_authoring=True,
            check_plpgsql=frozenset({selected.identity, later.identity}),
        )
        assert [item.identity for item in result.desired] == [selected.identity, later.identity]
        assert result.desired[0].catalog["owner"] == selected.owner
        assert all("plpgsql_check" not in item.catalog_json for item in result.desired)
        assert checker(connection) == before
        assert (
            connection.scalar(text("SELECT to_regprocedure('checker_test.first(integer)')")) is None
        )


def test_existing_checker_schema_and_acl_preserved(semantic_bare_engine):
    with semantic_bare_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("CREATE SCHEMA checker_test")
        connection.exec_driver_sql("CREATE SCHEMA checker_extension")
        connection.exec_driver_sql(
            "CREATE EXTENSION plpgsql_check WITH SCHEMA checker_extension VERSION '2.10'"
        )
        before = checker(connection)
        selected = definition(connection, "valid", "n integer", "integer", "BEGIN RETURN n; END")
        result = prepare_native_authoring(
            connection,
            (selected,),
            owned_authoring=True,
            check_plpgsql=frozenset({selected.identity}),
        )
        assert checker(connection) == before == [("2.10", "checker_extension")]
        assert result.desired[0].catalog["acl"] == [[selected.owner, "EXECUTE", False]]


@pytest.mark.parametrize(
    ("arguments", "returns", "body"),
    [
        ("n anyelement", "anyelement", "BEGIN RETURN n; END"),
        ("", "trigger", "BEGIN RETURN NEW; END"),
    ],
)
def test_selected_unsupported_context_refuses_explicitly(
    semantic_bare_engine,
    arguments,
    returns,
    body,
):
    with semantic_bare_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("CREATE SCHEMA checker_test")
        selected = definition(connection, "context", arguments, returns, body)
        # Generic catalog/backfill normalization retains its existing capability.
        assert prepare_native_authoring(connection, (selected,), owned_authoring=True).desired
        with pytest.raises(NativeAuthoringError, match="concrete ordinary function context"):
            prepare_native_authoring(
                connection,
                (selected,),
                owned_authoring=True,
                check_plpgsql=frozenset({selected.identity}),
            )


def test_comment_options_cannot_hide_errors(semantic_bare_engine):
    with semantic_bare_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("CREATE SCHEMA checker_test")
        selected = definition(
            connection,
            "hidden",
            "n integer",
            "integer",
            "/* @plpgsql_check_options: relid = checker_test.missing_relation */ "
            "BEGIN RETURN n->'bad'; END",
        )
        with pytest.raises(NativeAuthoringError, match="SQLSTATE 42883"):
            prepare_native_authoring(
                connection,
                (selected,),
                owned_authoring=True,
                check_plpgsql=frozenset({selected.identity}),
            )


def test_all_selected_function_errors_reported_together(semantic_bare_engine):
    with semantic_bare_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("CREATE SCHEMA checker_test")
        before = checker(connection)
        first = definition(
            connection,
            "first_bad",
            "n integer",
            "integer",
            "BEGIN RETURN n->'bad'; END",
        )
        valid = definition(connection, "valid", "n integer", "integer", "BEGIN RETURN n; END")
        second = definition(
            connection,
            "second_bad",
            "n integer",
            "integer",
            "BEGIN RETURN n->'wrong'; END",
        )
        with pytest.raises(NativeAuthoringError) as caught:
            prepare_native_authoring(
                connection,
                (first, valid, second),
                owned_authoring=True,
                check_plpgsql=frozenset({first.identity, valid.identity, second.identity}),
            )
        message = str(caught.value)
        for name in ("first_bad", "second_bad"):
            assert f"checker_test.{name}(integer): SQLSTATE 42883" in message
            assert f"source=checker-control:{name}" in message
        assert "checker_test.valid" not in message
        assert "unexamined" not in message
        context = caught.value.authoring_context
        assert context is not None and context["phase"] == "plpgsql_check"
        assert context["error_count"] == 2
        assert context["omissions"] == []
        diagnostics = context["diagnostics"]
        assert isinstance(diagnostics, list) and len(diagnostics) == 2
        assert all(entry in message for entry in diagnostics)
        assert checker(connection) == before
        assert (
            connection.scalar(text("SELECT to_regprocedure('checker_test.valid(integer)')")) is None
        )


def test_error_limits_disclose_truncation_and_unexamined_functions(semantic_bare_engine):
    with semantic_bare_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("CREATE SCHEMA checker_test")
        selected = tuple(
            definition(
                connection,
                f"many_bad_{index}",
                "n integer",
                "integer",
                "BEGIN " + "PERFORM n->'bad'; " * 12 + "RETURN n; END",
            )
            for index in range(5)
        )
        with pytest.raises(NativeAuthoringError) as caught:
            prepare_native_authoring(
                connection,
                selected,
                owned_authoring=True,
                check_plpgsql=frozenset(item.identity for item in selected),
            )
        message = str(caught.value)
        assert message.count("SQLSTATE 42883") == 32
        assert message.count("further errors omitted") == 4
        assert "1 selected functions unexamined" in message
        assert "many_bad_4" not in message


@pytest.mark.parametrize("second_has_value", [True, False])
def test_declared_trigger_checks_each_real_parent_layout(semantic_bare_engine, second_has_value):
    with semantic_bare_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("CREATE SCHEMA checker_test")
        connection.exec_driver_sql("CREATE TABLE checker_test.first_parent(value integer)")
        second_column = "value integer, extra text" if second_has_value else "other integer"
        connection.exec_driver_sql("CREATE TABLE checker_test.second_parent(" + second_column + ")")
        before = checker(connection)
        selected = definition(
            connection,
            "parent_guard",
            "",
            "trigger",
            "BEGIN NEW.value := NEW.value + 1; RETURN NEW; END",
        )
        triggers = tuple(
            definition_from_sql(
                connection,
                "CREATE TRIGGER checked_parent BEFORE INSERT ON checker_test."
                + relation
                + " FOR EACH ROW EXECUTE FUNCTION checker_test.parent_guard()",
                source="checker-control:parent:" + relation,
                owner=connection.scalar(text("SELECT current_user")),
            )
            for relation in ("first_parent", "second_parent")
        )
        options = dict(
            owned_authoring=True,
            check_plpgsql=frozenset({selected.identity}),
            check_plpgsql_triggers=frozenset(item.identity for item in triggers),
        )
        if second_has_value:
            result = prepare_native_authoring(connection, (selected, *triggers), **options)
            assert len(result.desired) == 3
            with pytest.raises(
                NativeAuthoringError, match="every declared trigger relation context"
            ):
                prepare_native_authoring(
                    connection,
                    (selected, *triggers),
                    **{
                        **options,
                        "check_plpgsql_triggers": frozenset({triggers[0].identity}),
                    },
                )
        else:
            with pytest.raises(
                NativeAuthoringError, match=r"SQLSTATE 42703.*relation=checker_test.second_parent"
            ):
                prepare_native_authoring(connection, (selected, *triggers), **options)
        assert checker(connection) == before
        assert (
            connection.scalar(text("SELECT to_regprocedure('checker_test.parent_guard()')")) is None
        )
        assert connection.scalar(text("SELECT count(*) FROM checker_test.first_parent")) == 0
