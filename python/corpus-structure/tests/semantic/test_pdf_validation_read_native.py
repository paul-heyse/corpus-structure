"""Rollback PostgreSQL controls for captured PDF folds and frozen-check dispatch."""

import json
from copy import copy
from hashlib import sha256
from typing import Any

import psycopg
import pytest
from pglast import ast, parse_sql
from pglast.stream import RawStream
from sqlalchemy import Column, MetaData, Table, UniqueConstraint, func, literal, select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.pdf_binary_identity_native import pdf_binary_identity_sql
from corpus_structure.semantic.pdf_contracts import integrated_metadata_policy, trusted_pdf_context
from corpus_structure.semantic.pdf_record_identity import IdentityFold
from corpus_structure.semantic.pdf_validation_read_native import (
    _equal_rows,
    pdf_validation_native_programs,
)
from corpus_structure.semantic.value_codec import decimal_digit_limit


@pytest.fixture
def validation_controls(infrastructure_engine, request):
    isolation = getattr(request, "param", "READ COMMITTED")
    with infrastructure_engine.connect().execution_options(isolation_level=isolation) as connection:
        transaction = connection.begin()
        try:
            for name in ("ops", "kb", "sem", "data"):
                connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS " + name)
            controls = MetaData()
            for name in (
                "sem.input",
                "ops.pdf_stage_build",
                "ops.pdf_validation_check",
                "ops.pdf_published_revision",
                "ops.pdf_build_validation",
                "ops.pdf_frozen_build",
                "ops.task",
                "ops.data_derivation",
                "kb.pdf_record_access",
                "kb.pdf_record_region",
                "ops.pdf_record_document",
                "kb.pdf_record_native",
                "kb.pdf_record_membership",
                "ops.pdf_artifact_stream",
            ):
                owner = get_metadata().tables[name]
                table = Table(
                    owner.name,
                    controls,
                    *(Column(c.name, c.type) for c in owner.columns),
                    schema=owner.schema,
                )
                if name == "ops.pdf_validation_check":
                    table.append_constraint(
                        UniqueConstraint("build_id", "attempt", "holder", "check_name")
                    )
            controls.create_all(connection)
            from corpus_structure.semantic.target_installation import foundation_programs

            for source, selected in (
                (
                    foundation_programs(
                        get_metadata(), decimal_digits=decimal_digit_limit()
                    ).identity,
                    {"canonical_json"},
                ),
                (
                    pdf_binary_identity_sql(),
                    {
                        "pdf_identity_frame",
                        "pdf_identity_fold_start",
                        "pdf_identity_fold_step",
                        "pdf_identity_fold_finish",
                    },
                ),
            ):
                for statement in parse_sql(source):
                    node = statement.stmt
                    if (
                        isinstance(node, ast.CreateFunctionStmt)
                        and node.funcname
                        and node.funcname[-1].sval in selected
                    ):
                        execute_native_sql(connection, RawStream()(node))
            connection.exec_driver_sql("""
                CREATE TEMP TABLE control_events(event text);
                CREATE TEMP TABLE control_contexts(task bigint,project_id text);
                CREATE TEMP TABLE control_oracle(receipt text);
                INSERT INTO control_oracle VALUES('actual-oracle');
                CREATE FUNCTION ops.require_pdf_stage_owner(bigint,bigint,text) RETURNS void LANGUAGE plpgsql AS $$
                BEGIN INSERT INTO control_events VALUES('owner'); END $$;
                CREATE FUNCTION ops.require_pdf_frozen(p_build text,bigint,bigint,text,text)
                RETURNS ops.pdf_stage_build LANGUAGE plpgsql AS $$
                DECLARE b ops.pdf_stage_build; BEGIN
                INSERT INTO control_events VALUES('frozen');
                SELECT * INTO STRICT b FROM ops.pdf_stage_build WHERE build_id=p_build; RETURN b; END $$;
                CREATE FUNCTION ops.require_pdf_operation(text,text) RETURNS void LANGUAGE plpgsql AS $$
                BEGIN INSERT INTO control_events VALUES('operation'); END $$;
                CREATE FUNCTION ops.read_pdf_certification_requirement(text,bigint,bigint,text,text)
                RETURNS TABLE(oracle_receipt_id text) LANGUAGE sql AS $$ SELECT receipt FROM control_oracle $$;
                CREATE FUNCTION ops.pdf_task_context(p_task bigint) RETURNS TABLE(project_id text)
                LANGUAGE sql AS $$ SELECT project_id FROM control_contexts WHERE task=p_task $$;
                CREATE FUNCTION ops.ddo_node_valid(text,text) RETURNS boolean LANGUAGE sql AS $$ SELECT true $$;
                CREATE FUNCTION ops.pdf_check_build_inventory(text,text,text) RETURNS void LANGUAGE plpgsql AS $$
                BEGIN INSERT INTO control_events VALUES('inventory'); END $$;
                CREATE FUNCTION ops.pdf_check_access_correspondence(text) RETURNS void LANGUAGE plpgsql AS $$
                BEGIN INSERT INTO control_events VALUES('access'); END $$;
                CREATE FUNCTION ops.pdf_record_logical_identity(text,text) RETURNS text LANGUAGE sql AS $$ SELECT repeat('a',64) $$;
            """)
            programs = pdf_validation_native_programs(
                get_metadata(), pdf_domain=trusted_pdf_context().domain
            )
            for program in programs.values():
                execute_native_sql(connection, program)
            dependencies = [("β", b"second"), ("A", b"first")]
            connection.execute(
                get_metadata().tables["sem.input"].insert(),
                [
                    dict(
                        release_id="release",
                        input_kind="dependency",
                        input_name=name,
                        content=content,
                    )
                    for name, content in dependencies
                ],
            )
            connection.execute(
                get_metadata().tables["ops.pdf_stage_build"].insert(),
                dict(
                    build_id="build",
                    task_id=1,
                    attempt=2,
                    holder="holder",
                    release_id="release",
                    state="frozen",
                    source_digest="source",
                    schema_digest="schema",
                    recipe_digest="recipe",
                ),
            )
            connection.exec_driver_sql("INSERT INTO control_contexts VALUES(1,'project')")
            yield connection, dependencies
        finally:
            transaction.rollback()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def test_contract_folds_match_independent_frames_and_projection_multisets(validation_controls):
    connection, dependencies = validation_controls
    import yaml

    staging = yaml.safe_load(get_metadata().info["physical_sources"]["pdf-staging.yaml"])
    profile = json.loads(staging["annotations"]["pds:projection_write_profile"])
    levels = sorted(set(profile["allowed_isolation"]))
    expected = IdentityFold("pdf-validation-contract-v5")
    for name, content in sorted(dependencies, key=lambda item: item[0].encode()):
        encoded = name.encode()
        expected.add(len(encoded).to_bytes(8, "big") + encoded + sha256(content).digest())
    expected.add(
        b"pdf-projection-write-profile-v1"
        + sha256(canonical({"allowed_isolation": levels})).digest()
    )
    expected.add(
        b"pdf-integrated-metadata-policy-v1"
        + sha256(canonical(integrated_metadata_policy())).digest()
    )
    digest = expected.digest().hex()
    assert connection.scalar(select(func.ops.pdf_validation_contract("release"))) == digest
    with pytest.raises(DBAPIError, match="dependencies missing"), connection.begin_nested():
        connection.scalar(select(func.ops.pdf_validation_contract("absent")))

    access = get_metadata().tables["kb.pdf_record_access"]
    row: dict[str, Any] = {column.name: None for column in access.columns}
    row.update(product_id="build", revision_id="build", pointer="#/β")
    connection.execute(
        access.insert(), [row, row | {"product_id": "other", "revision_id": "other"}]
    )
    body = canonical(
        {key: value for key, value in row.items() if key not in {"product_id", "revision_id"}}
    )
    projection = IdentityFold("pdf-validation-projection-v1")
    projection.add(bytes.fromhex(digest))
    projection.add(b"access" + sha256(body).digest())
    assert (
        connection.scalar(select(func.ops.pdf_projection_contract("build", "release")))
        == projection.digest().hex()
    )
    connection.execute(access.insert(), row)
    projection.add(b"access" + sha256(body).digest())
    assert (
        connection.scalar(select(func.ops.pdf_projection_contract("build", "release")))
        == projection.digest().hex()
    )


