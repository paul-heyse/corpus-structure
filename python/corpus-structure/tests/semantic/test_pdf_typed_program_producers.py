"""Typed PDF staging/spool authority agrees with its independent function/ACL inventory."""

import pytest
from pglast import ast, parse_sql
from pglast.stream import RawStream

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.migrations import ALEMBIC_DIR, head_revision
from corpus_structure.semantic.native_authoring import load_native_state
from corpus_structure.semantic.native_objects import NativeAuthoringError
from corpus_structure.semantic.native_program import NativeRoutine
from corpus_structure.semantic.native_program_registry import ProgramDeclaration, render_programs
from corpus_structure.semantic.pdf_spool_native import pdf_spool_native_programs
from corpus_structure.semantic.pdf_staging_native import stage_native_programs, stage_native_sql

SPOOL = {
    "register_pdf_spool_producer",
    "pdf_lowering_contract_name",
    "pdf_spool_material_identity",
    "pdf_spool_request_material",
    "read_pdf_spool_recovery_candidates",
    "register_pdf_spool_contributor",
    "pdf_spool_contributors",
    "read_pdf_spool_contributors",
}
STAGING = {
    "prepare_pdf_stage",
    "require_pdf_stage_scratch",
    "adopt_pdf_batch",
    "pdf_task_context",
    "pdf_stage_owner_current",
    "require_pdf_stage_owner",
    "begin_pdf_build",
    "require_pdf_build",
    "retain_pdf_original",
    "read_pdf_producer_basis",
    "inspect_pdf_progress",
    "resume_pdf_build",
    "abandon_pdf_build",
}
INTERNAL = {
    "pdf_lowering_contract_name",
    "pdf_spool_material_identity",
    "pdf_spool_request_material",
    "pdf_spool_contributors",
    "require_pdf_stage_scratch",
    "pdf_task_context",
    "pdf_stage_owner_current",
    "require_pdf_stage_owner",
    "require_pdf_build",
}
SCHEMAS = frozenset({"ops", "sem", "data", "kb", "eval"})


def producers():
    model = get_metadata()
    return (
        *pdf_spool_native_programs(target_metadata=model),
        *stage_native_programs(target_metadata=model),
    )


def prerequisites(declarations):
    frozen = load_native_state(ALEMBIC_DIR / "versions" / f"{head_revision()}_native.json")
    return frozenset(item.identity for item in frozen) - {item.identity for item in declarations}


def test_pdf_owner_inventory_and_access_are_typed_and_preserve_raw_function_and_acl_contract():
    declarations = producers()
    assert {program.identity.name for program in declarations} == SPOOL | STAGING
    assert len(declarations) == 21
    assert all(
        isinstance(program, ProgramDeclaration)
        and isinstance(program.routine, NativeRoutine)
        and program.owner == role_name("publisher")
        for program in declarations
    )
    raw = tuple(item.stmt for item in parse_sql(stage_native_sql(target_metadata=get_metadata())))
    functions = {}
    for statement in raw:
        if isinstance(statement, ast.CreateFunctionStmt):
            assert statement.funcname
            functions[statement.funcname[-1].sval] = statement
    grants = {}
    revokes = set()
    for statement in raw:
        if not isinstance(statement, ast.GrantStmt):
            continue
        for target in statement.objects or ():
            if not isinstance(target, ast.ObjectWithArgs):
                continue
            assert target.objname
            name = target.objname[-1].sval
            if name not in SPOOL | STAGING:
                continue
            if statement.is_grant:
                grants.setdefault(name, set()).update(
                    role.rolename for role in (statement.grantees or ())
                )
            elif any(
                role.roletype.name == "ROLESPEC_PUBLIC" for role in (statement.grantees or ())
            ):
                revokes.add(name)
    assert revokes == SPOOL | STAGING
    for program in declarations:
        name = program.identity.name
        # Parsing is a verification view, never the current declaration source.
        declaration = parse_sql(program.routine.render())[0].stmt
        assert declaration is not None
        assert RawStream()(declaration) == RawStream()(functions[name])
        expected = set() if name in INTERNAL else {role_name("writer")}
        assert grants.get(name, set()) == expected
        assert {role for role, _, _ in program.access.grants(program.owner)} == expected
        assert program.access.internal is (name in INTERNAL)


def test_pdf_program_dependencies_resolve_against_actual_registered_providers():
    declarations = producers()
    rendered = render_programs(
        declarations, registry_schemas=SCHEMAS, prerequisites=prerequisites(declarations)
    )
    assert {item.declaration.identity.name for item in rendered} == SPOOL | STAGING
    by_name = {item.declaration.identity.name: item for item in rendered}
    assert {item.name for item in by_name["read_pdf_spool_recovery_candidates"].callees} >= {
        "pdf_spool_material_identity",
        "pdf_spool_request_material",
        "read_pdf_producer_basis",
        "require_pdf_build",
        "require_pdf_operation",
    }
    assert ("ops", "pdf_stage_build", None) in by_name["require_pdf_build"].model_inputs
    assert ("ops", "pdf_stage_receipt", None) in by_name["adopt_pdf_batch"].model_inputs
    missing = frozenset(
        item
        for item in prerequisites(declarations)
        if (item.schema, item.name) != ("ops", "pdf_contract_input")
    )
    with pytest.raises(NativeAuthoringError, match=r"unresolved callee ops\.pdf_contract_input"):
        render_programs(declarations, registry_schemas=SCHEMAS, prerequisites=missing)
