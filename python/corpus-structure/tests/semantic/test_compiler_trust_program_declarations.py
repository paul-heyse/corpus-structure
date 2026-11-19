"""Compiler and trust authoring retain typed roles and explicit marker slots."""

import json

from sqlalchemy import text

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.data_operation_compiler_native import (
    compiler_native_programs,
    compiler_native_sql,
    data_operation_native_descriptor_program,
)
from corpus_structure.semantic.data_operation_subjects import subject_scope_values
from corpus_structure.semantic.effect_policy import effect_native_programs
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import (
    INTERNAL_PROGRAM,
    NativeProgramAccess,
    execute_native_sql,
)
from corpus_structure.semantic.native_program import NativeRoutine
from corpus_structure.semantic.native_program_registry import ProgramClosures, ProgramValidity
from corpus_structure.semantic.support_trust_native import (
    support_scope_programs,
    support_trust_native_programs,
)


def test_compiler_trust_and_effect_producers_keep_structured_owners_and_roles(monkeypatch):
    def refuse_render(self):
        raise AssertionError("producer rendered before native authoring boundary")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    model = get_metadata()
    compiler = compiler_native_programs(model, subject_scopes=subject_scope_values())
    programs = (
        *compiler,
        data_operation_native_descriptor_program(
            "a" * 64, ProgramClosures("b" * 64, "c" * 64, {}, {})
        ),
        *support_trust_native_programs(model),
        *support_scope_programs(model),
    )
    explicit = {
        "admit_data_operation_definitions": NativeProgramAccess(purposes=("admit",)),
        "admit_data_operation_effect_grants": NativeProgramAccess(purposes=("admit",)),
        "data_operation_native_descriptor": NativeProgramAccess(
            purposes=("read", "write", "admit", "evaluate")
        ),
    }
    for declaration in programs:
        assert declaration.source == "data-operations:forward"
        assert declaration.owner == role_name("publisher")
        assert declaration.access == explicit.get(declaration.identity.name, INTERNAL_PROGRAM)
    assert {item.identity for item in effect_native_programs(model)} <= {
        item.identity for item in compiler
    }
    marked = {item.identity.name: item.validity for item in programs if item.validity}
    assert marked == {
        "ddo_conservative_dependencies_valid": (ProgramValidity("conservative", "validator"),)
    }
    scopes = support_scope_programs(model)[0]
    assert scopes.identity.arguments == ("text", "text", "jsonb")
    assert scopes.routine.returns.setof is True
    assert tuple(name for name, _ in scopes.routine.table_columns) == ("scope",)


def test_compiler_uses_installed_descriptor_and_preserves_kind_semantics(
    infrastructure_rollback,
):
    model = get_metadata()
    captured = compiler_native_sql(model, subject_scopes=subject_scope_values())
    assert "sem.data_operation_native_descriptor()" in captured
    assert "__DDO_" not in captured
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA sem")
    descriptor = data_operation_native_descriptor_program(
        "a" * 64, ProgramClosures("b" * 64, "c" * 64, {}, {})
    )
    execute_native_sql(connection, descriptor.render())
    for declaration in compiler_native_programs(model, subject_scopes=subject_scope_values()):
        if declaration.identity.name == "ddo_input_kind_contracts":
            execute_native_sql(connection, declaration.routine.render())
    assert connection.scalar(text("SELECT sem.data_operation_native_descriptor()")) == {
        "version": "data-operation-native-v1",
        "source_digest": "a" * 64,
        "lowering_digest": "b" * 64,
        "read_closure": "c" * 64,
        "validator_identities": {},
    }
    archive = {
        "kinds": [
            {"semantic_id": name, "facts": {"json": {"abstract": abstract}}, "complete": complete}
            for name, abstract, complete in (
                ("base", True, True),
                ("included", False, True),
                ("incomplete", False, False),
            )
        ],
        "edges": [
            {"source": name, "target": "base", "relation": "inherits"}
            for name in ("included", "incomplete")
        ],
        "identities": [
            {"owner": name, "domain": "kind", "key": "kind:" + name}
            for name in ("base", "included", "incomplete")
        ],
    }
    assert connection.scalar(
        text("SELECT sem.ddo_input_kind_contracts(CAST(:model AS jsonb),'base')"),
        {"model": json.dumps(archive)},
    ) == ["kind:included"]