def test_frozen_check_order_dispatch_replay_missing_oracle_and_stale_witness(validation_controls):
    connection, _ = validation_controls

    def check(name):
        connection.scalar(select(func.ops.check_pdf_build("build", 1, 2, "holder", "frozen", name)))

    with pytest.raises(DBAPIError, match="seal missing or stale"), connection.begin_nested():
        check("identity")
    connection.exec_driver_sql("DELETE FROM control_oracle")
    with pytest.raises(DBAPIError, match="no passed round-trip oracle"), connection.begin_nested():
        check("seal")
    connection.exec_driver_sql("INSERT INTO control_oracle VALUES('oracle')")
    check("seal")
    assert connection.scalars(text("SELECT event FROM control_events")).all() == [
        "owner",
        "frozen",
        "operation",
        "frozen",
    ]
    connection.exec_driver_sql("DELETE FROM control_events")
    for name in ("inventory", "access", "identity", "projection"):
        check(name)
    rows = connection.execute(
        text("SELECT check_name,result_digest FROM ops.pdf_validation_check ORDER BY check_name")
    ).all()
    assert {name for name, _ in rows} == {"seal", "inventory", "access", "identity", "projection"}
    assert dict(rows)["identity"] == "a" * 64
    assert dict(rows)["projection"] == connection.scalar(
        select(func.ops.pdf_projection_contract("build", "release"))
    )
    assert connection.scalars(text("SELECT event FROM control_events")).all() == [
        "frozen",
        "operation",
        "inventory",
        "owner",
        "frozen",
        "frozen",
        "operation",
        "access",
        "owner",
        "frozen",
        "frozen",
        "operation",
        "owner",
        "frozen",
        "frozen",
        "operation",
        "owner",
        "frozen",
    ]
    check("identity")
    assert connection.scalar(text("SELECT count(*) FROM ops.pdf_validation_check")) == 5
    with pytest.raises(DBAPIError, match="unknown frozen PDF check"), connection.begin_nested():
        check("unknown")
    connection.exec_driver_sql(
        "UPDATE ops.pdf_validation_check SET frozen_digest='stale' WHERE check_name='seal'"
    )
    with (
        pytest.raises(DBAPIError, match="result differs for sealed premises"),
        connection.begin_nested(),
    ):
        check("seal")


