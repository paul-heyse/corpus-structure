"""Runs (P0-O-1, orchestration §3.4): what the insert records, options, the profile check, status
moves, cancelling and liveness."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url

from corpus_structure.core._model.revision import CONTENT_HASH, KEY_SCHEME
from corpus_structure.core.vocab import RunKind, RunStatus
from corpus_structure.orchestrate import runs
from corpus_structure.settings import Settings

REPO = Path(__file__).resolve().parents[4]


def make(db: Connection, w: SimpleNamespace, **kw: Any) -> runs.CreatedRun:
    return runs.create_run(
        db,
        project_id=w.project_id,
        kind=kw.pop("kind", RunKind.FULL),
        versions=w.versions,
        registry=w.registry,
        documents=w.documents,
        commit="test",
        **kw,
    )


def test_the_insert_records_the_reference_run_and_the_revisions(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = orch.setup_project(db, tmp_path)
    first = make(db, w)
    db.execute(
        text("UPDATE meta.project SET promoted_run_id = :r WHERE id = :p"),
        {"r": first.id, "p": w.project_id},
    )
    second = make(db, w)
    db.execute(
        text("UPDATE meta.project SET promoted_run_id = NULL WHERE id = :p"), {"p": w.project_id}
    )
    rows = {
        r.id: r
        for r in db.execute(
            text(
                "SELECT r.id, r.reference_run_id, r.key_scheme, r.schema_version_id, r.status, "
                "m.content_hash FROM ops.run r JOIN meta.model_revision m "
                "ON m.id = r.model_revision_id"
            )
        )
    }
    assert rows[first.id].reference_run_id is None
    assert rows[second.id].reference_run_id == first.id  # the pointer at insert, kept after
    assert rows[second.id].key_scheme == KEY_SCHEME
    assert rows[second.id].content_hash == CONTENT_HASH
    assert rows[second.id].schema_version_id == w.versions.schema_version_id
    assert rows[second.id].status == "created"
    assert not any(name.startswith(("set_reference", "update_reference")) for name in dir(runs))


def test_options_are_resolved_with_their_precedence_and_reread_unchanged(
    db: Connection, orch: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    w = orch.setup_project(db, tmp_path)
    assert make(db, w, settings=Settings()).options.sources["gpu_mode"] == "default"
    monkeypatch.setenv("CORPUS_GPU__MODE", "exclusive")
    by_setting = make(db, w, settings=Settings(), explicit={"agent_reuse": "by_unit"})
    assert by_setting.options.options.gpu_mode == "exclusive"
    assert by_setting.options.sources["gpu_mode"] == "setting"
    assert by_setting.options.options.agent_reuse == "by_unit"
    explicit = make(db, w, settings=Settings(), explicit={"gpu_mode": "co-resident"})
    assert explicit.options.options.gpu_mode == "co-resident"
    assert explicit.options.sources["gpu_mode"] == "option"
    monkeypatch.setenv("CORPUS_GPU__MODE", "auto")
    stored = runs.stored_options(db, by_setting.id)
    assert stored.gpu_mode == "exclusive" and stored.agent_reuse == "by_unit"  # not the env now
    raw = db.execute(text("SELECT options FROM ops.run WHERE id = :r"), {"r": explicit.id})
    assert set(raw.scalar_one()) == {
        "agent_mode",
        "agent_reuse",
        "gpu_mode",
        "corpus",
        "scope",
        "fresh",
        "configs",
        "method_configs",
    }
    assert stored.configs == {
        "ingest.html/default": by_setting.configs["ingest.html/default"].config_hash
    }


def test_agent_mode_defaults_by_kind_and_no_setting_supplies_it(
    db: Connection, orch: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    w = orch.setup_project(db, tmp_path)
    monkeypatch.setenv("CORPUS_AGENT_MODE", "wait")  # no such setting: it sets nothing
    assert make(db, w).options.options.agent_mode == "complete"
    assert make(db, w, kind=RunKind.SLICE).options.options.agent_mode == "wait"
    with pytest.raises(runs.RunError, match="refused in phase 0"):
        make(db, w, kind=RunKind.EXPERIMENT)


def test_the_corpus_hash_is_stable_for_equal_bytes_and_configuration(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = orch.setup_project(db, tmp_path)
    a, b = make(db, w), make(db, w)
    hashes = dict(db.execute(text("SELECT id, corpus_hash FROM ops.run")).all())
    assert hashes[a.id] == hashes[b.id]
    assert runs.corpus_hash(w.documents, ["cfg:x"]) != runs.corpus_hash(w.documents[1:], ["cfg:x"])
    assert runs.corpus_hash(w.documents, ["cfg:x"]) != runs.corpus_hash(w.documents, ["cfg:y"])


def test_a_profile_naming_a_kind_outside_the_schema_version_refuses_the_run(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    profile = (REPO / "sources" / "siegrist.yaml").read_text(encoding="utf-8")
    edited = profile.replace(
        '"p.math": {statement_kind: theorem}', '"p.math": {statement_kind: "minimal:koan"}'
    )
    assert edited != profile
    (sources / "siegrist.yaml").write_text(edited, encoding="utf-8")
    w = orch.setup_project(db, tmp_path, sources=sources)
    with pytest.raises(runs.ProfileRefused) as err:
        make(db, w)
    assert err.value.issues[0][:2] == ("siegrist", "unknown_statement_kind")
    assert "minimal:koan" in str(err.value) and "block_hints" in str(err.value)
    assert db.execute(text("SELECT count(*) FROM ops.run")).scalar_one() == 0
    assert db.execute(text("SELECT count(*) FROM ops.task")).scalar_one() == 0


def test_transitions_finish_and_cancel(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = orch.setup_project(db, tmp_path)
    run = make(db, w, kind=RunKind.INGEST).id
    runs.transition(db, run, [RunStatus.CREATED], RunStatus.RUNNING)
    with pytest.raises(runs.IllegalTransition, match="is running"):
        runs.transition(db, run, [RunStatus.CREATED], RunStatus.RUNNING)
    runs.finish_run(db, run)
    row = db.execute(
        text("SELECT status, cut_at, finished_at FROM ops.run WHERE id = :r"), {"r": run}
    ).one()
    assert row.status == "finished" and row.cut_at is not None and row.cut_at <= row.finished_at
    other = make(db, w).id
    db.execute(
        text(
            "INSERT INTO ops.task (run_id, stage, unit_type, method_config_id, input_hash, "
            "status) SELECT :r, 'ingest', 'document', id, 'i', 'pending' FROM "
            "ops.method_config LIMIT 1"
        ),
        {"r": other},
    )
    assert runs.cancel_run(db, other) == 1
    task = db.execute(
        text("SELECT status, reason FROM ops.task WHERE run_id = :r"), {"r": other}
    ).one()
    assert tuple(task) == ("cancelled", "run_cancelled")
    with pytest.raises(runs.IllegalTransition):
        runs.cancel_run(db, other)


def test_a_run_without_its_liveness_lock_is_orphaned(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    with committing_db.begin() as conn:
        w = orch.setup_project(conn, tmp_path)
        run = make(conn, w).id
        runs.transition(conn, run, [RunStatus.CREATED], RunStatus.RUNNING)
    url = make_url(committing_db.url).set(drivername="postgresql").render_as_string(False)
    lock = runs.Liveness(url, run)
    with committing_db.connect() as conn:
        assert run not in runs.orphaned(conn)
    lock.close()
    with committing_db.connect() as conn:
        assert runs.orphaned(conn) == [run]
    assert os.getpid()
