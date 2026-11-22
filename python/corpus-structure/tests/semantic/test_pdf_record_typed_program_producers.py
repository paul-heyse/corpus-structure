"""Record producers retain their qualified native definitions and real purpose grants."""

import pytest
from pglast import ast, parse_sql
from pglast.stream import RawStream

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.migrations import ALEMBIC_DIR
from corpus_structure.semantic.native_authoring import load_native_state
from corpus_structure.semantic.native_objects import NativeAuthoringError
from corpus_structure.semantic.native_program_registry import render_programs
from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_record_access_native import (
    pdf_access_correspondence_programs,
    pdf_access_correspondence_sql,
)
from corpus_structure.semantic.pdf_record_digest_native import (
    pdf_record_logical_identity_programs,
    pdf_record_logical_identity_sql,
)
from corpus_structure.semantic.pdf_record_proof_native import (
    pdf_record_proof_programs,
    pdf_record_proof_sql,
)
from corpus_structure.semantic.pdf_selected_source_native import (
    selected_source_reader_programs,
    selected_source_reader_sql,
)

DIGEST = {
    "pdf_identity_text",
    "pdf_identity_inline",
    "pdf_identity_ascii_string",
    "pdf_identity_stream_scalar",
    "pdf_identity_companion_scalar",
    "pdf_record_logical_identity",
}
ACCESS = {
    "pdf_projection_scalar_matches",
    "pdf_projection_stream_value",
    "pdf_projection_stream_matches",
    "pdf_check_access_correspondence",
}
PROOF = {
    "read_pdf_record_identity_frames",
    "read_pdf_record_identity_items",
    "read_pdf_record_identity_targets",
}
SELECTED = {"read_pdf_selected_source_events"}
SCHEMAS = frozenset({"ops", "sem", "data", "kb", "eval"})


def contexts():
    model = get_metadata()
    domain = trusted_pdf_context().domain
    return (
        (
            pdf_record_logical_identity_programs(target_metadata=model),
            pdf_record_logical_identity_sql(target_metadata=model),
            DIGEST,
        ),
        (pdf_record_proof_programs(model), pdf_record_proof_sql(model), PROOF),
        (pdf_access_correspondence_programs(model), pdf_access_correspondence_sql(model), ACCESS),
        (
            selected_source_reader_programs(target_metadata=model, pdf_domain=domain),
            selected_source_reader_sql(target_metadata=model, pdf_domain=domain),
            SELECTED,
        ),
    )


def test_record_programs_preserve_inventory_owner_registered_acl_and_raw_capture():
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
            assert program.owner == role_name("publisher")
            expected_purposes = (
                ("read", "evaluate")
                if name in PROOF
                else ("read", "write", "evaluate")
                if name in SELECTED
                else ()
            )
            assert program.access.purposes == expected_purposes
            assert program.access.internal is (not expected_purposes)
            prior = frozen[program.identity]
            assert prior.catalog["owner"] == program.owner
            expected_acl = {
                (program.owner, "EXECUTE", False),
                *program.access.grants(program.owner),
            }
            assert {tuple(item) for item in prior.catalog["acl"]} == expected_acl
            parsed = parse_sql(program.routine.render())[0].stmt
            assert parsed is not None
            assert RawStream()(parsed) == RawStream()(functions[name])
    assert count == 14


def test_record_programs_require_authentic_provider_dependencies():
    programs = tuple(program for cohort, _, _ in contexts() for program in cohort)
    frozen = load_native_state(ALEMBIC_DIR / "versions/semantic_sbx_current_root_native.json")
    providers = frozenset(item.identity for item in frozen) - {
        program.identity for program in programs
    }
    rendered = render_programs(programs, registry_schemas=SCHEMAS, prerequisites=providers)
    by_name = {item.declaration.identity.name: item for item in rendered}
    assert len(by_name) == 14
    assert {callee.name for callee in by_name["read_pdf_selected_source_events"].callees} >= {
        "require_published_companion_pin",
        "read_pdf_published_revision",
        "pdf_record_context_rows",
    }
    assert {callee.name for callee in by_name["pdf_record_logical_identity"].callees} == {
        "pdf_identity_verify_artifact",
        "pdf_record_identity_frames",
    }
    without_frame_provider = frozenset(
        item
        for item in providers
        if (item.schema, item.name) != ("ops", "pdf_record_identity_frames")
    )
    with pytest.raises(
        NativeAuthoringError, match=r"unresolved callee ops\.pdf_record_identity_frames"
    ):
        render_programs(programs, registry_schemas=SCHEMAS, prerequisites=without_frame_provider)
