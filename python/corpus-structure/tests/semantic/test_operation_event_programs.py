"""Generated event guards retain selected-cut and exact authorization contracts."""

import json
from copy import deepcopy
from dataclasses import asdict

import pytest
from pglast import ast
from sqlalchemy import Column, MetaData, Table, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.evaluate.declared_operation_events import (
    AUTHORIZATION_EFFECT,
    AUTHORIZATION_FACTORY,
    AUTHORIZATION_OPERATION,
)
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
from corpus_structure.semantic.operation_event_native import operation_event_native_sql
from corpus_structure.semantic.prepared_sql import prepare_sql


def test_generated_operation_event_guards_bind_and_keep_exact_eligibility(native_rollback):
    connection = native_rollback.connection
    execute_native_sql(connection, "CREATE EXTENSION IF NOT EXISTS plpgsql_check VERSION '2.10'")
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, operation_event_native_sql(get_metadata()))
        for signature in (
            "ops.ddo_operation_event_completion_scopes(ops.data_request)",
            "ops.ddo_operation_event_dependency_scopes(text)",
            "ops.ddo_operation_event_require_frame(ops.data_request,jsonb)",
            "ops.ddo_operation_event_require_fit(ops.data_request,jsonb)",
            "ops.ddo_operation_event_require_parameters(ops.data_request)",
            "ops.ddo_require_operation_event_completion(ops.data_request,jsonb)",
            "ops.ddo_operation_event_dependencies_valid(text)",
        ):
            errors = (
                connection.execute(
                    text(
                        "SELECT message FROM public.plpgsql_check_function_tb(CAST(:signature AS regprocedure),fatal_errors=>false) WHERE level='error'"
                    ),
                    {"signature": signature},
                )
                .scalars()
                .all()
            )
            assert errors == [], (signature, errors)
        definition = {
            "operation_id": AUTHORIZATION_OPERATION,
            "profile": "command",
            "implementation_revision": "implementation-slice:captured",
            "support_contract": {
                "effects": [asdict(AUTHORIZATION_EFFECT)],
                "capabilities": {
                    "preparation": "native-publication",
                    "forms": ["scalar"],
                    "prepared_factory": {
                        "entrypoint": AUTHORIZATION_FACTORY,
                        "source_digest": "a" * 64,
                    },
                },
            },
        }
        query = text(
            "SELECT coalesce(ops.ddo_operation_event_command_eligible(jsonb_populate_record(NULL::sem.data_operation_definition,CAST(:definition AS jsonb))),false)"
        )
        assert connection.scalar(query, {"definition": json.dumps(definition)}) is True
        renamed = deepcopy(definition)
        renamed["operation_id"] = "other.authorize"
        assert connection.scalar(query, {"definition": json.dumps(renamed)}) is True
        for change in (
            "profile",
            "preparation",
            "forms",
            "factory",
            "source",
            "effects",
            "implementation",
        ):
            invalid = deepcopy(definition)
            capabilities = invalid["support_contract"]["capabilities"]
            if change == "profile":
                invalid["profile"] = "derivation"
            elif change == "preparation":
                capabilities["preparation"] = "none"
            elif change == "forms":
                capabilities["forms"] = ["batch"]
            elif change == "factory":
                capabilities["prepared_factory"]["entrypoint"] = ""
            elif change == "source":
                capabilities["prepared_factory"]["source_digest"] = "uncaptured"
            elif change == "effects":
                invalid["support_contract"]["effects"] = []
            else:
                invalid["implementation_revision"] = "uncaptured-source"
            assert connection.scalar(query, {"definition": json.dumps(invalid)}) is False
        assert (
            connection.scalar(
                text("SELECT ops.ddo_operation_event_dependencies_valid('missing-event-episode')")
            )
            is False
        )
        assert (
            connection.scalar(
                text(
                    'SELECT count(*) FROM ops.ddo_operation_event_completion_scopes(jsonb_populate_record(NULL::ops.data_request,\'{"operation_id":"unrelated"}\'))'
                )
            )
            == 0
        )
    with native_owner(connection, "corpus_sem_writer"):
        with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
            connection.scalar(
                text("SELECT ops.ddo_operation_event_dependencies_valid('missing-event-episode')")
            )
        assert getattr(refusal.value.orig, "sqlstate", None) == "42501"


