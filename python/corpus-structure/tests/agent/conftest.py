"""Agent-interface test support (agent interface §6, P0-A-1).

**The world** (on a committing clone): a project over the vendored trace pages with the
statistics pack and phase 0's registered methods (ingest, M09, M11, M13, M24, consolidation, M19);
a run with renditions, M09's mentions, M11's values, M13's scopes and M24 tasks for the five trace
units of `fixtures/s0`.
The stage runner creates every task, so M24's tasks carry their packet hashes exactly as in
production.

**The tools** are called through an in-process `Client(server)` on a `Session` the test holds, so
the lease, the served record and the caches persist across calls (`Tools.call`).

`importlib` import mode leaves this module unimportable from the tests; its parts are served by the
`agent` fixture.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anyio
import pytest
import yaml
from sqlalchemy import Connection, Engine, text

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef, RenditionContent, segment_key
from corpus_structure.core.method import (
    MethodSettings,
    UnitRef,
)
from corpus_structure.core.payloads import MentionPayload, ScopePayload
from corpus_structure.core.vocab import (
    RunKind,
    RunStatus,
    Stage,
)

REPO = Path(__file__).resolve().parents[4]
TRACE_CORPUS = REPO / "fixtures" / "trace" / "corpus"
S0 = REPO / "fixtures" / "s0"
STATISTICS = REPO / "domains" / "statistics"
ROOT = "siegrist_random/random"
TRACE_UNITS = ("T1-leadin", "T1-dfn1", "T2", "T3", "T4")
STATS_METHODS = yaml.safe_load((STATISTICS / "methods.yaml").read_text(encoding="utf-8"))
PACK_MACROS = {k: MacroDef(body=v) for k, v in STATS_METHODS["math"]["macros"].items()}


def s0(name: str) -> dict[str, Any]:
    return json.loads((S0 / f"{name}.json").read_text(encoding="utf-8"))


# --- In-memory analysis (the grammar runs here, in the test process's main thread) ---------------


@dataclass(frozen=True)
class Analysis:
    content: RenditionContent
    macros: dict[str, MacroDef]
    mentions: list[Any]
    scopes: list[Any]


_ANALYSES: dict[str, Analysis] = {}


def analyse(content: RenditionContent) -> Analysis:
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.math.scope import Binders, resolve_scopes
    from corpus_structure.methods.math.spans import extract, formula_values, read_spans

    key = content.canonical_text
    if key not in _ANALYSES:
        macros = tex.effective_macros(content.macros, PACK_MACROS)
        readings = read_spans(content, macros, tuple(STATS_METHODS["math"]["constants"]))
        extraction = extract(readings)
        scopes = resolve_scopes(
            content,
            formula_values(readings),
            extraction.mentions,
            extraction.relations,
            macros,
            Binders(**STATS_METHODS["binders"]),
            SentenceConfig(),
        )
        _ANALYSES[key] = Analysis(content, dict(macros), list(extraction.mentions), scopes)
    return _ANALYSES[key]


@cache
def page_content(page: str) -> RenditionContent:
    from corpus_structure.ingest.html import build_rendition
    from corpus_structure.ingest.profile import compile_profile, load_profile
    from corpus_structure.ingest.sentences import SentenceConfig

    source = f"{ROOT}/{page}"
    corpus = (
        TRACE_CORPUS if (TRACE_CORPUS / source).exists() else REPO / "docs/statistics_corpus/corpus"
    )
    raw = (corpus / source).read_bytes()
    profile = compile_profile(load_profile("siegrist"))
    return build_rendition(raw, profile, SentenceConfig(), source_uri=source).content


def _rendition(content: RenditionContent, rendition_key: str) -> Any:
    from corpus_structure.methods.math.methods import _Rendition

    keys = {segment_key(rendition_key, x.kind, x.start, x.end): i
            for i, x in enumerate(content.document.walk())}  # fmt: skip
    return _Rendition(0, rendition_key, "", content, keys)


def mention_payloads(content: RenditionContent, rendition_key: str) -> list[MentionPayload]:
    """M09's stored mentions, by I2b's own draft builder over the in-memory analysis."""
    from corpus_structure.methods.math.methods import math_drafts

    a = analyse(content)
    drafts = math_drafts(_rendition(content, rendition_key), a.mentions, ())
    return [d.payload for d in drafts if isinstance(d.payload, MentionPayload)]


def scope_payloads(
    content: RenditionContent, rendition_key: str, m09_task: int | None, ordinals: dict[Any, int]
) -> list[ScopePayload]:
    """M13's stored scopes, by I2b's own draft builder; `ordinals` maps a mention's (start, end)
    to its M09 ordinal."""
    from corpus_structure.core.payloads import MentionRef
    from corpus_structure.methods.math.methods import scope_drafts

    refs = {k: MentionRef(task=m09_task, ordinal=i) if m09_task is not None
            else MentionRef(ordinal=i) for k, i in ordinals.items()}  # fmt: skip
    drafts = scope_drafts(_rendition(content, rendition_key), analyse(content).scopes, refs)
    return [d.payload for d in drafts if isinstance(d.payload, ScopePayload)]


# --- The world ---------------------------------------------------------------------------------


def write_pack(root: Path, guideline: str | None = None) -> Path:
    """A copy of the statistics pack, its guideline optionally replaced."""
    pack = root / "statistics"
    shutil.copytree(STATISTICS, pack)
    if guideline is not None:
        (pack / "guideline.md").write_text(guideline, encoding="utf-8")
    return pack


def methods() -> list[Any]:
    """Phase 0's registered methods, with a fresh M24 (its caches are per instance)."""
    from corpus_structure.methods.llm.agent_opus import AgentOpus
    from corpus_structure.orchestrate.phase0 import METHODS

    return [AgentOpus() if m.name == "agent.opus" else m for m in METHODS]