def test_typed_row_equivalence_preserves_json_number_spelling_and_duplicate_multiplicity(
    validation_controls,
):
    connection, _ = validation_controls
    connection.exec_driver_sql("""
        INSERT INTO kb.pdf_record_native(product_id,revision_id,record_id,scalars_json)
        VALUES('current','current','one','{"value":1}'::jsonb),('prior','prior','one','{"value":1.0}'::jsonb)
    """)
    equal = select(
        _equal_rows(get_metadata(), literal("current"), literal("prior"), "kb.pdf_record_native")
    )
    assert connection.scalar(equal) is False
    connection.exec_driver_sql(
        """UPDATE kb.pdf_record_native SET scalars_json='{"value":1}'::jsonb"""
    )
    assert connection.scalar(equal) is True
    connection.exec_driver_sql(
        "INSERT INTO kb.pdf_record_native SELECT * FROM kb.pdf_record_native WHERE product_id='current'"
    )
    assert connection.scalar(equal) is False


def test_predecessor_reuse_requires_exact_project_rows_and_foreign_revision_refuses_access_reuse(
    validation_controls,
):
    connection, _ = validation_controls
    contract = connection.scalar(select(func.ops.pdf_validation_contract("release")))
    connection.execute(get_metadata().tables["ops.task"].insert(), [{"id": 10}, {"id": 20}])
    connection.execute(
        get_metadata().tables["ops.data_derivation"].insert(),
        [
            {"id": "episode-10", "producer_task_id": 10},
            {"id": "episode-20", "producer_task_id": 20},
        ],
    )
    connection.exec_driver_sql(
        "INSERT INTO control_contexts VALUES(10,'project'),(20,'other-project')"
    )
    for name, task in (("prior", 10), ("other-project", 20)):
        connection.execute(
            get_metadata().tables["ops.pdf_published_revision"].insert(),
            dict(
                build_id=name,
                task_id=task,
                kind="native",
                frozen_digest="old-frozen",
                logical_digest="logical",
                source_digest="source",
                schema_digest="schema",
                recipe_digest="recipe",
                release_id="release",
            ),
        )
        connection.execute(
            get_metadata().tables["ops.pdf_build_validation"].insert(),
            dict(
                build_id=name,
                frozen_digest="old-frozen",
                logical_digest="logical",
                native_contract_digest=contract,
                native_callbacks=True,
                contract_digest="b" * 64,
            ),
        )
    connection.execute(
        get_metadata().tables["ops.pdf_frozen_build"].insert(),
        {"build_id": "build", "kind": "native"},
    )

    def check(name):
        connection.scalar(select(func.ops.check_pdf_build("build", 1, 2, "holder", "frozen", name)))

    check("seal")
    assert (
        connection.scalar(
            text(
                "SELECT predecessor_build_id FROM ops.pdf_validation_check WHERE check_name='seal'"
            )
        )
        == "prior"
    )
    check("access")
    check("projection")
    assert connection.execute(
        text(
            "SELECT check_name,predecessor_build_id FROM ops.pdf_validation_check ORDER BY check_name"
        )
    ).all() == [
        ("access", "prior"),
        ("projection", "prior"),
        ("seal", "prior"),
    ]
    assert (
        connection.scalar(
            text("SELECT result_digest FROM ops.pdf_validation_check WHERE check_name='projection'")
        )
        == "b" * 64
    )
    connection.exec_driver_sql("DELETE FROM ops.pdf_validation_check WHERE check_name='access'")
    connection.execute(
        get_metadata().tables["kb.pdf_record_access"].insert(),
        {"product_id": "build", "revision_id": "foreign"},
    )
    connection.exec_driver_sql("DELETE FROM control_events")
    check("access")
    assert (
        connection.scalar(
            text(
                "SELECT predecessor_build_id FROM ops.pdf_validation_check WHERE check_name='access'"
            )
        )
        is None
    )
    assert "access" in connection.scalars(text("SELECT event FROM control_events")).all()


