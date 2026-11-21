"""Independent native controls for current-family receipt reconfirmation."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import literal, select, text
from sqlalchemy.exc import IntegrityError

from corpus_structure.semantic.completion_validation_native import completion_validation_programs
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import INTERNAL_PROGRAM, execute_native_sql
from corpus_structure.semantic.native_program import NativeRoutine, Parameter, pg_type
from corpus_structure.semantic.native_program_registry import (
    ProgramDeclaration,
    ProgramValidity,
    program_closures,
    render_programs,
)


def test_receipt_requires_each_current_family_and_records_only_missing(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    connection.exec_driver_sql("CREATE SCHEMA sem")
    for sql in (
        "CREATE TABLE ops.data_request(id text, release_id text, operation_id text)",
        "CREATE TABLE ops.data_derivation(id text)",
        "CREATE TABLE ops.data_completion_intent(id text)",
        "CREATE TABLE ops.data_publication_receipt(id text,derivation_id text,intent_id text,validation_identities jsonb)",
        "CREATE TABLE ops.data_validity_reconfirmation(receipt_id text,validator_family text,validator_identity text,confirmed_at timestamptz,PRIMARY KEY(receipt_id,validator_family,validator_identity))",
        "CREATE TABLE ops.allow_validation(ok boolean)",
        "INSERT INTO ops.allow_validation VALUES(false)",
        "INSERT INTO ops.data_request VALUES('request','release','operation')",
        "INSERT INTO ops.data_derivation VALUES('episode')",
        "INSERT INTO ops.data_completion_intent VALUES('intent')",
        "INSERT INTO ops.data_publication_receipt VALUES('receipt','episode','intent','{\"artifact\":\"a\"}')",
        """CREATE FUNCTION ops.ddo_require_episode_correspondence(ops.data_derivation,ops.data_completion_intent)
        RETURNS ops.data_request LANGUAGE plpgsql AS $$BEGIN
        IF NOT (SELECT ok FROM ops.allow_validation) THEN RAISE EXCEPTION 'current validator refused' USING ERRCODE='23514'; END IF;
        RETURN (SELECT r FROM ops.data_request r); END$$""",
        'CREATE FUNCTION ops.ddo_current_validation_identities(text,text) RETURNS jsonb LANGUAGE sql AS $$ SELECT \'{"artifact":"a","rich":"r"}\'::jsonb $$',
    ):
        connection.exec_driver_sql(sql)
    for routine in completion_validation_programs(get_metadata()):
        if routine.name in {
            "ddo_missing_validation_identities",
            "ddo_receipt_validation_current",
            "ddo_reconfirm_completion_validity",
        }:
            execute_native_sql(connection, routine.render())

    def missing(required):
        return connection.scalar(
            text(
                "SELECT ops.ddo_missing_validation_identities('receipt',CAST(:required AS jsonb))"
            ),
            {"required": json.dumps(required)},
        )

    assert missing({"artifact": "a"}) == {}
    assert missing({"artifact": "a", "rich": "r"}) == {"rich": "r"}
    assert missing({"artifact": "changed"}) == {"artifact": "changed"}
    with (
        pytest.raises(IntegrityError, match="current validator refused"),
        connection.begin_nested(),
    ):
        connection.exec_driver_sql("SELECT ops.ddo_reconfirm_completion_validity('receipt')")
    assert connection.scalar(text("SELECT count(*) FROM ops.data_validity_reconfirmation")) == 0
    connection.exec_driver_sql("UPDATE ops.allow_validation SET ok=true")
    for _ in range(2):
        connection.exec_driver_sql("SELECT ops.ddo_reconfirm_completion_validity('receipt')")
    assert connection.execute(
        text("SELECT validator_family,validator_identity FROM ops.data_validity_reconfirmation")
    ).all() == [("rich", "r")]
    assert missing({"artifact": "a", "rich": "r"}) == {}
    assert missing({"rich": "new"}) == {"rich": "new"}
    assert connection.scalar(
        text("SELECT validation_identities FROM ops.data_publication_receipt")
    ) == {"artifact": "a"}


def test_independent_family_guard_edit_changes_only_its_closure():
    def declaration(name, *, family=None):
        return ProgramDeclaration(
            NativeRoutine(
                "ops",
                name,
                (Parameter("value", pg_type("text")),),
                pg_type("bool"),
                select(literal(True)),
            ),
            "independent-family-control",
            "owner",
            INTERNAL_PROGRAM,
            validity=() if family is None else (ProgramValidity(family, "validator"),),
        )

    artifact = declaration("artifact", family="artifact")
    rich = declaration("rich", family="rich")
    conservative = declaration("conservative", family="conservative")
    # The closure owner requires its real protocol roots even for an isolated fixture.
    lower = replace(
        declaration("ddo_lower_data_operation_definitions"),
        routine=NativeRoutine(
            "sem",
            "ddo_lower_data_operation_definitions",
            (Parameter("p", pg_type("jsonb")), Parameter("q", pg_type("boolean"))),
            pg_type("bool"),
            select(literal(True)),
        ),
    )
    read = replace(
        declaration("read_demand_result"),
        routine=NativeRoutine(
            "ops",
            "read_demand_result",
            (Parameter("p", pg_type("jsonb")),),
            pg_type("bool"),
            select(literal(True)),
        ),
    )

    def closures(values):
        rendered = render_programs(tuple(values), registry_schemas=frozenset({"ops", "sem"}))
        return program_closures(tuple(item.declared_definition for item in rendered), ())

    before = closures((artifact, rich, conservative, lower, read))
    changed = replace(artifact, routine=replace(artifact.routine, body=select(literal(False))))
    after = closures((changed, rich, conservative, lower, read))
    assert before.validators["artifact"] != after.validators["artifact"]
    assert {
        key for key in before.validators if before.validators[key] != after.validators[key]
    } == {"artifact"}
    assert before.read == after.read
    assert before.lowering == after.lowering


def test_current_family_programs_install_on_actual_postgresql(semantic_bare_engine, tmp_path):
    from corpus_structure.semantic.target_installation import capture_target_installation
    from semantic.test_target_installation_native import install_target_root

    capture = capture_target_installation(get_metadata())
    _, authoring, _, _, _, _ = install_target_root(semantic_bare_engine, capture, tmp_path)
    names = {item.identity.name for item in authoring.desired}
    assert {
        "ddo_missing_validation_identities",
        "ddo_require_completion_invariants",
        "ddo_require_completion_families",
        "ddo_require_episode_identity",
    } <= names
    assert {
        "ddo_require_episode_" + family + "_correspondence"
        for family in (
            "artifact",
            "definition",
            "contextual",
            "rich",
            "record_grade",
            "record_fit",
            "operation_event",
        )
    } <= names


def test_consuming_family_is_checked_under_current_request(infrastructure_rollback):
    from corpus_structure.semantic.completion_validation_native import consuming_completion_programs

    connection = infrastructure_rollback
    for statement in (
        "CREATE SCHEMA ops",
        "CREATE TABLE ops.data_request(id text,release_id text,operation_id text,project_id text,recipe text,request_key text,binding jsonb)",
        "CREATE TABLE ops.data_derivation(id text,intent_id text)",
        "CREATE TABLE ops.data_completion_intent(id text,payload jsonb)",
        "INSERT INTO ops.data_request VALUES('original','old','operation','project','same-recipe','same-key','{}'),('consumer','new','operation','project','same-recipe','same-key','{}'),('unchanged','same','operation','project','same-recipe','same-key','{}')",
        "INSERT INTO ops.data_derivation VALUES('episode','intent')",
        "INSERT INTO ops.data_completion_intent VALUES('intent','{\"outputs\":[\"retained\"]}')",
        "CREATE FUNCTION ops.ddo_require_episode_correspondence(ops.data_derivation,ops.data_completion_intent) RETURNS ops.data_request LANGUAGE sql AS $$ SELECT r FROM ops.data_request r WHERE id='original' $$",
        'CREATE FUNCTION ops.ddo_current_validation_identities(text,text) RETURNS jsonb LANGUAGE sql AS $$ SELECT CASE WHEN $1=\'new\' THEN \'{"artifact":"a","rich":"changed"}\'::jsonb ELSE \'{"artifact":"a","rich":"r"}\'::jsonb END $$',
        """CREATE FUNCTION ops.ddo_require_completion_families(r ops.data_request,payload jsonb,families jsonb) RETURNS void LANGUAGE plpgsql AS $$BEGIN
        IF r.release_id<>'new' OR families<>'{"rich":"changed"}'::jsonb OR payload<>'{"outputs":["retained"]}'::jsonb THEN RAISE EXCEPTION 'wrong consuming basis' USING ERRCODE='23514'; END IF;
        IF current_setting('udm.allow_consumer',true) IS DISTINCT FROM 'yes' THEN RAISE EXCEPTION 'current family refused' USING ERRCODE='23514'; END IF; END$$""",
        "CREATE FUNCTION ops.ddo_conservative_dependencies_valid(text) RETURNS boolean LANGUAGE sql AS $$ SELECT true $$",
    ):
        connection.exec_driver_sql(statement)
    bridge, _ = consuming_completion_programs(get_metadata())
    execute_native_sql(connection, bridge.render())
    query = "SELECT ops.ddo_require_consuming_episode('episode', r) FROM ops.data_request r WHERE id='consumer'"
    connection.exec_driver_sql(query.replace("id='consumer'", "id='original'"))
    # A consuming release with identical family identities does not recheck either
    # artifact or rich validation. The current-family stub still refuses calls.
    connection.exec_driver_sql(query.replace("id='consumer'", "id='unchanged'"))
    with pytest.raises(IntegrityError, match="current family refused"), connection.begin_nested():
        connection.exec_driver_sql(query)
    connection.exec_driver_sql("SET LOCAL udm.allow_consumer='yes'")
    connection.exec_driver_sql(query)
    connection.exec_driver_sql("UPDATE ops.data_request SET recipe='different' WHERE id='consumer'")
    with (
        pytest.raises(IntegrityError, match="original producer contract"),
        connection.begin_nested(),
    ):
        connection.exec_driver_sql(query)
    assert connection.scalar(text("SELECT payload FROM ops.data_completion_intent")) == {
        "outputs": ["retained"]
    }