@pytest.fixture
def event_scope_connection(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    connection.exec_driver_sql("CREATE SCHEMA sem")
    connection.execute(
        CreateTable(get_metadata().tables["ops.data_request"], include_foreign_key_constraints=[])
    )
    definition = get_metadata().tables["sem.data_operation_definition"]
    definitions = Table(
        "data_operation_definition",
        MetaData(),
        *(
            Column(name, definition.c[name].type, nullable=False)
            for name in ("release_id", "operation_id", "input_roles", "validity_families")
        ),
        schema="sem",
    )
    connection.execute(CreateTable(definitions))
    connection.execute(
        definitions.insert(),
        [
            dict(
                release_id="scope-release",
                operation_id=operation,
                input_roles=[{"name": role}],
                validity_families=families,
            )
            for operation, role, families in (
                ("operation_event.frame", "question", ["operation-event"]),
                ("operation_event.fit", "specification", ["operation-event"]),
                ("family.question", "question", ["operation-event"]),
                ("family.specification", "specification", ["operation-event"]),
                ("ordinary.question", "question", []),
                ("ordinary.specification", "specification", []),
            )
        ],
    )
    # Controlled input and cut ports let the actual generated scope consumer
    # select and validate its original/prediction/frame values independently.
    connection.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_record_grade_input(r ops.data_request,role_name text) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$ SELECT jsonb_build_object('body',r.binding->role_name) $$"
    )
    connection.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_record_grade_cut_scopes(project text,cut text) RETURNS SETOF text LANGUAGE sql IMMUTABLE AS $$ SELECT 'grade:'||cut $$"
    )
    connection.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_record_fit_cut_scopes(project text,selection jsonb) RETURNS SETOF text LANGUAGE sql IMMUTABLE AS $$ SELECT 'fit:'||(selection->>'use_id') $$"
    )
    parsed = prepare_sql(operation_event_native_sql(get_metadata()), source="event-scopes")
    for i, statement in enumerate(parsed.statements):
        node = statement.stmt
        if (
            isinstance(node, ast.CreateFunctionStmt)
            and node.funcname
            and node.funcname[-1].sval == "ddo_operation_event_completion_scopes"
        ):
            execute_native_sql(connection, parsed.excerpt(i))
    yield connection


def _scopes(connection, request):
    return sorted(
        connection.execute(
            text(
                "SELECT * FROM ops.ddo_operation_event_completion_scopes(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)))"
            ),
            {"r": json.dumps(request)},
        )
        .scalars()
        .all()
    )


def test_event_scope_consumer_preserves_distinct_cuts_and_fit_selection(event_scope_connection):
    request = {
        "release_id": "scope-release",
        "project_id": "project",
        "operation_id": "operation_event.frame",
        "binding": {
            "question": {
                "original_selection": {"project_id": "project", "cut_canonical_json": "original"},
                "prediction_selection": {
                    "project_id": "project",
                    "cut_canonical_json": "prediction",
                },
            }
        },
    }
    assert _scopes(event_scope_connection, request) == ["grade:original", "grade:prediction"]
    question = request["binding"]["question"]
    question["prediction_selection"] = question["original_selection"]
    assert _scopes(event_scope_connection, request) == ["grade:original"]
    question["prediction_selection"] = {"project_id": "foreign", "cut_canonical_json": "prediction"}
    with (
        pytest.raises(DBAPIError, match="another project") as refusal,
        event_scope_connection.begin_nested(),
    ):
        _scopes(event_scope_connection, request)
    assert getattr(refusal.value.orig, "sqlstate", None) == "23514"
    request = {
        "release_id": "scope-release",
        "project_id": "project",
        "operation_id": "operation_event.fit",
        "binding": {"specification": {"frame": {"selection": {"use_id": "selected"}}}},
    }
    assert _scopes(event_scope_connection, request) == ["fit:selected"]


@pytest.mark.parametrize("family", ["family", "ordinary", "unknown"])
@pytest.mark.parametrize(
    ("role", "body", "expected"),
    [
        (
            "question",
            {
                "original_selection": {"project_id": "project", "cut_canonical_json": "original"},
                "prediction_selection": {
                    "project_id": "project",
                    "cut_canonical_json": "prediction",
                },
            },
            ["grade:original", "grade:prediction"],
        ),
        (
            "specification",
            {"frame": {"selection": {"use_id": "selected"}}},
            ["fit:selected"],
        ),
    ],
)
def test_event_scope_consumer_requires_declared_family_before_interpreting_roles(
    event_scope_connection, family, role, body, expected
):
    request = {
        "release_id": "scope-release",
        "project_id": "project",
        "operation_id": f"{family}.{role}",
        "binding": {role: body},
    }
    assert _scopes(event_scope_connection, request) == (expected if family == "family" else [])
