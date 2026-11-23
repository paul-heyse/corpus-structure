"""Generated nominal product admission retains custody and exact replay."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pglast import ast
from sqlalchemy import bindparam, insert, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
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
        "sem.data_rule",
        "kb.data_validity",
        "kb.data_product",
        "kb.data_product_member",
        "ops.data_request",
        "ops.data_completion_intent",
        "ops.data_retained_population",
        "ops.data_retained_population_item",
        "kb.data_product_population",
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
        "ddo_body_kind_contracts_impl",
        "ddo_body_kind_contracts",
        "ddo_body_access",
        "ddo_admitted_body_kind_contracts",
        "ddo_admitted_body_access",
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
            and node.funcname[-1].sval in required_helpers
        ):
            execute_native_sql(connection, parsed.excerpt(i))
    # The publisher programs use their real codecs, rules and schemas.
    # The fixture supplies only the original request and source-subject facts.
    connection.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_operation_subject(text,text) RETURNS text LANGUAGE sql "
        "AS $$ SELECT 'project-subject'::text $$"
    )
    from corpus_structure.semantic.data_operation_rule_native import rule_native_programs

    generated_rules = native_sql_script(
        program.render()
        for program in rule_native_programs(get_metadata())
        if program.name
        in {
            "ddo_rule_premise",
            "ddo_rule_violation",
            "ddo_establish_rule",
            "ddo_rule_expression",
            "ddo_rule_target_partition",
            "ddo_apply_product_rules",
        }
    )
    selected = prepare_sql(
        generated_rules + "\n" + product_admission_native_sql(get_metadata()),
        source="product-realization",
    )
    for i, statement in enumerate(selected.statements):
        node = statement.stmt
        if (
            isinstance(node, ast.CreateFunctionStmt)
            and node.funcname
            and node.funcname[-1].sval
            in {
                "ddo_partition_field",
                "ddo_require_empty_product_populations",
                "ddo_retain_population_rows",
                "ddo_promote_population_rows",
                "ddo_rule_premise",
                "ddo_rule_expression",
                "ddo_rule_target_partition",
                "ddo_rule_violation",
                "ddo_establish_rule",
                "ddo_apply_product_rules",
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
    fields = {"label": "retained member", "value": 2**33}
    member = {
        "kind_contract": "leaf",
        "context": member_context,
        "body": fields,
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


def _compact_fixture_population(connection, packet):
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_partitions import partition_group_digests

    specification = connection.scalar(
        text("SELECT collections FROM sem.data_kind_contract WHERE kind_contract=:kind"),
        {"kind": packet["kind_contract"]},
    )
    manifests, upload = [], []
    for partition in packet["partitions"]:
        body = decode_semantic_value(partition["body"])
        groups = specification["declarations"].get(partition["collection"], {}).get("field_groups", {})
        manifests.append(
            {
                **{key: value for key, value in partition.items() if key != "body"},
                "item_count": len(body),
                "group_digests": partition_group_digests(body, groups),
            }
        )
        upload.extend(
            {
                "output_role": "result",
                "output_position": 0,
                "collection": partition["collection"],
                "partition_key": partition["partition_key"],
                "item_ordinal": ordinal,
                "canonical_text": json_bytes(semantic_value(item)).decode(),
            }
            for ordinal, item in enumerate(body)
        )
    return {**packet, "partitions": manifests}, upload


def realize(connection, context, packet):
    from corpus_structure.semantic.data_operation_partition_native import population_scratch_specs

    intent = None
    if packet.get("partitions"):
        packet, upload = _compact_fixture_population(connection, packet)
        model = get_metadata()
        scratch, _ = population_scratch_specs(model)
        if connection.scalar(text("SELECT to_regclass(:scratch)"), {"scratch": scratch.qualified_name}) is None:
            connection.execute(scratch.create_statement())
        connection.exec_driver_sql("TRUNCATE TABLE pg_temp.ddo_population_upload")
        if upload:
            connection.execute(insert(scratch.row_table()), upload)
        intent = "fixture-intent:" + uuid4().hex
        connection.execute(
            insert(model.tables["ops.data_completion_intent"]).values(
                id=intent, request_id=intent, generation=1, producer_task_id=1, producer_attempt=1,
                producer_holder="fixture", runtime_id="fixture", payload={}, payload_digest="fixture",
                created_at=datetime.now(UTC),
            )
        )
        connection.execute(
            text(
                "SELECT ops.ddo_retain_population_rows("
                "jsonb_populate_record(NULL::ops.data_request,:context), :intent, :completion)"
            ).bindparams(bindparam("context", type_=JSONB()), bindparam("completion", type_=JSONB())),
            {
                "context": json.loads(json.dumps(context)),
                "intent": intent,
                "completion": {"outputs": [{"role": "result", "position": 0, "product": packet}]},
            },
        )
    return connection.scalar(
        text(
            """SELECT ops.ddo_install_product_context(
                :context, :packet, '{"project-subject":"project"}', :intent, 'result', 0::bigint)"""
        ).bindparams(bindparam("context", type_=JSONB()), bindparam("packet", type_=JSONB())),
        {"context": context, "packet": packet, "intent": intent},
    )


def test_product_members_are_exact_and_idempotent(product_connection):
    context, packet = product_packet()
    first = realize(product_connection, context, packet)
    assert realize(product_connection, context, packet) == first
    assert product_connection.scalar(text("SELECT count(*) FROM kb.data_product")) == 1
    assert product_connection.scalar(text("SELECT count(*) FROM kb.data_product_member")) == 1
    product_connection.execute(text("UPDATE kb.data_product_member SET body='[]'::jsonb"))
    with (
        pytest.raises(DBAPIError, match="member rows differ") as refusal,
        product_connection.begin_nested(),
    ):
        realize(product_connection, context, packet)
    assert getattr(refusal.value.orig, "sqlstate", None) == "23514"


def test_product_member_refuses_evaluator_role_crossing(product_connection):
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
    from corpus_structure.semantic.data_operation_rule_native import rule_native_programs
    from corpus_structure.semantic.native_authoring import physical_row_type_context
    from corpus_structure.semantic.native_objects import native_sql_script

    with physical_row_type_context(connection, get_metadata()):
        execute_native_sql(
            connection, "CREATE EXTENSION IF NOT EXISTS plpgsql_check VERSION '2.10'"
        )
        with native_owner(connection, "corpus_sem_publisher"):
            execute_native_sql(connection, product_admission_native_sql(get_metadata()))
            execute_native_sql(
                connection,
                native_sql_script(
                    routine.render() for routine in rule_native_programs(get_metadata())
                ),
            )
            for signature in (
                "ops.ddo_rule_premise(jsonb,text,text,text,text)",
                "ops.ddo_rule_violation(jsonb,text,text,text,text)",
                "ops.ddo_rule_target_partition(jsonb,text,text)",
                "ops.ddo_apply_product_rules(text,text,text)",
                "ops.ddo_apply_bound_product_rules(text,text,text,text)",
                "ops.establish_data_rule_proof(jsonb)",
                "ops.ddo_install_product_context(jsonb,jsonb,jsonb,text,text,bigint)",
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


def test_product_programs_have_typed_inputs():
    from corpus_structure.semantic.data_product_admission_native import (
        product_admission_native_programs,
    )

    model = get_metadata()
    programs = product_admission_native_programs(model)
    assert [(program.name, program.argument_types) for program in programs] == [
        ("ddo_partition_field", ("jsonb", "text")),
        ("ddo_require_empty_product_populations", ("jsonb", "jsonb")),
        ("ddo_require_population_scratch", ("text", "regclass", "text[]")),
        ("prepare_data_population_upload", ("text", "bigint", "bigint", "bigint", "text", "text")),
        ("ddo_require_population_upload", ("jsonb",)),
        ("ddo_retain_population_rows", ("ops.data_request", "text", "jsonb")),
        (
            "ddo_consume_population_upload",
            ("ops.data_request", "text", "jsonb", "jsonb", "boolean"),
        ),
        ("ddo_promote_population_rows", ("text", "text", "bigint", "text", "bigint")),
        ("ddo_install_product_context", ("jsonb", "jsonb", "jsonb", "text", "text", "bigint")),
        ("ddo_admit_original_source", ("jsonb",)),
        ("admit_authored_data", ("jsonb",)),
        ("admit_original_document_asset", ("jsonb",)),
    ]


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


def test_typed_population_copy_admits_once_and_promotes_exact_items(product_connection):
    import pyarrow as pa
    from corpus_structure.schema.integrity import role_name
    from corpus_structure.semantic.arrow_transfer import copy_arrow_stream
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_partitions import partition_group_digests
    from corpus_structure.semantic.data_operation_read_native import read_native_programs
    from corpus_structure.semantic.data_product_admission_native import (
        product_admission_native_programs,
    )
    from corpus_structure.semantic.population_transfer import population_item_write_profile

    conn = product_connection
    context, packet, bodies, declaration = partition_fixture(conn)
    model = get_metadata()
    request = model.tables["ops.data_request"]
    task = model.tables["ops.task"]
    conn.execute(CreateTable(task, include_foreign_key_constraints=[]))
    for program in product_admission_native_programs(model):
        if program.name in {
            "ddo_require_population_scratch",
            "prepare_data_population_upload",
            "ddo_require_population_upload",
            "ddo_retain_population_rows",
            "ddo_consume_population_upload",
            "ddo_promote_population_rows",
        }:
            execute_native_sql(conn, program.render())
    conn.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_authorize_request(r ops.data_request) RETURNS void "
        "LANGUAGE plpgsql AS $$ BEGIN IF r.project_id <> 'project' THEN "
        "RAISE EXCEPTION 'out of scope'; END IF; END $$"
    )
    conn.execute(
        insert(request).values(
            id="request",
            request_key="request-key",
            project_id="project",
            release_id="release",
            runtime_id="runtime",
            operation_id="operation",
            recipe="recipe",
            subject="root",
            analyzed_scope=None,
            binding={},
            generation=1,
            original_source="source",
        )
    )
    now = datetime.now(UTC)
    task_id = conn.scalar(
        insert(task)
        .values(
            release_id="release",
            data_request_id="request",
            data_generation=1,
            status="running",
            attempt=1,
            claimed_by="worker",
            lease_until=now + timedelta(minutes=5),
            cost={},
            priority=0,
            created_at=now,
        )
        .returning(task.c.id)
    )
    fence = dict(
        request_id="request",
        generation=1,
        task_id=task_id,
        attempt=1,
        holder="worker",
        release_id="release",
    )
    conn.execute(update(request).values(live_task_id=task_id))
    conn.execute(
        insert(model.tables["ops.data_completion_intent"]).values(
            id="intent",
            request_id="request",
            generation=1,
            producer_task_id=task_id,
            producer_attempt=1,
            producer_holder="worker",
            runtime_id="runtime",
            payload={},
            payload_digest="test",
            created_at=now,
        )
    )
    publisher, writer = role_name("publisher"), role_name("writer")
    conn.exec_driver_sql(f"GRANT USAGE ON SCHEMA ops TO {publisher}, {writer}")
    conn.exec_driver_sql(f"GRANT SELECT ON ops.data_request, ops.task TO {publisher}")
    conn.exec_driver_sql(
        "ALTER FUNCTION ops.prepare_data_population_upload(text,bigint,bigint,bigint,text,text) "
        f"OWNER TO {publisher}"
    )
    profile = population_item_write_profile(release_id="release", model=model)
    compact, upload = [], []
    for partition, body in zip(packet["partitions"], bodies, strict=True):
        compact.append(
            {
                **{key: value for key, value in partition.items() if key != "body"},
                "item_count": len(body),
                "group_digests": partition_group_digests(body, declaration["field_groups"]),
            }
        )
        tagged_items = partition["body"][1]
        assert isinstance(tagged_items, list)
        for ordinal, item in enumerate(tagged_items):
            upload.append(
                {
                    "output_role": "result",
                    "output_position": 0,
                    "collection": partition["collection"],
                    "partition_key": partition["partition_key"],
                    "item_ordinal": ordinal,
                    "canonical_text": json_bytes(item).decode(),
                }
            )
    packet["partitions"] = compact
    completion = {"outputs": [{"role": "result", "position": 0, "product": packet}]}
    start = text(
        "SELECT ops.prepare_data_population_upload(:request_id,:generation,:task_id,:attempt,"
        ":holder,:release_id)"
    )
    retain = text(
        "SELECT ops.ddo_consume_population_upload(r,'intent',:completion,:fence,:fresh) "
        "FROM ops.data_request r WHERE r.id='request'"
    ).bindparams(bindparam("completion", type_=JSONB()), bindparam("fence", type_=JSONB()))

    def stage(rows):
        with native_owner(conn, writer):
            conn.execute(start, fence)
            assert conn.scalar(
                text(
                    "SELECT NOT has_table_privilege(current_user, 'pg_temp.ddo_population_upload', 'SELECT')"
                )
            )
            assert copy_arrow_stream(
                conn,
                profile,
                target=("pg_temp", "ddo_population_upload"),
                batches=(pa.RecordBatch.from_pylist(rows, schema=profile.schema),),
            ) == len(rows)

    def consume(*, fresh=True, claiming=fence):
        conn.execute(retain, {"completion": completion, "fence": claiming, "fresh": fresh})

    stage(upload)
    with pytest.raises(DBAPIError, match="another attempt or release"), conn.begin_nested():
        consume(claiming=dict(fence, attempt=2))
    consume()
    assert conn.scalar(text("SELECT count(*) FROM ops.data_retained_population_item")) == 3
    assert conn.scalar(text("SELECT count(*) FROM kb.data_product_population")) == 0
    stage(upload)
    consume(fresh=False)
    stage([dict(row, canonical_text=row["canonical_text"] + " ") for row in upload])
    with pytest.raises(DBAPIError, match="replay differs"), conn.begin_nested():
        consume(fresh=False)

    product = conn.scalar(
        text(
            'SELECT ops.ddo_install_product_context(:context,:packet,\'{"project-subject":"project"}\','
            "'intent','result',0::bigint)"
        ).bindparams(bindparam("context", type_=JSONB()), bindparam("packet", type_=JSONB())),
        {"context": context, "packet": packet},
    )
    assert conn.scalar(text("SELECT to_regclass('kb.data_product_partition')")) is None
    assert conn.scalar(text("SELECT count(*) FROM kb.data_product_population")) == 3
    conn.exec_driver_sql(
        """CREATE FUNCTION ops.ddo_binding_rows(
          text, text, jsonb, text, text, jsonb, jsonb, bool, jsonb
        ) RETURNS TABLE(product text, member text) LANGUAGE sql AS $$
          SELECT pin->>'product_id', pin->>'member_id' FROM jsonb_array_elements($9) AS pin
          WHERE $1 = 'demand' AND $2 = 'operation' AND $4 = 'read' AND pin->>'product_id' = $5
        $$"""
    )
    read = next(
        program.routine
        for program in read_native_programs(model)
        if program.routine.name == "data_binding_reference_item"
    )
    execute_native_sql(conn, read.render())
    query = text(
        "SELECT * FROM ops.data_binding_reference_item("
        "'demand','operation','{}'::jsonb,:read,:product,NULL,NULL,:pins,:capacity,"
        "'tokens','b',:address)"
    ).bindparams(bindparam("pins", type_=JSONB()), bindparam("address", type_=JSONB()))
    params = {
        "read": "read",
        "product": product,
        "pins": [{"product_id": product, "member_id": None}],
        "capacity": 65536,
        "address": [0, 2],
    }
    assert conn.execute(query, params).all() == [(product, upload[0]["canonical_text"])]
    assert conn.execute(query, params | {"address": [0, 3]}).all() == []
    assert conn.execute(query, params | {"read": "other"}).all() == []
    assert conn.execute(query, params | {"capacity": 1}).all() == [(product, None)]


def test_binding_population_read_is_limited_to_admitted_whole_products(product_connection):
    from corpus_structure.semantic.data_operation_read_native import read_native_programs

    conn = product_connection
    context, product, _, _ = partition_fixture(conn)
    admitted = realize(conn, context, product)
    conn.exec_driver_sql(
        """CREATE FUNCTION ops.ddo_binding_rows(
          text, text, jsonb, text, text, jsonb, jsonb, bool, jsonb
        ) RETURNS TABLE(product text, member text) LANGUAGE sql AS $$
          SELECT pin->>'product_id', pin->>'member_id' FROM jsonb_array_elements($9) AS pin
          WHERE $1 = 'demand' AND $2 = 'operation' AND $4 = 'read' AND pin->>'product_id' = $5
        $$"""
    )
    program = next(
        item.routine
        for item in read_native_programs(get_metadata())
        if item.routine.name == "data_binding_population_items"
    )
    execute_native_sql(conn, program.render())
    query = text(
        "SELECT product_id, partition_key, item_ordinal, canonical_text "
        "FROM ops.data_binding_population_items("
        "'demand','operation','{}'::jsonb,:read,:admitted,NULL,NULL,:pins,:capacity)"
    ).bindparams(bindparam("pins", type_=JSONB()))

    def read(*, capacity=65536, pin_member=None, read_id="read"):
        return conn.execute(
            query,
            dict(
                admitted=admitted,
                read=read_id,
                capacity=capacity,
                pins=[
                    {"product_id": "unselected", "member_id": None},
                    {"product_id": admitted, "member_id": pin_member},
                ],
            ),
        ).all()

    returned = read()
    assert {row.product_id for row in returned} == {admitted}
    assert [
        (row.partition_key, row.item_ordinal, json.loads(row.canonical_text)) for row in returned
    ] == [
        (packet["partition_key"], position, item)
        for packet in product["partitions"]
        for position, item in enumerate(packet["body"][1])
    ]
    assert read(pin_member="manifest") == read(read_id="other") == []
    assert read(capacity=1) == [(None, None, None, None)]


def test_partition_admission_recomputes_content_groups_and_roots(product_connection):
    from corpus_structure.semantic.data_operation_partitions import partition_group_digests

    context, packet, bodies, declaration = partition_fixture(product_connection)
    key = realize(product_connection, context, packet)
    assert realize(product_connection, context, packet) == key
    rows = product_connection.execute(
        text(
            "SELECT p.ordinal,p.partition_digest,p.item_count,p.group_digests,i.canonical_text "
            "FROM ops.data_retained_population p JOIN ops.data_retained_population_item i "
            "USING (intent_id,output_role,output_position,collection,partition_key) "
            "JOIN kb.data_product_population v USING (intent_id,output_role,output_position,collection,partition_key) "
            "WHERE v.product_id=:key ORDER BY p.ordinal"
        ),
        {"key": key},
    ).all()
    assert len(rows) == 3
    for n, row in enumerate(rows):
        assert row.ordinal == n and row.item_count == 1
        assert row.partition_digest == packet["partitions"][n]["partition_digest"]
        assert json.loads(row.canonical_text) == packet["partitions"][n]["body"][1][0]
        assert row.group_digests == partition_group_digests(bodies[n], declaration["field_groups"])

    from copy import deepcopy

    from corpus_structure.semantic.data_operation_identity import canonical_identity
    from corpus_structure.semantic.data_operation_partitions import partition_header

    shuffled = deepcopy(packet)
    shuffled["partitions"].reverse()
    assert realize(product_connection, context, shuffled) == key
    reordered_mapping = deepcopy(packet)
    tagged_items = reordered_mapping["partitions"][0]["body"][1]
    assert isinstance(tagged_items, list)
    item = tagged_items[0]
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
            "SELECT group_digests FROM ops.data_retained_population WHERE product_id=:key AND ordinal=0"
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
                "SELECT partition_digest FROM ops.data_retained_population WHERE product_id=:key AND ordinal=0"
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
    ["digest", "duplicate", "ordinal", "root", "list", "missing", "omitted", "extra", "placement"],
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
    elif alteration == "omitted":
        del packet["partitions"]
    elif alteration == "extra":
        partitions[0]["collection"] = "undeclared"
    elif alteration == "placement":
        partitions[0]["placement"]["start"] += 1
    with pytest.raises(DBAPIError), product_connection.begin_nested():
        realize(product_connection, context, packet)
    assert product_connection.scalar(text("SELECT count(*) FROM kb.data_product_population")) == 0
    assert product_connection.scalar(text("SELECT count(*) FROM kb.data_product")) == 0


def test_partition_replay_refuses_missing_stored_row(product_connection):
    context, packet, _, _ = partition_fixture(product_connection)
    key = realize(product_connection, context, packet)
    product_connection.execute(
        text("DELETE FROM ops.data_retained_population WHERE product_id=:key AND ordinal=0"),
        {"key": key},
    )
    with pytest.raises(DBAPIError, match="visible population differs"), product_connection.begin_nested():
        realize(product_connection, context, packet)


@pytest.mark.parametrize(
    ("form", "parameters", "paths", "violates"),
    [
        ("unique", {"paths": ["start"]}, ("start",), False),
        ("unique", {"paths": ["start"]}, ("start",), True),
        ("dense_ordinal", {"path": "start", "start": 0}, ("start",), False),
        ("dense_ordinal", {"path": "start", "start": 2}, ("start",), True),
        (
            "dense_ordinal",
            {"path": "start", "start": 0, "group_by": ["end"]},
            ("start", "end"),
            False,
        ),
        (
            "dense_ordinal",
            {"path": "start", "start": 0, "group_by": ["end"]},
            ("start", "end"),
            True,
        ),
        ("ordered_by", {"paths": ["start"]}, ("start",), False),
        ("ordered_by", {"paths": ["end"]}, ("end",), True),
        (
            "span_within",
            {"start": "start", "end": "end", "limit": "limit", "coordinates": "relative"},
            ("start", "end", "limit"),
            False,
        ),
        (
            "span_within",
            {"start": "start", "end": "end", "limit": "wrong_limit", "coordinates": "relative"},
            ("start", "end", "wrong_limit"),
            True,
        ),
        (
            "refers_to",
            {"paths": ["link"], "target_paths": ["start"], "target_collection": "tokens"},
            ("link", "start"),
            False,
        ),
        (
            "refers_to",
            {"paths": ["dangling"], "target_paths": ["start"], "target_collection": "tokens"},
            ("dangling", "start"),
            True,
        ),
        (
            "predicate",
            {"expression": {"op": "ge", "args": [{"field": "limit"}, {"field": "end"}]}},
            ("limit", "end"),
            False,
        ),
        (
            "predicate",
            {"expression": {"op": "ge", "args": [{"field": "wrong_limit"}, {"field": "end"}]}},
            ("wrong_limit", "end"),
            True,
        ),
    ],
)
def test_declared_rules_establish_or_reject_admission_atomically(
    product_connection, form, parameters, paths, violates
):
    from corpus_structure.semantic.data_operation_partitions import (
        partition_header,
        partition_packet,
    )

    connection = product_connection
    context, product, *_ = partition_fixture(connection)
    scope = "partition"
    body = [
        {"start": 0, "end": 3, "limit": 4, "wrong_limit": 0, "link": 1, "dangling": 5},
        {"start": 1, "end": 2, "limit": 4, "wrong_limit": 0, "link": 0, "dangling": 5},
    ]
    if (form == "unique" and violates) or ("group_by" in parameters and not violates):
        body[1]["start"] = 0
    packets = [partition_packet("tokens", "only", 0, 0, 5, body)]
    product["body"] = semantic_value({"tokens": partition_header(packets)})
    product["partitions"] = packets
    specification = {
        "id": form,
        "scope": scope,
        "collection": "tokens",
        "checker": "admission",
        "fingerprint": "rule:" + form,
        "form": form,
        "parameters": parameters,
        "reads": [{"side": "source", "path": path, "groups": []} for path in paths],
    }
    connection.execute(
        insert(get_metadata().tables["sem.data_rule"]).values(
            release_id="release",
            rule_id=form,
            kind_contract="partitioned",
            fingerprint=specification["fingerprint"],
            specification=specification,
        )
    )
    count = text("SELECT count(*) FROM kb.data_validity")
    if violates:
        with (
            pytest.raises(DBAPIError, match=f"collection rule {form} violated"),
            connection.begin_nested(),
        ):
            realize(connection, context, product)
        assert connection.scalar(count) == 0
        assert connection.scalar(text("SELECT count(*) FROM kb.data_product")) == 0
        assert connection.scalar(text("SELECT count(*) FROM kb.data_product_population")) == 0
        return
    key = realize(connection, context, product)
    assert connection.scalar(count) == 1
    assert realize(connection, context, product) == key
    assert connection.scalar(count) == 1
    assert (
        connection.scalar(
            text(
                "SELECT ops.ddo_establish_rule(CAST(:spec AS jsonb), :product, 'only', NULL, NULL)"
            ),
            {"spec": json.dumps(specification), "product": key},
        )
        == 0
    )


def test_rule_premise_tracks_only_declared_paths_and_placement(product_connection):
    from corpus_structure.semantic.data_operation_partitions import (
        partition_header,
        partition_packet,
    )

    connection = product_connection
    context, packet, *_ = partition_fixture(connection)
    key = realize(connection, context, packet)
    changed = [
        partition_packet(
            "tokens", "moved", 0, 100, 105, [{"start": 0, "end": 4, "label": "elsewhere"}]
        ),
    ]
    packet["body"] = semantic_value({"tokens": partition_header(changed)})
    packet["partitions"] = changed
    moved = realize(connection, context, packet)

    spec = {
        "id": "observe",
        "scope": "partition",
        "collection": "tokens",
        "checker": "admission",
        "fingerprint": "rule:observe",
        "form": "unique",
        "parameters": {"paths": ["start"]},
        "reads": [{"side": "source", "path": "start", "groups": []}],
    }
    query = text("SELECT ops.ddo_rule_premise(CAST(:spec AS jsonb), :key, :part, NULL, NULL)")

    def premise(key, name):
        return connection.scalar(query, {"spec": json.dumps(spec), "key": key, "part": name})

    assert premise(key, "b") == premise(moved, "moved")
    spec["reads"].append({"side": "source", "path": "$placement.start", "groups": []})
    assert premise(key, "b") != premise(moved, "moved")
    spec["reads"] = [
        {"side": "source", "path": path, "groups": ["geometry"]} for path in ("start", "end")
    ]
    assert premise(key, "b") != premise(moved, "moved")


@pytest.mark.parametrize("dangling", [False, True])
def test_local_partition_pair_follows_the_declared_address(product_connection, dangling):
    from corpus_structure.semantic.data_operation_partitions import (
        partition_header,
        partition_packet,
    )

    connection = product_connection
    context, packet, *_ = partition_fixture(connection)
    bodies = (
        [{"start": 4, "target": "b", "link": 9 if dangling else 1}],
        [{"start": 1, "target": "a", "link": 4}],
    )
    packets = [
        partition_packet("tokens", name, ordinal, 0, 10, body)
        for ordinal, (name, body) in enumerate(zip(("a", "b"), bodies, strict=True))
    ]
    packet["body"] = semantic_value({"tokens": partition_header(packets)})
    packet["partitions"] = packets
    spec = {
        "id": "link",
        "scope": "partition-pair",
        "collection": "tokens",
        "checker": "admission",
        "fingerprint": "rule:link",
        "form": "refers_to",
        "parameters": {
            "paths": ["link"],
            "target_paths": ["start"],
            "target_collection": "tokens",
            "target_key": "target",
        },
        "reads": [{"side": "source", "path": path, "groups": []} for path in ("link", "target")]
        + [{"side": "target", "path": "start", "groups": []}],
    }
    connection.execute(
        insert(get_metadata().tables["sem.data_rule"]).values(
            release_id="release",
            rule_id="link",
            kind_contract="partitioned",
            fingerprint=spec["fingerprint"],
            specification=spec,
        )
    )
    if dangling:
        with (
            pytest.raises(DBAPIError, match="collection rule link violated"),
            connection.begin_nested(),
        ):
            realize(connection, context, packet)
        assert connection.scalar(text("SELECT count(*) FROM kb.data_validity")) == 0
        return
    key = realize(connection, context, packet)
    assert connection.scalar(text("SELECT count(*) FROM kb.data_validity")) == 2
    assert (
        connection.scalar(
            text("SELECT ops.ddo_rule_target_partition(CAST(:spec AS jsonb), :key, 'a')"),
            {"spec": json.dumps(spec), "key": key},
        )
        == "b"
    )


def test_retained_selected_use_establishes_only_its_current_rule_premise(product_connection):
    """Execute the real selected-product, read-currency and rule program on a finite fixture."""
    from datetime import timedelta

    from corpus_structure.semantic.data_operation_rule_native import rule_native_programs
    from corpus_structure.semantic.data_read_boundary_native import read_boundary_native_programs

    connection = product_connection
    model = get_metadata()
    for name in (
        "ops.data_demand",
        "ops.data_obligation",
        "ops.data_demand_read",
        "ops.data_demand_read_scope",
        "ops.data_trust_scope",
        "ops.original_source_admission",
        "ops.demand_use",
        "ops.data_derivation",
        "ops.data_derivation_input",
        "ops.data_derivation_output",
        "ops.data_derivation_support",
        "ops.data_derivation_original_support",
        "ops.data_population",
        "sem.data_operation_definition",
    ):
        connection.execute(CreateTable(model.tables[name], include_foreign_key_constraints=[]))
    # No issuer, transitive support, population or selected-use substitutions
    # exist in this fixture. Supply the support owner decision for the two
    # retained episodes. The actual cut, use, reachability, disclosure and
    # proof checks execute below. Revocation exercises real retained epochs.
    for statement in (
        "CREATE FUNCTION sem.data_operation_native_descriptor() RETURNS jsonb LANGUAGE sql "
        "AS $$SELECT jsonb_build_object('read_closure','test-kernel')$$",
        "CREATE FUNCTION ops.ddo_policy_authority_leaf(text) RETURNS boolean LANGUAGE sql AS 'SELECT false'",
        "CREATE FUNCTION ops.ddo_structural_report_support(text,ops.data_demand_read,jsonb) "
        "RETURNS jsonb LANGUAGE sql AS 'SELECT NULL::jsonb'",
        "CREATE FUNCTION ops.ddo_support_reference_node(jsonb) "
        "RETURNS jsonb LANGUAGE sql AS 'SELECT NULL::jsonb'",
        "CREATE FUNCTION ops.ddo_valid_closure(text[],text[],ops.data_demand_read,text[]) "
        "RETURNS TABLE(kind text,id text,valid boolean) LANGUAGE plpgsql AS $$ BEGIN "
        "IF 'unrelated-use'=ANY($1) THEN RAISE EXCEPTION 'unrelated support reached'; END IF; "
        "RETURN QUERY SELECT 'use'::text,u,true FROM unnest($1) u UNION ALL "
        "SELECT 'episode'::text,d.id,true FROM ops.data_derivation d WHERE d.id=ANY($2) "
        "OR EXISTS (SELECT 1 FROM ops.demand_use u WHERE u.id=ANY($1) AND u.derivation_id=d.id); "
        "END $$",
    ):
        execute_native_sql(connection, statement)
    for program in read_boundary_native_programs(model):
        if program.name in {
            "ddo_read_acquisition_present",
            "ddo_require_read_epochs",
            "ddo_require_read_current",
            "ddo_read_visible",
        }:
            execute_native_sql(connection, program.render())
    endpoint = next(
        program
        for program in rule_native_programs(model)
        if program.name == "establish_data_rule_proof"
    )
    execute_native_sql(connection, endpoint.render())

    def add(relation, **values):
        connection.execute(insert(model.tables[relation]).values(**values))

    context, packet, *_ = partition_fixture(connection)
    current_product = realize(connection, context, packet)
    foreign_product = realize(connection, {**context, "project_id": "other"}, packet)
    now, snapshot, xid = connection.execute(
        text("SELECT clock_timestamp(),pg_current_snapshot()::text,pg_current_xact_id()::text")
    ).one()
    before = now - timedelta(seconds=1)
    project = context["project_id"]
    add(
        "ops.data_demand",
        id="retained-demand",
        project_id=project,
        release_id="release",
        runtime_id="runtime",
        root={},
        selection={},
        strength="value",
        created_at=before,
    )
    add(
        "ops.data_obligation",
        id="retained-obligation",
        demand_id="retained-demand",
        operation_id="operation",
        subject=context["subject"],
        analyzed_scope={},
        parameters={},
        created_at=before,
        created_xid=xid,
    )
    add(
        "ops.data_derivation",
        id="retained-episode",
        request_id="retained-request",
        generation=1,
        intent_id="intent",
        release_id="release",
        recipe="recipe",
        runtime_id="runtime",
        producer_task_id=1,
        producer_attempt=1,
        outcome="success",
        completed_at=before,
    )
    add(
        "ops.demand_use",
        id="retained-use",
        demand_id="retained-demand",
        obligation_id="retained-obligation",
        request_id="retained-request",
        generation=1,
        fate="fulfilled",
        derivation_id="retained-episode",
        selection={},
        trust_snapshot={},
        created_at=before,
        created_xid=xid,
    )
    add(
        "ops.data_obligation",
        id="unrelated-obligation",
        demand_id="retained-demand",
        operation_id="operation",
        subject=context["subject"],
        analyzed_scope={},
        parameters={},
        created_at=before,
        created_xid=xid,
    )
    add(
        "ops.demand_use",
        id="unrelated-use",
        demand_id="retained-demand",
        obligation_id="unrelated-obligation",
        request_id="retained-request",
        generation=1,
        fate="fulfilled",
        derivation_id="retained-episode",
        selection={},
        trust_snapshot={},
        created_at=before,
        created_xid=xid,
    )
    for position, product_id in enumerate((current_product, foreign_product)):
        add(
            "ops.data_derivation_output",
            derivation_id="retained-episode",
            role="output",
            position=position,
            multiplicity=1,
            product_id=product_id,
        )
    add("ops.data_trust_scope", scope="retained-scope", project_id=project, epoch=0)
    add(
        "ops.data_demand_read_scope",
        read_id="retained-read",
        scope="retained-scope",
        epoch=0,
        ordinary=True,
        domain=False,
    )
    add(
        "ops.data_demand_read",
        id="retained-read",
        demand_id="retained-demand",
        read_snapshot=snapshot,
        frontier_at=now,
        owner_xid=xid,
        kernel_digest="test-kernel",
        scope={"product_ids": [current_product, foreign_product]},
        trust_snapshot={},
        access_universes=["ordinary"],
        public_disclosure=False,
        grade_census_eligible=False,
        fit_census_eligible=False,
    )
    rules = (
        ("order", "fingerprint:order", "ordered_by", {"paths": ["start"]}),
        ("dense", "fingerprint:dense", "dense_ordinal", {"path": "start", "start": 0}),
    )

    def rule_record(rule_id, fingerprint, form, parameters):
        return {
            "id": rule_id,
            "scope": "partition",
            "collection": "tokens",
            "checker": "admission",
            "fingerprint": fingerprint,
            "form": form,
            "parameters": parameters,
            "reads": [
                {"side": "source", "path": path, "groups": []}
                for path in (parameters["paths"] if form == "ordered_by" else [parameters["path"]])
            ],
        }

    for rule_id, fingerprint, form, parameters in rules:
        add(
            "sem.data_rule",
            rule_id=rule_id,
            release_id="release",
            kind_contract="partitioned",
            fingerprint=fingerprint,
            specification=rule_record(rule_id, fingerprint, form, parameters),
        )
    connection.exec_driver_sql("GRANT USAGE ON SCHEMA ops TO corpus_sem_writer")
    connection.exec_driver_sql(
        "REVOKE EXECUTE ON FUNCTION ops.establish_data_rule_proof(jsonb) FROM PUBLIC"
    )
    connection.exec_driver_sql(
        "GRANT EXECUTE ON FUNCTION ops.establish_data_rule_proof(jsonb) TO corpus_sem_writer"
    )

    def establish(**changes):
        payload = {
            "demand_id": "retained-demand",
            "read_id": "retained-read",
            "use_id": "retained-use",
            "derivation_id": "retained-episode",
            "product_id": current_product,
            "partition_key": "b",
            "rule_id": "order",
            **changes,
        }
        with native_owner(connection, "corpus_sem_writer"):
            return connection.scalar(
                text("SELECT ops.establish_data_rule_proof(CAST(:payload AS jsonb))"),
                {"payload": json.dumps(payload)},
            )

    assert establish() == {"established": 1, "matched": 0}
    assert establish() == {"established": 0, "matched": 1}
    assert establish(rule_id="dense") == {"established": 1, "matched": 0}
    with pytest.raises(DBAPIError, match="requires exact selected use"), connection.begin_nested():
        establish(use_id="missing-use")
    with (
        pytest.raises(DBAPIError, match="requires disclosed selected product"),
        connection.begin_nested(),
    ):
        establish(product_id=foreign_product)
    with (
        pytest.raises(DBAPIError, match="does not identify admitted partition"),
        connection.begin_nested(),
    ):
        establish(partition_key="missing-partition")

    # Isolate the retained proof protocol by controlling the new prepared rule metadata.
    # Release compiler tests separately establish how a parameter edit changes the key.
    replacement = rule_record(
        "order", "fingerprint:order-edited", "ordered_by", {"paths": ["start", "end"]}
    )
    rule_table = model.tables["sem.data_rule"]
    connection.execute(
        rule_table.update()
        .where(rule_table.c.rule_id == "order")
        .values(
            fingerprint=replacement["fingerprint"],
            specification=replacement,
        )
    )
    assert establish() == {"established": 1, "matched": 0}
    assert establish(rule_id="dense") == {"established": 0, "matched": 1}
    proof = model.tables["kb.data_validity"]
    assert len(connection.execute(proof.select()).all()) == 3

    trust = model.tables["ops.data_trust_scope"]
    connection.execute(trust.update().values(epoch=1))
    with pytest.raises(DBAPIError, match="read trust changed"), connection.begin_nested():
        establish()
