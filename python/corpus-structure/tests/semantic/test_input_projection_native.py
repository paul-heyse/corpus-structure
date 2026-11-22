"""Admitted partition metadata and body-free projection key parity."""

import json
from dataclasses import asdict, replace
from decimal import Decimal
from hashlib import sha256
from typing import Any, cast

import pytest
from sqlalchemy import bindparam, insert, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import migrations
from corpus_structure.semantic._data_operation_wire import WireResultBinding
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    OperationSelection,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_identity import projected_computation_identity
from corpus_structure.semantic.data_operation_model import InputReadProjection, ProjectedCollection
from corpus_structure.semantic.data_operation_partitions import partition_group_digests
from corpus_structure.semantic.data_operation_projection_values import input_projection_digest
from corpus_structure.semantic.data_operation_read_native import read_native_programs
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.metadata import get_metadata, table
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.request_attachment_native import _computation_identity_program
from corpus_structure.semantic.target_installation import capture_target_installation
from native_test_support import principal_engine
from semantic.data_operation_declaration_support import root_subject
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE, admit_kernel, prepare_kernel
from semantic.test_data_product_admission_programs import (
    partition_fixture,
    realize,
)
from semantic.test_data_product_admission_programs import product_connection as product_connection
from semantic.test_target_installation_native import install_target_root


def test_selected_whole_projection_digest_never_reads_partition_bodies(product_connection):
    connection = product_connection
    context, product, bodies, layout = partition_fixture(connection)
    header = decode_semantic_value(product["body"]) | {
        "source": {
            "document": "a",
            "ignored": "not an observed field",
            "precision": Decimal("1.2"),
        },
        "optional": None,
        "selectors": [{"relation": "original", "section": 2}],
    }
    product["body"] = semantic_value(header)
    admitted = realize(connection, context, product)

    # Supply the existing binding owner's selection response in this isolated
    # product fixture, which does not install all demand, trust and request state.
    connection.exec_driver_sql("CREATE TABLE ops.data_demand(id text, release_id text)")
    connection.exec_driver_sql(
        "CREATE TABLE sem.data_operation_definition("
        "release_id text, operation_id text, input_roles jsonb)"
    )
    connection.exec_driver_sql("INSERT INTO ops.data_demand VALUES ('demand', 'release')")
    connection.exec_driver_sql(
        """CREATE FUNCTION ops.ddo_binding_rows(
          text, text, jsonb, text, text, jsonb, jsonb, bool, jsonb
        ) RETURNS TABLE(product text, member text, meaning_body jsonb) LANGUAGE sql AS $$
          SELECT p.id, NULL::text, p.canonical_body
          FROM kb.data_product AS p
          JOIN jsonb_array_elements($9) AS pin ON p.id = pin->>'product_id'
          WHERE $1 = 'demand' AND $2 = 'operation' AND $4 = 'read' AND NOT $8
            AND pin->>'member_id' IS NULL
        $$"""
    )
    procedures = ("ddo_input_projection_header", "ddo_binding_input_projection_digest")
    programs = {
        entry.routine.name: entry
        for entry in read_native_programs(get_metadata())
        if entry.routine.name in procedures
    }
    for name in procedures:
        execute_native_sql(connection, programs[name].routine.render())

    # Product and group commitments were admitted before removing the unneeded
    # column. The fixture's transaction rolls back the DDL and all test writes.
    connection.exec_driver_sql("ALTER TABLE kb.data_product_partition DROP COLUMN body")
    read = text(
        "SELECT ops.ddo_binding_input_projection_digest("
        "'demand','operation','{}'::jsonb,:read,'subject',NULL,NULL,:pins,:role)"
    ).bindparams(bindparam("pins", type_=JSONB()))
    update = text(
        "INSERT INTO sem.data_operation_definition VALUES ('release', 'operation', :roles)"
    ).bindparams(bindparam("roles", type_=JSONB()))
    metadata = [
        {
            **{key: packet[key] for key in ("collection", "partition_key", "ordinal", "placement")},
            "group_digests": partition_group_digests(body, layout["field_groups"]),
        }
        for packet, body in zip(product["partitions"], bodies, strict=True)
    ]
    pins = [{"product_id": admitted, "member_id": None}]
    selectors = (
        ProjectedCollection("tokens", ("geometry",), True, True, True),
        ProjectedCollection("tokens", ("labels",), True, False, False),
        ProjectedCollection("tokens", (), False, False, True),
    )
    for index, selection in enumerate(selectors):
        projection = InputReadProjection(
            1,
            "whole",
            ("optional", "selectors", "source.document", "source.missing", "source.precision"),
            (selection,),
            None,
            f"input-read-projection:test-{index}",
        )
        connection.exec_driver_sql("DELETE FROM sem.data_operation_definition")
        connection.execute(
            update,
            {
                "roles": [
                    {
                        "name": "inventory",
                        "collection": "scalar",
                        "minimum": 1,
                        "maximum": 1,
                        "read_projection": asdict(projection),
                    }
                ],
            },
        )
        assert connection.scalar(read, dict(read="read", pins=pins, role="inventory")) == (
            input_projection_digest(projection, header, metadata)
        )

    assert connection.scalar(read, dict(read="other", pins=pins, role="inventory")) is None
    with pytest.raises(DBAPIError, match="declared scalar whole role"), connection.begin_nested():
        connection.scalar(read, dict(read="read", pins=pins, role="other"))
    with pytest.raises(DBAPIError, match="exact whole-product pin"), connection.begin_nested():
        connection.scalar(
            read,
            dict(read="read", pins=[{"product_id": admitted, "member_id": "m"}], role="inventory"),
        )


