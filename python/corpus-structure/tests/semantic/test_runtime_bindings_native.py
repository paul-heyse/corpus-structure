"""Actual native runtime custody, same-release pins and independent reuse controls."""

import json
from hashlib import sha256
from types import SimpleNamespace

import psycopg
import pytest
from pydantic import create_model
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import _operation_calls as calls
from corpus_structure.semantic.contracts import analysis_implementation_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    record_method,
    start_run,
)
from corpus_structure.semantic.runtime_binding_store import (
    persist_runtime_binding,
    runtime_binding_for_run,
)
from corpus_structure.semantic.runtime_bindings import RuntimeBindingError, prepare_runtime_binding
from corpus_structure.semantic.types import SourceArtifact

from .operation_scenario_support import prepare_operation_scenario


def alternate_runtime(prepared):
    inputs = tuple(
        SourceArtifact(item.name, item.content + b"\n# independent runtime variant\n")
        if item.name in {"invocation/operations.py", "package/semantic/operations.py"}
        else item
        for item in analysis_implementation_inputs()
    )
    return prepare_runtime_binding(prepared, inputs)


def native_run(conn, prepared, binding):
    """Model an independently installed runtime after native custody registration."""
    persist_runtime_binding(conn, prepared, binding)
    return calls.create_run(
        conn,
        project_id=calls.ProjectId("p"),
        release_id=calls.ReleaseId(prepared.release_id),
        runtime_id=calls.RuntimeId(binding.runtime_id),
        realization_id=calls.RealizationId("z"),
        revision=0,
        dependencies=b"{}",
        kind="full",
        phase=0,
        options={},
        guideline="",
        code_commit="runtime-test",
        projection_context=prepared,
    )


def test_distinct_runtime_pins_preserve_one_release_and_reopen_exact_archives(
    semantic_db_engine, semantic_writer_engine
):
    prepared = prepare_operation_scenario(semantic_db_engine)
    first = prepare_runtime_binding(prepared)
    second = alternate_runtime(prepared)
    assert first.runtime_id != second.runtime_id
    release = table("sem.release")
    with semantic_db_engine.connect() as conn:
        original = conn.execute(select(release.c.prepared_bytes, release.c.manifest_bytes)).one()
    with semantic_writer_engine.begin() as conn:
        first_run = create_run(
            conn, project_id="p", binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full", options={}, code_commit="runtime-test", prepared=prepared,
            runtime_binding=first,
        )
        second_run = native_run(conn, prepared, second)
        assert persist_runtime_binding(conn, prepared, first) == first.runtime_id
    with semantic_writer_engine.connect() as conn:
        assert runtime_binding_for_run(conn, first_run, prepared) == first
        assert runtime_binding_for_run(conn, second_run, prepared) == second
        assert conn.scalar(text("SELECT count(*) FROM sem.runtime_binding")) == 2
        assert conn.scalar(text("SELECT count(*) FROM sem.release")) == 1
        assert conn.execute(
            select(release.c.prepared_bytes, release.c.manifest_bytes)
        ).one() == original


@pytest.mark.parametrize(
    "mutation", ["release", "archive", "contract", "model", "compiler", "semantic", "membership"]
)
def test_native_registration_refuses_altered_or_incompatible_binding(
    semantic_db_engine, semantic_writer_engine, mutation
):
    prepared = prepare_operation_scenario(semantic_db_engine)
    binding = prepare_runtime_binding(prepared)
    manifest, archive = json.loads(binding.manifest), json.loads(binding.archive)
    if mutation == "release":
        manifest["release_id"] = "release:another"
    elif mutation == "archive":
        archive["inputs"][0]["content_hex"] = "00"
    elif mutation == "contract":
        manifest["version"] = "runtime-binding-999"
    elif mutation == "model":
        manifest["execution_model_id"] = "execution:another"
    elif mutation == "compiler":
        manifest["execution_compiler_version"] = "26"
    elif mutation == "semantic":
        manifest["semantic_inputs"] = []
    else:
        archive["inputs"] = archive["inputs"][1:]
    manifest_bytes = canonical_bytes(manifest)
    with pytest.raises(DBAPIError) as rejected, semantic_writer_engine.begin() as conn:
        calls.register_runtime_binding(
            conn, release_id=calls.ReleaseId(prepared.release_id),
            runtime_id=calls.RuntimeId("runtime:" + sha256(manifest_bytes).hexdigest()),
            manifest=manifest_bytes, archive=canonical_bytes(archive),
            projection_context=prepared,
        )
    assert isinstance(rejected.value.orig, psycopg.Error)
    assert rejected.value.orig.sqlstate == "23514"


