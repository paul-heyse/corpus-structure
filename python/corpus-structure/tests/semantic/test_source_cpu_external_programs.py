"""Typed grouped providers retain codec, exact CPU and external custody contracts."""

import json

from sqlalchemy import Column, MetaData, Table, text

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.data_operation_cpu_basis import cpu_input_basis_native_programs
from corpus_structure.semantic.external_execution_native import external_execution_native_programs
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import INTERNAL_PROGRAM, execute_native_sql
from corpus_structure.semantic.native_program import NativeRoutine
from corpus_structure.semantic.native_protocol_authoring import native_logical_sources
from corpus_structure.semantic.source_value_native import source_value_native_programs


def source_programs():
    return source_value_native_programs(native_logical_sources()["observations.yaml"])


def test_grouped_producers_retain_unrendered_private_declarations(monkeypatch):
    def refuse_render(self):
        raise AssertionError("producer rendered before native registry authoring")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    model = get_metadata()
    sources = source_programs()
    cpu = cpu_input_basis_native_programs(target_metadata=model)
    external = external_execution_native_programs(
        model, model.info["physical_sources"]["data-operation-native.yaml"]
    )
    assert len(sources) == 5
    assert len(cpu) == 3
    assert len(external) == 11
    for declaration in (*sources, *cpu, *external):
        assert declaration.source == "data-operations:forward"
        assert declaration.owner == role_name("publisher")
        assert declaration.access == INTERNAL_PROGRAM
    assert {item.identity.name for item in cpu} == {
        "ddo_cpu_input_basis",
        "ddo_cpu_original_producer",
        "ddo_cpu_reply_output",
    }
    assert all(item.routine.volatility == "immutable" for item in sources)


def test_typed_source_codec_preserves_exact_scalar_tags_and_order(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA data")
    for declaration in source_programs():
        execute_native_sql(connection, declaration.routine.render())
    original = {"large": 2**70, "false": False, "empty": [], "text": "β", "null": None}
    encoded = connection.scalar(
        text("SELECT data.record_json_source(CAST(:raw AS jsonb))"), {"raw": json.dumps(original)}
    )
    fields = {field["name"]: field["value"] for field in encoded["fields"]}
    assert fields["large"] == {"kind": "integer", "integer": 2**70}
    assert fields["false"] == {"kind": "boolean", "boolean": False}
    assert fields["null"] == {"kind": "null"}
    assert (
        connection.scalar(
            text("SELECT data.record_source_json(CAST(:value AS jsonb))"),
            {"value": json.dumps(encoded)},
        )
        == original
    )
    assert connection.scalar(
        text("SELECT data.report_field(CAST(:value AS jsonb),'text')"),
        {"value": json.dumps(encoded)},
    ) == {"kind": "text", "text": "β"}


def test_typed_external_receipt_projects_original_custody(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    model = get_metadata()
    owner = model.tables["ops.data_external_receipt"]
    controls = MetaData()
    Table(
        owner.name, controls, *(Column(field.name, field.type) for field in owner.c), schema="ops"
    )
    controls.create_all(connection)
    declaration = next(
        item
        for item in external_execution_native_programs(
            model, model.info["physical_sources"]["data-operation-native.yaml"]
        )
        if item.identity.name == "ddo_external_receipt_value"
    )
    execute_native_sql(connection, declaration.routine.render())
    physical = dict(
        id="receipt",
        packet_id="packet",
        packet_digest="a" * 64,
        request_id="request",
        generation=7,
        task_id=9007199254740993,
        attempt=11,
        holder="original-holder",
        runtime_id="original-runtime",
        admitting_principal="original-principal",
        actor_assertion="actor",
        model_assertion=None,
        result_digest="b" * 64,
    )
    actual = connection.scalar(
        text(
            "SELECT ops.ddo_external_receipt_value(jsonb_populate_record(NULL::ops.data_external_receipt,CAST(:value AS jsonb)))"
        ),
        {"value": json.dumps(physical)},
    )
    assert actual == {
        "version": "external-execution-receipt-v1",
        "receipt_id": "receipt",
        **{name: value for name, value in physical.items() if name != "id"},
    }
