"""Release identity and receipt guards run typed programs on PostgreSQL."""

import json
from hashlib import sha256

import psycopg
import pytest
from sqlalchemy import Column, MetaData, Table, Text, func, literal, select, text
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
        assert "jsonb_array_elements" in checks and "'functions'" in checks
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


def test_catalog_programs_bind_the_explicit_physical_contract_relation():
    from types import SimpleNamespace

    from pglast import parse_plpgsql, parse_sql

    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.native_admission_release import physical_catalog_checks

    declared = metadata.tables["sem.physical_contract"].to_metadata(
        MetaData(), name="captured_physical_contract"
    )
    proposed = SimpleNamespace(tables={"sem.physical_contract": declared})
    source = function(
        "public",
        "captured_catalog_checks",
        parameters=(Parameter("expected", pg_type("jsonb")),),
        returns=pg_type("void"),
        body=Block(physical_catalog_checks(proposed), (Local("spec", pg_type("jsonb")),)),
    )
    assert parse_sql(source) and parse_plpgsql(source)
    assert "sem.captured_physical_contract" in source
    assert "FROM sem.physical_contract " not in source


@pytest.fixture
def catalog_program_connection(infrastructure_rollback):
    from sqlalchemy.schema import CreateTable

    from corpus_structure.semantic.native_admission_release import (
        index_catalog_checks,
        native_check_catalog_checks,
        physical_catalog_checks,
        trigger_catalog_checks,
    )

    connection = infrastructure_rollback
    connection.execute(CreateSchema("catalog_admission_control"))
    connection.exec_driver_sql(
        "CREATE TABLE catalog_admission_control.items ("
        "value integer,other integer,CONSTRAINT positive_value CHECK (value>0))"
    )
    connection.exec_driver_sql(
        "CREATE INDEX item_value_idx ON catalog_admission_control.items(value)"
    )
    connection.exec_driver_sql(
        "CREATE VIEW catalog_admission_control.projected AS SELECT 1 AS value"
    )
    connection.exec_driver_sql(
        "CREATE FUNCTION catalog_admission_control.touch() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER positive_guard BEFORE UPDATE OF value,other "
        "ON catalog_admission_control.items FOR EACH ROW "
        "EXECUTE FUNCTION catalog_admission_control.touch('first','second')"
    )
    contract = Table(
        "catalog_contract",
        MetaData(),
        Column("physical_id", Text),
        Column("source_digest", Text),
        Column("checks", JSONB),
        schema="pg_temp",
    )
    connection.execute(CreateTable(contract))
    checks = [
        dict(
            relation="catalog_admission_control.items",
            name="positive_value",
            expression="(value > 0)",
        )
    ]
    connection.execute(
        contract.insert().values(
            physical_id="physical:control", source_digest="checks:control", checks=checks
        )
    )
    from types import SimpleNamespace

    target = SimpleNamespace(tables={"sem.physical_contract": contract})
    statements = (
        *physical_catalog_checks(target),
        *trigger_catalog_checks(),
        *index_catalog_checks(),
        *native_check_catalog_checks(),
    )
    source = function(
        "pg_temp",
        "admit_catalog_programs",
        parameters=(Parameter("expected", pg_type("jsonb")),),
        returns=pg_type("void"),
        body=Block(statements, (Local("spec", pg_type("jsonb")),)),
        search_path=("pg_catalog", "pg_temp"),
    )
    execute_native_sql(connection, source)
    expected = dict(
        physical_id="physical:control",
        physical_checks_source_digest="checks:control",
        physical_relations=["catalog_admission_control.items"],
        views=[dict(relation="catalog_admission_control.projected", query="SELECT 1 AS value")],
        triggers=[
            dict(
                relation="catalog_admission_control.items",
                name="positive_guard",
                function="catalog_admission_control.touch()",
                type=19,
                deferrable=False,
                deferred=False,
                columns=["value", "other"],
                when=None,
                args=b"first\0second\0".hex(),
            )
        ],
        indexes=[
            dict(
                index="catalog_admission_control.item_value_idx",
                relation="catalog_admission_control.items",
                definition="CREATE INDEX item_value_idx ON catalog_admission_control.items USING btree (value)",
            )
        ],
        checks=[
            dict(
                relation="catalog_admission_control.items",
                name="positive_value",
                definition="CHECK ((value > 0))",
            )
        ],
    )
    return connection, contract, checks, expected


def test_catalog_programs_accept_exact_independent_declarations(catalog_program_connection):
    connection, _, _, expected = catalog_program_connection
    connection.execute(
        text("SELECT pg_temp.admit_catalog_programs(CAST(:expected AS jsonb))"),
        {"expected": json.dumps(expected)},
    )


@pytest.mark.parametrize(
    "defect,diagnostic",
    [
        ("source", "physical CHECK contract is unavailable"),
        (
            "expression",
            "physical CHECK expression differs: catalog_admission_control.items.positive_value",
        ),
        ("extra-check", "unexpected physical CHECK"),
        ("view", "native selected-fact view differs"),
        (
            "trigger-columns",
            "native execution guard differs: catalog_admission_control.items.positive_guard",
        ),
        (
            "trigger-args",
            "native execution guard differs: catalog_admission_control.items.positive_guard",
        ),
        (
            "trigger-type",
            "native execution guard differs: catalog_admission_control.items.positive_guard",
        ),
        ("index", "native source search index differs"),
        ("check-definition", "native CHECK expression differs: catalog_admission_control.items"),
    ],
)
def test_catalog_programs_refuse_changed_catalog_or_expected_fact(
    catalog_program_connection, defect, diagnostic
):
    connection, contract, checks, expected = catalog_program_connection
    if defect == "source":
        expected["physical_checks_source_digest"] = "another-source"
    elif defect == "expression":
        checks[0]["expression"] = "(value >= 0)"
        connection.execute(contract.update().values(checks=checks))
    elif defect == "extra-check":
        connection.exec_driver_sql(
            "ALTER TABLE catalog_admission_control.items ADD CONSTRAINT extra_positive CHECK(other>0)"
        )
    elif defect == "view":
        expected["views"][0]["query"] = "SELECT 2 AS value"
    elif defect == "trigger-columns":
        expected["triggers"][0]["columns"].reverse()
    elif defect == "trigger-args":
        expected["triggers"][0]["args"] = b"first\0changed\0".hex()
    elif defect == "trigger-type":
        expected["triggers"][0]["type"] = 17
    elif defect == "index":
        expected["indexes"][0]["definition"] += " WHERE value>1"
    else:
        expected["checks"][0]["definition"] = "CHECK ((value >= 0))"
    with (
        pytest.raises(DBAPIError, match=diagnostic.replace(".", r"\.")) as captured,
        connection.begin_nested(),
    ):
        connection.execute(
            text("SELECT pg_temp.admit_catalog_programs(CAST(:expected AS jsonb))"),
            {"expected": json.dumps(expected)},
        )
    assert isinstance(captured.value.orig, psycopg.Error)
    assert captured.value.orig.sqlstate == "23514"
