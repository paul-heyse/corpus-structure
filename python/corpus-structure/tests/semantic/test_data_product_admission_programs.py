"""Generated nominal packets and leaf projections retain custody and exact replay."""

import json

import pytest
from pglast import ast
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_product_admission_native import product_admission_native_sql
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
from corpus_structure.semantic.native_protocol_authoring import native_protocol_sources, native_sql
from corpus_structure.semantic.prepared_sql import prepare_sql


@pytest.fixture
def product_connection(infrastructure_rollback):
    connection = infrastructure_rollback
    for name in ("data", "ops", "sem", "kb"):
        connection.exec_driver_sql(f"CREATE SCHEMA {name}")
    for name in (
        "sem.data_kind_contract",
        "sem.data_kind_release",
        "kb.data_product",
        "kb.data_product_member",
        *(
            "kb.data_member_" + name
            for name in ("coordinate", "role", "endpoint", "coverage", "choice")
        ),
    ):
        connection.execute(
            CreateTable(get_metadata().tables[name], include_foreign_key_constraints=[])
        )
    from corpus_structure.semantic.target_installation import foundation_programs

    identity = prepare_sql(foundation_programs().identity, source="product-identity-test-helpers")
    for i, statement in enumerate(identity.statements):
        node = statement.stmt
        if (
            isinstance(node, ast.CreateFunctionStmt)
            and node.funcname
            and node.funcname[-1].sval in {"canonical_json", "decimal_canonical"}
        ):
            execute_native_sql(connection, identity.excerpt(i))
    parsed = prepare_sql(
        native_sql(native_protocol_sources()), source="product-realization-test-helpers"
    )
    for i, statement in enumerate(parsed.statements):
        node = statement.stmt
        if (
            isinstance(node, ast.CreateFunctionStmt)
            and node.funcname
            and node.funcname[-1].sval
            in {
                "ddo_fields",
                "ddo_normalize",
                "ddo_json_meaning",
                "ddo_identity",
                "ddo_digest",
                "ddo_authorize",
                "ddo_require_subject_source",
                "ddo_field",
                "ddo_json",
                "ddo_kind_access",
                "ddo_body_kind_contracts",
                "ddo_body_access",
            }
        ):
            execute_native_sql(connection, parsed.excerpt(i))
    # This isolated database intentionally omits request/source tables. The
    # directly tested product program uses real codecs, policy and schemas.
    selected = prepare_sql(
        product_admission_native_sql(get_metadata()), source="product-realization"
    )
    for i, statement in enumerate(selected.statements):
        node = statement.stmt
        if (
            isinstance(node, ast.CreateFunctionStmt)
            and node.funcname
            and node.funcname[-1].sval == "ddo_install_product_context"
        ):
            execute_native_sql(connection, selected.excerpt(i))
    for name, member_schema, member_contracts in (
        ("container", {}, ["leaf"]),
        ("leaf", {"not": {}}, []),
    ):
        connection.execute(
            insert(get_metadata().tables["sem.data_kind_contract"]).values(
                kind_contract=name,
                kind="urn:" + name,
                body_schema={},
                meaning_schema={},
                member_schema=member_schema,
                member_contracts=member_contracts,
                families=["coordinate", "role", "endpoint", "coverage", "choice"],
                universe="ordinary",
            )
        )
        connection.execute(
            insert(get_metadata().tables["sem.data_kind_release"]).values(
                release_id="release", kind_contract=name
            )
        )
    yield connection


def product_packet(member_ids=("one",)):
    context = {
        "project_id": "project",
        "release_id": "release",
        "subject": "root",
        "subject_definition": "project-subject",
        "original_source": "source",
        "analyzed_scope": None,
    }
    member_context = {
        key: value for key, value in context.items() if key not in {"project_id", "release_id"}
    }
    # Declared physical leaves are BIGINT. Values above int4's maximum must not
    # acquire a separate, narrower SQL cast boundary.
    fields = {
        "coordinates": [{"original_source": "source", "start": 2**33, "end": 2**33 + 1, "page": 1}],
        "roles": [{"role": "item", "position": 2**33, "multiplicity": 1}],
        "endpoints": [{"scope": "local", "role": "self", "member_id": "one"}],
        "coverage": [{"scope": "whole", "start": 2**33, "end": 2**33 + 1, "complete": True}],
        "choices": [{"choice_group": "group", "alternative": "a", "selected": True}],
    }
    member = {
        "kind_contract": "leaf",
        "context": member_context,
        "body": fields,
        **fields,
    }
    canonical_packet = {key: member[key] for key in ("kind_contract", "context", "body")}
    return context, {
        "kind_contract": "container",
        "body": semantic_value(
            {"members": [dict(canonical_packet, member_id=identity) for identity in member_ids]}
        ),
        "members": [
            dict(member, member_id=identity, body=semantic_value(fields)) for identity in member_ids
        ],
    }


def realize(connection, context, packet):
    return connection.scalar(
        text(
            'SELECT ops.ddo_install_product_context(CAST(:context AS jsonb),CAST(:packet AS jsonb),\'{"project-subject":"project"}\')'
        ),
        {"context": json.dumps(context), "packet": json.dumps(packet)},
    )


