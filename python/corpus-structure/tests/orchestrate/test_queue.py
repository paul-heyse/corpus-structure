"""Worker claiming, leases, fencing and retries (P0-O-1, orchestration §3.6)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest
from sqlalchemy import Connection, Engine, text

from corpus_structure.core.method import (
    MeasurementDraft,
    ObservationDraft,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.payloads import MentionPayload
from corpus_structure.core.vocab import (
    MeasurementScope,
    MethodFamily,
    ObservationKind,
    ObservationOutcome,
    RunKind,
    Stage,
    TaskStatus,
    TaskUnitType,
)
from corpus_structure.orchestrate import context, queue, runs, tasks

PARSE_DETAIL = (
    "INSERT INTO meta.payload_schema (model_revision_id, class, kind, version, "
    "compatibility_class, json_schema_id, arrow_schema, reason, authorized_by) SELECT id, "
    "'test:parse_detail', 'parse_detail', 1, 'initial', 'test', '', 'test', 'test' FROM "
    "meta.model_revision LIMIT 1 ON CONFLICT DO NOTHING"
)


def setup(db: Connection, orch: SimpleNamespace, tmp_path: Path, n: int = 4) -> SimpleNamespace:
    m09 = orch.Stub("extract.math", TaskUnitType.DOCUMENT, MethodFamily.EXTRACT)
    w = orch.setup_project(db, tmp_path, methods=[orch.ingest_stub(), m09])
    db.execute(text(PARSE_DETAIL))
    created = runs.create_run(
        db,
        project_id=w.project_id,
        kind=RunKind.FULL,
        versions=w.versions,
        registry=w.registry,
        documents=w.documents,
        commit="t",
    )
    view = context.run_view(db, created.id)
    docs = db.execute(
        text("SELECT id, key FROM kb.document WHERE project_id = :p ORDER BY key"),
        {"p": w.project_id},
    ).all()[:n]
    rc = created.configs["ingest.html/default"]
    units = [
        UnitView(UnitRef(TaskUnitType.DOCUMENT, d.id, d.key), view, document_id=d.id) for d in docs
    ]
    made = tasks.create_tasks(
        db, created.id, Stage.INGEST, rc, w.registry.method("ingest.html"), units
    )
    return SimpleNamespace(w=w, run=created.id, config=rc.method_config_id, tasks=made, docs=docs)


def claim(conn: Connection, s: SimpleNamespace, holder: str, n: int = 1) -> list[queue.Claimed]:
    return queue.claim(conn, s.run, Stage.INGEST, s.config, holder, n)


def test_two_connections_claim_disjoint_tasks(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    with committing_db.begin() as conn:
        s = setup(conn, orch, tmp_path)
    with committing_db.connect() as a, committing_db.connect() as b:
        ta, tb = a.begin(), b.begin()
        first = claim(a, s, "w1", 2)
        second = claim(b, s, "w2", 3)  # SKIP LOCKED: the first's rows are not waited for
        ta.commit()
        tb.commit()
    assert len(first) == 2 and len(second) == 2
    assert not {c.id for c in first} & {c.id for c in second}
    assert {c.attempt for c in first + second} == {1}


def ingest_result(orch: SimpleNamespace, c: queue.Claimed) -> UnitResult:
    return UnitResult(
        ref=UnitRef(TaskUnitType.DOCUMENT, c.unit_id, c.unit_key),
        outcome=ObservationOutcome.EMPTY,
        rendition=orch.page_content(str(c.unit_key)),
        parse_detail={"warnings": []},
    )


def test_an_expired_lease_is_claimed_again_and_the_stale_write_commits_nothing(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    s = setup(db, orch, tmp_path, n=1)
    (stale,) = claim(db, s, "w1")
    db.execute(
        text("UPDATE ops.task SET lease_until = now() - interval '1 second' WHERE id = :i"),
        {"i": stale.id},
    )
    (fresh,) = claim(db, s, "w2")
    assert (fresh.id, fresh.attempt) == (stale.id, 2)
    with pytest.raises(queue.LeaseLost), db.begin_nested():
        queue.write_result(db, stale.id, stale.attempt, ingest_result(orch, stale))
    assert db.execute(text("SELECT count(*) FROM kb.rendition")).scalar_one() == 0
    assert queue.write_result(db, fresh.id, fresh.attempt, ingest_result(orch, fresh)) == "done"
    row = db.execute(
        text(
            "SELECT status, attempt, finished_at IS NOT NULL, lease_until FROM "
            "ops.task WHERE id = :i"
        ),
        {"i": fresh.id},
    ).one()
    assert tuple(row) == ("done", 2, True, None)
    assert db.execute(text("SELECT count(*) FROM kb.rendition_build")).scalar_one() == 1


def test_the_terminal_write_holds_observations_and_measurements(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    s = setup(db, orch, tmp_path, n=1)
    (c,) = claim(db, s, "w1")
    queue.write_result(db, c.id, c.attempt, ingest_result(orch, c))
    ren = db.execute(text("SELECT id FROM kb.rendition")).scalar_one()
    # a second task, on the rendition, with a span draft and a measurement
    m09 = s.w.registry.method("extract.math")
    rc = runs.create_run  # unused: the run's recorded configuration is read below
    del rc
    config = db.execute(
        text(
            "SELECT c.id FROM ops.method_config c JOIN ops.method m ON m.id = "
            "c.method_id WHERE m.name = 'extract.math'"
        )
    ).scalar_one()
    task = db.execute(
        text(
            "INSERT INTO ops.task (run_id, stage, unit_type, unit_id, "
            "method_config_id, input_hash, status, attempt) VALUES (:r, "
            "'normalize', 'rendition', :u, :c, 'h', 'running', 1) RETURNING id"
        ),
        {"r": s.run, "u": ren, "c": config},
    ).scalar_one()
    payload = MentionPayload.model_validate({"label": "L", "text": "X", "start": 0, "end": 3})
    result = UnitResult(
        ref=UnitRef(TaskUnitType.RENDITION, ren),
        outcome=ObservationOutcome.PRODUCED,
        observations=(
            ObservationDraft(
                kind=ObservationKind.MENTION,
                payload=payload,
                payload_class=MentionPayload,
                payload_version="1",
                rendition_id=ren,
                span=(0, 3),
            ),
        ),
        measurements=(
            MeasurementDraft(
                metric="math.count", scope_type=MeasurementScope.RENDITION, scope_id=ren, value=1.0
            ),
        ),
    )
    assert queue.write_result(db, task, 1, result) == "done"
    obs = db.execute(
        text(
            "SELECT o.span_id IS NOT NULL, p.kind FROM kb.observation o JOIN "
            "meta.payload_schema p ON p.id = o.payload_schema_id"
        )
    ).one()
    assert tuple(obs) == (True, "mention")
    measured = db.execute(text("SELECT task_id, metric FROM ops.measurement")).one()
    assert tuple(measured) == (task, "math.count")
    del m09


def test_transient_failures_retry_until_the_third_attempt(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    s = setup(db, orch, tmp_path, n=1)
    outcomes = []
    for holder in ("w1", "w2", "w3"):
        (c,) = claim(db, s, holder)
        outcomes.append(queue.retry_task(db, c.id, c.attempt, "serialization failure"))
    assert outcomes == [TaskStatus.PENDING, TaskStatus.PENDING, TaskStatus.FAILED]
    assert claim(db, s, "w4") == []


def test_settle_classifies_failures(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    with committing_db.begin() as conn:
        s = setup(conn, orch, tmp_path, n=3)
        claimed = claim(conn, s, "w1", 3)
    transient = psycopg.errors.SerializationFailure("could not serialize")
    assert queue.settle(committing_db, claimed[0], transient) == TaskStatus.PENDING
    assert queue.settle(committing_db, claimed[1], ValueError("a defect")) == TaskStatus.FAILED
    failed = UnitResult(
        ref=UnitRef(TaskUnitType.DOCUMENT, claimed[2].unit_id),
        outcome=ObservationOutcome.FAILED,
        error="unreadable",
    )
    assert queue.settle(committing_db, claimed[2], failed) == TaskStatus.FAILED
    with committing_db.connect() as conn:
        rows = queue.task_rows(conn, [c.id for c in claimed])
    assert [r.status for r in rows] == ["pending", "failed", "failed"]
    assert all(r.finished_at is not None for r in rows[1:])


def test_a_heartbeat_renews_held_leases(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    import time

    with committing_db.begin() as conn:
        s = setup(conn, orch, tmp_path, n=1)
        (c,) = claim(conn, s, "w1")
        conn.execute(
            text("UPDATE ops.task SET lease_until = now() + interval '1 second' WHERE id = :i"),
            {"i": c.id},
        )
    with queue.Heartbeat(committing_db, every=0.2) as beat:
        beat.held[c.id] = c.attempt
        time.sleep(0.6)
    with committing_db.connect() as conn:
        left: Any = conn.execute(
            text("SELECT lease_until - now() FROM ops.task WHERE id = :i"), {"i": c.id}
        ).scalar_one()
    assert left.total_seconds() > 200
