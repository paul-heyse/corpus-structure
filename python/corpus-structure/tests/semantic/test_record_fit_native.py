"""Native fit correspondence controls; numerical fitting stays the real CPU kernel."""

import json
from copy import deepcopy
from hashlib import sha256

import pytest
from evaluate.declared_record_policy_test_support import fit_basis as fit_basis
from pglast import ast
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.evaluate.declared_record_policy import fit_declared_record_policy
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import metadata, table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.record_policy_completion_native import (
    record_policy_completion_native_sql,
)
from semantic.test_record_policy_completion_native import (
    policy_projection_connection as policy_projection_connection,
)


def basis_hash(first, second, specification):
    return sha256(
        canonical_bytes(semantic_value([first.frame_digest, second.frame_digest, specification]))
    ).hexdigest()


@pytest.fixture
def fit_correspondence_connection(policy_projection_connection):
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql

    for source, names in (
        (native_sql(native_protocol_sources()), {"ddo_digest"}),
        (record_policy_completion_native_sql(metadata), {"ddo_require_record_fit_correspondence"}),
    ):
        parsed = prepare_sql(source, source="fit-correspondence-control")
        for index, statement in enumerate(parsed.statements):
            node = statement.stmt
            if (
                isinstance(node, ast.CreateFunctionStmt)
                and node.funcname
                and node.funcname[-1].sval in names
            ):
                policy_projection_connection.exec_driver_sql(
                    parsed.excerpt(index), execution_options={"no_parameters": True}
                )
    return policy_projection_connection


def check(connection, first, second, specification, fitted):
    values = {
        name: canonical_bytes(semantic_value(value)).decode()
        for name, value in (
            ("first", first),
            ("second", second),
            ("specification", specification),
            ("fitted", fitted),
        )
    }
    connection.execute(
        text(
            "SELECT ops.ddo_require_record_fit_correspondence(CAST(:first AS jsonb),CAST(:second AS jsonb),CAST(:specification AS jsonb),CAST(:fitted AS jsonb))"
        ),
        values,
    )


def test_program_fit_matches_real_numerical_fit_and_exact_tagged_basis(
    fit_correspondence_connection, fit_basis
):
    first, second, specification = fit_basis
    fitted = fit_declared_record_policy(first, second, specification).fitted
    assert fitted is not None
    expected = basis_hash(first, second, specification.model_dump(mode="json"))
    assert fitted.judgment_basis_digest == expected
    check(
        fit_correspondence_connection,
        first.model_dump(mode="json"),
        second.model_dump(mode="json"),
        specification.model_dump(mode="json"),
        fitted.model_dump(mode="json"),
    )


@pytest.mark.parametrize(
    "change", ["threshold", "procedure", "population", "family", "recipe", "conditioning"]
)
def test_copied_self_consistent_fit_refuses_different_actual_specification(
    fit_correspondence_connection, fit_basis, change
):
    first, second, specification = fit_basis
    fitted = fit_declared_record_policy(first, second, specification).fitted
    assert fitted is not None
    altered = specification.model_dump(mode="json")
    if change == "threshold":
        altered["threshold"] = 0.75
    elif change == "procedure":
        altered["threshold_procedure"] = "different-predeclared-procedure"
    elif change == "population":
        from evaluate.declared_record_policy_support import source

        altered["applicability"]["sources"] = [source(901).model_dump(mode="json")]
    elif change == "family":
        altered["family_contract"] = "different-actual-family-contract"
    elif change == "recipe":
        altered["reading_recipe"] = "different-actual-reading-recipe"
    else:
        altered["assumptions"] = "different declared conditioning"
    # Refreshing the basis digest cannot disguise an old fitted body's mismatch
    # with a different request. No producer/CPU receipt is invented in this control.
    body = fitted.model_dump(mode="json")
    body["judgment_basis_digest"] = basis_hash(first, second, altered)
    with pytest.raises(DBAPIError, match=r"actual frozen feature|actual input frames"):
        check(
            fit_correspondence_connection,
            first.model_dump(mode="json"),
            second.model_dump(mode="json"),
            altered,
            body,
        )