def test_native_computation_key_preserves_typed_parameters(product_connection):
    routine = _computation_identity_program()
    execute_native_sql(product_connection, routine.render())
    parameters = {"parameters": {"cutoff": Decimal("1.2")}, "replicate": None}
    values: dict[str, Any] = {
        "project": "project:one",
        "recipe": "recipe:one",
        "role": "inventory",
        "projection_digest": "input-projection-value:selected",
        "parameters": parameters,
        "inference": "inference:one",
    }
    literal = (
        b'["ddo","projected-computation","1",["mapping",'
        b'[["inference",["string","inference:one"]],'
        b'["inputs",["mapping",[["inventory",["string","input-projection-value:selected"]]]]],'
        b'["parameters",["mapping",[["parameters",["mapping",[["cutoff",["decimal","1.2"]]]]],'
        b'["replicate",["null"]]]]],'
        b'["project",["string","project:one"]],["recipe",["string","recipe:one"]]]]]'
    )
    actual = projected_computation_identity(**values)
    assert actual.canonical_input == literal
    assert actual.key == "projected-computation:" + sha256(literal).hexdigest()
    query = text(
        "SELECT ops.ddo_projected_computation_key("
        ":project,:recipe,:role,:projection_digest,:parameters,:inference)"
    ).bindparams(bindparam("parameters", type_=JSONB()))
    assert (
        product_connection.scalar(query, values | {"parameters": semantic_value(parameters)})
        == actual.key
    )
    variants: dict[str, Any] = {
        "project": "project:two",
        "recipe": "recipe:two",
        "role": "different",
        "projection_digest": "input-projection-value:changed",
        "parameters": {"parameters": {"cutoff": "1.2"}, "replicate": None},
        "inference": "inference:two",
    }
    for field, value in variants.items():
        changed = values | {field: value}
        compared = product_connection.scalar(
            query, changed | {"parameters": semantic_value(changed["parameters"])}
        )
        assert compared == projected_computation_identity(**changed).key
        assert compared != actual.key


_CANONICAL = "segment.sentences/canonical-projection"
_PRODUCER = "urn:ddo-test:sample"


def _projected_storage_recipe():
    assert STORAGE.declaration_content is not None
    declaration = json.loads(STORAGE.declaration_content)
    consumer = next(
        row for row in declaration["operations"] if row["id"] == "urn:ddo-test:value-consumer"
    )
    # Exercise the enforced port's attachment contract independently of a live
    # parser. The test supplies a synthetic producer and publishes native values.
    consumer["id"] = _CANONICAL
    consumer["roles"][0]["read_projection"] = {"scope": "whole", "header": ["value"]}
    producer = next(row for row in declaration["operations"] if row["id"] == _PRODUCER)
    producer["parameters"] = {"lexical_label": {"value_type": "string", "required": False}}
    return replace(
        STORAGE,
        name="projected-computation-attachment",
        schema_text=STORAGE.schema_text + "      lexical_label: {range: string}\n",
        declaration_content=json.dumps(declaration).encode(),
    )


