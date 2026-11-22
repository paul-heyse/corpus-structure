"""Typed payload declarations preserve real grants, dependencies and inlining contracts."""

import pytest
from pglast import ast, parse_sql
from pglast.stream import RawStream

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.migrations import ALEMBIC_DIR
from corpus_structure.semantic.native_authoring import load_native_state
from corpus_structure.semantic.native_objects import NativeAuthoringError
from corpus_structure.semantic.native_program_registry import render_programs
from corpus_structure.semantic.pdf_companion_adoption_native import (
    companion_adoption_programs,
    companion_adoption_sql,
)
from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_domain import pdf_domain_sources
from corpus_structure.semantic.pdf_domain_native import (
    pdf_domain_native_programs,
    pdf_domain_native_sql,
)
from corpus_structure.semantic.pdf_shared_stream_queries import (
    shared_stream_queries_programs,
    shared_stream_queries_sql,
)
from corpus_structure.semantic.pdf_shared_stream_writes import (
    shared_stream_writes_programs,
    shared_stream_writes_sql,
)
from corpus_structure.semantic.pdf_shared_streams import (
    part_wire_contract_programs,
    part_wire_contract_sql,
)

DOMAIN = {"pdf_contract_input", "admit_pdf_operation_contracts", "require_pdf_operation"}
PART = {"pdf_part_upload_contract"}
COMPANIONS = {"prepare_pdf_companions", "adopt_pdf_companions"}
QUERIES = {
    "pdf_stream_project",
    "pdf_artifact_parts",
    "pdf_shared_stream_ready",
    "pdf_pending_stream_owner_dead",
}
WRITES = {
    "probe_pdf_shared_streams",
    "pdf_reclaim_pending_stream",
    "pdf_cleanup_pending_build",
    "pdf_shared_stream_mutation_guard",
    "pdf_adopt_shared_stream_descriptors",
    "pdf_adopt_shared_stream_parts",
    "pdf_verify_shared_stream",
}
SCHEMAS = frozenset({"ops", "sem", "data", "kb", "eval"})


def contexts():
    model, context = get_metadata(), trusted_pdf_context()
    sources = pdf_domain_sources(
        physical_sources=model.info["physical_sources"],
        linkml_types=model.info["physical_linkml_types"],
    )
    return (
        (
            pdf_domain_native_programs(sources=sources, target_metadata=model),
            pdf_domain_native_sql(sources=sources, target_metadata=model),
            DOMAIN,
        ),
        (part_wire_contract_programs(model), part_wire_contract_sql(model), PART),
        (
            companion_adoption_programs(context, model),
            companion_adoption_sql(context, model),
            COMPANIONS,
        ),
        (shared_stream_queries_programs(model), shared_stream_queries_sql(model), QUERIES),
        (shared_stream_writes_programs(model), shared_stream_writes_sql(model), WRITES),
    )


def semantic_declaration(statement):
    assert isinstance(statement, ast.CreateFunctionStmt)
    # SQL option serialization order is not an executable property. All flags,
    # values, defaults, bodies and output columns still compare independently.
    statement.options = tuple(sorted(statement.options or (), key=lambda option: option.defname))
    return RawStream()(statement)


def test_payload_programs_preserve_inventory_owner_acl_and_current_raw_capture():
    frozen = {
        item.identity: item
        for item in load_native_state(
            ALEMBIC_DIR / "versions/semantic_sbx_current_root_native.json"
        )
    }
    count = 0
    for programs, raw, expected_names in contexts():
        assert {program.identity.name for program in programs} == expected_names
        functions = {}
        for item in parse_sql(raw):
            statement = item.stmt
            if isinstance(statement, ast.CreateFunctionStmt):
                assert statement.funcname
                functions[statement.funcname[-1].sval] = statement
        for program in programs:
            count += 1
            name = program.identity.name
            expected = (
                ("write", "read", "admit", "evaluate")
                if name == "require_pdf_operation"
                else ("write",)
                if name in COMPANIONS | {"probe_pdf_shared_streams"}
                else ()
            )
            assert program.access.purposes == expected
            assert program.access.internal is (not expected)
            assert (
                program.owner == frozen[program.identity].catalog["owner"] == role_name("publisher")
            )
            expected_acl = {
                (program.owner, "EXECUTE", False),
                *program.access.grants(program.owner),
            }
            assert {
                tuple(entry) for entry in frozen[program.identity].catalog["acl"]
            } == expected_acl
            assert semantic_declaration(
                parse_sql(program.routine.render())[0].stmt
            ) == semantic_declaration(functions[name])
    assert count == 17


def test_payload_programs_refuse_missing_actual_providers():
    programs = tuple(program for cohort, _, _ in contexts() for program in cohort)
    frozen = load_native_state(ALEMBIC_DIR / "versions/semantic_sbx_current_root_native.json")
    providers = frozenset(item.identity for item in frozen) - {
        program.identity for program in programs
    }
    rendered = render_programs(programs, registry_schemas=SCHEMAS, prerequisites=providers)
    assert len(rendered) == 17
    by_name = {item.declaration.identity.name: item for item in rendered}
    assert {callee.name for callee in by_name["adopt_pdf_companions"].callees} >= {
        "pdf_adopt_shared_stream_descriptors",
        "pdf_adopt_shared_stream_parts",
        "require_pdf_build",
    }
    assert ("ops", "pdf_shared_stream", None) in by_name[
        "pdf_pending_stream_owner_dead"
    ].model_inputs
    without_build = frozenset(
        item for item in providers if (item.schema, item.name) != ("ops", "require_pdf_build")
    )
    with pytest.raises(NativeAuthoringError, match=r"unresolved callee ops\.require_pdf_build"):
        render_programs(programs, registry_schemas=SCHEMAS, prerequisites=without_build)


def test_part_reader_keeps_invoker_inlining_and_declared_null_defaults():
    model = get_metadata()
    queries = {
        program.identity.name: program.routine for program in shared_stream_queries_programs(model)
    }
    reader = queries["pdf_artifact_parts"]
    assert reader.search_path == () and reader.security_definer is False
    assert reader.volatility == "stable" and reader.strict is False
    assert not isinstance(reader.body, str)
    parameters = {parameter.name: parameter for parameter in reader.parameters}
    stage_default = parameters["p_stage"].default
    stream_default = parameters["p_streams"].default
    assert stage_default is not None and stream_default is not None
    assert RawStream()(stage_default) == "FALSE"
    assert RawStream()(stream_default) == "NULL"
    assert queries["pdf_stream_project"].strict is True
    writers = {
        program.identity.name: program.routine for program in shared_stream_writes_programs(model)
    }
    assert writers["probe_pdf_shared_streams"].security_definer is True
    trigger_names = writers["pdf_shared_stream_mutation_guard"].returns.names
    assert trigger_names
    assert trigger_names[-1].sval == "trigger"
    complete = next(
        parameter
        for parameter in writers["pdf_verify_shared_stream"].parameters
        if parameter.name == "p_complete"
    )
    assert complete.default is not None
    assert RawStream()(complete.default) == "TRUE"
