"""Rollback controls for generated protected companion adoption and model shapes."""

import json
from copy import copy

import pytest
import yaml
from sqlalchemy import Column, MetaData, Table, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.pdf_companion_adoption_native import companion_adoption_sql
from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_shared_streams import pdf_companion_scratch_specs


@pytest.fixture
def adoption(infrastructure_rollback):
    conn = infrastructure_rollback
    execute_native_sql(conn, "CREATE SCHEMA ops")
    names = [
        "ops.pdf_stage_build",
        *(spec.source.fullname for spec in pdf_companion_scratch_specs(get_metadata())),
    ]
    for name in dict.fromkeys(names):
        source = (
            get_metadata().tables[name]
            if name in get_metadata().tables
            else next(
                spec.source
                for spec in pdf_companion_scratch_specs(get_metadata())
                if spec.source.fullname == name
            )
        )
        relation = Table(
            source.name,
            MetaData(),
            *(Column(field.name, field.type, primary_key=field.primary_key) for field in source.c),
            schema=source.schema,
        )
        conn.execute(CreateTable(relation))
    for spec in pdf_companion_scratch_specs(get_metadata()):
        relation = Table(
            spec.name,
            MetaData(),
            *(Column(field.name, field.type) for field in spec.source.c),
            schema="pg_temp",
        )
        conn.execute(CreateTable(relation))
    execute_native_sql(
        conn,
        """
CREATE FUNCTION ops.require_pdf_build(text,bigint,bigint,text) RETURNS ops.pdf_stage_build
LANGUAGE plpgsql AS $$
DECLARE b ops.pdf_stage_build;
BEGIN
 IF $3<>1 OR $4<>'owner' THEN RAISE EXCEPTION 'stale owner' USING ERRCODE='P0004'; END IF;
 b.build_id:=$1; b.release_id:='captured'; RETURN b;
END $$;
CREATE FUNCTION ops.require_pdf_operation(text,text) RETURNS void LANGUAGE sql AS 'SELECT NULL::void';
CREATE FUNCTION ops.require_pdf_stage_scratch(text,regclass) RETURNS void LANGUAGE sql AS 'SELECT NULL::void';
CREATE FUNCTION ops.pdf_part_upload_contract() RETURNS regclass LANGUAGE sql
 RETURN 'pg_temp.pc_pdf_stage_artifact_part'::regclass;
CREATE FUNCTION ops.pdf_adopt_shared_stream_descriptors(text,regclass) RETURNS void LANGUAGE sql AS 'SELECT NULL::void';
CREATE FUNCTION ops.pdf_adopt_shared_stream_parts(text,regclass) RETURNS void LANGUAGE sql AS 'SELECT NULL::void';
CREATE FUNCTION ops.pdf_verify_shared_stream(text,text) RETURNS void LANGUAGE sql AS 'SELECT NULL::void';
CREATE FUNCTION ops.pdf_companion_field_bytes(text,text,text,boolean) RETURNS bytea LANGUAGE sql RETURN ''::bytea;
""",
    )
    execute_native_sql(conn, companion_adoption_sql(trusted_pdf_context(), get_metadata()))
    yield conn


def occurrence(name):
    return dict(
        occurrence_id=name,
        kind="text",
        address_space="native_item",
        precision="item",
        pointer="#/texts/0",
    )


def upload(conn, name, ordinal, **changes):
    conn.execute(
        text(
            "INSERT INTO pg_temp.pc_pdf_stage_companion(product_id,revision_id,family,local_id,ordinal,body) VALUES('b','b','occurrence',:name,:ordinal,CAST(:body AS jsonb))"
        ),
        dict(name=name, ordinal=ordinal, body=json.dumps(occurrence(name) | changes)),
    )


def invoke(conn, attempt=1):
    conn.execute(
        text("SELECT ops.adopt_pdf_companions('b',7,:attempt,'owner','exact')"),
        dict(attempt=attempt),
    )


def test_generated_set_replay_and_changed_duplicate_are_atomic(adoption):
    conn = adoption
    upload(conn, "one", 0)
    invoke(conn)
    invoke(conn)
    assert conn.scalar(text("SELECT count(*) FROM ops.pdf_stage_companion")) == 1
    conn.execute(
        text(
            'UPDATE pg_temp.pc_pdf_stage_companion SET body=body||\'{"pointer":"#/texts/1"}\'::jsonb'
        )
    )
    with pytest.raises(DBAPIError, match="changed companion duplicate"), conn.begin_nested():
        invoke(conn)
    assert conn.scalar(text("SELECT body->>'pointer' FROM ops.pdf_stage_companion")) == "#/texts/0"


@pytest.mark.parametrize(
    "mutation,message",
    [
        ("shape", "parsing record shape differs"),
        ("ordinal", "identity/order"),
        ("duplicate", "duplicate key"),
        ("fence", "stale owner"),
    ],
)
def test_generated_set_refuses_independent_invalid_inputs(adoption, mutation, message):
    conn = adoption
    upload(conn, "one", 0)
    if mutation == "shape":
        upload(conn, "two", 1, unknown=True)
    elif mutation == "ordinal":
        upload(conn, "two", 0)
    elif mutation == "duplicate":
        upload(conn, "one", 0)
    with pytest.raises(DBAPIError, match=message), conn.begin_nested():
        invoke(conn, 2 if mutation == "fence" else 1)
    assert conn.scalar(text("SELECT count(*) FROM ops.pdf_stage_companion")) == 0


def test_adoption_upload_limits_come_from_captured_physical_source(adoption):
    conn = adoption
    selected = copy(get_metadata())
    sources = dict(get_metadata().info["physical_sources"])
    staging = yaml.safe_load(sources["pdf-staging.yaml"])
    profile = json.loads(staging["annotations"]["pds:upload_profile"])
    profile["max_rows"] = 1
    staging["annotations"]["pds:upload_profile"] = json.dumps(profile)
    sources["pdf-staging.yaml"] = yaml.safe_dump(staging).encode()
    selected.info = {**get_metadata().info, "physical_sources": sources}
    execute_native_sql(conn, companion_adoption_sql(trusted_pdf_context(), selected))
    upload(conn, "one", 0)
    upload(conn, "two", 1)
    with pytest.raises(DBAPIError, match="upload profile exceeded"), conn.begin_nested():
        invoke(conn)


def test_generated_adoption_binds_against_actual_native_catalog(native_rollback):
    conn = native_rollback.connection
    from corpus_structure.semantic.native_objects import native_owner

    execute_native_sql(conn, "CREATE EXTENSION IF NOT EXISTS plpgsql_check VERSION '2.10'")
    with native_owner(conn, "corpus_sem_publisher"):
        execute_native_sql(conn, companion_adoption_sql(trusted_pdf_context(), get_metadata()))
        conn.exec_driver_sql("SELECT ops.prepare_pdf_companions()")
        failures = (
            conn.execute(
                text(
                    "SELECT message FROM public.plpgsql_check_function_tb("
                    "'ops.adopt_pdf_companions(text,bigint,bigint,text,text)'::regprocedure, fatal_errors=>false) "
                    "WHERE level='error'"
                )
            )
            .scalars()
            .all()
        )
        assert failures == []
    with native_owner(conn, "corpus_sem_reader"):
        with pytest.raises(DBAPIError) as refused, conn.begin_nested():
            invoke(conn)
        assert getattr(refused.value.orig, "sqlstate", None) == "42501"