def test_frozen_predictor_correspondence_preserves_signed_zero_tags(
    fit_correspondence_connection, fit_basis
):
    first, second, specification = fit_basis
    fitted = fit_declared_record_policy(first, second, specification).fitted
    assert fitted is not None
    altered = specification.model_dump(mode="json")
    assert altered["frozen_feature"]["parameters"]["center"][0] == 0.0
    altered["frozen_feature"]["parameters"]["center"][0] = -0.0
    body = fitted.model_dump(mode="json")
    body["judgment_basis_digest"] = basis_hash(first, second, altered)
    assert json.dumps(altered["frozen_feature"]) != json.dumps(body["instance"]["feature"])
    with pytest.raises(DBAPIError, match="actual frozen feature"):
        check(
            fit_correspondence_connection,
            first.model_dump(mode="json"),
            second.model_dump(mode="json"),
            altered,
            body,
        )


def test_actual_grade_frame_change_cannot_reuse_old_fit_provenance(
    fit_correspondence_connection, fit_basis
):
    from corpus_structure.evaluate.declared_record_policy import DdoRecordGrade

    first, second, specification = fit_basis
    fitted = fit_declared_record_policy(first, second, specification).fitted
    assert fitted is not None
    changed = DdoRecordGrade.from_frame(
        first.frame.model_copy(update={"reference_digest": "a" * 64})
    )
    altered = specification.model_dump(mode="json")
    altered["feature_selection"]["frame_digest"] = changed.frame_digest
    # All nonnumerical metadata is independently changed to the new frame; the
    # copied predictor's original fit provenance must still refuse.
    calibration = deepcopy(second.model_dump(mode="json"))
    calibration["frame"]["held_out_from"] = [changed.frame_digest]
    copied = fitted.model_dump(mode="json")
    copied["judgment_basis_digest"] = basis_hash(changed, second, altered)
    with pytest.raises(DBAPIError, match="actual input frames"):
        check(
            fit_correspondence_connection,
            changed.model_dump(mode="json"),
            calibration,
            altered,
            copied,
        )


@pytest.fixture
def fit_guard_connection(infrastructure_rollback):
    sql = record_policy_completion_native_sql(metadata)
    connection = infrastructure_rollback
    for name in ("sem", "data", "ops", "kb"):
        connection.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {name}")
    for name in (
        "ops.data_request",
        "ops.data_demand",
        "ops.data_demand_read",
        "ops.data_derivation",
        "ops.data_completion_intent",
        "sem.data_operation_definition",
        "sem.data_kind_contract",
        "kb.data_product",
    ):
        connection.execute(CreateTable(table(name), include_foreign_key_constraints=[]))
    connection.exec_driver_sql(sql, execution_options={"no_parameters": True})
    yield connection


def test_fit_native_helpers_compile_and_nonfit_scopes_are_empty(fit_guard_connection):
    connection = fit_guard_connection
    request = json.dumps({"operation_id": "unrelated", "project_id": "unrelated-project"})
    assert (
        connection.scalar(
            text(
                "SELECT count(*) FROM ops.ddo_record_fit_completion_scopes(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)))"
            ),
            {"r": request},
        )
        == 0
    )
    connection.execute(
        text(
            "SELECT ops.ddo_require_record_fit_completion(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)),'{}'::jsonb)"
        ),
        {"r": request},
    )
    assert (
        connection.scalar(text("SELECT ops.ddo_record_fit_dependencies_valid('missing-episode')"))
        is False
    )
    assert (
        connection.scalar(
            text(
                "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='ops' AND p.proname LIKE '%record_fit%' AND EXISTS(SELECT FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) grant_ WHERE grant_.grantee=0 AND grant_.privilege_type='EXECUTE')"
            )
        )
        == 0
    )


