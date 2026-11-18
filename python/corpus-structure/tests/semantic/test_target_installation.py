"""Fresh installation selects current physical custody without legacy execution."""

import json

import pytest
import yaml

from corpus_structure.schema.physical import compile_physical
from corpus_structure.semantic.archive_native import archive_native_sql
from corpus_structure.semantic.archive_transport import archive_tables
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.pdf_domain import CONTRACT, pdf_domain_sources


def prepared_target():
    return compile_physical(
        metadata.info["physical_sources"], linkml_types=metadata.info["physical_linkml_types"]
    )


def test_target_physical_model_keeps_request_pdf_and_release_custody_without_old_roots():
    target = prepared_target()
    assert {
        "ops.task",
        "ops.data_request",
        "ops.source_build",
        "ops.pdf_published_revision",
        "kb.document",
        "kb.source_artifact",
        "sem.runtime_binding",
        "kb.data_product",
    } <= set(target.tables)
    assert not {
        "ops.run",
        "ops.method",
        "ops.method_config",
        "ops.completed_result",
        "kb.source_view",
        "ops.run_source_view",
        "data.fact",
        "data.selected_fact",
    } & set(target.tables)
    assert not any(relation.schema == "eval" for relation in target.tables.values())
    assert not {
        "sem.execution_operation",
        "sem.execution_transition",
        "sem.execution_edge",
        "sem.operation_effect",
        "sem.transition_effect",
    } & set(target.tables)
    task = target.tables["ops.task"]
    assert {
        "data_request_id",
        "data_generation",
        "invocation_key",
        "attempt",
        "claimed_by",
        "lease_until",
        "result_digest",
    } <= set(task.c.keys())
    assert not {
        "run_id",
        "method_config_id",
        "stage",
        "unit_id",
        "unit_type",
        "reused_task_id",
        "packet_hash",
        "input_hash",
    } & set(task.c.keys())
    assert not task.c.data_request_id.nullable and not task.c.data_generation.nullable
    assert "selected_result_run_id" not in target.tables["data.project"].c
    for relation in target.tables.values():
        for foreign in relation.foreign_keys:
            assert foreign.column.table.fullname in target.tables


def test_target_archive_uses_the_exact_supplied_metadata_and_pdf_actions():
    target = prepared_target()
    assert all(relation.metadata is target for relation in archive_tables(target))
    assert "CREATE TEMP TABLE" in archive_native_sql(target_metadata=target)
    sources = pdf_domain_sources(
        physical_sources=target.info["physical_sources"],
        linkml_types=target.info["physical_linkml_types"],
    )
    contract = json.loads(next(source.content for source in sources if source.name == CONTRACT))
    assert {"read_native_source", "retain_pdf_original", "seal_pdf_build"} <= set(
        contract["actions"]
    )
    assert not {"publish_source_view", "read_source_view"} & set(contract["actions"])
    assert all(
        entry["operation"] not in {"publish_source_view", "read_source_view"}
        for invariant in contract["diagnostics"]
        for entry in invariant["diagnostics"]
    )


def test_target_native_capture_and_shared_task_checks_have_no_legacy_task_branch():
    from pglast import parse_plpgsql, parse_sql

    from corpus_structure.semantic.native_products import current_admission_fields
    from corpus_structure.semantic.target_installation import (
        capture_target_installation,
        target_pdf_sql,
        target_task_guard_sql,
    )

    capture = capture_target_installation(prepared_target())
    fields = current_admission_fields(capture.authoring_inputs, target_metadata=capture.metadata)
    assert fields["views"] == []
    assert "analytical_abi" not in fields
    assert "data.selected_fact" not in fields["physical_relations"]
    assert fields["physical_id"] == capture.metadata.info["physical_model_id"]
    captured = {source.name: source.content for source in capture.authoring_inputs.sources}
    checks = captured["authoring/data-operation-task-checks.sql"].decode()
    guard = target_task_guard_sql(
        capture.metadata.info["physical_sources"]["data-operation-native.yaml"], checks
    )
    assert parse_sql(guard) and parse_plpgsql(guard)
    assert all(
        name not in guard
        for name in ("ops.run", "method_config", "execution_task_state", "require_transition")
    )
    assert all(
        message in guard
        for message in (
            "protected admitted request generation",
            "invalid data claim fence",
            "data task association/terminal state immutable",
            "data completion requires receipt",
        )
    )
    payload = target_pdf_sql(capture)
    assert parse_sql(payload)
    assert all(name not in payload for name in ("ops.run", "kb.source_view", "ops.method_config"))
    assert "ops.retain_pdf_original" in payload and "ops.seal_pdf_build" in payload