@pytest.fixture
def projected_kernel(semantic_bare_engine, native_settings, tmp_path, monkeypatch):
    admin = semantic_bare_engine
    target = capture_target_installation(get_metadata())
    *_, revision_path = install_target_root(admin, target, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", revision_path)
    recipe = _projected_storage_recipe()
    preparation = prepare_kernel(recipe, directory=tmp_path / "kernel")
    with admin.begin() as connection:
        kernel = admit_kernel(connection, recipe, preparation=preparation)
    writer = principal_engine(native_settings, "write", admin.url.database)
    try:
        yield replace(kernel, engine=writer)
    finally:
        writer.dispose()


def test_native_projected_basis_preserves_distinct_request_custody(
    projected_kernel, semantic_bare_engine
):
    engine = projected_kernel.engine
    model = projected_kernel.model
    source_kind = next(kind for kind in model.kinds if kind.name == "Sample")
    sample_kind = projected_kernel.identities[source_kind.semantic_id, "kind"]
    operation = model.operation(_CANONICAL)
    role = next(role for role in operation.roles if role.direction == "input")
    assert role.read_projection is not None
    body = {"value": 15}
    digest = input_projection_digest(role.read_projection, body, [])

    def sample_output(completion):
        completion["outputs"][0]["product"].update(
            kind_contract=sample_kind, body=semantic_value(body)
        )

    with semantic_bare_engine.begin() as connection:
        connection.execute(insert(table("data.project")).values(project_id="ddo-other"))

    destinations = (("ddo-test", 1), ("ddo-test", 2), ("ddo-other", 1))
    requests = []
    keys = []
    retained_episode = None
    for project, page in destinations:
        demand, _, _, producer = attach(
            projected_kernel,
            operation=_PRODUCER,
            targets=(_CANONICAL,),
            analyzed_scope={"page": page},
            project_id=project,
        )
        fence = claim(projected_kernel, producer)
        publish(projected_kernel, fence, retain(projected_kernel, fence, mutate=sample_output))
        with engine.begin() as connection:
            planner = DemandPlanner(model, DataOperationStorage(connection))
            snapshot = planner.resume(demand["demand_id"])
        with engine.begin() as connection:
            planner = DemandPlanner(model, DataOperationStorage(connection))
            (ready,) = planner.ready(snapshot, authorization=b"{}")
        native = json.loads(ready.native)
        current = json.loads(ready.binding)
        assert ready.operation == _CANONICAL
        assert native["action"] == "compute"
        with semantic_bare_engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT r.request_key, c.computation_key, r.analyzed_scope, r.project_id "
                    "FROM ops.data_request r "
                    "JOIN ops.data_request_computation c ON c.request_id=r.id "
                    "AND c.generation=r.generation WHERE r.id=:id"
                ),
                {"id": native["request_id"]},
            ).one()
        assert row.project_id == project
        assert row.analyzed_scope == {"page": page}
        assert row.request_key == native["request_id"]
        assert (
            row.computation_key
            == projected_computation_identity(
                project=project,
                recipe=projected_kernel.identities[_CANONICAL, "recipe"],
                role=role.name,
                projection_digest=digest,
                parameters=decode_semantic_value(current["parameters"]),
                inference=current["inference"],
            ).key
        )
        requests.append(native["request_id"])
        keys.append(row.computation_key)

        # Publish the first contextual output. Equal computation on the next
        # context alone does not authorize use of this output occurrence.
        if page == 1 and project == "ddo-test":
            fence = claim(projected_kernel, native)
            intent = retain(
                projected_kernel,
                fence,
                mutate=lambda completion, selected=current: completion.update(
                    inputs=selected["inputs"], support=selected["support"]
                ),
            )
            retained_episode = publish(projected_kernel, fence, intent)["derivation_id"]

    assert len(set(requests)) == 3
    assert keys[0] == keys[1]
    assert keys[0] != keys[2]

    # New lexical output, fixed projected value and the same authorized output occurrence.
    # The new request has its own custody and selected support, without a new task.
    assert retained_episode is not None
    revised = freeze_demand(
        model,
        roots=(root_subject(subject="subject:one", source="source:test", scope={"page": 1}),),
        targets=(_CANONICAL,),
        selections=(OperationSelection(_PRODUCER, b'{"lexical_label":"revised"}'),),
        inference="inference:test",
        execution_profile="execution:test",
    )
    with engine.begin() as connection:
        planner = DemandPlanner(model, DataOperationStorage(connection))
        current = planner.register(
            revised,
            project="ddo-test",
            release=projected_kernel.prepared.release_id,
            runtime=projected_kernel["runtime"],
        )["demand_id"]
    with engine.begin() as connection:
        snapshot = DemandPlanner(model, DataOperationStorage(connection)).resume(current)
    with engine.begin() as connection:
        planner = DemandPlanner(model, DataOperationStorage(connection))
        (source,) = planner.ready(snapshot, authorization=b"{}")
    assert source.operation == _PRODUCER
    fence = claim(projected_kernel, json.loads(source.native))

    def revised_output(completion):
        sample_output(completion)
        completion["outputs"][0]["product"]["body"] = semantic_value(
            {**body, "lexical_label": "revised"}
        )

    original = publish(
        projected_kernel, fence, retain(projected_kernel, fence, mutate=revised_output)
    )
    with engine.begin() as connection:
        snapshot = DemandPlanner(model, DataOperationStorage(connection)).resume(current)
    with engine.begin() as connection:
        planner = DemandPlanner(model, DataOperationStorage(connection))
        assert planner.ready(snapshot, authorization=b"{}") == ()
        (current_request,) = planner.fulfilled_request_ids
    assert current_request not in requests
    with engine.begin() as connection:
        snapshot = DemandPlanner(model, DataOperationStorage(connection)).resume(current)
    target = next(row for row in snapshot["obligations"] if row["operation_id"] == _CANONICAL)
    result = next(
        use for use in snapshot["uses"] if use["obligation_id"] == target["obligation_id"]
    )
    assert result["fate"] == "fulfilled" and result["derivation_id"] == retained_episode
    assert result["request_id"] == current_request
    selection = cast(WireResultBinding, result["selection"])
    support = selection["support"][0]
    assert "derivation_id" in support and support["derivation_id"] == original["derivation_id"]
