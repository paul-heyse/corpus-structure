"""`ingest.html` and `profile.segments` as registered methods under O1 (ingest and math §3.6, §5
P0-I-1b): `ci project init --domain statistics` over the vendored trace pages, then ingest-kind
runs through `commands.start_run` with phase 0's registry and graph, on a database clone.

The statistics pack is copied with its `methods.yaml` narrowed to the registered methods: its
`agent.opus` and `normalize.formula` configurations belong to methods not registered yet, and the
registry refuses a configuration of an unregistered method.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from sqlalchemy import Engine, text

from corpus_structure.cli import orchestrate as cli_orchestrate
from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import RunKind, RunStatus
from corpus_structure.ingest.profile import SOURCES_DIR
from corpus_structure.orchestrate import commands, phase0
from corpus_structure.orchestrate.registry import MethodRegistry, load_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.settings import Settings

REPO = Path(__file__).resolve().parents[4]
CORPUS = REPO / "fixtures/trace/corpus"
PAGES = 4
REGISTERED = {m.name for m in phase0.METHODS}


def write_methods(pack: Path, edit: Any = None) -> None:
    data = yaml.safe_load((DOMAINS / "statistics" / "methods.yaml").read_text(encoding="utf-8"))
    data["configs"] = {m: c for m, c in data["configs"].items() if m in REGISTERED}
    if edit is not None:
        edit(data)
    (pack / "methods.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


@pytest.fixture
def world(
    committing_db: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> SimpleNamespace:
    domains = tmp_path / "domains"
    pack = domains / "statistics"
    shutil.copytree(DOMAINS / "statistics", pack)
    write_methods(pack)

    @contextmanager
    def engine(settings: Any, timeout: float = 30.0) -> Iterator[Engine]:
        yield committing_db

    seams = {
        "registry_for": phase0.registry,
        "graph": phase0.PHASE0,
        "domains": domains,
        "run_pass": phase0.stub_pass,
        "evaluate": phase0.stub_evaluate,
    }
    monkeypatch.setattr(cli_orchestrate, "ENGINE", engine)
    monkeypatch.setattr(cli_orchestrate, "PHASE0", lambda: seams)
    url = committing_db.url.set(drivername="postgresql").render_as_string(hide_password=False)
    return SimpleNamespace(
        engine=committing_db,
        domains=domains,
        pack=pack,
        url=url,
        settings=lambda: Settings(database={"url": url}),
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )


def ingest_run(w: SimpleNamespace, registry_for: Any = phase0.registry) -> int:
    report = commands.start_run(
        w.engine,
        url=w.url,
        registry_for=registry_for,
        graph=phase0.PHASE0,
        run_pass=phase0.stub_pass,
        evaluate=phase0.stub_evaluate,
        kind=RunKind.INGEST,
        domains=w.domains,
        method_settings=w.method_settings,
    )
    assert report.status is RunStatus.FINISHED
    return report.run_id


def counts(w: SimpleNamespace) -> dict[str, int]:
    queries = {
        "renditions": "SELECT count(*) FROM kb.rendition",
        "builds": "SELECT count(*) FROM kb.rendition_build",
        "segments": "SELECT count(*) FROM kb.segment",
        "max_segment": "SELECT coalesce(max(id), 0) FROM kb.segment",
        "markup": "SELECT count(*) FROM kb.observation WHERE kind = 'author_markup'",
        "measurements": "SELECT count(*) FROM ops.measurement WHERE metric LIKE 'segment.%'",
    }
    with w.engine.connect() as conn:
        return {k: int(conn.execute(text(q)).scalar_one()) for k, q in queries.items()}


def tasks(w: SimpleNamespace, run_id: int) -> dict[str, list[str]]:
    with w.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT m.name, t.status FROM ops.task t JOIN ops.method_config c ON c.id = "
                "t.method_config_id JOIN ops.method m ON m.id = c.method_id WHERE t.run_id = :r "
                "ORDER BY t.id"
            ),
            {"r": run_id},
        )
        out: dict[str, list[str]] = {}
        for name, status in rows:
            out.setdefault(name, []).append(status)
        return out


def selected(w: SimpleNamespace, run_id: int) -> set[int]:
    with w.engine.connect() as conn:
        return set(
            conn.execute(
                text("SELECT rendition_id FROM kb.run_rendition WHERE run_id = :r"), {"r": run_id}
            ).scalars()
        )


def test_the_statistics_project_inits_and_ingest_runs_write_by_content(
    cli: Any, world: SimpleNamespace, tmp_path: Path
) -> None:
    w = world
    args = ["project", "init", "--domain", "statistics", "--corpus", str(CORPUS), "--json"]
    result = cli(*args, settings=w.settings)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["documents"] == PAGES

    # A first run: four renditions, their builds, segments, author markup and measurements.
    first = ingest_run(w)
    assert tasks(w, first) == {
        "ingest.html": ["done"] * PAGES,
        "profile.segments": ["empty"] * PAGES,
    }
    after_first = counts(w)
    assert (after_first["renditions"], after_first["builds"]) == (PAGES, PAGES)
    assert after_first["segments"] > 0 and after_first["markup"] > 0
    assert after_first["measurements"] > 0
    assert len(selected(w, first)) == PAGES
    with w.engine.connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM kb.rendition_build b JOIN meta.payload_schema p ON "
                    "p.id = b.payload_schema_id WHERE p.kind = 'parse_detail' AND "
                    "b.parse_detail ? 'encoding'"
                )
            ).scalar_one()
            == PAGES
        )
        # each synthesized claim names its enclosing unit by a segment key of its rendition
        missing = conn.execute(
            text(
                "SELECT count(*) FROM kb.observation o WHERE o.payload ? 'synthesize' AND NOT "
                "EXISTS (SELECT 1 FROM kb.segment s WHERE s.rendition_id = o.rendition_id AND "
                "s.kind = 'unit' AND s.key = o.payload->'value'->'unit'->>'segment')"
            )
        ).scalar_one()
        synthesized = conn.execute(
            text("SELECT count(*) FROM kb.observation WHERE payload ? 'synthesize'")
        ).scalar_one()
        assert synthesized > 0 and missing == 0
        # every markup value names a segment of its rendition
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM kb.observation o WHERE o.kind = 'author_markup' AND NOT "
                    "EXISTS (SELECT 1 FROM kb.segment s WHERE s.rendition_id = o.rendition_id AND "
                    "s.key = o.payload->'value'->>'segment')"
                )
            ).scalar_one()
            == 0
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM ops.measurement m JOIN kb.segment s ON s.id = m.scope_id "
                    "WHERE m.metric LIKE 'segment.%' AND s.key = m.scope_key"
                )
            ).scalar_one()
            == after_first["measurements"]
        )

    # A second run reuses every task and writes nothing.
    second = ingest_run(w)
    assert {s for v in tasks(w, second).values() for s in v} == {"reused"}
    assert counts(w) == after_first
    assert selected(w, second) == selected(w, first)

    # A changed configuration with identical content adds build rows and no segment.
    write_methods(
        w.pack, lambda d: d["configs"]["segment.sentences"]["default"].update(batch_size=8)
    )
    third = ingest_run(w)
    assert tasks(w, third)["ingest.html"] == ["done"] * PAGES
    after_third = counts(w)
    assert after_third["builds"] == 2 * PAGES
    assert {k: after_third[k] for k in ("renditions", "segments", "max_segment")} == {
        k: after_first[k] for k in ("renditions", "segments", "max_segment")
    }
    assert selected(w, third) == selected(w, first)

    # A profile change that alters the text adds a rendition beside the old one.
    sources = tmp_path / "sources"
    sources.mkdir()
    profile = yaml.safe_load((SOURCES_DIR / "siegrist.yaml").read_text(encoding="utf-8"))
    profile["references"]["render"] = "placeholder"
    (sources / "siegrist.yaml").write_text(yaml.safe_dump(profile), encoding="utf-8")

    def changed(pack: Path) -> MethodRegistry:
        return MethodRegistry(phase0.METHODS, load_methods(pack / "methods.yaml"), sources)

    fourth = ingest_run(w, changed)
    after_fourth = counts(w)
    assert after_fourth["renditions"] == 2 * PAGES
    assert after_fourth["segments"] > after_third["segments"]
    assert selected(w, fourth).isdisjoint(selected(w, first))
    assert selected(w, first) == selected(w, third)  # the earlier runs keep their renditions
    with w.engine.connect() as conn:
        texts = conn.execute(
            text("SELECT canonical_text FROM kb.rendition WHERE id = ANY(:i)"),
            {"i": sorted(selected(w, fourth))},
        ).scalars()
        assert all("[ref]" in t for t in texts)