def test_product_member_families_are_exact_idempotent_and_use_declared_leaf_types(
    product_connection,
):
    context, packet = product_packet()
    first = realize(product_connection, context, packet)
    assert realize(product_connection, context, packet) == first
    for name in (
        "data_product",
        "data_product_member",
        *(
            "data_member_" + name
            for name in ("coordinate", "role", "endpoint", "coverage", "choice")
        ),
    ):
        assert product_connection.scalar(text("SELECT count(*) FROM kb." + name)) == 1
    assert product_connection.scalar(text("SELECT start FROM kb.data_member_coordinate")) == 2**33
    assert product_connection.execute(
        text("SELECT endpoint_product,endpoint_member FROM kb.data_member_endpoint")
    ).one() == (first, "one")
    product_connection.execute(text("UPDATE kb.data_member_role SET position=3"))
    with (
        pytest.raises(DBAPIError, match="identity collision at ordinal") as refusal,
        product_connection.begin_nested(),
    ):
        realize(product_connection, context, packet)
    assert getattr(refusal.value.orig, "sqlstate", None) == "23514"


def test_product_member_projection_refuses_changes_and_evaluator_role_crossing(product_connection):
    context, packet = product_packet()
    packet["members"][0]["coordinates"] = []
    with (
        pytest.raises(DBAPIError, match="projection differs") as refusal,
        product_connection.begin_nested(),
    ):
        realize(product_connection, context, packet)
    assert getattr(refusal.value.orig, "sqlstate", None) == "P0001"
    assert product_connection.scalar(text("SELECT count(*) FROM kb.data_product")) == 0
    product_connection.execute(
        text("UPDATE sem.data_kind_contract SET universe='evaluator' WHERE kind_contract='leaf'")
    )
    product_connection.exec_driver_sql("GRANT USAGE ON SCHEMA data,ops,sem,kb TO corpus_sem_writer")
    context, packet = product_packet()
    with (
        pytest.raises(DBAPIError, match="evaluator data requires") as denied,
        product_connection.begin_nested(),
        native_owner(product_connection, "corpus_sem_writer"),
    ):
        realize(product_connection, context, packet)
    assert getattr(denied.value.orig, "sqlstate", None) == "42501"


def test_product_members_require_the_same_finite_ordered_packet(product_connection):
    context, packet = product_packet(("one", "two"))
    removed = dict(packet, members=packet["members"][:1])
    swapped = dict(packet, members=packet["members"][::-1])
    for invalid, message in (
        (removed, "body/member projection count disagreement"),
        (swapped, "member context/body differs from canonical container packet"),
    ):
        with (
            pytest.raises(DBAPIError, match=message) as refusal,
            product_connection.begin_nested(),
        ):
            realize(product_connection, context, invalid)
        assert getattr(refusal.value.orig, "sqlstate", None) == "P0001"
        assert product_connection.scalar(text("SELECT count(*) FROM kb.data_product_member")) == 0
    product = realize(product_connection, context, packet)
    assert product_connection.execute(
        text(
            "SELECT member_id FROM kb.data_product_member WHERE product_id=:id ORDER BY member_id"
        ),
        {"id": product},
    ).scalars().all() == ["one", "two"]


def test_generated_product_admission_binds_in_actual_native_model(native_rollback):
    connection = native_rollback.connection
    execute_native_sql(connection, "CREATE EXTENSION IF NOT EXISTS plpgsql_check VERSION '2.10'")
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, product_admission_native_sql(get_metadata()))
        for signature in (
            "ops.ddo_install_product_context(jsonb,jsonb,jsonb)",
            "ops.ddo_admit_original_source(jsonb)",
            "ops.admit_authored_data(jsonb)",
            "ops.admit_original_document_asset(jsonb)",
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
        for name, kind in (
            ("admit_authored_data", "original-document"),
            ("admit_original_document_asset", "authored-fact"),
        ):
            with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
                connection.execute(
                    text("SELECT ops." + name + "(CAST(:p AS jsonb))"),
                    {"p": json.dumps({"reference": {"kind": kind}})},
                )
            assert getattr(refusal.value.orig, "sqlstate", None) == "P0001"


def test_product_programs_retain_typed_bodies_and_follow_captured_member_schema():
    from copy import copy

    import yaml

    from corpus_structure.semantic.data_product_admission_native import (
        product_admission_native_programs,
    )

    model = get_metadata()
    programs = product_admission_native_programs(model)
    assert [(program.name, program.argument_types) for program in programs] == [
        ("ddo_install_product_context", ("jsonb", "jsonb", "jsonb")),
        ("ddo_admit_original_source", ("jsonb",)),
        ("admit_authored_data", ("jsonb",)),
        ("admit_original_document_asset", ("jsonb",)),
    ]
    captured = copy(model)
    captured.info = dict(model.info)
    captured.info["physical_sources"] = dict(model.info["physical_sources"])
    protocol = yaml.safe_load(captured.info["physical_sources"]["data-operation-native.yaml"])
    protocol["definitions"]["coordinate"]["required"].append("page")
    captured.info["physical_sources"]["data-operation-native.yaml"] = yaml.safe_dump(
        protocol
    ).encode()
    changed = product_admission_native_programs(captured)[0].render()
    assert (
        "ops.ddo_fields(family_value, ARRAY['original_source', 'start', 'end', 'page']" in changed
    )
    assert (
        "ops.ddo_fields(family_value, ARRAY['original_source', 'start', 'end'], ARRAY['page'])"
        in programs[0].render()
    )
