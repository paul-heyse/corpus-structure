"""The complete binding owner exposes structured providers and ledger outputs."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import text

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.data_operation_binding_native import (
    binding_native_programs,
    binding_native_sources,
)
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import INTERNAL_PROGRAM, execute_native_sql
from corpus_structure.semantic.native_program import NativeRoutine


def test_binding_owner_exposes_every_structured_program_without_text_reparse(monkeypatch):
    def refuse_render(self):
        raise AssertionError("binding owner eagerly rendered its provider")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    programs = binding_native_programs()
    assert len(programs) == len({item.identity for item in programs}) == 31
    for declaration in programs:
        assert declaration.source == "data-operation-bindings:forward"
        assert declaration.owner == role_name("publisher")
        assert declaration.access == INTERNAL_PROGRAM
    ledger = next(
        item for item in programs if item.identity.name == "ddo_derivation_input_positions"
    )
    assert ledger.identity.arguments == ("jsonb", "jsonb")
    assert ledger.routine.returns.setof is True
    assert tuple(name for name, _ in ledger.routine.table_columns) == (
        "input_record",
        "physical_position",
    )
    admission = next(item for item in programs if item.identity.name == "ddo_require_binding")
    assert admission.routine.parameters[-1].name == "p_read_checked"
    assert admission.routine.parameters[-1].default is not None


def test_binding_owner_matches_actual_capture_and_refuses_independent_change():
    model = get_metadata()
    sources = binding_native_sources(target_metadata=model)
    assert len(binding_native_programs(target_metadata=model, sources=sources)) == 31
    changed = tuple(
        replace(item, content=item.content + b"\nchanged")
        if item.name == "native/data-operation-bindings.sql"
        else item
        for item in sources
    )
    with pytest.raises(ValueError, match="differ from captured"):
        binding_native_programs(target_metadata=model, sources=changed)


def test_typed_binding_ledger_and_dependency_closure_keep_actual_semantics(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    programs = {item.identity.name: item for item in binding_native_programs()}
    for name in ("ddo_derivation_input_positions", "ddo_consumed_producers"):
        execute_native_sql(connection, programs[name].routine.render())
    inputs = [
        dict(role="set", product_id=product, member_id=None, position=9) for product in ("B", "A")
    ] + [dict(role="sequence", product_id="C", member_id=None, position=5)]
    roles = [dict(name="set", collection="set"), dict(name="sequence", collection="sequence")]
    rows = (
        connection.execute(
            text(
                "SELECT * FROM ops.ddo_derivation_input_positions(CAST(:inputs AS jsonb),CAST(:roles AS jsonb))"
            ),
            {"inputs": json.dumps(inputs), "roles": json.dumps(roles)},
        )
        .mappings()
        .all()
    )
    assert {(row["input_record"]["product_id"], row["physical_position"]) for row in rows} == {
        ("A", 0),
        ("B", 1),
        ("C", 5),
    }
    assert {
        row["input_record"]["position"] for row in rows if row["input_record"]["role"] == "set"
    } == {9}
    selection = dict(
        operations=[
            dict(operation=name, dependencies=deps)
            for name, deps in (("a", ["b"]), ("b", ["d"]), ("d", []), ("unrelated", []))
        ],
        discovery=[],
    )
    assert connection.scalar(
        text("SELECT ops.ddo_consumed_producers(CAST(:selection AS jsonb),'a')"),
        {"selection": json.dumps(selection)},
    ) == ["b", "d"]
