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
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.value_codec import decimal_digit_limit


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
        "kb.data_product_partition",
        *(
            "kb.data_member_" + name
            for name in ("coordinate", "role", "endpoint", "coverage", "choice")
        ),
    ):
        connection.execute(
            CreateTable(get_metadata().tables[name], include_foreign_key_constraints=[])
        )
    from corpus_structure.semantic.target_installation import foundation_programs

    identity = prepare_sql(
        foundation_programs(get_metadata(), decimal_digits=decimal_digit_limit()).identity,
        source="product-identity-test-helpers",
    )
    for i, statement in enumerate(identity.statements):
        node = statement.stmt
        if (
            isinstance(node, ast.CreateFunctionStmt)
            and node.funcname
            and node.funcname[-1].sval in {"canonical_json", "decimal_canonical"}
        ):
            execute_native_sql(connection, identity.excerpt(i))
    from corpus_structure.semantic.closure_native import closure_foundation_parts
    from corpus_structure.semantic.data_operation_read_native import read_native_programs
    from corpus_structure.semantic.data_operation_value_native import data_operation_value_programs
    from corpus_structure.semantic.demand_authority_native import demand_authority_programs
    from corpus_structure.semantic.native_objects import native_sql_script
    from corpus_structure.semantic.support_trust_native import support_trust_native_programs

    helpers = (
        *closure_foundation_parts(get_metadata()),
        *data_operation_value_programs(),
        *support_trust_native_programs(get_metadata()),
        *read_native_programs(get_metadata()),
        *demand_authority_programs(get_metadata(), subject_scopes=("project", "original-source")),
    )
    required_helpers = {
        "require_float_lexical",
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
    parsed = prepare_sql(
        native_sql_script(
            item.render() for item in helpers if item.routine.name in required_helpers
        ),
        source="product-realization-test-helpers",
    )
    for i, statement in enumerate(parsed.statements):
        node = statement.stmt
        if (
            isinstance(node, ast.CreateFunctionStmt)
            and node.funcname
            and node.funcname[-1].sval
            in {
                "require_float_lexical",
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
            and node.funcname[-1].sval
            in {
                "ddo_partition_field",
                "ddo_install_product_partitions",
                "ddo_acquired_product_partition",
                "ddo_install_product_context",
            }
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
    from corpus_structure.semantic.native_authoring import physical_row_type_context

    with physical_row_type_context(connection, get_metadata()):
        execute_native_sql(
            connection, "CREATE EXTENSION IF NOT EXISTS plpgsql_check VERSION '2.10'"
        )
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
        ("ddo_partition_field", ("jsonb", "text")),
        ("ddo_install_product_partitions", ("text", "jsonb", "jsonb", "jsonb", "boolean")),
        ("ddo_acquired_product_partition", ("text", "text", "text", "text")),
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
    changed = next(
        p
        for p in product_admission_native_programs(captured)
        if p.name == "ddo_install_product_context"
    ).render()
    assert (
        "ops.ddo_fields(family_value, ARRAY['original_source', 'start', 'end', 'page']" in changed
    )
    assert (
        "ops.ddo_fields(family_value, ARRAY['original_source', 'start', 'end'], ARRAY['page'])"
        in next(p for p in programs if p.name == "ddo_install_product_context").render()
    )


def partition_fixture(connection):
    from decimal import Decimal

    from corpus_structure.semantic.data_operation_partitions import (
        partition_header,
        partition_packet,
    )

    declaration = {
        "unit": "partitioned",
        "partition_key": "block",
        "item_order": ["start", "end"],
        "address": ["start", "end"],
        "field_groups": {"geometry": ["start", "end"], "labels": ["label", "optional"]},
    }
    specification = {
        "declarations": {"tokens": declaration},
        "schemas": {
            "tokens": {"body_schema": {"type": "object"}, "meaning_schema": {"type": "array"}}
        },
    }
    connection.execute(
        insert(get_metadata().tables["sem.data_kind_contract"]).values(
            kind_contract="partitioned",
            kind="urn:partitioned",
            body_schema={},
            meaning_schema={},
            member_schema={"not": {}},
            member_contracts=[],
            families=[],
            universe="ordinary",
            collections=specification,
        )
    )
    connection.execute(
        insert(get_metadata().tables["sem.data_kind_release"]).values(
            release_id="release", kind_contract="partitioned"
        )
    )
    bodies = [
        [{"start": 0, "end": 2, "label": "café", "fraction": 0.5}],
        [{"start": 0, "end": 1, "label": "東京", "fraction": Decimal("0.125"), "optional": None}],
        [{"start": 1, "end": 3, "label": "three"}],
    ]
    packets = [
        partition_packet("tokens", name, n, n * 10, n * 10 + 5, body)
        for n, (name, body) in enumerate(zip(("b", "a", "é"), bodies, strict=True))
    ]
    context, _ = product_packet()
    return (
        context,
        {
            "kind_contract": "partitioned",
            "body": semantic_value({"tokens": partition_header(packets)}),
            "members": [],
            "partitions": packets,
        },
        bodies,
        declaration,
    )


def test_partition_admission_recomputes_content_groups_and_roots(product_connection):
    from corpus_structure.semantic.data_operation_partitions import partition_group_digests

    context, packet, bodies, declaration = partition_fixture(product_connection)
    key = realize(product_connection, context, packet)
    assert realize(product_connection, context, packet) == key
    rows = product_connection.execute(
        text(
            "SELECT ordinal,partition_digest,item_count,group_digests,body FROM kb.data_product_partition WHERE product_id=:key ORDER BY ordinal"
        ),
        {"key": key},
    ).all()
    assert len(rows) == 3
    for n, row in enumerate(rows):
        assert row.ordinal == n and row.item_count == 1
        assert row.partition_digest == packet["partitions"][n]["partition_digest"]
        assert row.body == packet["partitions"][n]["body"]
        assert row.group_digests == partition_group_digests(bodies[n], declaration["field_groups"])

    from copy import deepcopy

    from corpus_structure.semantic.data_operation_identity import canonical_identity
    from corpus_structure.semantic.data_operation_partitions import partition_header

    shuffled = deepcopy(packet)
    shuffled["partitions"].reverse()
    assert realize(product_connection, context, shuffled) == key
    reordered_mapping = deepcopy(packet)
    rows = reordered_mapping["partitions"][0]["body"][1]
    assert isinstance(rows, list)
    item = rows[0]
    assert isinstance(item, list)
    fields = item[1]
    assert isinstance(fields, list)
    fields.reverse()
    assert realize(product_connection, context, reordered_mapping) == key

    edited = deepcopy(packet)
    edited_body = [dict(bodies[0][0], label="changed")]
    edited["partitions"][0]["body"] = semantic_value(edited_body)
    edited["partitions"][0]["partition_digest"] = canonical_identity("partition", edited_body).key
    edited["body"] = semantic_value({"tokens": partition_header(edited["partitions"])})
    edited_key = realize(product_connection, context, edited)
    assert edited_key != key
    edited_groups = product_connection.scalar(
        text(
            "SELECT group_digests FROM kb.data_product_partition WHERE product_id=:key AND ordinal=0"
        ),
        {"key": edited_key},
    )
    assert edited_groups["geometry"] == rows[0].group_digests["geometry"]
    assert edited_groups["labels"] != rows[0].group_digests["labels"]

    moved = deepcopy(packet)
    moved["partitions"][0]["placement"] = {"start": 100, "end": 105}
    moved["body"] = semantic_value({"tokens": partition_header(moved["partitions"])})
    moved_key = realize(product_connection, context, moved)
    assert moved_key != key
    assert (
        product_connection.scalar(
            text(
                "SELECT partition_digest FROM kb.data_product_partition WHERE product_id=:key AND ordinal=0"
            ),
            {"key": moved_key},
        )
        == rows[0].partition_digest
    )

    reordered = deepcopy(packet)
    reordered["partitions"][0]["ordinal"], reordered["partitions"][1]["ordinal"] = 1, 0
    original_header = partition_header(packet["partitions"])
    changed_header = partition_header(reordered["partitions"])
    assert original_header["root"] == changed_header["root"]
    assert original_header["placement_root"] != changed_header["placement_root"]
    reordered["body"] = semantic_value({"tokens": changed_header})
    assert realize(product_connection, context, reordered) != key


@pytest.mark.parametrize(
    "alteration",
    ["digest", "duplicate", "ordinal", "root", "list", "missing", "extra", "placement"],
)
def test_partition_admission_refuses_inconsistent_population_atomically(
    product_connection, alteration
):
    context, packet, _, _ = partition_fixture(product_connection)
    partitions = packet["partitions"]
    if alteration == "digest":
        partitions[0]["partition_digest"] = "partition:forged"
    elif alteration == "duplicate":
        partitions.append(partitions[0])
    elif alteration == "ordinal":
        partitions[0]["ordinal"] = 20
    elif alteration == "root":
        packet["body"] = semantic_value({"tokens": {"root": "forged"}})
    elif alteration == "list":
        packet["body"] = semantic_value({"tokens": []})
    elif alteration == "missing":
        partitions.pop()
    elif alteration == "extra":
        partitions[0]["collection"] = "undeclared"
    elif alteration == "placement":
        partitions[0]["placement"]["start"] += 1
    with pytest.raises(DBAPIError), product_connection.begin_nested():
        realize(product_connection, context, packet)
    assert product_connection.scalar(text("SELECT count(*) FROM kb.data_product_partition")) == 0
    assert product_connection.scalar(text("SELECT count(*) FROM kb.data_product")) == 0


def test_partition_replay_refuses_missing_stored_row(product_connection):
    context, packet, _, _ = partition_fixture(product_connection)
    key = realize(product_connection, context, packet)
    product_connection.execute(
        text("DELETE FROM kb.data_product_partition WHERE product_id=:key AND ordinal=0"),
        {"key": key},
    )
    with pytest.raises(DBAPIError, match="replay differs"), product_connection.begin_nested():
        realize(product_connection, context, packet)


def test_acquired_partition_lookup_keeps_parent_kind_and_project_authority(product_connection):
    context, packet, _, _ = partition_fixture(product_connection)
    key = realize(product_connection, context, packet)
    query = text("SELECT ops.ddo_acquired_product_partition(:key,:project,:collection,:partition)")
    parameters = {"key": key, "project": "project", "collection": "tokens", "partition": "a"}
    result = product_connection.scalar(query, parameters)
    assert result["partition_key"] == "a" and result["body"] == packet["partitions"][1]["body"]
    for replacement in ({"project": "foreign"}, {"partition": "missing"}):
        with pytest.raises(DBAPIError), product_connection.begin_nested():
            product_connection.scalar(query, parameters | replacement)
    product_connection.execute(
        text(
            "UPDATE sem.data_kind_contract SET universe='evaluator' WHERE kind_contract='partitioned'"
        )
    )
    product_connection.exec_driver_sql("GRANT USAGE ON SCHEMA data,ops,sem,kb TO corpus_sem_writer")
    with (
        pytest.raises(DBAPIError),
        product_connection.begin_nested(),
        native_owner(product_connection, "corpus_sem_writer"),
    ):
        product_connection.scalar(query, parameters)
