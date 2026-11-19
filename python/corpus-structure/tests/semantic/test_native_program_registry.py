"""Independent expectations for typed call custody and installation ordering."""

from dataclasses import replace

import pytest
from sqlalchemy import func, select

from corpus_structure.semantic.native_objects import (
    INTERNAL_PROGRAM,
    NativeAuthoringError,
    NativeIdentity,
)
from corpus_structure.semantic.native_program import NativeRoutine, pg_type
from corpus_structure.semantic.native_program_registry import ProgramDeclaration, render_programs


def _declaration(name, body, *, after=()):
    return ProgramDeclaration(
        NativeRoutine("data", name, (), pg_type("text"), select(body)),
        "registry-control",
        "owner",
        INTERNAL_PROGRAM,
        install_after=after,
    )


def test_typed_program_calls_and_installation_order():
    provider = _declaration("provider", func.pg_catalog.current_user())
    reader = _declaration("reader", func.data.provider())
    recursive = _declaration("recursive", func.data.recursive())
    programs = render_programs((reader, provider, recursive), registry_schemas=frozenset({"data"}))
    assert [item.declaration.identity.name for item in programs] == [
        "provider",
        "reader",
        "recursive",
    ]
    assert programs[2].callees == {NativeIdentity("function", "data", "recursive")}
    assert programs[1].callees == {NativeIdentity("function", "data", "provider")}
    assert "data.provider()" in programs[1].statement


def test_unresolved_call_duplicate_identity_and_install_cycle_refuse():
    declaration = _declaration("one", func.data.two())
    with pytest.raises(NativeAuthoringError, match=r"unresolved callee data\.two"):
        render_programs((declaration,), registry_schemas=frozenset({"data"}))
    with pytest.raises(NativeAuthoringError, match="duplicate native declaration"):
        render_programs((declaration, declaration), registry_schemas=frozenset({"data"}))
    second = _declaration("two", func.data.one(), after=(declaration.identity,))
    first = replace(declaration, install_after=(second.identity,))
    with pytest.raises(NativeAuthoringError, match="dependency cycle"):
        render_programs((first, second), registry_schemas=frozenset({"data"}))


def test_typed_model_inputs_and_explicit_overload_references():
    from sqlalchemy import Column, MetaData, Table, Text, literal

    from corpus_structure.semantic.native_program import Parameter

    table = Table("record", MetaData(), Column("value", Text()), schema="sem")
    provider = ProgramDeclaration(
        NativeRoutine(
            "data",
            "provider",
            (Parameter("p", pg_type("text")),),
            pg_type("text"),
            select(literal("text")),
        ),
        "registry-control",
        "owner",
        INTERNAL_PROGRAM,
    )
    overloaded = replace(
        provider,
        routine=replace(provider.routine, parameters=(Parameter("p", pg_type("int4")),)),
    )
    reader = _declaration("reader", func.data.provider(table.c.value))
    schemas = frozenset({"data", "sem"})
    with pytest.raises(NativeAuthoringError, match=r"unresolved callee data\.provider"):
        render_programs((provider, overloaded, reader), registry_schemas=schemas)
    reader = replace(
        reader,
        explicit_callees=(provider.identity,),
        install_after=(provider.identity,),
    )
    rendered = render_programs((reader, overloaded, provider), registry_schemas=schemas)
    result = next(item for item in rendered if item.declaration.identity.name == "reader")
    assert result.callees == {NativeIdentity("function", "data", "provider", ("text",))}
    assert ("sem", "record", "value") in result.model_inputs


def test_identity_producer_declares_exact_recursive_callee_and_internal_access():
    from corpus_structure.schema.integrity import role_name
    from corpus_structure.semantic.data_operation_value_native import canonical_identity_programs
    from corpus_structure.semantic.value_codec import decimal_digit_limit

    declarations = canonical_identity_programs(decimal_digits=decimal_digit_limit())
    rendered = render_programs(declarations, registry_schemas=frozenset({"data"}))
    assert [program.declaration.identity for program in rendered] == [
        NativeIdentity("function", "data", "canonical_json", ("jsonb",)),
        NativeIdentity("function", "data", "decimal_canonical", ("text",)),
    ]
    assert rendered[0].callees == {NativeIdentity("function", "data", "canonical_json", ("jsonb",))}
    assert rendered[1].callees == frozenset()
    assert all(program.declaration.owner == role_name("publisher") for program in rendered)
    assert all(
        isinstance(program.declaration, ProgramDeclaration)
        and program.declaration.access == INTERNAL_PROGRAM
        for program in rendered
    )
    assert all(program.declaration.source == "target-current:identity.sql" for program in rendered)