def test_native_pin_and_archive_are_immutable_and_writer_cannot_bypass_registration(
    semantic_db_engine, semantic_writer_engine
):
    prepared = prepare_operation_scenario(semantic_db_engine)
    binding = prepare_runtime_binding(prepared)
    with semantic_writer_engine.begin() as conn:
        run = native_run(conn, prepared, binding)
    for sql, parameters in (
        ("UPDATE ops.run SET runtime_id=NULL WHERE id=:run", {"run": run}),
        ("UPDATE sem.runtime_binding SET archive_bytes='different'::bytea", {}),
        ("DELETE FROM sem.runtime_binding", {}),
    ):
        with pytest.raises(DBAPIError), semantic_db_engine.begin() as conn:
            conn.execute(text(sql), parameters)
    with pytest.raises(DBAPIError) as denied, semantic_writer_engine.begin() as conn:
        conn.execute(table("sem.runtime_binding").insert().values(
            release_id=prepared.release_id, runtime_id="runtime:unregistered",
            manifest_bytes=b"{}", archive_bytes=b"{}",
        ))
    assert isinstance(denied.value.orig, psycopg.Error)
    assert denied.value.orig.sqlstate == "42501"
    with semantic_writer_engine.connect() as conn:
        assert runtime_binding_for_run(conn, run, prepared) == binding


def test_runtime_change_fences_python_twin_selection_and_native_reuse(
    semantic_db_engine, semantic_writer_engine
):
    prepared = prepare_operation_scenario(semantic_db_engine)
    first = prepare_runtime_binding(prepared)
    second = alternate_runtime(prepared)
    with semantic_writer_engine.begin() as conn:
        origin_run = native_run(conn, prepared, first)
        same_run = native_run(conn, prepared, first)
        other_run = native_run(conn, prepared, second)
        config = record_method(
            conn, SimpleNamespace(name="read", version="1", family="ingest",
                tier="deterministic", confidence_source=None, unit_type="run",
                Config=create_model("RuntimeReadConfig")),
            "default", {}, "runtime-reuse-config", prepared=prepared,
        )
        origin = create_task(conn, run_id=origin_run, config_id=config,
            stage="ingest", unit_type="run", input_hash="same")
        claim = claim_tasks(conn, run_id=origin_run, config_id=config, holder="worker")[0]
        complete_task(conn, task_id=origin, attempt=claim.attempt, holder="worker",
            prepared=prepared, observations=[], outcome="empty")
        same = create_task(conn, run_id=same_run, config_id=config,
            stage="ingest", unit_type="run", input_hash="same")
        other = create_task(conn, run_id=other_run, config_id=config,
            stage="ingest", unit_type="run", input_hash="same")
        task = table("ops.task")
        assert conn.scalar(select(task.c.reused_task_id).where(task.c.id == same)) == origin
        assert conn.scalar(select(task.c.status).where(task.c.id == other)) == "pending"
        assert conn.scalar(text("SELECT ops.valid_reuse(jsonb_populate_record(NULL::ops.task, "
            "jsonb_build_object('id',-1,'run_id',:run,'reused_task_id',:origin,'status','reused',"
            "'method_config_id',:config,'input_hash','same','unit_type','run')))"),
            {"run": other_run, "origin": origin, "config": config}) is False


def test_changed_runtime_cannot_start_or_claim_an_existing_run(
    semantic_db_engine, semantic_writer_engine
):
    prepared = prepare_operation_scenario(semantic_db_engine)
    other_runtime = alternate_runtime(prepared)
    with semantic_writer_engine.begin() as conn:
        run = native_run(conn, prepared, other_runtime)
    with semantic_writer_engine.begin() as conn:
        with pytest.raises(RuntimeBindingError, match="installed runtime differs"):
            start_run(conn, run, prepared=prepared)
        with pytest.raises(RuntimeBindingError, match="installed runtime differs"):
            claim_tasks(conn, run_id=run, config_id=calls.MethodConfigId(-1),
                holder="worker", prepared=prepared)
        assert conn.scalar(select(table("ops.run").c.status).where(
            table("ops.run").c.id == run)) == "created"


def test_unknown_runtime_and_legacy_creation_abi_cannot_create_an_unpinned_current_run(
    semantic_db_engine, semantic_writer_engine
):
    prepared = prepare_operation_scenario(semantic_db_engine)
    with (
        pytest.raises(DBAPIError, match="unknown same-release runtime binding"),
        semantic_writer_engine.begin() as conn,
    ):
        calls.create_run(
            conn, project_id=calls.ProjectId("p"),
            release_id=calls.ReleaseId(prepared.release_id),
            runtime_id=calls.RuntimeId("runtime:unknown"),
            realization_id=calls.RealizationId("z"), revision=0, dependencies=b"{}",
            kind="full", phase=0, options={}, guideline="", code_commit="test",
            projection_context=prepared,
        )
    with (
        pytest.raises(DBAPIError, match="new run requires an immutable runtime binding"),
        semantic_writer_engine.begin() as conn,
    ):
        conn.execute(text("SELECT ops.create_run('p',:release,'z',0,'{}'::bytea,'full',"
            "0,'{}'::jsonb,'','test')"), {"release": prepared.release_id})
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM ops.run")) == 0