def test_captured_recognition_reader_is_an_exact_current_pdf_authoring_input():
    from dataclasses import replace
    from pathlib import Path

    from pglast import parse_sql

    from corpus_structure.semantic.native_inventory import update_function_inventory
    from corpus_structure.semantic.target_installation import (
        capture_target_installation,
        target_pdf_sql,
    )

    capture = capture_target_installation(prepared_target())
    source = next(
        item
        for item in capture.authoring_inputs.sources
        if item.name == "authoring/pdf-captured-recognition.sql"
    )
    assert (
        source.content
        == (
            Path(__file__).parents[2]
            / "src/corpus_structure/semantic/sql/source_record_recognition.sql"
        ).read_bytes()
    )
    # Offline PL/pgSQL parsing cannot resolve the actual ops composite row type.
    # The normal PostgreSQL authoring checker owns that installed-layout check.
    assert parse_sql(source.content.decode())
    inventory = {}
    update_function_inventory(inventory, target_pdf_sql(capture))
    specification = inventory["ops.record_captured_recognition_text(bigint,text,text,text,jsonb)"]
    assert specification["owner"] == "corpus_sem_publisher"
    assert set(specification["execute_roles"]) == {
        "corpus_sem_reader",
        "corpus_sem_writer",
        "corpus_sem_evaluator",
    }
    altered = replace(
        source,
        content=source.content.replace(
            b"original precision differs", b"changed captured precision diagnostic"
        ),
    )
    changed = replace(
        capture,
        authoring_inputs=replace(
            capture.authoring_inputs,
            sources=tuple(
                altered if item.name == source.name else item
                for item in capture.authoring_inputs.sources
            ),
        ),
    )
    assert "changed captured precision diagnostic" in target_pdf_sql(changed)
    assert "original precision differs" not in target_pdf_sql(changed)


def test_target_observation_projection_uses_acquired_spec_after_ambient_source_restores(
    monkeypatch,
):
    import json
    from dataclasses import replace

    from pglast import ast, parse_sql
    from pglast.stream import RawStream

    from corpus_structure.semantic import pdf_domain
    from corpus_structure.semantic.pdf_observations import MEANING_SPEC
    from corpus_structure.semantic.target_installation import (
        capture_target_installation,
        target_pdf_sql,
    )
    from corpus_structure.semantic.types import SourceArtifact
    from semantic.pdf_domain_support import altered_domain

    acquire = pdf_domain.pdf_domain_sources

    def selected_sources(**kwargs):
        contract, *sources = acquire(**kwargs)
        original = pdf_domain.PdfDomainContract(contract.content, tuple(sources))
        declaration = next(source for source in sources if source.name == MEANING_SPEC)
        selected = json.loads(declaration.content)
        selected["binding_fields"].remove("seed")
        domain = altered_domain(
            original,
            sources=tuple(
                replace(source, content=json.dumps(selected).encode())
                if source.name == MEANING_SPEC
                else source
                for source in sources
            ),
        )
        return (SourceArtifact(pdf_domain.CONTRACT, domain.content), *domain.sources)

    with monkeypatch.context() as acquisition:
        acquisition.setattr(pdf_domain, "pdf_domain_sources", selected_sources)
        captured = capture_target_installation(prepared_target())
    statement = next(
        row.stmt
        for row in parse_sql(target_pdf_sql(captured))
        if isinstance(row.stmt, ast.CreateFunctionStmt)
        and row.stmt.funcname
        and row.stmt.funcname[-1].sval == "pdf_observation_meaning"
    )
    assert "'seed',observed->'binding'->'seed'" not in RawStream()(statement)


