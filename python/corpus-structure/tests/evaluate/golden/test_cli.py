"""`ci golden split`, `create` and `status` through Typer's runner, stdout and stderr apart
(P0-E-1; evaluation §6)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Engine

from corpus_structure.cli import orchestrate as cli_orchestrate
from corpus_structure.orchestrate import phase0
from corpus_structure.settings import Settings


@pytest.fixture
def world(
    committing_db: Engine,
    gw: SimpleNamespace,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> SimpleNamespace:
    with committing_db.begin() as conn:
        w = gw.setup_world(conn, tmp_path)
        gw.ingest_run(conn, w, gw.spike_contents(w))

    @contextmanager
    def engine(settings: Any, timeout: float = 30.0) -> Iterator[Engine]:
        yield committing_db

    seams = {
        "registry_for": lambda root: w.registry,
        "graph": phase0.PHASE0,
        "domains": w.pack.parent,
        "run_pass": phase0.stub_pass,
        "evaluate": phase0.stub_evaluate,
    }
    monkeypatch.setattr(cli_orchestrate, "ENGINE", engine)
    monkeypatch.setattr(cli_orchestrate, "PHASE0", lambda: seams)
    url = committing_db.url.set(drivername="postgresql").render_as_string(hide_password=False)
    w.settings = lambda: Settings(database={"url": url})
    return w


def ci(cli: Any, w: SimpleNamespace, *args: str) -> Any:
    return cli("golden", *args, settings=w.settings)


def test_split_create_and_status(cli: Any, world: SimpleNamespace) -> None:
    split = ci(cli, world, "split", "--json")
    assert split.exit_code == 0, split.stderr
    assert json.loads(split.stdout)["added"] == {"dev": 4}
    created = ci(cli, world, "create", "--split", "dev", "--label", "p0", "--json")
    assert created.exit_code == 0, created.stderr
    made = json.loads(created.stdout)
    assert (made["units"], made["forced"], made["tasks"]) == (40, 13, 80)
    status = ci(cli, world, "status", "--label", "p0", "--json")
    assert status.exit_code == 0, status.stderr
    (one,) = json.loads(status.stdout)["sets"]
    assert one["units"] == {"draft": 40} and one["golden_run_status"] == "awaiting_agent"
    assert one["golden_run_id"] == made["golden_run_id"] and one["stale"] == []
    rendered = ci(cli, world, "status", "--label", "p0")
    assert rendered.exit_code == 0 and "golden set p0 (dev)" in rendered.stdout


def test_refusals_exit_1_with_the_reason_on_stderr(cli: Any, world: SimpleNamespace) -> None:
    ci(cli, world, "split")
    assert ci(cli, world, "create", "--split", "dev", "--label", "p0").exit_code == 0
    again = ci(cli, world, "create", "--split", "dev", "--label", "p0")
    assert again.exit_code == 1 and "labels are not reused" in again.stderr
    missing = ci(cli, world, "status", "--label", "nope")
    assert missing.exit_code == 1 and missing.stdout == ""
    assert "no golden set 'nope'" in missing.stderr
    sourceless = ci(cli, world, "create", "--split", "dev", "--label", "x", "--from-run", "99999")
    assert sourceless.exit_code == 1 and "no run 99999" in sourceless.stderr
