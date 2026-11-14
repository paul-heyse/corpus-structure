"""Actual prospective native guards enforce the same method/release dimensional product."""

import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    create_run,
    create_task,
    record_method,
)
from semantic.method_dimensions_native_support import (
    current_guarded_database as current_guarded_database,
)
from semantic.operation_scenario_support import prepare_operation_scenario


class Config(BaseModel):
    pass


def task(admin, writer):
    prepared = prepare_operation_scenario(admin)
    current_guarded_database(admin)
    method = SimpleNamespace(
        name="normalize.formula",
        version="dimension-control-1",
        family="normalize",
        tier="deterministic",
        confidence_source=None,
        unit_type="run",
        Config=Config,
    )
    with writer.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        config = record_method(conn, method, "default", {}, "dimension-config", prepared=prepared)
        identity = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="normalize",
            unit_type="run",
            input_hash="test",
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="owner")[0]
    return prepared, run, config, identity, claim


def complete(conn, claim, *, family="value", outcome="produced", confidence=None, envelope=None):
    payload = {
        "observation_key": "method-dimension-control",
        "item_key": "control",
        "family": family,
        "outcome": outcome,
        "payload": {"kind": "object", "fields": []},
    }
    if confidence is not None:
        payload["confidence_source"] = confidence
    rows = [
        {
            "ordinal": 0,
            "observation_key": "method-dimension-control",
            "kind": family,
            "payload_definition": "SourceObservation",
            "payload": payload,
            "outcome": outcome,
        }
    ]
    return conn.scalar(
        text(
            "SELECT ops.complete_task(:task,:attempt,'owner',CAST(:rows AS jsonb),'done',NULL,"
            "CAST(:envelope AS jsonb))"
        ),
        {
            "task": claim.task_id,
            "attempt": claim.attempt,
            "rows": json.dumps(rows),
            "envelope": json.dumps(envelope) if envelope is not None else None,
        },
    )


def test_native_report_dimensions_refuse_before_observation_effects(
    commit_db_engine, commit_writer_engine
):
    _prepared, _run, _config, identity, claim = task(commit_db_engine, commit_writer_engine)
    for values, message in [
        ({"family": "mention"}, "family/outcome"),
        ({"outcome": "done"}, "family/outcome"),
        ({"confidence": "agent"}, "confidence provenance"),
        ({"envelope": {"outcome": "not_recorded"}}, "method result outcome is not admitted"),
        (
            {"envelope": {"outcome": "empty"}},
            "method result outcome differs from protected task completion",
        ),
    ]:
        with pytest.raises(DBAPIError, match=message), commit_writer_engine.begin() as conn:
            complete(conn, claim, **values)
        with commit_db_engine.connect() as conn:
            assert (
                conn.scalar(
                    text("SELECT count(*) FROM kb.observation WHERE task_id=:task"),
                    {"task": identity},
                )
                == 0
            )
            assert (
                conn.scalar(text("SELECT status FROM ops.task WHERE id=:task"), {"task": identity})
                == "running"
            )
            assert (
                conn.scalar(
                    text("SELECT count(*) FROM ops.task_result WHERE task_id=:task"),
                    {"task": identity},
                )
                == 0
            )
    with commit_writer_engine.begin() as conn:
        receipt = complete(conn, claim, envelope={"outcome": "produced"})
        assert receipt["receipt"]["protocol"] == "done"
        assert receipt["receipt"]["task_id"] == identity
    with commit_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM kb.observation WHERE task_id=:task"), {"task": identity}
            )
            == 1
        )


def test_native_task_guard_rejects_metadata_outside_its_release(
    commit_db_engine, commit_writer_engine
):
    _prepared, run, config, _identity, _claim = task(commit_db_engine, commit_writer_engine)
    with commit_db_engine.begin() as conn:
        method_id = conn.scalar(
            select(table("ops.method_config").c.method_id).where(
                table("ops.method_config").c.id == config
            )
        )
        original = dict(
            conn.execute(select(table("ops.method")).where(table("ops.method").c.id == method_id))
            .mappings()
            .one()
        )
        original.pop("id")
        original.update(version="dimension-invalid-metadata", family="ingest")
        bad_method = conn.scalar(
            table("ops.method").insert().values(**original).returning(table("ops.method").c.id)
        )
        bad_config = conn.scalar(
            table("ops.method_config")
            .insert()
            .values(method_id=bad_method, name="bad", params={}, config_hash="bad-dimension")
            .returning(table("ops.method_config").c.id)
        )
    with pytest.raises(DBAPIError, match="not admitted"), commit_writer_engine.begin() as conn:
        create_task(
            conn,
            run_id=run,
            config_id=bad_config,
            stage="normalize",
            unit_type="run",
            input_hash="wrong-family",
        )
    with commit_db_engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT count(*) FROM ops.task WHERE run_id=:run"), {"run": run}) == 1
        )
