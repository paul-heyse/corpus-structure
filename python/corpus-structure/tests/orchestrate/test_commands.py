"""`ci project init`, `ci run`, `ci run cancel`, `ci status` and `ci tasks` (P0-O-1, orchestration
§3.13), through the Typer app on a clone, with the stub registry and graph in place of phase 0's."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, text

from corpus_structure.cli import orchestrate as cli_orchestrate
from corpus_structure.core.method import UnitRef, UnitResult, UnitView
from corpus_structure.core.vocab import (
    MethodFamily,
    ObservationOutcome,
    RunKind,
    RunStatus,
    Stage,
    TaskUnitType,
)
from corpus_structure.orchestrate import phase0, project, runs
from corpus_structure.orchestrate.registry import MethodRegistry, load_methods
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.settings import Settings

PARSE_DETAIL = (
    "INSERT INTO meta.payload_schema (model_revision_id, class, kind, version, "
    "compatibility_class, json_schema_id, arrow_schema, reason, authorized_by) SELECT id, "
    "'test:parse_detail', 'parse_detail', 1, 'initial', 'test', '', 'test', 'test' FROM "
    "meta.model_revision LIMIT 1 ON CONFLICT DO NOTHING"
)


def documents(conn: Connection, view: Any, cfg: Any) -> Iterable[UnitRef]:
    rows = conn.execute(
        text(
            "SELECT d.id, d.key FROM kb.document d JOIN ops.run r ON r.project_id = d.project_id "
            "WHERE r.id = :r AND d.key = ANY(:k) ORDER BY d.key"
        ),
        {"r": view.run_id, "k": list(view.options["corpus"]["documents"])},
    )
    return [UnitRef(TaskUnitType.DOCUMENT, int(r.id), str(r.key)) for r in rows]


@pytest.fixture
def world(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> SimpleNamespace:
    def ingest(unit: UnitView, cfg: Any, ctx: Any) -> UnitResult:
        return UnitResult(
            ref=unit.ref,
            outcome=ObservationOutcome.EMPTY,
            rendition=orch.page_content(str(unit.ref.unit_key)),
            parse_detail={"warnings": []},
        )

    stubs = [
        orch.ingest_stub(result=ingest),
        orch.Stub("consolidate.claims", TaskUnitType.RUN, MethodFamily.CONSOLIDATE),
        orch.Stub("validate.rules", TaskUnitType.RUN, MethodFamily.VALIDATE),
        orch.Stub("evaluate.score", TaskUnitType.RUN, MethodFamily.EVAL),
    ]
    pack = orch.write_pack(tmp_path / "domains")
    with committing_db.begin() as conn:
        conn.execute(text(PARSE_DETAIL))

    def registry_for(root: Path) -> MethodRegistry:
        return MethodRegistry(stubs, load_methods(root / "methods.yaml"))

    seams = {
        "registry_for": registry_for,
        "graph": Graph(((Stage.INGEST, (Step("ingest.html/default", units=documents),)),)),
        "domains": pack.parent,
        "run_pass": phase0.stub_pass,
        "evaluate": phase0.stub_evaluate,
    }

    @contextmanager
    def engine(settings: Any, timeout: float = 30.0) -> Iterator[Engine]:
        yield committing_db

    monkeypatch.setattr(cli_orchestrate, "ENGINE", engine)
    monkeypatch.setattr(cli_orchestrate, "PHASE0", lambda: seams)
    url = committing_db.url.set(drivername="postgresql").render_as_string(hide_password=False)
    return SimpleNamespace(
        engine=committing_db,
        pack=pack,
        registry_for=registry_for,
        settings=lambda: Settings(database={"url": url}),
        corpus=orch.CORPUS,
    )


def ci(cli: Any, w: SimpleNamespace, *args: str) -> Any:
    return cli(*args, settings=w.settings)


def init(cli: Any, w: SimpleNamespace, name: str | None = None) -> dict[str, Any]:
    args = ["project", "init", "--domain", "minimal", "--corpus", str(w.corpus), "--json"]
    result = ci(cli, w, *args, *(["--name", name] if name else []))
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def test_init_run_status_and_tasks(cli: Any, world: SimpleNamespace) -> None:
    made = init(cli, world)
    assert made["name"] == "minimal" and made["documents"] > 0
    assert init(cli, world)["documents_added"] == 0  # idempotent

    result = ci(cli, world, "run", "--json", "--gpu-mode", "exclusive", "--fresh", "ingest.html")
    assert result.exit_code == 0, result.output
    run = json.loads(result.stdout)
    assert run["status"] == "finished"
    assert run["options"]["sources"]["gpu_mode"] == "option"
    assert run["options"]["sources"]["agent_mode"] == "default"
    assert run["options"]["options"]["fresh"] == ["ingest.html"]

    status = json.loads(ci(cli, world, "status", "--json").stdout)
    progress = status["progress"]
    assert progress["run"]["run_id"] == run["run_id"] and progress["orphaned"] == []
    assert progress["run"]["cut_at"] is not None and progress["run"]["cut_m19_task_id"]
    ingest = [c for c in progress["run"]["stages"] if c["stage"] == "ingest"]
    assert ingest == [
        {"stage": "ingest", "status": "done", "reason": None, "count": made["documents"]}
    ]
    assert "database.url" in status["settings"]["resolved"]

    listing = json.loads(
        ci(cli, world, "tasks", "--json", "--status", "done", "--limit", "2").stdout
    )
    assert len(listing["tasks"]) == 2 and listing["total"] >= made["documents"]
    assert listing["tasks"][0]["config"] == "ingest.html/default"
    rendered = ci(cli, world, "tasks", "--limit", "1")
    assert rendered.exit_code == 0 and "more match" in rendered.stdout

    refused = ci(cli, world, "run", "cancel", str(run["run_id"]))
    assert refused.exit_code == 1 and "already over" in refused.stderr


def test_an_orphaned_run_is_reported_and_cancelled(cli: Any, world: SimpleNamespace) -> None:
    made = init(cli, world)
    with world.engine.begin() as conn:
        versions = project.ensure_pack_versions(conn, made["project_id"], world.pack, "human:t")
        docs = [tuple(r) for r in conn.execute(text("SELECT key, content_hash FROM kb.document"))]
        orphan = runs.create_run(
            conn,
            project_id=made["project_id"],
            kind=RunKind.FULL,
            versions=versions,
            registry=world.registry_for(world.pack),
            documents=docs,
            commit="t",
        ).id
        runs.transition(conn, orphan, [RunStatus.CREATED], RunStatus.RUNNING)  # no liveness lock
    status = json.loads(ci(cli, world, "status", str(orphan), "--json").stdout)
    assert status["progress"]["orphaned"] == [orphan]
    result = ci(cli, world, "run", "cancel", str(orphan), "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(ci(cli, world, "status", "--json").stdout)["progress"]["orphaned"] == []


def test_refusals_exit_1_with_the_reason(cli: Any, world: SimpleNamespace) -> None:
    none = ci(cli, world, "run")
    assert none.exit_code == 1 and "ci project init" in none.stderr
    init(cli, world)
    init(cli, world, name="second")
    two = ci(cli, world, "run")
    assert two.exit_code == 1 and "--project" in two.stderr
    missing = ci(cli, world, "status", "999999")
    assert missing.exit_code == 1 and "no run" in missing.stderr