def test_two_legitimate_fit_requests_cannot_exchange_self_consistent_fitted_bodies(
    fit_correspondence_connection, fit_basis
):
    from corpus_structure.evaluate.declared_record_policy import DdoRecordFitSpecification

    first, second, original = fit_basis
    revised = DdoRecordFitSpecification.model_validate_json(
        canonical_bytes({**original.model_dump(mode="json"), "threshold": 0.75})
    )
    old = fit_declared_record_policy(first, second, original).fitted
    current = fit_declared_record_policy(first, second, revised).fitted
    assert old is not None and current is not None
    assert (old.instance.threshold, current.instance.threshold) == (0.99, 0.75)
    assert old.instance.feature == current.instance.feature
    copied = old.model_dump(mode="json")
    copied["judgment_basis_digest"] = current.judgment_basis_digest
    with pytest.raises(DBAPIError, match="actual frozen feature"):
        check(
            fit_correspondence_connection,
            first.model_dump(mode="json"),
            second.model_dump(mode="json"),
            revised.model_dump(mode="json"),
            copied,
        )


def test_generated_policy_completion_programs_bind_in_actual_native_model(native_rollback):
    from corpus_structure.semantic.native_objects import execute_native_sql, native_owner

    connection = native_rollback.connection
    execute_native_sql(connection, "CREATE EXTENSION IF NOT EXISTS plpgsql_check VERSION '2.10'")
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, record_policy_completion_native_sql(metadata))
        for signature in (
            "ops.ddo_policy_authorization_value(jsonb)",
            "ops.ddo_policy_authorization_meaning(jsonb)",
            "ops.ddo_require_policy_authorization_completion(ops.data_request,jsonb)",
            "ops.ddo_require_record_fit_correspondence(jsonb,jsonb,jsonb,jsonb)",
            "ops.ddo_record_fit_require_finite_cut(ops.data_demand,ops.data_demand_read)",
            "ops.ddo_record_fit_selections(ops.data_request)",
            "ops.ddo_record_fit_cut_scopes(text,jsonb)",
            "ops.ddo_record_fit_completion_scopes(ops.data_request)",
            "ops.ddo_record_fit_dependency_scopes(text)",
            "ops.ddo_record_fit_require_selection(ops.data_request,text,jsonb,boolean)",
            "ops.ddo_record_fit_require_producer(ops.data_request,jsonb)",
            "ops.ddo_require_record_fit_completion(ops.data_request,jsonb)",
            "ops.ddo_record_fit_dependencies_valid(text)",
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
        assert (
            connection.scalar(
                text("SELECT ops.ddo_record_fit_dependencies_valid('missing-policy-episode')")
            )
            is False
        )


def test_fit_selection_rows_preserve_roles_and_refuse_changed_cut(fit_guard_connection):
    connection = fit_guard_connection
    # Supply the existing input port with a controlled specification; the native
    # selection/cut validation and TABLE output execute unchanged on PostgreSQL.
    connection.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_record_grade_input(r ops.data_request,role_name text) "
        "RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$ SELECT jsonb_build_object('body',r.binding->'specification') $$"
    )
    selections = {}
    for name in ("feature", "calibration"):
        cut = json.dumps(
            {
                "project_id": "project:selection",
                "demand_id": "demand:" + name,
                "read_id": "read:" + name,
            }
        )
        selections[name + "_selection"] = {
            "project_id": "project:selection",
            "demand_id": "demand:" + name,
            "read_id": "read:" + name,
            "cut_canonical_json": cut,
            "expected_cut": "cut-selection:" + sha256(cut.encode()).hexdigest(),
        }
    request = {"project_id": "project:selection", "binding": {"specification": selections}}
    query = text(
        "SELECT role_name,selection FROM ops.ddo_record_fit_selections(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)))"
    )
    assert connection.execute(query, {"r": json.dumps(request)}).all() == [
        ("feature_grade", selections["feature_selection"]),
        ("calibration_grade", selections["calibration_selection"]),
    ]
    selections["feature_selection"]["expected_cut"] = "cut-selection:changed"
    with (
        pytest.raises(DBAPIError, match="actual original project/cut/read pins") as refusal,
        connection.begin_nested(),
    ):
        connection.execute(query, {"r": json.dumps(request)}).all()
    assert getattr(refusal.value.orig, "sqlstate", None) == "23514"