@pytest.mark.parametrize("validation_controls", ["REPEATABLE READ"], indirect=True)
def test_check_isolation_policy_comes_from_supplied_capture(validation_controls, monkeypatch):
    connection, _ = validation_controls
    import yaml

    from corpus_structure.semantic import pdf_contracts

    domain = trusted_pdf_context().domain
    captured = copy(get_metadata())
    sources = dict(get_metadata().info["physical_sources"])
    staging = yaml.safe_load(sources["pdf-staging.yaml"])
    profile = json.loads(staging["annotations"]["pds:projection_write_profile"])
    profile["allowed_isolation"] = ["serializable"]
    staging["annotations"]["pds:projection_write_profile"] = json.dumps(profile)
    sources["pdf-staging.yaml"] = yaml.safe_dump(staging).encode()
    captured.info = {**get_metadata().info, "physical_sources": sources}

    def forbidden():
        raise AssertionError("explicit captured authoring must not reacquire current PDF context")

    monkeypatch.setattr(pdf_contracts, "trusted_pdf_context", forbidden)
    with pytest.raises(ValueError, match="read committed"):
        pdf_validation_native_programs(captured, pdf_domain=domain)
    program = pdf_validation_native_programs(get_metadata(), pdf_domain=domain)["check_build"]
    execute_native_sql(connection, program)
    with (
        pytest.raises(DBAPIError, match="requires READ COMMITTED") as failure,
        connection.begin_nested(),
    ):
        connection.scalar(
            select(func.ops.check_pdf_build("build", 1, 2, "holder", "frozen", "seal"))
        )
    assert isinstance(failure.value.orig, psycopg.Error)
    assert failure.value.orig.sqlstate == "25000"