def test_current_descriptor_and_projection_guard_do_not_inherit_obsolete_storage():
    from pglast import parse_sql

    from corpus_structure.semantic.archive_projection_native import execution_projection_check_sql
    from corpus_structure.semantic.native_admission import native_admission_sql
    from corpus_structure.semantic.native_products import (
        admission_kernel,
        literal_json_descriptor,
    )
    from corpus_structure.semantic.target_installation import (
        capture_target_installation,
        target_admission_descriptor,
    )

    capture = capture_target_installation(prepared_target())
    # This checks declaration rendering, without pretending the unnormalized
    # declaration is an admitted native catalog or an installed database.
    sql = native_admission_sql(
        admission_kernel(),
        inputs=capture.authoring_inputs,
        base_descriptor=target_admission_descriptor(capture, ()),
        target_metadata=capture.metadata,
    )
    descriptor = literal_json_descriptor(sql, "data.execution_contract_descriptor")
    assert parse_sql(sql)
    assert {table["relation"] for table in descriptor["tables"]} == set(capture.metadata.tables)
    assert descriptor["views"] == []
    assert not any(reader["relation"].startswith("eval.") for reader in descriptor["readers"])
    guard = execution_projection_check_sql(capture.metadata)
    assert "FROM sem.execution_operation" not in guard
    assert "kind = 'execution_model'" in guard
    assert "requires current declared data operations" in guard
    assert parse_sql(guard)


def test_explicit_pdf_metadata_controls_lossless_equality_and_native_read_types():
    from sqlalchemy import Double, literal
    from sqlalchemy.dialects.postgresql import dialect

    from corpus_structure.semantic.pdf_validation_read_native import _equal_rows
    from corpus_structure.semantic.published_document import published_readers_sql

    target = prepared_target()
    # A deliberately changed physical type must reach both actual consumers;
    # an ambient model with the original bigint would choose different equality.
    target.tables["kb.pdf_record_access"].c.ordinal.type = Double()
    equality = _equal_rows(
        target, literal("current"), literal("previous"), "kb.pdf_record_access"
    ).compile(dialect=dialect(), compile_kwargs={"literal_binds": True})
    assert "float8send(CAST(kb.pdf_record_access.ordinal AS DOUBLE PRECISION))" in str(equality)
    assert "ordinal DOUBLE PRECISION" in published_readers_sql(target_metadata=target)


def test_native_definition_source_cohort_cannot_be_mixed_with_another_physical_capture():
    from corpus_structure.semantic.data_operation_storage import data_operation_native_definitions
    from corpus_structure.semantic.target_installation import capture_target_installation

    capture = capture_target_installation(prepared_target())
    changed = dict(metadata.info["physical_sources"])
    document = yaml.safe_load(changed["physical.yaml"])
    document["description"] = "A different explicitly captured physical source."
    changed["physical.yaml"] = yaml.safe_dump(document).encode()
    other = compile_physical(changed, linkml_types=metadata.info["physical_linkml_types"])
    # Refusal precedes any database type lookup or normalization effect.
    with pytest.raises(ValueError, match="same captured physical sources"):
        data_operation_native_definitions(
            None, target_metadata=other, sources=capture.authoring_inputs.native_sources
        )


def test_frozen_target_environment_does_not_import_current_metadata(monkeypatch):
    import builtins
    from contextlib import nullcontext
    from types import SimpleNamespace

    from corpus_structure.semantic.alembic_environment import run_migrations

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "corpus_structure.semantic.metadata":
            raise AssertionError("frozen target deployment imported current compiler metadata")
        return original_import(name, *args, **kwargs)

    received = {}
    connection = object()
    context = SimpleNamespace(
        config=SimpleNamespace(attributes={"connection": connection}),
        is_offline_mode=lambda: False,
        configure=lambda **kwargs: received.update(kwargs),
        begin_transaction=nullcontext,
        run_migrations=lambda: received.update(applied_frozen_revision=True),
    )
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    run_migrations(context)
    assert received["connection"] is connection
    assert received["target_metadata"] is None
    assert received["applied_frozen_revision"] is True