def test_runtime_mutual_calls_do_not_create_installation_cycles():
    from corpus_structure.semantic.native_program import Block, Return

    first = _declaration("first", func.data.second())
    second = _declaration("second", func.data.first())
    first = replace(
        first, routine=replace(first.routine, body=Block((Return(func.data.second()),)))
    )
    second = replace(
        second, routine=replace(second.routine, body=Block((Return(func.data.first()),)))
    )
    rendered = render_programs((first, second), registry_schemas=frozenset({"data"}))
    assert [item.declaration.identity.name for item in rendered] == ["first", "second"]
    assert rendered[0].callees == {second.identity}
    assert rendered[1].callees == {first.identity}


def test_foundation_archive_and_float_programs_have_direct_typed_custody():
    from corpus_structure.schema.integrity import role_name
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.target_installation import foundation_programs

    foundation = foundation_programs(get_metadata())
    programs = {item.declaration.identity: item for item in foundation.programs}
    assert set(programs) == {
        NativeIdentity("function", "data", "canonical_json", ("jsonb",)),
        NativeIdentity("function", "data", "decimal_canonical", ("text",)),
        NativeIdentity("function", "data", "require_float_lexical", ("text",)),
        NativeIdentity("function", "sem", "require_archive_bytes", ("text",)),
        NativeIdentity("function", "sem", "refuse_immutable_mutation"),
        NativeIdentity("function", "sem", "guard_finalized_insert"),
        NativeIdentity("function", "data", "require_runtime_principal", ("text",)),
        NativeIdentity("function", "sem", "require_admission_caller"),
        NativeIdentity(
            "function",
            "sem",
            "record_deployment_admission",
            ("text", "text", "text", "text", "bytea"),
        ),
        NativeIdentity("function", "sem", "activate_release", ("text", "text", "text", "bigint")),
    }
    archive = programs[NativeIdentity("function", "sem", "require_archive_bytes", ("text",))]
    assert archive.callees == {NativeIdentity("function", "data", "canonical_json", ("jsonb",))}
    assert ("sem", "input", "content") in archive.model_inputs
    assert ("sem", "artifact", "content") in archive.model_inputs
    assert ("sem", "release", None) in archive.model_inputs
    assert all(item.declaration.owner == role_name("publisher") for item in programs.values())
    external = {}
    for item in programs.values():
        assert isinstance(item.declaration, ProgramDeclaration)
        if item.declaration.access != INTERNAL_PROGRAM:
            external[item.declaration.identity.name] = item.declaration.access.purposes
    assert external == {
        "activate_release": ("admit",),
        "record_deployment_admission": ("admit",),
        "require_runtime_principal": ("read", "write", "evaluate", "admit"),
    }


def test_view_and_trigger_bind_their_providers_in_creation_order():
    from pglast import ast, parse_sql

    from corpus_structure.semantic.native_program_registry import RelationProgramDeclaration

    def relation(sql):
        statement = parse_sql(sql)[0].stmt
        assert isinstance(statement, (ast.CreateTrigStmt, ast.ViewStmt))
        return RelationProgramDeclaration(statement, "registry-control", "owner")

    provider = _declaration("value", func.pg_catalog.current_user())
    view = relation("CREATE OR REPLACE VIEW data.z_provider AS SELECT data.value()")
    consumer = relation("CREATE OR REPLACE VIEW data.a_consumer AS SELECT * FROM data.z_provider")
    trigger = relation(
        "CREATE TRIGGER a_guard INSTEAD OF INSERT ON data.a_consumer "
        "FOR EACH ROW EXECUTE FUNCTION data.guard()"
    )
    guard = _declaration("guard", func.pg_catalog.current_user())
    declarations = (trigger, view, provider, consumer, guard)
    programs = render_programs(declarations, registry_schemas=frozenset({"data"}))
    assert [item.declaration.identity.name for item in programs] == [
        "guard",
        "value",
        "z_provider",
        "a_consumer",
        "a_guard",
    ]
    assert programs[3].callees == {view.identity}
    assert programs[4].callees == {consumer.identity, guard.identity}
    changed = replace(view, source="relocated")
    regenerated = render_programs(
        (changed,),
        registry_schemas=frozenset({"data"}),
        prerequisites=frozenset({provider.identity}),
    )
    assert regenerated[0].program_identity == programs[2].program_identity


def test_reference_collection_visits_shared_clauses_once(monkeypatch):
    from corpus_structure.semantic.native_program_registry import _References

    leaf = func.data.value()
    get_children = leaf.get_children
    visited = []

    def observe(**options):
        visited.append(leaf)
        return get_children(**options)

    monkeypatch.setattr(leaf, "get_children", observe)
    expression = leaf
    for _ in range(8):
        expression = func.coalesce(expression, expression)
    references = _References()
    references.read(expression)
    assert len(visited) == 1
    assert references.calls == {("data", "value", 0)}
