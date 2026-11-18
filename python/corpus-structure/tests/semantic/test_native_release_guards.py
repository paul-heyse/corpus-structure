"""Release identity and receipt guards run typed programs on PostgreSQL."""

import json
from hashlib import sha256

import pytest
from sqlalchemy import Column, MetaData, Table, Text, func, literal, select
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateSchema

from corpus_structure.semantic.native_admission import catalog_checks
from corpus_structure.semantic.native_admission_release import (
    native_receipt_admission,
    release_preconditions,
)
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.native_products import admission_kernel, function_bodies
from corpus_structure.semantic.native_program import Block, Do, Local, Parameter, function, pg_type
from native_test_support import principal_engine


@pytest.fixture
def release_guard_context(infrastructure_commit_engine):
    metadata = MetaData()
    release = Table("release", metadata, Column("release_id", Text, primary_key=True), schema="sem")
    finalized = Table(
        "release_finalization", metadata, Column("release_id", Text, primary_key=True), schema="sem"
    )
    receipt = Table(
        "deployment_admission",
        metadata,
        Column("release_id", Text, primary_key=True),
        Column("physical_id", Text, primary_key=True),
        Column("deployment_id", Text, primary_key=True),
        Column("kind", Text),
        Column("content", BYTEA),
        schema="sem",
    )
    with infrastructure_commit_engine.begin() as connection:
        connection.execute(CreateSchema("sem"))
        connection.execute(CreateSchema("data"))
        metadata.create_all(connection)
        # Independent callees isolate the generated admission orchestration.
        connection.exec_driver_sql("""
            CREATE FUNCTION sem.require_execution_projection(text) RETURNS void LANGUAGE plpgsql AS $$ BEGIN RETURN; END $$;
            CREATE FUNCTION data.execution_contract_descriptor() RETURNS jsonb LANGUAGE sql AS $$ SELECT '{"physical_id":"physical-control"}'::jsonb $$;
            CREATE FUNCTION sem.record_deployment_admission(text,text,text,text,bytea) RETURNS void LANGUAGE sql AS $$
            INSERT INTO sem.deployment_admission(release_id,physical_id,deployment_id,kind,content) VALUES($1,$2,$3,$4,$5) $$;
        """)
        connection.exec_driver_sql(
            function(
                "public",
                "admission_receipt_control",
                parameters=tuple(
                    Parameter(name, pg_type(kind))
                    for name, kind in (("r", "text"), ("expected", "jsonb"), ("owner_name", "text"))
                ),
                returns=pg_type("void"),
                body=Block(native_receipt_admission(metadata)),
                security_definer=True,
                search_path=("pg_catalog", "pg_temp"),
            )
        )
    return infrastructure_commit_engine, metadata, release, finalized, receipt


def test_release_preconditions_preserve_finalization_and_unknown_release_refusals(
    release_guard_context,
):
    engine, metadata, release, finalized, _ = release_guard_context
    program = Do(
        Block(
            release_preconditions(metadata),
            locals=(
                Local("r", pg_type("text"), literal("release-control", Text())),
                Local("expected", pg_type("jsonb")),
            ),
        )
    )
    with engine.begin() as connection:
        with pytest.raises(DBAPIError, match="release is not finalized"), connection.begin_nested():
            execute_native_sql(connection, program)
        connection.execute(finalized.insert().values(release_id="release-control"))
        with (
            pytest.raises(DBAPIError, match="unknown execution release"),
            connection.begin_nested(),
        ):
            execute_native_sql(connection, program)
        connection.execute(release.insert().values(release_id="release-control"))
        execute_native_sql(connection, program)


def test_native_receipt_requires_exact_identity_and_restricted_first_admission(
    release_guard_context, native_settings
):
    engine, _, _, _, receipt = release_guard_context
    expected = {"physical_id": "physical-control", "detail": [1, None, "exact-bytes"]}

    def admission(value):
        return select(
            func.public.admission_receipt_control(
                "release-control",
                literal(value, JSONB()),
                "corpus_sem_publisher",
            )
        )

    with engine.begin() as connection:
        connection.execute(admission(expected))
        row = connection.execute(select(receipt)).mappings().one()
        assert row["deployment_id"] == sha256(row["content"]).hexdigest()
        assert json.loads(row["content"]) == expected
        assert (row["release_id"], row["physical_id"], row["kind"]) == (
            "release-control",
            "physical-control",
            "native",
        )
        connection.execute(admission(expected))
        assert connection.scalar(select(func.count()).select_from(receipt)) == 1
    reader = principal_engine(native_settings, "read", engine.url.database)
    try:
        with reader.connect() as connection:
            connection.execute(admission(expected))
            for changed in (
                {**expected, "physical_id": "other-physical"},
                {**expected, "detail": [1, None, "changed-bytes"]},
            ):
                with (
                    pytest.raises(DBAPIError, match="restricted admission phase") as refusal,
                    connection.begin_nested(),
                ):
                    connection.execute(admission(changed))
                assert getattr(refusal.value.orig, "sqlstate", None) == "42501"
    finally:
        reader.dispose()


def test_catalog_extraction_retains_exact_old_and_current_catalog_area():
    from corpus_structure.semantic.migrations import ALEMBIC_DIR

    old = (ALEMBIC_DIR / "versions" / "semantic_ddo_pe_n7_admission.sql").read_text()
    current = admission_kernel()
    for source in (old, current):
        body = function_bodies(source)["data.require_execution_release"]
        checks = catalog_checks(body)
        assert "sem.physical_contract" in checks
        assert "jsonb_array_elements(expected->'functions')" in checks
        assert "sem.record_deployment_admission" not in checks
        assert "release is not finalized" not in checks


def test_release_semantic_guards_follow_explicit_physical_relations():
    from types import SimpleNamespace

    from pglast import parse_plpgsql, parse_sql

    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.native_admission_release import release_semantic_checks

    captured_artifact = metadata.tables["sem.artifact"].to_metadata(
        MetaData(), name="captured_artifact"
    )
    proposed = SimpleNamespace(tables={**metadata.tables, "sem.artifact": captured_artifact})
    source = function(
        "public",
        "captured_release_semantics",
        parameters=(Parameter("r", pg_type("text")), Parameter("expected", pg_type("jsonb"))),
        returns=pg_type("void"),
        body=Block(release_semantic_checks(proposed)),
        search_path=("pg_catalog", "pg_temp"),
    )
    assert parse_sql(source) and parse_plpgsql(source)
    assert "sem.captured_artifact" in source
    assert "FROM sem.artifact" not in source
    for refusal in (
        "release contains unresolved or unchecked required semantics",
        "required authored SQL lacks exact current physical admission",
        "archived DDO native constraint projection is missing or incompatible",
        "unsupported required native constraint scope or pattern",
        "unsupported required native binary inference profile",
        "target archive contains legacy execution model",
    ):
        assert refusal in source