def registry_for(pack: Path, registered: Sequence[Any] | None = None) -> Any:
    from corpus_structure.orchestrate.registry import MethodRegistry, load_methods

    return MethodRegistry(list(registered or methods()), load_methods(pack / "methods.yaml"))


def trace_unit_keys() -> list[str]:
    return [s0(name)["unit_key"] for name in TRACE_UNITS]


def build_world(
    engine: Engine, tmp: Path, guideline: str | None = None, units: Sequence[str] | None = None
) -> SimpleNamespace:
    from corpus_structure.orchestrate import project

    pack = write_pack(tmp / "domains", guideline)
    registry = registry_for(pack)
    with engine.begin() as conn:
        report = project.init_project(
            conn, domain="statistics", corpus=TRACE_CORPUS, registry=registry, domains=pack.parent
        )
        documents = [
            tuple(r)
            for r in conn.execute(
                text(
                    "SELECT key, content_hash FROM kb.document WHERE project_id = :p ORDER BY key"
                ),
                {"p": report.project_id},
            )
        ]
    w = SimpleNamespace(
        engine=engine,
        pack=pack,
        registry=registry,
        project_id=report.project_id,
        documents=documents,
        units=list(units or trace_unit_keys()),
        tmp=tmp,
    )
    w.url = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    return w


def start_run(w: SimpleNamespace, **explicit: Any) -> int:
    """A run through ingest, M09, M11, M13 and M24's task creation (not sealed)."""
    from corpus_structure.orchestrate import phase0, project, runs
    from corpus_structure.orchestrate.runner import Graph, Runner, Step

    with w.engine.begin() as conn:
        versions = project.ensure_pack_versions(conn, w.project_id, w.pack, "human:test")
        run = runs.create_run(
            conn,
            project_id=w.project_id,
            kind=RunKind.FULL,
            versions=versions,
            registry=w.registry,
            documents=w.documents,
            commit="t",
            explicit=explicit or None,
        ).id
        runs.transition(conn, run, [RunStatus.CREATED], RunStatus.RUNNING)

    def m24_units(conn: Connection, view: Any, cfg: Any) -> list[UnitRef]:
        method = w.registry.method("agent.opus")
        return [u for u in method.select(view, cfg) if u.unit_key in w.units]

    runner = Runner(
        w.engine,
        w.registry,
        Graph(()),
        phase0.stub_pass,
        None,
        MethodSettings(data_dir=w.tmp, model_cache=w.tmp),
    )
    for stage, step in (
        (Stage.INGEST, Step("ingest.html/default")),
        (Stage.NORMALIZE, Step("extract.math/default", upstream=("ingest.html",))),
        (Stage.NORMALIZE, Step("normalize.formula/default", upstream=("ingest.html",))),
        (
            Stage.SCOPE,
            Step("resolve.symbol_scope/default", upstream=("extract.math", "normalize.formula")),
        ),
        (Stage.PROPOSE, Step("agent.opus/extract", upstream=("ingest.html",), units=m24_units)),
    ):
        runner.step(run, stage, step)
    return run


@pytest.fixture(scope="module")
def world_engine(db_server: Any) -> Iterator[Engine]:
    with db_server.clone(f"ci_test_{os.getpid()}_agent_{id(object())}") as engine:
        yield engine


@pytest.fixture(scope="module")
def world(world_engine: Engine, tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    """A project with one run whose M24 tasks are the five trace units, per test module."""
    w = build_world(world_engine, tmp_path_factory.mktemp("agent"))
    w.run = start_run(w)
    return w


# --- The tools ---------------------------------------------------------------------------------


@dataclass
class Tools:
    """Calls the main profile's tools through an in-process client on one session."""

    server: Any
    session: Any

    def raw(self, name: str, **args: Any) -> Any:
        from fastmcp import Client

        async def main() -> Any:
            async with Client(self.server) as client:
                return await client.call_tool(name, args, raise_on_error=False)

        return anyio.run(main)

    def call(self, name: str, **args: Any) -> Any:
        result = self.raw(name, **args)
        if result.is_error:
            raise AssertionError(f"{name}: {result.content[0].text}")
        return result.structured_content if result.structured_content is not None else result.data

    def error(self, name: str, **args: Any) -> str:
        result = self.raw(name, **args)
        assert result.is_error, f"{name} succeeded: {result.structured_content}"
        return str(result.content[0].text)


def tools(engine: Engine, domains: Path | None = None) -> Tools:
    from corpus_structure.intervene.server import build_server
    from corpus_structure.intervene.service import Session

    session = Session(engine, domains=domains)
    return Tools(build_server(session), session)


@pytest.fixture
def agent() -> SimpleNamespace:
    return SimpleNamespace(
        s0=s0,
        TRACE_UNITS=TRACE_UNITS,
        page_content=page_content,
        analyse=analyse,
        mention_payloads=mention_payloads,
        scope_payloads=scope_payloads,
        build_world=build_world,
        start_run=start_run,
        tools=tools,
        write_pack=write_pack,
        registry_for=registry_for,
        methods=methods,
        PACK_MACROS=PACK_MACROS,
        STATISTICS=STATISTICS,
        REPO=REPO,
    )
