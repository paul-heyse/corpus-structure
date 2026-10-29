"""Phase 0's own registry and pack (orchestration §3.8, §3.13): the statistics pack inits through
`ci project init` with `phase0.registry`, and the real ingest step stores its author markup on the
segments it names (`value.segment` resolved to the stored segment's id by `queue.write_result`)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from corpus_structure.cli import orchestrate as cli_orchestrate
from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import RunKind, RunStatus, Stage
from corpus_structure.orchestrate import phase0, project, runs
from corpus_structure.orchestrate.runner import Graph, Runner, Step
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.settings import Settings

TRACE = Path(__file__).resolve().parents[4] / "fixtures" / "trace" / "corpus"


@pytest.fixture
def ci_on(committing_db: Engine, monkeypatch: pytest.MonkeyPatch) -> Any:
    @contextmanager
    def engine(settings: Any, timeout: float = 30.0) -> Iterator[Engine]:
        yield committing_db

    monkeypatch.setattr(cli_orchestrate, "ENGINE", engine)  # phase 0's own registry and domains
    url = committing_db.url.set(drivername="postgresql").render_as_string(hide_password=False)
    return lambda: Settings(database={"url": url})


def test_the_statistics_pack_inits_with_the_phase0_registry(
    cli: Any, ci_on: Any, committing_db: Engine, tmp_path: Path
) -> None:
    result = cli(
        "project",
        "init",
        "--domain",
        "statistics",
        "--corpus",
        str(TRACE),
        "--json",
        settings=ci_on,
    )
    assert result.exit_code == 0, result.output
    made = json.loads(result.stdout)
    assert made["documents"] == 4 and made["profiles"] == ["siegrist"]

    # the real ingest step over the trace pages: its markup lies on the segments it names
    registry = phase0.registry(DOMAINS / "statistics")
    with committing_db.begin() as conn:
        versions = project.ensure_pack_versions(
            conn, made["project_id"], DOMAINS / "statistics", "human:test"
        )
        documents = [
            tuple(r)
            for r in conn.execute(text("SELECT key, content_hash FROM kb.document ORDER BY key"))
        ]
        run = runs.create_run(
            conn,
            project_id=made["project_id"],
            kind=RunKind.FULL,
            versions=versions,
            registry=registry,
            documents=documents,
            commit="t",
        ).id
        runs.transition(conn, run, [RunStatus.CREATED], RunStatus.RUNNING)
    runner = Runner(
        committing_db,
        registry,
        Graph(()),
        phase0.stub_pass,
        None,
        MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    runner.step(run, Stage.INGEST, Step("ingest.html/default"))
    with committing_db.connect() as conn:
        statuses = conn.execute(
            text("SELECT status, count(*) FROM ops.task WHERE run_id = :r GROUP BY 1"), {"r": run}
        ).all()
        assert dict(statuses) == {"done": 4}
        rows = conn.execute(
            text(
                "SELECT o.segment_id, o.payload -> 'value' ->> 'segment' AS named, s.key "
                "FROM kb.observation o LEFT JOIN kb.segment s ON s.id = o.segment_id "
                "WHERE o.kind = 'author_markup'"
            )
        ).all()
    assert rows and all(r.segment_id is not None and r.key == r.named for r in rows)


def test_a_real_run_passes_through_consolidation_with_the_registered_config(
    committing_db: Engine, tmp_path: Path
) -> None:
    from corpus_structure.consolidate import pass_ as consolidate

    registry = phase0.registry(DOMAINS / "statistics")
    with committing_db.begin() as conn:
        made = project.init_project(conn, domain="statistics", corpus=TRACE, registry=registry)
        versions = project.ensure_pack_versions(
            conn, made.project_id, DOMAINS / "statistics", "human:test"
        )
        documents = [
            tuple(r)
            for r in conn.execute(text("SELECT key, content_hash FROM kb.document ORDER BY key"))
        ]
        run = runs.create_run(
            conn,
            project_id=made.project_id,
            kind=RunKind.FULL,
            versions=versions,
            registry=registry,
            documents=documents,
            commit="t",
        ).id
    calls: list[tuple[str, int | None]] = []

    def run_pass(conn: Any, run_id: int, pass_: str, m19: int | None) -> Any:
        calls.append((pass_, m19))
        return consolidate.run_pass(conn, run_id, pass_, m19)

    graph = Graph(((Stage.INGEST, (Step("ingest.html/default"),)),))
    runner = Runner(
        committing_db,
        registry,
        graph,
        run_pass,
        phase0.stub_evaluate,
        MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    assert runner.run(run) == RunStatus.FINISHED
    with committing_db.connect() as conn:
        m19 = conn.execute(
            text("SELECT cut_m19_task_id FROM ops.run WHERE id = :r"), {"r": run}
        ).scalar_one()
        assert calls == [("assemble", None), ("finalize", m19)]
        config = consolidate.config_of(conn, run, "finalize")
    assert config.aliases["articles"] == ["the", "a", "an"]
    assert len(config.math["macros"]) == 16 and config.engine == "duckdb"
